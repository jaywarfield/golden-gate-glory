# toolkits/shared/_common.py
# Mission Veteran AI — a Golden Gate Glory project
# Shared utilities — PII guard, credential helper, KB loader
# Used by all four toolkits.

import json
import os
import re
import logging

logger = logging.getLogger(__name__)

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
    api_key = os.environ.get("WATSONX_API_KEY", "").strip()
    project_id = os.environ.get("WATSONX_PROJECT_ID", "").strip()
    url = os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com").strip()
    if not api_key:
        raise RuntimeError(
            "WATSONX_API_KEY environment variable is not set. "
            "Add it in Railway → Variables tab."
        )
    if not project_id:
        raise RuntimeError(
            "WATSONX_PROJECT_ID environment variable is not set. "
            "Add it in Railway → Variables tab."
        )
    # Validate URL looks sane before handing to SDK (avoids cryptic SDK error)
    if not url.startswith("https://"):
        raise RuntimeError(
            f"WATSONX_URL looks wrong: {url!r}. "
            "Expected: https://us-south.ml.cloud.ibm.com"
        )
    return {
        "api_key": api_key,
        "url": url,
        "project_id": project_id,
    }


# ---------------------------------------------------------------------------
# LLM JSON parser
# ---------------------------------------------------------------------------

def parse_llm_json(raw: str, tool_name: str = "") -> dict | list:
    """
    Parse a JSON string returned by an LLM.
    Handles empty responses, markdown fences, and leading/trailing text.
    Raises ValueError with a descriptive message on failure.
    """
    if not raw or not raw.strip():
        raise ValueError(
            f"LLM returned an empty response{' in ' + tool_name if tool_name else ''}. "
            "This can happen if the job description is too short, in an unsupported language, "
            "or if the model timed out. Please try again."
        )
    text = raw.strip()
    # Strip markdown fences: ```json ... ``` or ``` ... ```
    if text.startswith("```"):
        lines = text.splitlines()
        # drop first line (```json or ```) and last line (```)
        inner = lines[1:] if lines[-1].strip() == "```" else lines[1:]
        if inner and inner[-1].strip() == "```":
            inner = inner[:-1]
        text = "\n".join(inner).strip()
    # Find first { or [ in case model added preamble text
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        idx = text.find(start_char)
        if idx != -1:
            # find last matching close char
            end_idx = text.rfind(end_char)
            if end_idx > idx:
                text = text[idx:end_idx + 1]
                break
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        logger.warning("parse_llm_json failed for %s: %s | raw=%r", tool_name, exc, raw[:200])
        raise ValueError(
            f"Model returned invalid JSON{' in ' + tool_name if tool_name else ''}: {exc}. "
            f"Raw response started with: {raw[:100]!r}"
        )


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
