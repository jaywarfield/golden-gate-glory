# toolkits/gap_analyzer/analyze_skills_gap.py
# Mission Veteran AI
# Toolkit: gap_analyzer
# Tool: analyze_skills_gap
#
# Compares a veteran's skill inventory against the target job description,
# identifies gaps, and recommends:
#   - IBM SkillsBuild courses (local KB)
#   - DoD SkillBridge programs (local KB)
# Grounded by: IBM SkillsBuild Course Catalog + DoD SkillBridge Program List

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

from shared._common import (
    contains_pii, pii_warning_message, get_credentials,
    lookup_skillsbuild, lookup_skillbridge,
)

from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission


@tool(permission=ToolPermission.READ_ONLY)
def analyze_skills_gap(
    veteran_skills_json: str,
    target_career_path: str,
    job_description: str,
) -> dict:
    """
    Compare a veteran's skill inventory against a target job description,
    identify covered and gap skills, and recommend IBM SkillsBuild courses
    and DoD SkillBridge programs from local knowledge bases.

    Args:
        veteran_skills_json: JSON string — the skills array returned by map_military_skills.
        target_career_path: One of: Project Management, Operations,
                            IT/Cybersecurity, Logistics.
        job_description: Full text of the civilian job posting (PII-free).

    Returns:
        A dict with keys: covered_skills, gap_skills, coverage_pct,
        skillsbuild_recommendations, skillbridge_programs,
        disclaimer, pii_warning (if any), error (if any).
    """
    if contains_pii(job_description):
        return {
            "covered_skills": None, "gap_skills": None, "coverage_pct": 0,
            "skillsbuild_recommendations": None, "skillbridge_programs": None,
            "disclaimer": None, "pii_warning": pii_warning_message(), "error": None,
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
  "coverage_pct": integer 0-100 representing percentage of JD skills covered.
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
                GenParams.MAX_NEW_TOKENS: 600,
                GenParams.TEMPERATURE: 0.2,
            },
        )
        raw = model.generate_text(prompt=prompt).strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())

        gap_skills = result.get("gap_skills", [])

        # ── KB-grounded course and program lookups ─────────────────────────
        skillsbuild = lookup_skillsbuild(target_career_path, gap_skills)
        skillbridge = lookup_skillbridge(target_career_path)

        return {
            "covered_skills": result.get("covered_skills", []),
            "gap_skills": gap_skills,
            "coverage_pct": result.get("coverage_pct", 0),
            "skillsbuild_recommendations": [
                {
                    "course_id": c["course_id"],
                    "course_title": c["title"],
                    "credential": c["credential"],
                    "estimated_hours": c["estimated_hours"],
                    "url": c["url"],
                    "skill_tags": c["skill_tags"],
                }
                for c in skillsbuild
            ],
            "skillbridge_programs": [
                {
                    "program_id": p["program_id"],
                    "organization": p["organization"],
                    "program_name": p["program_name"],
                    "duration_weeks": p["duration_weeks"],
                    "location_type": p["location_type"],
                    "url": p["url"],
                }
                for p in skillbridge
            ],
            "disclaimer": (
                "DRAFT – Review before use. "
                "IBM SkillsBuild course recommendations are sourced from the local "
                "knowledge base — verify availability at skillsbuild.org. "
                "DoD SkillBridge programs require command approval and separation "
                "timeline eligibility — verify at skillbridge.osd.mil."
            ),
            "pii_warning": None,
            "error": None,
        }

    except Exception as exc:
        return {
            "covered_skills": None, "gap_skills": None, "coverage_pct": 0,
            "skillsbuild_recommendations": None, "skillbridge_programs": None,
            "disclaimer": None, "pii_warning": None, "error": str(exc),
        }
