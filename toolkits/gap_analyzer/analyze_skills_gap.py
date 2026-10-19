# toolkits/gap_analyzer/analyze_skills_gap.py
# Mission Veteran AI
# Toolkit: gap_analyzer
# Tool: analyze_skills_gap
#
# Compares a veteran's skill inventory against the target job description,
# identifies gaps, and recommends free IBM SkillsBuild courses.

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
def analyze_skills_gap(
    veteran_skills_json: str,
    target_career_path: str,
    job_description: str,
) -> dict:
    """
    Compare a veteran's skill inventory against a target job description,
    identify covered and gap skills, and recommend IBM SkillsBuild courses.

    Args:
        veteran_skills_json: JSON string — the skills array returned by map_military_skills.
        target_career_path: One of: Project Management, Operations,
                            IT/Cybersecurity, Logistics.
        job_description: Full text of the civilian job posting (PII-free).

    Returns:
        A dict with keys: covered_skills, gap_skills, coverage_pct,
        skillsbuild_recommendations, disclaimer, pii_warning (if any), error (if any).
    """
    if contains_pii(job_description):
        return {
            "covered_skills": None,
            "gap_skills": None,
            "coverage_pct": 0,
            "skillsbuild_recommendations": None,
            "disclaimer": None,
            "pii_warning": pii_warning_message(),
        }

    creds = get_credentials()
    client = APIClient(
        credentials=Credentials(url=creds["url"], api_key=creds["api_key"]),
        project_id=creds["project_id"],
    )

    prompt = f"""You are a veteran career transition expert and skills gap analyst.

Given the veteran's skill inventory and the job description below, produce a gap analysis.
Return ONLY a valid JSON object with exactly these keys:
  "covered_skills": array of skill strings the veteran already has that match the JD,
  "gap_skills": array of skill strings required by the JD but not in the veteran's inventory,
  "coverage_pct": integer 0-100 representing percentage of JD skills covered,
  "skillsbuild_recommendations": array of objects with "course_title" and "url" keys,
    recommending 2–4 free IBM SkillsBuild courses that address the gap skills.
    Use real SkillsBuild course titles. URL format: https://skillsbuild.org/...
No preamble, no explanation, no markdown fences.

Target career path: {target_career_path}

Veteran skill inventory:
{veteran_skills_json}

Job description:
{job_description}

JSON object:"""

    try:
        model = ModelInference(
            model_id="ibm/granite-4-h-small",
            api_client=client,
            params={
                GenParams.MAX_NEW_TOKENS: 800,
                GenParams.TEMPERATURE: 0.2,
            },
        )
        raw = model.generate_text(prompt=prompt).strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())

        result["disclaimer"] = (
            "DRAFT – Review before use. SkillsBuild course recommendations are "
            "suggestions only. Verify availability at skillsbuild.org."
        )
        result["pii_warning"] = None
        result["error"] = None
        return result

    except Exception as exc:
        return {
            "covered_skills": None,
            "gap_skills": None,
            "coverage_pct": 0,
            "skillsbuild_recommendations": None,
            "disclaimer": None,
            "pii_warning": None,
            "error": str(exc),
        }
