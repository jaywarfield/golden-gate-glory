"""
tools/phase1_tool.py
Golden Gate Glory – Veteran Career Navigator Agent
Phase 1: translate_bullet()

Translates a PII-free military accomplishment bullet into a civilian
ATS-ready resume bullet using IBM Granite via watsonx.ai.

Import into watsonx Orchestrate:
    orchestrate tools import -f tools/phase1_tool.py -k python

Environment variables required (set in .env or watsonx Orchestrate secrets):
    WATSONX_API_KEY   – your IBM Cloud API key
    WATSONX_URL       – watsonx.ai endpoint, e.g. https://us-south.ml.cloud.ibm.com
    WATSONX_PROJECT_ID – your watsonx.ai project ID
"""

from __future__ import annotations

import os
import re
import textwrap
from typing import Optional

from ibm_watsonx_orchestrate.agent_builder.tools import tool

# ---------------------------------------------------------------------------
# Lazy import: ibm-watsonx-ai is installed in the watsonx notebook environment.
# When running locally, install with:  pip install ibm-watsonx-ai python-dotenv
# ---------------------------------------------------------------------------
try:
    from ibm_watsonx_ai import APIClient, Credentials
    from ibm_watsonx_ai.foundation_models import ModelInference
    from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as Params
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "ibm-watsonx-ai is not installed. "
        "Run: pip install ibm-watsonx-ai"
    ) from exc

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODEL_ID = "ibm/granite-4-h-small"  # multitenant – Granite 4.0 Small, IBM indemnified

SYSTEM_PROMPT = textwrap.dedent("""\
    You are an expert U.S. military-to-civilian career transition writer.

    SCOPE: You translate PII-free military accomplishment bullets into
    civilian ATS-ready resume bullets. You do nothing else.

    RULES – follow every rule without exception:
    1. Use the X-Y-Z structure: accomplished X, measured by Y, by doing Z.
    2. Generate ONLY from the provided bullet and metrics. Do NOT invent,
       assume, or embellish any fact, number, credential, or outcome.
    3. Replace ALL military jargon (ranks, acronyms, unit names, mission
       terms) with plain civilian equivalents.
    4. If a required fact is missing, insert [MISSING: description] as a
       placeholder. Never fill a placeholder with invented content.
    5. Do NOT make hiring predictions, eligibility claims, benefit
       statements, or career guarantees.
    6. Output exactly one civilian resume bullet. No preamble, no
       explanation, no trailing commentary.

    DISCLAIMER (append verbatim after the bullet on a new line):
    ---
    DRAFT – Review before use. Confirm every claim. Remove any remaining
    jargon or sensitive detail before submitting to an employer.
""")

# ---------------------------------------------------------------------------
# Credential helper
# ---------------------------------------------------------------------------

def _get_credentials() -> Credentials:
    """
    Build Credentials from environment variables.
    Reads WATSONX_API_KEY and WATSONX_URL.
    Raises ValueError with a clear message if either is missing.
    """
    api_key = os.environ.get("WATSONX_API_KEY", "").strip()
    url = os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com").strip()

    if not api_key:
        raise ValueError(
            "WATSONX_API_KEY environment variable is not set. "
            "Set it in your .env file or watsonx Orchestrate secrets."
        )
    return Credentials(url=url, api_key=api_key)


# ---------------------------------------------------------------------------
# PII guard – lightweight check before sending to the model
# ---------------------------------------------------------------------------

_PII_PATTERNS = [
    (r"\b\d{3}-\d{2}-\d{4}\b",          "SSN pattern detected"),
    (r"\b\d{10}\b",                       "Possible DoD ID detected"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "Email address detected"),
    (r"\b\d{3}[\s.-]\d{3}[\s.-]\d{4}\b", "Phone number pattern detected"),
]

def _check_pii(text: str) -> Optional[str]:
    """Return a warning string if a PII pattern is detected, else None."""
    for pattern, label in _PII_PATTERNS:
        if re.search(pattern, text):
            return label
    return None


# ---------------------------------------------------------------------------
# Public tool function – imported by watsonx Orchestrate
# ---------------------------------------------------------------------------

@tool
def translate_bullet(
    bullet: str,
    target_role: str = "",
    metrics: str = "",
) -> dict:
    """
    Translate a PII-free military accomplishment bullet into a civilian ATS-ready resume bullet using IBM Granite via watsonx.ai.

    Args:
        bullet (str): A single PII-free military accomplishment bullet. Example: "Led a 12-person logistics team supporting time-sensitive operations across multiple sites."
        target_role (str): Optional civilian role or career path the veteran is targeting. Example: "Supply Chain Manager".
        metrics (str): Optional quantifiable metrics from the original record. Example: "Improved on-time delivery from 82% to 96%; managed $4.2M in equipment."

    Returns:
        dict: A dictionary containing translated_bullet (str), model_id (str), pii_warning (str), and error (str).
    """
    result: dict = {
        "translated_bullet": "",
        "model_id": MODEL_ID,
        "pii_warning": "",
        "error": "",
    }

    # -- PII guard --
    combined_input = f"{bullet} {metrics}"
    pii_flag = _check_pii(combined_input)
    if pii_flag:
        result["pii_warning"] = (
            f"PII CHECK: {pii_flag}. "
            "Remove sensitive information before submitting."
        )

    if not bullet.strip():
        result["error"] = "bullet is required and cannot be empty."
        return result

    # -- Build user prompt --
    role_line = f"TARGET ROLE: {target_role.strip()}\n" if target_role.strip() else ""
    metrics_line = f"METRICS: {metrics.strip()}\n" if metrics.strip() else ""
    user_prompt = (
        f"{role_line}"
        f"{metrics_line}"
        f"MILITARY BULLET: {bullet.strip()}\n\n"
        "CIVILIAN RESUME BULLET:"
    )

    # -- Call Granite --
    try:
        credentials = _get_credentials()
        project_id = os.environ.get("WATSONX_PROJECT_ID", "").strip()

        client = APIClient(credentials=credentials)

        model = ModelInference(
            model_id=MODEL_ID,
            api_client=client,
            project_id=project_id if project_id else None,
            params={
                Params.MAX_NEW_TOKENS: 300,
                Params.MIN_NEW_TOKENS: 20,
                Params.TEMPERATURE: 0.1,     # low temperature = consistent, grounded output
                Params.REPETITION_PENALTY: 1.1,
            },
        )

        # Granite 4.0 uses plain System:/User: format (no <|system|> tokens)
        response = model.generate(
            prompt=f"System:\n{SYSTEM_PROMPT}\nUser:\n{user_prompt}\nAssistant:\n",
        )

        generated = response["results"][0]["generated_text"].strip()
        result["translated_bullet"] = generated

    except Exception as exc:  # pylint: disable=broad-except
        result["error"] = f"Model call failed: {type(exc).__name__}: {exc}"

    return result
