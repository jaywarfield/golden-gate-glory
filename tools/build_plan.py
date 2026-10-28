# tools/build_plan.py
# Mission Veteran AI by G3
# Tools: analyze_job_description, build_resume_draft, evaluate_export_gate
#
# Three-tool pipeline:
#   1. analyze_job_description  — extract required skills/keywords from a JD
#   2. build_resume_draft       — produce an evidence-tagged resume draft
#   3. evaluate_export_gate     — block export until all tags are resolved

import json
import os
import time

from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

from shared._common import contains_pii, pii_warning_message, get_credentials
from shared.governance import log_inference, get_subscription_ids

from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission

_MODEL_ID = "ibm/granite-4-h-small"


def _client() -> APIClient:
    creds = get_credentials()
    return APIClient(
        credentials=Credentials(url=creds["url"], api_key=creds["api_key"]),
        project_id=creds["project_id"],
    )


def _model(client: APIClient) -> ModelInference:
    return ModelInference(
        model_id=_MODEL_ID,
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

    t0 = time.monotonic()
    try:
        raw = _model(_client()).generate_text(prompt=prompt).strip()
        latency_ms = (time.monotonic() - t0) * 1000
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())
        result["pii_warning"] = None
        result["error"] = None

        # ── Governance: log inference fact ────────────────────────────────
        subs = get_subscription_ids()
        log_inference(
            tool_name="analyze_job_description",
            model_id=_MODEL_ID,
            prompt=prompt,
            response=raw,
            input_data={"jd_length": len(job_description)},
            output_data={
                "role_level": result.get("role_level"),
                "industry": result.get("industry"),
                "required_skill_count": len(result.get("required_skills", [])),
                "error": None,
            },
            subscription_id=subs.get("analyze_job_description"),
            latency_ms=latency_ms,
        )

        return result
    except Exception as exc:
        log_inference(
            tool_name="analyze_job_description",
            model_id=_MODEL_ID,
            prompt=prompt,
            response="",
            input_data={"jd_length": len(job_description)},
            output_data={"error": str(exc)},
            subscription_id=get_subscription_ids().get("analyze_job_description"),
            latency_ms=(time.monotonic() - t0) * 1000,
        )
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

    # ── Context block reused by both the draft prompt and grounding check ───
    context_block = (
        f"Service branch: {service_branch}\n"
        f"Specialty code: {specialty_code}\n"
        f"Service summary: {service_summary}\n"
        f"Translated bullets: {translated_bullets_json}\n"
        f"Skill inventory: {skill_inventory_json}\n"
        f"Job analysis: {job_analysis_json}"
    )

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

{context_block}

JSON object:"""

    t0_draft = time.monotonic()
    try:
        raw = _model(_client()).generate_text(prompt=prompt).strip()
        latency_ms_draft = (time.monotonic() - t0_draft) * 1000
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        sections = json.loads(raw.strip())

        # ── Grounding check: verify every EVIDENCED tag ────────────────────
        # Build a flat list of all EVIDENCED items for the check prompt.
        evidenced_items = [
            {"section": section, "index": i, "text": item["text"]}
            for section, items in sections.items()
            for i, item in enumerate(items)
            if item.get("tag") == "EVIDENCED"
        ]

        grounding_warnings = []

        if evidenced_items:
            check_prompt = f"""You are a strict fact-checker for veteran resumes.

Below is the ORIGINAL SOURCE CONTEXT that a resume was built from, followed by a list
of resume items that were tagged [EVIDENCED] — meaning they must be DIRECTLY supported
by the source context.

For each item, respond ONLY with a JSON array. Each element must have:
  "index":    the same integer index provided in the input
  "section":  the same section name provided in the input
  "verdict":  "CONFIRMED" if the text is directly supported by the source context,
              or "DOWNGRADE" if it adds, inflates, or implies anything not present
  "reason":   one sentence explaining a DOWNGRADE, or "" for CONFIRMED

SOURCE CONTEXT:
{context_block}

EVIDENCED ITEMS TO CHECK:
{json.dumps(evidenced_items, indent=2)}

JSON array:"""

            t0_check = time.monotonic()
            check_raw = _model(_client()).generate_text(prompt=check_prompt).strip()
            latency_ms_check = (time.monotonic() - t0_check) * 1000

            if check_raw.startswith("```"):
                check_raw = check_raw.split("```")[1]
                if check_raw.startswith("json"):
                    check_raw = check_raw[4:]

            try:
                verdicts = json.loads(check_raw.strip())
            except Exception:
                verdicts = []

            # Apply downgrades directly to the sections dict
            for v in verdicts:
                if v.get("verdict") == "DOWNGRADE":
                    sec = v.get("section")
                    idx = v.get("index")
                    reason = v.get("reason", "")
                    if sec in sections and isinstance(idx, int) and idx < len(sections[sec]):
                        sections[sec][idx]["tag"] = "INFERRED"
                        grounding_warnings.append({
                            "section": sec,
                            "text": sections[sec][idx]["text"],
                            "reason": reason,
                        })
        else:
            latency_ms_check = 0.0

        # Count tags across all sections (after any grounding downgrades)
        evidenced = inferred = missing = 0
        for items in sections.values():
            for item in items:
                tag = item.get("tag", "")
                if tag == "EVIDENCED":
                    evidenced += 1
                elif tag == "INFERRED":
                    inferred += 1
                elif tag == "MISSING":
                    missing += 1

        result = {
            "resume_sections": sections,
            "evidenced_count": evidenced,
            "inferred_count": inferred,
            "missing_count": missing,
            "grounding_warnings": grounding_warnings,
            "disclaimer": (
                "DRAFT – Review before use. Confirm every claim against your "
                "service record before submitting to an employer. "
                "INFERRED and MISSING items require your review and resolution. "
                + (
                    f"{len(grounding_warnings)} item(s) were automatically downgraded "
                    "from EVIDENCED to INFERRED by the grounding check — "
                    "review these carefully."
                    if grounding_warnings else
                    "All EVIDENCED items passed the grounding check."
                )
            ),
            "pii_warning": None,
            "error": None,
        }

        # ── Governance: log inference fact ────────────────────────────────
        subs = get_subscription_ids()
        log_inference(
            tool_name="build_resume_draft",
            model_id=_MODEL_ID,
            prompt=prompt,
            response=raw,
            input_data={"service_branch": service_branch},
            output_data={
                "evidenced_count": evidenced,
                "inferred_count": inferred,
                "missing_count": missing,
                "grounding_downgrade_count": len(grounding_warnings),
                "error": None,
            },
            subscription_id=subs.get("build_resume_draft"),
            latency_ms=latency_ms_draft + latency_ms_check,
            metadata={"fairness_attribute_service_branch": service_branch},
        )

        return result

    except Exception as exc:
        log_inference(
            tool_name="build_resume_draft",
            model_id=_MODEL_ID,
            prompt=prompt,
            response="",
            input_data={"service_branch": service_branch},
            output_data={"evidenced_count": 0, "inferred_count": 0, "missing_count": 0, "error": str(exc)},
            subscription_id=get_subscription_ids().get("build_resume_draft"),
            latency_ms=(time.monotonic() - t0_draft) * 1000,
            metadata={"fairness_attribute_service_branch": service_branch},
        )
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
    grounding_downgrade_count: int = 0,
    gate_holds_json: str = "[]",
) -> dict:
    """
    Evaluate whether a resume draft is cleared for export.

    Export is BLOCKED if any of the following remain unresolved:
      - INFERRED-tagged items (including items downgraded by the grounding check)
      - MISSING-tagged items
      - Any explicit holds passed by the caller

    Args:
        inferred_count: Number of INFERRED-tagged items remaining in the draft
                        (includes items the grounding check downgraded from EVIDENCED).
        missing_count: Number of MISSING-tagged items in the draft.
        grounding_downgrade_count: Number of items the automated grounding check
                                   downgraded from EVIDENCED to INFERRED.
                                   These are surfaced as a distinct hold so the
                                   veteran knows they require extra scrutiny.
        gate_holds_json: Optional JSON array of specific hold descriptions
                         from the resume draft review.

    Returns:
        A dict with keys: gate_status ("OPEN" or "BLOCKED"),
        holds (list of blocking issues), grounding_downgrade_count, message.
    """
    holds = []

    try:
        explicit_holds = json.loads(gate_holds_json) if gate_holds_json.strip() else []
    except Exception:
        explicit_holds = []

    # Grounding downgrades are surfaced first — they are the most actionable
    # because the veteran can see exactly which claim was questioned and why.
    if grounding_downgrade_count > 0:
        holds.append(
            f"{grounding_downgrade_count} item(s) were downgraded from EVIDENCED to INFERRED "
            "by the automated grounding check. Review the 'grounding_warnings' list in the "
            "resume draft and confirm or correct each item before export."
        )

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
            "grounding_downgrade_count": grounding_downgrade_count,
            "message": (
                "Export is BLOCKED. Resolve all holds listed above before "
                "this document may be shared with an employer. "
                "Pay particular attention to any grounding-check warnings — "
                "these indicate claims the AI could not confirm against your "
                "provided service record."
            ),
        }

    return {
        "gate_status": "OPEN",
        "holds": [],
        "grounding_downgrade_count": grounding_downgrade_count,
        "message": (
            "Export gate OPEN. All resume items are EVIDENCED and passed the "
            "automated grounding check. "
            "Final human review by the veteran is still required before submission "
            "to an employer. Confirm every claim against your service record."
        ),
    }
