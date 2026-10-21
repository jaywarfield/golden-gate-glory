# toolkits/skill_mapper/map_military_skills.py
# Mission Veteran AI
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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

from shared._common import (
    contains_pii, pii_warning_message, get_credentials,
    lookup_crosswalk, load_onet_occupation_skills,
)

from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission


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

Given the military background and O*NET grounding data below, identify the civilian skills
this veteran has demonstrated. Return ONLY a valid JSON array.
Each element must have exactly two keys: "skill" and "category".
Categories must be one of: Leadership, Technical, Operations, Communication, Analytical.
List 8-15 distinct skills. Prefer skills that appear in the O*NET required skills list.
No preamble, no explanation, no markdown fences.

Service branch: {service_branch}
Specialty code: {specialty_code}
Target career path: {target_career_path}
{crosswalk_context}
{onet_context}
Service summary:
{service_summary}

JSON array:"""

    try:
        model = ModelInference(
            model_id="ibm/granite-4-h-small",
            api_client=client,
            params={
                GenParams.MAX_NEW_TOKENS: 600,
                GenParams.TEMPERATURE: 0.2,
            },
        )
        raw = model.generate_text(prompt=prompt).strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        skills = json.loads(raw.strip())

        return {
            "skills": skills,
            "skill_count": len(skills),
            "onet_soc": onet_soc,
            "civilian_title": civilian_title,
            "onet_required_skills": onet_required,
            "disclaimer": (
                "DRAFT – Review before use. Confirm every skill claim against "
                "your service record before submitting to an employer. "
                "Grounded by O*NET Military Crosswalk and O*NET Occupation Skills."
            ),
            "pii_warning": None,
            "error": None,
        }
    except Exception as exc:
        return {
            "skills": None, "skill_count": 0,
            "onet_soc": onet_soc, "civilian_title": civilian_title,
            "onet_required_skills": onet_required,
            "disclaimer": None, "pii_warning": None, "error": str(exc),
        }
