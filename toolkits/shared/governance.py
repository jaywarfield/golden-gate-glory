# toolkits/shared/governance.py
# Mission Veteran AI — a Golden Gate Glory project
# watsonx Governance — shared helper (no-op stub)
#
# Governance fact logging and monitor scoring are handled at the catalog level
# via governance/register_factsheets.py (FactSheetElements) — not at inference
# time via this file.
#
# ibm-aigov-facts-client==1.0.100 is an MLflow experiment-tracking client for
# watsonx.ai projects/spaces. It does not provide an inference-time payload
# logging or monitor scoring API compatible with the original OpenScale SDK
# this file was written against.
#
# All public functions here are intentional no-ops so that existing toolkit
# call sites continue to work without modification.
#
# To verify Governance connectivity:
#   export GOVERNANCE_INSTANCE_GUID=<guid-from-resource-list>
#   export GOVERNANCE_API_KEY=<your-ibm-cloud-api-key>  # defaults to WATSONX_API_KEY
#   make governance

import logging

logger = logging.getLogger(__name__)


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
    """No-op. Returns None. Inference logging is not supported by ibm-aigov-facts-client==1.0.100."""
    return None


def score_payload(
    *,
    subscription_id: str,
    input_data: dict,
    output_data: dict,
) -> dict | None:
    """No-op. Returns None. Monitor scoring is not supported by ibm-aigov-facts-client==1.0.100."""
    return None


def get_subscription_ids() -> dict:
    """Returns an empty dict. Subscription IDs are not used in ibm-aigov-facts-client==1.0.100."""
    return {}
