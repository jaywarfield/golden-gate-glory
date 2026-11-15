# toolkits/resume_parser/extract_resume_skills.py
# Mission Veteran AI by G3
# Tool: extract_resume_skills
#
# Uses IBM Granite to read the full resume text and extract a structured
# list of civilian skills directly evidenced in that text.
# Mirrors the pattern of analyze_job_description / map_military_skills.

import time

from shared._common import contains_pii, pii_warning_message, parse_llm_json, llm_generate
from shared.governance import log_inference, get_subscription_ids

try:
    from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
except ImportError:
    def tool(**_kw): return lambda f: f          # no-op decorator
    class ToolPermission: READ_ONLY = None       # noqa: E701

_MODEL_ID = "meta-llama/llama-3-1-8b-instruct"


@tool(permission=ToolPermission.READ_ONLY)
def extract_resume_skills(
    resume_text: str,
    service_branch: str = "",
    specialty_code: str = "",
) -> dict:
    """
    Extract civilian skills from a veteran's resume text using AI.

    Reads the full resume and returns ONLY skills that are explicitly
    evidenced in the text — not inferred from the specialty code alone.
    Every skill includes a short verbatim quote as evidence.

    Args:
        resume_text:    Full PII-free resume text.
        service_branch: Military branch (e.g. "Army") — context only.
        specialty_code: Occupational code (MOS/AFSC/rating) — context only.

    Returns:
        A dict with keys: skills (list of {skill_name, category, evidence}),
        skill_count, pii_warning (if any), error (if any).
    """
    if contains_pii(resume_text):
        return {
            "skills": None, "skill_count": 0,
            "pii_warning": pii_warning_message(), "error": None,
        }

    # Truncate to ~4000 chars to cap token usage on very long resumes
    resume_text = resume_text[:4000]

    prompt = f"""You are an expert civilian resume analyst for military veterans.

Read the resume below and extract ONLY the concrete civilian SKILLS that are
EXPLICITLY EVIDENCED in the text.

STRICT RULES — read each one carefully:
1. Source only: skills sections, certification lists, tools/technologies mentioned
   in experience bullets. Do NOT invent or infer skills not visible in the text.
2. Use standard civilian terminology (e.g. "Network Administration", not "DCGS comms").
3. Each skill_name MUST be a NOUN PHRASE — a thing you can have or know, not an action.
   These are WRONG (verb phrases / activities):
     "managed Active Directory user accounts"  → WRONG
     "troubleshooting computer hardware"       → WRONG
     "maintaining LAN/WAN connectivity"        → WRONG
   These are RIGHT (noun-phrase skills):
     "Active Directory Administration"         → RIGHT
     "Computer Hardware Troubleshooting"       → RIGHT
     "LAN/WAN Network Administration"          → RIGHT
4. skill_name must be 2–5 words. Single words like "Technical", "Networking",
   "Leadership" are TOO VAGUE — do not include them.
5. Do NOT include job titles, rank, unit names, awards, or training course names.
6. No duplicates. Merge near-synonyms into one entry.

Return ONLY a valid JSON array. Each element must have exactly these keys:
  "skill_name" — 2–5 word noun phrase naming the skill
  "category"   — one of: Technical, Security, Leadership, Operations, Communication, Analytical
  "evidence"   — verbatim quote ≤12 words from the resume that proves this skill

No preamble, no explanation, no markdown fences.

Service branch: {service_branch or "Not specified"}
Specialty code: {specialty_code or "Not specified"}

Resume text:
{resume_text}

JSON array:"""

    t0 = time.monotonic()
    try:
        raw = llm_generate(prompt, _MODEL_ID, max_tokens=800)
        latency_ms = (time.monotonic() - t0) * 1000
        parsed = parse_llm_json(raw, "extract_resume_skills")

        # Normalise — model may wrap in {"skills": [...]} or return bare array
        if isinstance(parsed, dict):
            skills = (parsed.get("skills") or parsed.get("skill_list")
                      or list(parsed.values()))
            if skills and isinstance(skills[0], list):
                skills = skills[0]
        else:
            skills = parsed

        # Guard: model may return plain strings instead of objects
        if skills and isinstance(skills[0], str):
            skills = [{"skill_name": s, "category": "", "evidence": ""} for s in skills]

        # Normalise key name: model may use "skill" instead of "skill_name"
        import re as _re

        # O*NET cognitive/work-activity labels that are too generic to be useful
        # as resume skills.  The LLM sometimes echoes these from training data.
        _ONET_GENERIC = {
            "systems analysis", "critical thinking", "complex problem solving",
            "active listening", "monitoring", "judgment and decision making",
            "technology design", "coordination", "time management", "speaking",
            "writing", "reading comprehension", "learning strategies",
            "management of personnel resources", "management of material resources",
            "management of financial resources", "operations analysis",
            "systems evaluation", "quality control analysis", "troubleshooting",
            "equipment maintenance", "equipment selection", "installation",
            "operation monitoring", "operation and control", "programming",
            "repairing", "service orientation", "social perceptiveness",
            "instructing", "negotiation", "persuasion",
        }

        # First-word verb stems that mean the entry is a verb phrase, not a skill name
        _VERB_START = _re.compile(
            r'^(manag|maintain|operat|install|configur|resolv|troubleshoot|repair|'
            r'conduct|perform|monitor|support|develop|train|deploy|ensur|provid|'
            r'creat|document|inspect|track|audit|report|lead|supervis|coordinat|'
            r'implement|execut|identif|analyz|assess|prepar|updat|review|'
            r'establish|handl|mitigat|detect|prevent|protect|secur|control|'
            r'process|schedul|delegat|prioritiz)',
            _re.IGNORECASE
        )

        normalised = []
        for s in skills:
            if not isinstance(s, dict):
                continue
            name = (s.get("skill_name") or s.get("skill") or "").strip()
            if not name:
                continue
            words = name.split()
            # Drop: single-word entries (too vague)
            if len(words) < 2:
                continue
            # Drop: >5 words (sentence, not a skill name)
            if len(words) > 5:
                continue
            # Drop: known O*NET generic work-activity descriptors
            if name.lower() in _ONET_GENERIC:
                continue
            # Drop: verb-phrase entries (action, not skill name)
            if _VERB_START.match(words[0]):
                continue
            normalised.append({
                "skill_name": name,
                "category":   s.get("category", ""),
                "evidence":   s.get("evidence", ""),
            })
        skills = normalised

        result = {
            "skills":      skills,
            "skill_count": len(skills),
            "pii_warning": None,
            "error":       None,
        }

        # ── Governance: log inference fact ────────────────────────────────
        subs = get_subscription_ids()
        log_inference(
            tool_name="extract_resume_skills",
            model_id=_MODEL_ID,
            prompt=prompt,
            response=raw,
            input_data={
                "service_branch": service_branch,
                "specialty_code": specialty_code,
                "resume_length":  len(resume_text),
            },
            output_data={
                "skill_count": len(skills),
                "error": None,
            },
            subscription_id=subs.get("extract_resume_skills"),
            latency_ms=latency_ms,
            metadata={"fairness_attribute_service_branch": service_branch},
        )

        return result

    except Exception as exc:
        log_inference(
            tool_name="extract_resume_skills",
            model_id=_MODEL_ID,
            prompt=prompt,
            response="",
            input_data={
                "service_branch": service_branch,
                "specialty_code": specialty_code,
                "resume_length":  len(resume_text),
            },
            output_data={"skill_count": 0, "error": str(exc)},
            subscription_id=get_subscription_ids().get("extract_resume_skills"),
            latency_ms=(time.monotonic() - t0) * 1000,
            metadata={"fairness_attribute_service_branch": service_branch},
        )
        err_msg = f"{type(exc).__name__}: {exc}" if str(exc) else repr(exc)
        return {
            "skills": None, "skill_count": 0,
            "pii_warning": None, "error": err_msg,
        }
