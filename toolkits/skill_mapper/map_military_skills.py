# toolkits/skill_mapper/map_military_skills.py
# Mission Veteran AI
# Toolkit: skill_mapper
# Tool: map_military_skills
#
# Maps a veteran's military occupational specialty and service summary
# to a structured civilian skill inventory using IBM Granite.

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

from shared._common import contains_pii, pii_warning_message, get_credentials

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

    Args:
        service_branch: Military branch (e.g. "Army", "Navy", "Air Force").
        specialty_code: Occupational code (MOS, AFSC, rating, SFSC, or NEC).
        service_summary: 2–5 sentence PII-free description of duties and accomplishments.
        target_career_path: One of: Project Management, Operations,
                            IT/Cybersecurity, Logistics.

    Returns:
        A dict with keys: skills (list of dicts with skill + category), skill_count,
        disclaimer, pii_warning (if any), error (if any).
    """
    combined = f"{service_summary} {specialty_code}"
    if contains_pii(combined):
        return {
            "skills": None,
            "skill_count": 0,
            "disclaimer": None,
            "pii_warning": pii_warning_message(),
        }

    creds = get_credentials()
    client = APIClient(
        credentials=Credentials(url=creds["url"], api_key=creds["api_key"]),
        project_id=creds["project_id"],
    )

    prompt = f"""You are a veteran career transition expert.

Given the military background below, identify the civilian skills this veteran has demonstrated.
Return ONLY a valid JSON array. Each element must have exactly two keys: "skill" and "category".
Categories must be one of: Leadership, Technical, Operations, Communication, Analytical.
List 8–15 distinct skills. No preamble, no explanation, no markdown fences.

Service branch: {service_branch}
Specialty code: {specialty_code}
Target career path: {target_career_path}
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
        # Strip markdown fences if model adds them
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        skills = json.loads(raw.strip())

        return {
            "skills": skills,
            "skill_count": len(skills),
            "disclaimer": (
                "DRAFT – Review before use. Confirm every skill claim against "
                "your service record before submitting to an employer."
            ),
            "pii_warning": None,
            "error": None,
        }
    except Exception as exc:
        return {
            "skills": None,
            "skill_count": 0,
            "disclaimer": None,
            "pii_warning": None,
            "error": str(exc),
        }
