# toolkits/shared/_common.py
# Mission Veteran AI
# Shared utilities — PII guard, credential helper, KB loader
# Used by all four toolkits.

import json
import os
import re

# ---------------------------------------------------------------------------
# PII guard
# ---------------------------------------------------------------------------

_PII_PATTERNS = [
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),               # SSN
    re.compile(r"\b\d{10}\b"),                            # DoD ID (10-digit)
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),  # email
    re.compile(r"\b(\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),  # phone
    re.compile(r"\b\d{1,5}\s+\w+\s+(Street|St|Avenue|Ave|Road|Rd|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct)\b", re.IGNORECASE),  # address
]


def contains_pii(text: str) -> bool:
    """Return True if text matches any known PII pattern."""
    for pattern in _PII_PATTERNS:
        if pattern.search(text):
            return True
    return False


def pii_warning_message() -> str:
    return (
        "PII detected in input. Please remove all full names, Social Security numbers, "
        "DoD ID numbers, phone numbers, email addresses, home addresses, birth dates, "
        "medical details, classified information, exact unit identifiers, and exact "
        "deployment locations before resubmitting."
    )


# ---------------------------------------------------------------------------
# Credential helper
# ---------------------------------------------------------------------------

def get_credentials() -> dict:
    """Return watsonx.ai credentials from environment variables."""
    return {
        "api_key": os.environ["WATSONX_API_KEY"],
        "url": os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com"),
        "project_id": os.environ["WATSONX_PROJECT_ID"],
    }


# ---------------------------------------------------------------------------
# Knowledge base loader
# ---------------------------------------------------------------------------

# Resolve the knowledge-bases/ directory relative to this file's location
# toolkits/shared/_common.py → ../../knowledge-bases/
_KB_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "knowledge-bases")
)


def _load_kb(filename: str) -> list:
    """Load a JSON knowledge base file. Returns [] on missing/error."""
    path = os.path.join(_KB_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def load_onet_crosswalk() -> list:
    """O*NET Military Occupational Crosswalk (MOS/AFSC → SOC codes)."""
    return _load_kb("onet_military_crosswalk.json")


def load_onet_occupation_skills() -> list:
    """O*NET occupation skill requirements by career path."""
    return _load_kb("onet_occupation_skills.json")


def load_skillsbuild_courses() -> list:
    """IBM SkillsBuild course catalog."""
    return _load_kb("skillsbuild_courses.json")


def load_skillbridge_programs() -> list:
    """DoD SkillBridge approved program list."""
    return _load_kb("skillbridge_programs.json")


def lookup_crosswalk(specialty_code: str, branch: str = "") -> list:
    """
    Return O*NET crosswalk entries matching a specialty code.
    Case-insensitive, branch optional.
    """
    code = specialty_code.strip().upper()
    branch_lower = branch.strip().lower()
    results = []
    for entry in load_onet_crosswalk():
        if entry.get("mos", "").upper() == code:
            if not branch_lower or entry.get("branch", "").lower() == branch_lower:
                results.append(entry)
    return results


def lookup_skillsbuild(career_path: str, gap_skills: list) -> list:
    """
    Return IBM SkillsBuild courses matching the career path and gap skills.
    Returns up to 5 most relevant courses.
    """
    career_path_lower = career_path.lower()
    gap_lower = [s.lower() for s in gap_skills]
    scored = []
    for course in load_skillsbuild_courses():
        if career_path not in course.get("career_paths", []):
            continue
        score = sum(
            1 for tag in course.get("skill_tags", [])
            if any(g in tag.lower() or tag.lower() in g for g in gap_lower)
        )
        scored.append((score, course))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:5]]


def lookup_skillbridge(career_path: str) -> list:
    """
    Return DoD SkillBridge programs matching the career path.
    Returns up to 5 programs.
    """
    return [
        p for p in load_skillbridge_programs()
        if career_path in p.get("career_fields", [])
    ][:5]
