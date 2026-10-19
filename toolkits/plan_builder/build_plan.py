# toolkits/plan_builder/build_plan.py
# Mission Veteran AI
# Toolkit: plan_builder
# Tools: analyze_job_description, build_resume_draft, evaluate_export_gate
#
# Three-tool pipeline:
#   1. analyze_job_description  — extract required skills/keywords from a JD
#   2. build_resume_draft       — produce an evidence-tagged resume draft
#   3. evaluate_export_gate     — block export until all tags are resolved

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

from shared._common import contains_pii, pii_warning_message, get_credentials

from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission


def _client() -> APIClient:
    creds = get_credentials()
    return APIClient(
        credentials=Credentials(url=creds["url"], api_key=creds["api_key"]),
        project_id=creds["project_id"],
    )


def _model(client: APIClient) -> ModelInference:
    return ModelInference(
        model_id="ibm/granite-4-h-small",
        api_client=client,
        params={
            GenParams.MAX_NEW_TOKENS: 800,
            GenParams.TEMPERATURE: 0.2,
        },
    )


# ---------------------------------------------------------------------------
# Tool 1 — analyze_job_description
# ---------------------------------------------------------------------------

@tool(permission=ToolPermission.READ_ONLY)
def analyze_job_description(job_description: str) -> dict:
    """
    Extract required skills, keywords, and role context from a civilian
    job description to guide resume tailoring.

    Args:
        job_description: Full text of the civilian job posting (PII-free).

    Returns:
        A dict with keys: required_skills, preferred_skills, keywords,
        role_level, industry, pii_warning (if any), error (if any).
    """
    if contains_pii(job_description):
        return {"error": None, "pii_warning": pii_warning_message()}

    prompt = f"""You are an expert job description analyst.

Analyse the job description below and return ONLY a valid JSON object with these keys:
  "required_skills": array of must-have skill strings,
  "preferred_skills": array of nice-to-have skill strings,
  "keywords": array of ATS keyword strings,
  "role_level": one of "Entry", "Mid", "Senior", "Manager", "Director",
  "industry": industry sector string (e.g. "Defense Contracting", "Technology").
No preamble, no explanation, no markdown fences.

Job description:
{job_description}

JSON object:"""

    try:
        raw = _model(_client()).generate_text(prompt=prompt).strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())
        result["pii_warning"] = None
        result["error"] = None
        return result
    except Exception as exc:
        return {"pii_warning": None, "error": str(exc)}


# ---------------------------------------------------------------------------
# Tool 2 — build_resume_draft
# ---------------------------------------------------------------------------

@tool(permission=ToolPermission.READ_ONLY)
def build_resume_draft(
    service_branch: str,
    specialty_code: str,
    service_summary: str,
    translated_bullets_json: str,
    skill_inventory_json: str,
    job_analysis_json: str,
) -> dict:
    """
    Build an evidence-tagged resume draft. Every sentence is tagged:
    EVIDENCED (from provided inputs), INFERRED (LLM inference), or
    MISSING (required by JD but absent from inputs).

    Args:
        service_branch: Military branch (e.g. "Army").
        specialty_code: Occupational code (MOS/AFSC/rating/etc.).
        service_summary: 2–5 sentence PII-free service description.
        translated_bullets_json: JSON array from translate_bullet calls.
        skill_inventory_json: JSON array from map_military_skills.
        job_analysis_json: JSON object from analyze_job_description.

    Returns:
        A dict with keys: resume_sections (dict of section → tagged lines),
        inferred_count, missing_count, evidenced_count,
        disclaimer, pii_warning (if any), error (if any).
    """
    combined = f"{service_summary} {service_branch}"
    if contains_pii(combined):
        return {"resume_sections": None, "pii_warning": pii_warning_message()}

    prompt = f"""You are an expert veteran resume writer.

Using ONLY the evidence below, produce a resume draft. Tag each bullet/sentence:
  [EVIDENCED] — directly supported by the inputs below
  [INFERRED]  — reasonable inference from the inputs (must be plausible, not invented)
  [MISSING]   — required by the JD but absent from inputs; write a placeholder

Return ONLY a valid JSON object with this structure:
{{
  "summary": [ {{"tag": "EVIDENCED|INFERRED|MISSING", "text": "..."}} ],
  "skills": [ {{"tag": "...", "text": "..."}} ],
  "experience": [ {{"tag": "...", "text": "..."}} ],
  "education_certifications": [ {{"tag": "...", "text": "..."}} ]
}}
No preamble, no markdown fences.

Service branch: {service_branch}
Specialty code: {specialty_code}
Service summary: {service_summary}
Translated bullets: {translated_bullets_json}
Skill inventory: {skill_inventory_json}
Job analysis: {job_analysis_json}

JSON object:"""

    try:
        raw = _model(_client()).generate_text(prompt=prompt).strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        sections = json.loads(raw.strip())

        # Count tags across all sections
        evidenced = inferred = missing = 0
        for items in sections.values():
            for item in items:
                t = item.get("tag", "")
                if t == "EVIDENCED":
                    evidenced += 1
                elif t == "INFERRED":
                    inferred += 1
                elif t == "MISSING":
                    missing += 1

        return {
            "resume_sections": sections,
            "evidenced_count": evidenced,
            "inferred_count": inferred,
            "missing_count": missing,
            "disclaimer": (
                "DRAFT – Review before use. Confirm every claim against your "
                "service record before submitting to an employer. "
                "INFERRED and MISSING items require your review and resolution."
            ),
            "pii_warning": None,
            "error": None,
        }
    except Exception as exc:
        return {
            "resume_sections": None,
            "evidenced_count": 0,
            "inferred_count": 0,
            "missing_count": 0,
            "disclaimer": None,
            "pii_warning": None,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Tool 3 — evaluate_export_gate
# ---------------------------------------------------------------------------

@tool(permission=ToolPermission.READ_ONLY)
def evaluate_export_gate(
    inferred_count: int,
    missing_count: int,
    gate_holds_json: str = "[]",
) -> dict:
    """
    Evaluate whether a resume draft is cleared for export.
    Export is BLOCKED if any INFERRED or MISSING tags remain unresolved.

    Args:
        inferred_count: Number of INFERRED-tagged items in the draft.
        missing_count: Number of MISSING-tagged items in the draft.
        gate_holds_json: Optional JSON array of specific hold descriptions
                         from the resume draft review.

    Returns:
        A dict with keys: gate_status ("OPEN" or "BLOCKED"),
        holds (list of blocking issues), message.
    """
    holds = []

    try:
        explicit_holds = json.loads(gate_holds_json) if gate_holds_json.strip() else []
    except Exception:
        explicit_holds = []

    if inferred_count > 0:
        holds.append(
            f"{inferred_count} INFERRED item(s) must be confirmed or corrected by the veteran."
        )
    if missing_count > 0:
        holds.append(
            f"{missing_count} MISSING item(s) must be supplied by the veteran before export."
        )
    holds.extend(explicit_holds)

    if holds:
        return {
            "gate_status": "BLOCKED",
            "holds": holds,
            "message": (
                "Export is BLOCKED. Resolve all holds listed above before "
                "this document may be shared with an employer."
            ),
        }

    return {
        "gate_status": "OPEN",
        "holds": [],
        "message": (
            "Export gate OPEN. All resume items are EVIDENCED. "
            "Final review by the veteran is still required before submission."
        ),
    }
