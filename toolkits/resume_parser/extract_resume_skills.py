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

_MODEL_ID = "meta-llama/llama-3-3-70b-instruct"


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

    prompt = f"""You are an expert civilian resume analyst for military veterans.

Read the resume below and extract a structured list of CIVILIAN SKILLS that are
EXPLICITLY EVIDENCED in the text.

STRICT RULES:
1. Only list skills that appear in the resume text — in skills sections, experience
   bullets, certifications, or descriptions of responsibilities.
2. Use civilian terminology (e.g. "Network Administration" not "DCGS network ops").
3. Do NOT infer skills from the MOS/AFSC code alone — only extract what the text shows.
4. Do NOT include activities, duties, or job titles — only skills and competencies.
5. Each skill must be a noun phrase (2–5 words), not a sentence or verb phrase.
   WRONG: "managed Active Directory user accounts"
   RIGHT: "Active Directory Administration"
6. No duplicates. Merge near-synonyms into the best single entry.

Return ONLY a valid JSON array. Each element must have exactly these keys:
  "skill_name" — the civilian skill name (2–5 words, noun phrase)
  "category"   — one of: Technical, Security, Leadership, Operations, Communication, Analytical
  "evidence"   — a verbatim short quote (≤12 words) from the resume that supports this skill

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
        normalised = []
        for s in skills:
            if isinstance(s, dict):
                name = s.get("skill_name") or s.get("skill") or ""
                normalised.append({
                    "skill_name": name.strip(),
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
