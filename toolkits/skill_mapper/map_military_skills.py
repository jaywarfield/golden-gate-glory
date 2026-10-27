# toolkits/skill_mapper/map_military_skills.py
# Mission Veteran AI — a Golden Gate Glory project
# Toolkit: skill_mapper
# Tool: map_military_skills
#
# Maps a veteran's MOS/AFSC/rating and service summary to a structured
# civilian skill inventory.
# Grounded by: O*NET Military Crosswalk + O*NET Occupation Skills (local KB)
# LLM: ibm/granite-4-h-small (expands beyond KB where evidence supports)

import json
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

from shared._common import (
    contains_pii, pii_warning_message, get_credentials,
    lookup_crosswalk, load_onet_occupation_skills,
)
from shared.governance import log_inference, get_subscription_ids

from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission

_MODEL_ID = "ibm/granite-4-h-small"


@tool(permission=ToolPermission.READ_ONLY)
def map_military_skills(
    service_branch: str,
    specialty_code: str,
    service_summary: str,
    target_career_path: str,
) -> dict:
    """
    Map a veteran's military occupational specialty and PII-free service summary
    to a structured civilian skill inventory.
    Grounded by O*NET Military Crosswalk and O*NET Occupation Skills knowledge bases.

    Args:
        service_branch: Military branch (e.g. "Army", "Navy", "Air Force").
        specialty_code: Occupational code (MOS, AFSC, rating, SFSC, or NEC).
        service_summary: 2-5 sentence PII-free description of duties and accomplishments.
        target_career_path: One of: Project Management, Operations,
                            IT/Cybersecurity, Logistics.

    Returns:
        A dict with keys: skills (list of {skill, category}), skill_count,
        onet_soc (if crosswalk hit), civilian_title (if crosswalk hit),
        disclaimer, pii_warning (if any), error (if any).
    """
    combined = f"{service_summary} {specialty_code}"
    if contains_pii(combined):
        return {
            "skills": None, "skill_count": 0, "disclaimer": None,
            "pii_warning": pii_warning_message(), "error": None,
        }

    # ── Step 1: O*NET crosswalk lookup ─────────────────────────────────────
    crosswalk_hits = lookup_crosswalk(specialty_code, service_branch)
    onet_soc = crosswalk_hits[0]["onet_soc"] if crosswalk_hits else None
    civilian_title = crosswalk_hits[0]["civilian_title"] if crosswalk_hits else None

    # ── Step 2: O*NET occupation skills for the target career path ──────────
    onet_skills = load_onet_occupation_skills()
    path_entry = next(
        (e for e in onet_skills if e.get("career_path") == target_career_path), None
    )
    onet_required = path_entry["required_skills"] if path_entry else []
    onet_activities = path_entry["work_activities"] if path_entry else []

    # ── Step 3: LLM expansion grounded by KB data ───────────────────────────
    creds = get_credentials()
    client = APIClient(
        credentials=Credentials(url=creds["url"], api_key=creds["api_key"]),
        project_id=creds["project_id"],
    )

    crosswalk_context = (
        f"O*NET crosswalk: {specialty_code} → {civilian_title} (SOC {onet_soc})"
        if onet_soc else "No direct O*NET crosswalk match found."
    )
    onet_context = (
        f"O*NET required skills for {target_career_path}: {', '.join(onet_required)}"
        if onet_required else ""
    )

    prompt = f"""You are a veteran career transition expert grounded in O*NET occupational data.

Your task: identify ONLY the civilian skills this veteran has DIRECTLY DEMONSTRATED based on
the service summary and O*NET crosswalk data provided below.

STRICT RULES — violation produces a fabricated resume:
1. ONLY include a skill if it is explicitly supported by a word, phrase, or statement
   in the service summary above. Do not infer skills from the MOS/AFSC code alone.
2. Do NOT add skills because they are common for this MOS/AFSC in general.
   If this veteran's summary does not mention it, do not include it.
3. Do NOT pad the list. If only 4 skills are directly supported, return 4.
   Quality and accuracy matter more than quantity.
4. Each skill MUST map to the O*NET required skills list when possible, but only if
   that skill is also evidenced in the service summary.

Return ONLY a valid JSON array. Each element must have exactly these keys:
  "skill"    — the civilian skill name (prefer O*NET vocabulary)
  "category" — one of: Leadership, Technical, Operations, Communication, Analytical
  "evidence" — a verbatim short quote (≤15 words) from the service summary that
               supports this skill, OR "O*NET crosswalk: <civilian_title>" if the
               skill derives from the crosswalk match and the summary supports the role.

No preamble, no explanation, no markdown fences.

Service branch: {service_branch}
Specialty code: {specialty_code}
Target career path: {target_career_path}
{crosswalk_context}
{onet_context}
Service summary:
{service_summary}

JSON array:"""

    t0 = time.monotonic()
    try:
        model = ModelInference(
            model_id=_MODEL_ID,
            api_client=client,
            params={
                GenParams.MAX_NEW_TOKENS: 600,
                GenParams.TEMPERATURE: 0.2,
            },
        )
        raw = model.generate_text(prompt=prompt).strip()
        latency_ms = (time.monotonic() - t0) * 1000
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        skills = json.loads(raw.strip())

        # Count how many skills have direct textual evidence vs crosswalk-only
        evidence_sourced = sum(
            1 for s in skills
            if isinstance(s.get("evidence"), str)
            and not s["evidence"].startswith("O*NET crosswalk:")
        )

        result = {
            "skills": skills,
            "skill_count": len(skills),
            "evidence_sourced_count": evidence_sourced,
            "onet_soc": onet_soc,
            "civilian_title": civilian_title,
            "onet_required_skills": onet_required,
            "disclaimer": (
                "DRAFT – Review before use. Confirm every skill claim against "
                "your service record before submitting to an employer. "
                "Each skill includes an 'evidence' quote from your service summary. "
                "Skills marked 'O*NET crosswalk' derive from your specialty code mapping — "
                "verify these reflect your actual duties. "
                "Grounded by O*NET Military Crosswalk and O*NET Occupation Skills."
            ),
            "pii_warning": None,
            "error": None,
        }

        # ── Governance: log inference fact ────────────────────────────────
        subs = get_subscription_ids()
        log_inference(
            tool_name="map_military_skills",
            model_id=_MODEL_ID,
            prompt=prompt,
            response=raw,
            input_data={
                "service_branch": service_branch,
                "target_career_path": target_career_path,
                "crosswalk_hit": onet_soc is not None,
            },
            output_data={
                "skill_count": len(skills),
                "evidence_sourced_count": evidence_sourced,
                "onet_soc": onet_soc,
                "error": None,
            },
            subscription_id=subs.get("map_military_skills"),
            latency_ms=latency_ms,
            metadata={"fairness_attribute_service_branch": service_branch},
        )

        return result

    except Exception as exc:
        log_inference(
            tool_name="map_military_skills",
            model_id=_MODEL_ID,
            prompt=prompt,
            response="",
            input_data={"service_branch": service_branch, "target_career_path": target_career_path},
            output_data={"skill_count": 0, "error": str(exc)},
            subscription_id=get_subscription_ids().get("map_military_skills"),
            latency_ms=(time.monotonic() - t0) * 1000,
            metadata={"fairness_attribute_service_branch": service_branch},
        )
        return {
            "skills": None, "skill_count": 0,
            "onet_soc": onet_soc, "civilian_title": civilian_title,
            "onet_required_skills": onet_required,
            "disclaimer": None, "pii_warning": None, "error": str(exc),
        }
