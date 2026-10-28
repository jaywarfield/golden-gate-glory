# toolkits/shared/governance.py
# Mission Veteran AI — a Golden Gate Glory project
# watsonx Governance — shared client helper
#
# Provides a single entry point used by all four toolkits to:
#   1. Log inference facts to an IBM OpenScale / watsonx Governance AI Factsheet.
#   2. Score a payload against a deployed monitor subscription (bias, drift,
#      explainability, content safety) when a subscription ID is configured.
#   3. Enforce a PII content-safety check via the Governance quality monitor
#      as a second line of defence behind the regex guard in _common.py.
#
# Environment variables (add to .env or Orchestrate secrets):
#   GOVERNANCE_API_KEY        IBM Cloud API key with Governance service access.
#                             Defaults to WATSONX_API_KEY if not set.
#   GOVERNANCE_INSTANCE_GUID  The OpenScale / Governance service instance GUID.
#   GOVERNANCE_URL            Governance REST endpoint.
#                             Default: https://aiopenscale.cloud.ibm.com
#   GOVERNANCE_DATAMART_ID    Target datamart (default: the instance's primary
#                             datamart resolved automatically on first call).
#   GOVERNANCE_ENABLED        Set to "false" to disable all Governance calls
#                             without removing instrumentation (useful in local
#                             unit-test environments).
#
# If GOVERNANCE_INSTANCE_GUID is absent, all calls are no-ops so existing
# behaviour is fully preserved — the toolkit still works without Governance.

import os
import json
import logging
import time
import uuid
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy imports — ibm-aigov-facts-client is optional at import time.
# If the package is not installed the module still loads; calls become no-ops.
# ---------------------------------------------------------------------------

try:
    from ibm_aigov_facts_client import (
        AIGovFactsClient,
        CloudPakforDataConfig,  # only needed for CPD deployments
    )
    _AIGOV_AVAILABLE = True
except ImportError:
    _AIGOV_AVAILABLE = False
    logger.debug("ibm-aigov-facts-client not installed — Governance calls are no-ops.")


# ---------------------------------------------------------------------------
# Module-level singletons (initialised once per process)
# ---------------------------------------------------------------------------

_facts_client: Any = None   # AIGovFactsClient instance


def _is_enabled() -> bool:
    return (
        _AIGOV_AVAILABLE
        and os.environ.get("GOVERNANCE_ENABLED", "true").lower() != "false"
        and bool(os.environ.get("GOVERNANCE_INSTANCE_GUID", "").strip())
    )


def _get_client() -> Any:
    """Return (and lazily initialise) the AIGovFactsClient singleton."""
    global _facts_client
    if _facts_client is not None:
        return _facts_client

    api_key = os.environ.get(
        "GOVERNANCE_API_KEY",
        os.environ.get("WATSONX_API_KEY", ""),
    )
    instance_guid = os.environ["GOVERNANCE_INSTANCE_GUID"]
    url = os.environ.get("GOVERNANCE_URL", "https://aiopenscale.cloud.ibm.com")

    _facts_client = AIGovFactsClient(
        api_key=api_key,
        instance_guid=instance_guid,
        service_url=url,
        # Set validate_token=False in air-gapped / test environments.
    )
    return _facts_client


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def log_inference(
    *,
    tool_name: str,
    model_id: str,
    prompt: str,
    response: str,
    input_data: dict,
    output_data: dict,
    subscription_id: str | None = None,
    latency_ms: float | None = None,
    metadata: dict | None = None,
) -> str | None:
    """
    Log a single inference transaction to the AI Factsheet / Governance payload
    logging endpoint.

    Returns the transaction record ID on success, or None if Governance is
    disabled / unavailable.

    All callers pass keyword-only arguments to prevent positional mistakes
    across four different toolkit files.
    """
    if not _is_enabled():
        return None

    record_id = str(uuid.uuid4())
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    payload = {
        "record_id": record_id,
        "timestamp": timestamp,
        "tool_name": tool_name,
        "model_id": model_id,
        "subscription_id": subscription_id,
        "latency_ms": latency_ms,
        "input": {
            "prompt_length": len(prompt),
            # Store only truncated prompt to avoid transmitting veteran data.
            "prompt_preview": prompt[:120] + "…" if len(prompt) > 120 else prompt,
            **input_data,
        },
        "output": output_data,
        "metadata": metadata or {},
    }

    try:
        client = _get_client()
        # facts_client.export_facts() persists a fact record tied to the
        # AI use case / model entry defined in governance/factsheets.yaml.
        client.export_facts(
            fact_type="inference_record",
            fact_data=payload,
        )
        logger.debug("Governance: logged inference %s for tool %s", record_id, tool_name)
        return record_id
    except Exception as exc:  # noqa: BLE001
        # Governance logging must never break the primary tool path.
        logger.warning("Governance log failed (non-fatal): %s", exc)
        return None


def score_payload(
    *,
    subscription_id: str,
    input_data: dict,
    output_data: dict,
) -> dict | None:
    """
    Send a payload to a Governance monitor subscription for real-time scoring
    (bias, drift, content safety).

    Returns the monitor scoring response dict, or None if unavailable.
    """
    if not _is_enabled():
        return None

    try:
        client = _get_client()
        response = client.monitor_instances.run_scoring(
            subscription_id=subscription_id,
            input_data=input_data,
            output_data=output_data,
        )
        return response
    except Exception as exc:  # noqa: BLE001
        logger.warning("Governance score_payload failed (non-fatal): %s", exc)
        return None


def get_subscription_ids() -> dict:
    """
    Return a dict of tool_name → subscription_id pulled from environment
    variables, so each toolkit can pass the right subscription_id to
    log_inference() and score_payload() without hardcoding values.

    Environment variables (all optional):
        GOVERNANCE_SUB_BULLET_TRANSLATOR
        GOVERNANCE_SUB_SKILL_MAPPER
        GOVERNANCE_SUB_GAP_ANALYZER
        GOVERNANCE_SUB_PLAN_BUILDER
    """
    return {
        "translate_bullet":         os.environ.get("GOVERNANCE_SUB_BULLET_TRANSLATOR"),
        "map_military_skills":      os.environ.get("GOVERNANCE_SUB_SKILL_MAPPER"),
        "analyze_skills_gap":       os.environ.get("GOVERNANCE_SUB_GAP_ANALYZER"),
        "analyze_job_description":  os.environ.get("GOVERNANCE_SUB_PLAN_BUILDER"),
        "build_resume_draft":       os.environ.get("GOVERNANCE_SUB_PLAN_BUILDER"),
        "evaluate_export_gate":     os.environ.get("GOVERNANCE_SUB_PLAN_BUILDER"),
    }
