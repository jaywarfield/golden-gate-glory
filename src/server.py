# src/server.py
# Mission Veteran AI — a Golden Gate Glory project
# Bridge server: receives POST /api/translate from the web front-end and
# dispatches to the appropriate toolkit function, then normalises the
# response to the shape the front-end expects.
#
# Run locally:
#   cd /path/to/golden-gate-glory
#   uvicorn src.server:app --reload --port 8080
#
# Required environment variables (set in .env or shell):
#   WATSONX_API_KEY        — IBM Cloud API key
#   WATSONX_URL            — watsonx.ai endpoint (default: https://us-south.ml.cloud.ibm.com)
#   WATSONX_PROJECT_ID     — watsonx.ai project ID
#
# The server also serves web/index.html and static assets at GET /.

import json
import os
import sys
import httpx

from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# ── Path setup ─────────────────────────────────────────────────────────────
# Allow imports from the project root so toolkit modules resolve correctly.
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "toolkits"))

load_dotenv(_ROOT / ".env")

# ── Toolkit imports ─────────────────────────────────────────────────────────
from accomplishment_translator.translate_accomplishment import translate_accomplishment  # noqa: E402
from skill_mapper.map_military_skills import map_military_skills                        # noqa: E402
from gap_analyzer.analyze_skills_gap import analyze_skills_gap                          # noqa: E402
from plan_builder.build_plan import (                                                    # noqa: E402
    analyze_job_description,
    build_resume_draft,
    evaluate_export_gate,
)
from resume_parser.extract_resume_skills import extract_resume_skills                   # noqa: E402

# ── App ─────────────────────────────────────────────────────────────────────
app = FastAPI(title="Mission Veteran AI — Bridge Server")

# Allow GitHub Pages (and local dev) to POST to /api/translate.
# In production narrow ALLOWED_ORIGINS to your exact Pages URL.
_ALLOWED_ORIGINS = os.environ.get(
    "ALLOWED_ORIGINS",
    "*",          # default open for development; override in production
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type"],
)

_WEB_DIR = _ROOT / "web"


@app.get("/health")
def health():
    """Health check — returns env var status without exposing values."""
    import sys
    creds_ok = bool(os.environ.get("WATSONX_API_KEY")) and bool(os.environ.get("WATSONX_PROJECT_ID"))
    usajobs_key    = os.environ.get("USAJOBS_API_KEY", "")
    usajobs_agent  = os.environ.get("USAJOBS_USER_AGENT", "")
    return {
        "status": "ok",
        "python": sys.version,
        "WATSONX_API_KEY":      "set" if os.environ.get("WATSONX_API_KEY")    else "MISSING",
        "WATSONX_PROJECT_ID":   "set" if os.environ.get("WATSONX_PROJECT_ID") else "MISSING",
        "WATSONX_URL":          os.environ.get("WATSONX_URL", "MISSING"),
        "API_BASE":             os.environ.get("API_BASE", "not set"),
        "creds_ready":          creds_ok,
        "USAJOBS_API_KEY":      f"set ({len(usajobs_key)} chars)" if usajobs_key.strip() else "MISSING",
        "USAJOBS_USER_AGENT":   f"set ({len(usajobs_agent)} chars)" if usajobs_agent.strip() else "MISSING",
    }


@app.get("/")
def serve_index():
    return FileResponse(_WEB_DIR / "index.html")


# Serve any other static file under /web/ (CSS, JS, images if added later)
if _WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_WEB_DIR)), name="static")


# ── Main dispatch endpoint ───────────────────────────────────────────────────
@app.post("/api/translate")
async def translate(request: Request) -> JSONResponse:
    """
    Single endpoint that dispatches to the correct toolkit function based on
    the 'step' field in the request body.

    Request body shape:
        { "step": "<step_name>", "input": { ... } }

    Step names and their toolkit mappings:
        translate_resume  → extract_resume_skills (AI) + parse_resume_text (regex fallback)
                            + translate_accomplishment (per bullet) + O*NET crosswalk merge
        analyze_job       → analyze_job_description
        map_skills        → map_military_skills
        gap_analysis      → analyze_skills_gap
        build_resume      → build_resume_draft
        interview_prep    → build_interview_prep (internal — derived from resume draft)
        gate              → evaluate_export_gate
        search_jobs       → _step_search_jobs (USAJobs API proxy)
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    step: str = body.get("step", "")
    inp: dict[str, Any] = body.get("input", {})

    if not step:
        raise HTTPException(status_code=400, detail="Missing 'step' field")

    try:
        if step == "translate_resume":
            return JSONResponse(_step_translate_resume(inp))
        elif step == "analyze_job":
            return JSONResponse(_step_analyze_job(inp))
        elif step == "map_skills":
            return JSONResponse(_step_map_skills(inp))
        elif step == "gap_analysis":
            return JSONResponse(_step_gap_analysis(inp))
        elif step == "build_resume":
            return JSONResponse(_step_build_resume(inp))
        elif step == "interview_prep":
            return JSONResponse(_step_interview_prep(inp))
        elif step == "gate":
            return JSONResponse(_step_gate(inp))
        elif step == "search_jobs":
            return JSONResponse(await _step_search_jobs(inp))
        else:
            raise HTTPException(status_code=400, detail=f"Unknown step: {step!r}")

    except HTTPException:
        raise
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


# ── Step handlers ────────────────────────────────────────────────────────────

def _step_translate_resume(inp: dict) -> dict:
    """
    Accepts the full resume text, extracts summary + experience paragraphs,
    translates each experience block into an ATS bullet, and returns all
    extracted skill tokens merged with O*NET skills for the specialty code.

    Expected input:
        resume_text, service_branch, specialty_code, target_role, career_path

    Returns:
        { summary, bullets[], resume_skills[] }
    """
    import re as _re

    resume_text: str    = inp.get("resume_text", "").strip()
    target_role: str    = inp.get("target_role", "general civilian")
    specialty_code: str = inp.get("specialty_code", "").strip()
    service_branch: str = inp.get("service_branch", "").strip()
    career_path: str    = inp.get("career_path", "").strip()

    if not resume_text:
        return {"error": "resume_text is required"}

    # ── Parse the resume into sections ──────────────────────────────────────
    summary_text, exp_texts, resume_skills = _parse_resume(resume_text)

    if not summary_text and not exp_texts:
        return {"error": "Could not identify any content in the resume."}

    if not summary_text and exp_texts:
        summary_text = exp_texts.pop(0)

    # ── Batch-translate all fragments in ONE LLM call ────────────────────────
    # Collect all fragments to translate: summary sentences + experience blocks.
    # Sending them in a single prompt costs 1 token-quota call instead of N.
    def _clean_bullet(text: str) -> str:
        """Strip markdown artefacts and keep only the first sentence."""
        text = _re.sub(r'^\s*[\*\-\•\–]\s+', '', text.strip())
        lines = text.splitlines()
        clean_lines = []
        for line in lines:
            if _re.match(r'^\s*#+\s*', line):
                break
            clean_lines.append(line)
        text = ' '.join(clean_lines).strip()
        return _re.split(r'(?<=[.!?])\s+(?=[A-Z])', text, maxsplit=1)[0].strip()

    # Gather summary sentences that aren't already covered by exp_texts
    summary_sentences: list[str] = []
    if summary_text:
        exp_lower = ' '.join(exp_texts).lower()
        for sent in _re.split(r'(?<=[.!?])\s+', summary_text):
            sent = sent.strip()
            if len(sent) < 20:
                continue
            sig_words = [w for w in _re.findall(r'[a-z]+', sent.lower()) if len(w) > 4]
            overlap = sum(1 for w in sig_words if w in exp_lower)
            if sig_words and overlap < min(3, len(sig_words)):
                summary_sentences.append(sent)

    all_fragments = summary_sentences + exp_texts   # summary first, bullets after

    def _batch_translate(fragments: list[str], role: str) -> list[str]:
        """
        Translate all fragments in one LLM call.
        Returns a list of translated bullets (same order, SKIP entries removed).
        Falls back to the original fragments on any error.
        """
        if not fragments:
            return []

        from shared._common import llm_generate, parse_llm_json

        numbered = "\n".join(f'{i+1}. {f}' for i, f in enumerate(fragments))
        prompt = f"""You are an expert resume writer helping a U.S. military veteran transition to civilian employment.

Translate EACH numbered military accomplishment below into ONE ATS-ready civilian resume bullet.

Rules for EVERY bullet:
- Choose the strongest action verb that captures the same sentiment as the original.
- Replace ALL military jargon with plain civilian equivalents.
  Examples: "deployment" → "assignment", "theater" → "region", "NCO" → "supervisor",
  "unit" → "team", "mission" → "project", "MOS/AFSC" → "role".
- STRICT: Do not invent any fact, number, or detail not in the original.
- If a bullet is too vague to translate faithfully, write exactly: SKIP
- Each output must be ONE sentence only.

Target civilian role: {role}

Return ONLY a valid JSON array of strings, one per input, in the same order.
No preamble, no explanation, no markdown fences.

Military accomplishments:
{numbered}

JSON array:"""

        _BATCH_MODEL = "meta-llama/llama-3-3-70b-instruct"
        try:
            raw = llm_generate(prompt, _BATCH_MODEL, max_tokens=min(120 * len(fragments), 1200))
            parsed = parse_llm_json(raw, "batch_translate")
            if not isinstance(parsed, list):
                return fragments   # unexpected shape — fall back
            results = []
            for i, item in enumerate(parsed):
                text = str(item).strip().lstrip("•-– ").strip()
                if text.upper() == "SKIP" or not text:
                    continue
                cleaned = _clean_bullet(text)
                if cleaned:
                    results.append(cleaned)
            return results if results else fragments
        except Exception:
            return fragments   # any error — return originals untranslated

    bullets = _batch_translate(all_fragments, target_role)

    # ── AI skill extraction from the full resume text ────────────────────────
    # Non-fatal: quota / API errors fall back to regex-parsed resume_skills.
    try:
        ai_result = extract_resume_skills(
            resume_text=resume_text,
            service_branch=service_branch,
            specialty_code=specialty_code,
        )
        if ai_result.get("pii_warning"):
            return {"error": ai_result["pii_warning"]}
    except Exception:
        ai_result = {"skills": None}

    ai_skills_raw = ai_result.get("skills") or []
    if ai_skills_raw:
        seen_lower: set[str] = set()
        final_skills: list[str] = []
        for s in ai_skills_raw:
            name = (s.get("skill_name") or "").strip() if isinstance(s, dict) else str(s).strip()
            if name and name.lower() not in seen_lower:
                seen_lower.add(name.lower())
                final_skills.append(name)
    else:
        # AI call failed or returned nothing — fall back to regex-parsed skills
        seen_lower = {s.lower() for s in resume_skills}
        final_skills = list(resume_skills)

    # O*NET crosswalk skills are NOT appended here — they are generic work-activity
    # descriptors (e.g. "Critical Thinking", "Active Listening") that pollute the
    # user-facing skills display.  They are used downstream in map_military_skills
    # (step 4) where they serve as target vocabulary for the LLM, not as claimed skills.

    return {
        "summary":       summary_text,
        "bullets":       bullets,
        "resume_skills": final_skills,
    }


def _step_analyze_job(inp: dict) -> dict:
    """
    Analyze a job description and return required skills, keywords, industry.

    Expected input:
        job_description

    Returns (normalized for frontend):
        { role_title, industry, required_skills[], ats_keywords[],
          preferred_skills[], alignment_pct? }
    """
    jd: str = inp.get("job_description", "").strip()
    if not jd:
        return {"error": "job_description is required"}

    result = analyze_job_description(job_description=jd)

    if result.get("error"):
        return {"error": result["error"]}
    if result.get("pii_warning"):
        return {"error": result["pii_warning"]}

    # Normalize to what the frontend expects
    return {
        "role_title":       result.get("keywords", [""])[0] if result.get("keywords") else "",
        "industry":         result.get("industry", ""),
        "required_skills":  result.get("required_skills", []),
        "preferred_skills": result.get("preferred_skills", []),
        "ats_keywords":     result.get("keywords", []),
        "seniority_level":  result.get("role_level", ""),
        "alignment":        {},
    }


def _step_map_skills(inp: dict) -> dict:
    """
    Map military specialty + service summary to civilian skills.

    Expected input:
        service_branch, specialty_code, service_summary, target_career_path

    Returns:
        { skills[{skill_name, category, confidence}], gap_skills[], alignment_pct }
    """
    result = map_military_skills(
        service_branch=inp.get("service_branch", ""),
        specialty_code=inp.get("specialty_code", ""),
        service_summary=inp.get("service_summary", ""),
        target_career_path=inp.get("target_career_path", ""),
    )

    if result.get("error"):
        return {"error": result["error"]}
    if result.get("pii_warning"):
        return {"error": result["pii_warning"]}

    # Normalize skill shape: toolkit returns {skill, category, evidence}
    # frontend expects {skill_name, category, confidence}
    # Guard: Llama sometimes returns a plain array of strings instead of objects
    # Strip leading action verbs the LLM sometimes prepends to skill names
    # e.g. "Directed Network Infrastructure" → "Network Infrastructure"
    import re as _re
    _LEADING_VERB = _re.compile(
        r'^(directed|managed|led|supervised|performed|conducted|executed|'
        r'coordinated|oversaw|delivered|developed|maintained|ensured|'
        r'provided|utilized|supported|assisted|handled)\s+',
        _re.IGNORECASE,
    )
    def _clean_skill_name(raw: str) -> str:
        return _LEADING_VERB.sub('', (raw or '').strip()).strip()

    raw_skills = result.get("skills") or []
    skills = [
        {
            "skill_name": _clean_skill_name(s if isinstance(s, str) else s.get("skill", s.get("skill_name", ""))),
            "category":   "" if isinstance(s, str) else s.get("category", ""),
            "confidence": "High" if isinstance(s, str) else (
                "High" if not s.get("evidence", "").startswith("O*NET crosswalk") else "Medium"
            ),
            "evidence":   "" if isinstance(s, str) else s.get("evidence", ""),
        }
        for s in raw_skills
    ]

    return {
        "skills":          skills,
        "onet_soc":        result.get("onet_soc"),
        "civilian_title":  result.get("civilian_title"),
        "gap_skills":      [],   # filled by gap_analysis step
        "alignment_pct":   0,    # filled by gap_analysis step
    }


def _step_gap_analysis(inp: dict) -> dict:
    """
    Compare skill inventory against job description, find gaps,
    recommend SkillsBuild courses and SkillBridge programs.

    Expected input:
        veteran_skills_json, target_career_path, job_description

    Returns:
        { gap_skills[], matched_skills[], alignment_pct,
          skillsbuild_recommendations[], skillbridge_programs[] }
    """
    result = analyze_skills_gap(
        veteran_skills_json=inp.get("veteran_skills_json", "[]"),
        target_career_path=inp.get("target_career_path", ""),
        job_description=inp.get("job_description", ""),
    )

    # Surface any error from the toolkit (check both truthy and explicit None)
    if result.get("error") is not None and result.get("error") is not False:
        err = result["error"]
        if err:  # non-empty / non-zero
            return {"error": str(err)}
    if result.get("pii_warning"):
        return {"error": result["pii_warning"]}

    gap_skills_raw = result.get("gap_skills") or []
    covered        = result.get("covered_skills") or []

    # Normalize gap_skill entries — LLM may return strings OR dicts
    def _skill_name(s: Any) -> str:
        if isinstance(s, str):
            return s
        if isinstance(s, dict):
            return s.get("skill_name") or s.get("skill") or s.get("name") or str(s)
        return str(s)

    gap_skills_normalized = []
    for skill in gap_skills_raw:
        sname = _skill_name(skill)
        # Find any course that tags this skill
        matching_courses = [
            {
                "title":            c["course_title"],
                "credential_type":  c.get("credential", "Badge"),
                "hours_estimate":   c.get("estimated_hours", 0),
                "url":              c.get("url", "https://skillsbuild.org"),
            }
            for c in (result.get("skillsbuild_recommendations") or [])
            if any(sname.lower() in tag.lower() or tag.lower() in sname.lower()
                   for tag in c.get("skill_tags", []))
        ]
        gap_skills_normalized.append({
            "skill_name": sname,
            "priority":   "High",
            "courses":    matching_courses[:2],
        })

    return {
        "gap_skills":                 gap_skills_normalized,
        "covered_skills":             [{"skill_name": s} if isinstance(s, str) else s for s in covered],
        "coverage_pct":               result.get("coverage_pct", 0),
        "alignment_pct":              result.get("coverage_pct", 0),
        "skillsbuild_recommendations": result.get("skillsbuild_recommendations", []),
        "skillbridge_programs":        result.get("skillbridge_programs", []),
    }


def _step_build_resume(inp: dict) -> dict:
    """
    Build the evidence-tagged resume draft.

    Expected input:
        service_branch, specialty_code, service_summary,
        translated_bullets_json, skill_inventory_json, job_analysis_json,
        target_role

    Returns the resume draft in the shape renderStep5 expects:
        { summary{text,tag}, bullets[{text,tag,source}],
          skills_section[], inferred_count, missing_count, evidenced_count }
    """
    result = build_resume_draft(
        service_branch=inp.get("service_branch", ""),
        specialty_code=inp.get("specialty_code", ""),
        service_summary=inp.get("service_summary", ""),
        translated_bullets_json=inp.get("translated_bullets_json", "[]"),
        skill_inventory_json=inp.get("skill_inventory_json", "[]"),
        job_analysis_json=inp.get("job_analysis_json", "{}"),
    )

    if result.get("error"):
        return {"error": result["error"]}
    if result.get("pii_warning"):
        return {"error": result["pii_warning"]}

    sections = result.get("resume_sections") or {}

    # summary — first item from summary section
    sum_items = sections.get("summary", [])
    summary_item = sum_items[0] if sum_items else {"tag": "MISSING", "text": ""}
    summary = {
        "text":   summary_item.get("text", ""),
        "tag":    summary_item.get("tag", "MISSING"),
        "source": _source_label(summary_item),
    }

    # experience bullets
    bullets = [
        {
            "text":   item.get("text", ""),
            "tag":    item.get("tag", "EVIDENCED"),
            "source": _source_label(item),
        }
        for item in sections.get("experience", [])
    ]
    # append any additional summary items as bullets
    for item in sum_items[1:]:
        bullets.append({
            "text":   item.get("text", ""),
            "tag":    item.get("tag", "EVIDENCED"),
            "source": _source_label(item),
        })

    # skills section — flat list of skill name strings
    skills_section = [
        item.get("text", "")
        for item in sections.get("skills", [])
        if item.get("text")
    ]

    return {
        "summary":         summary,
        "bullets":         bullets,
        "skills_section":  skills_section,
        "inferred_count":  result.get("inferred_count", 0),
        "missing_count":   result.get("missing_count", 0),
        "evidenced_count": result.get("evidenced_count", 0),
        "grounding_warnings": result.get("grounding_warnings", []),
        "disclaimer":      result.get("disclaimer", ""),
    }


def _step_interview_prep(inp: dict) -> dict:
    """
    Generate interview preparation questions grounded by the resume draft.
    This step uses the job analysis + skill inventory to produce STAR-framed
    questions and talking points. Uses analyze_job_description as an anchor
    since there is no dedicated interview_prep toolkit yet.

    Returns the shape renderStep6 expects:
        { questions[{question, skill_mapped, star_scaffold{situation,task,action,result}}] }
    """
    skill_inventory: list = json.loads(inp.get("skill_inventory_json", "[]"))
    job_analysis: dict    = json.loads(inp.get("job_analysis_json", "{}"))
    target_role: str      = inp.get("target_role", "")
    service_summary: str  = inp.get("service_summary", "")

    required_skills: list = job_analysis.get("required_skills", [])

    # Build up to 3 questions — one per top required skill that appears in
    # the veteran's inventory (EVIDENCED), falling back to gap skills.
    veteran_skill_names = {s.get("skill_name", "").lower() for s in skill_inventory}

    questions = []
    for skill in required_skills:
        if len(questions) >= 3:
            break
        matched = skill.lower() in veteran_skill_names or any(
            skill.lower() in vs for vs in veteran_skill_names
        )
        questions.append({
            "question":     f"Tell me about a time you demonstrated {skill}.",
            "skill_mapped": skill,
            "star_scaffold": {
                "situation": f"In your role as {target_role or 'a military professional'}, describe the context.",
                "task":      f"What was the specific challenge related to {skill}?",
                "action":    "Describe the steps you took, using concrete examples from your service record.",
                "result":    "What was the measurable outcome? (Include numbers where possible.)",
            },
            "evidenced": matched,
        })

    # Pad to 3 if fewer matched
    if len(questions) < 3:
        questions.append({
            "question":     f"Why are you transitioning to {target_role or 'this role'}, and what value do you bring?",
            "skill_mapped": "Career transition",
            "star_scaffold": {
                "situation": "Briefly describe your military background.",
                "task":      "Explain what motivated this transition.",
                "action":    "Describe how your military skills map to civilian requirements.",
                "result":    "State the specific value you would add in this role.",
            },
            "evidenced": True,
        })

    return {"questions": questions[:3]}


def _step_gate(inp: dict) -> dict:
    """
    Evaluate whether the resume draft is cleared for export.

    Expected input:
        resume_draft_json (the full resumeDraft STATE object from the frontend)

    Returns:
        { gate_status, summary_message, gate_holds[] }
    """
    try:
        draft = json.loads(inp.get("resume_draft_json", "{}"))
    except Exception:
        return {"error": "Invalid resume_draft_json"}

    # Prefer live tag_counts (set by s5UpdateTagCounts after any Add/Delete)
    # over the original inferred_count/missing_count which are stale after edits
    tag_counts = draft.get("tag_counts", {})
    if tag_counts:
        inferred = tag_counts.get("INFERRED", 0)
        missing  = tag_counts.get("MISSING", 0)
    else:
        # Fallback: recompute from the actual bullet/summary tags
        all_items = list(draft.get("bullets") or [])
        if draft.get("summary"):
            s = draft["summary"]
            all_items.append(s if isinstance(s, dict) else {"tag": "EVIDENCED"})
        inferred = sum(1 for x in all_items if (x.get("tag","")).upper() == "INFERRED")
        missing  = sum(1 for x in all_items if (x.get("tag","")).upper() == "MISSING")

    warnings = draft.get("grounding_warnings", [])
    # Only count grounding warnings whose item is still INFERRED in the current draft.
    # If the user confirmed an item via "+ Add" (promoted to EVIDENCED), that warning
    # no longer blocks the gate — don't penalise confirmed items.
    all_items = list(draft.get("bullets") or [])
    s = draft.get("summary")
    if s:
        all_items.append(s if isinstance(s, dict) else {"tag": "EVIDENCED"})
    still_inferred_texts = {
        (x.get("text") or "").strip()
        for x in all_items
        if (x.get("tag", "")).upper() == "INFERRED"
    }
    active_warnings = [
        w for w in warnings
        if (w.get("text") or "").strip() in still_inferred_texts
    ]
    # extra_downgrade covers grounding warnings not already folded into inferred_count
    extra_downgrade = max(0, len(active_warnings) - inferred)

    result = evaluate_export_gate(
        inferred_count=inferred,
        missing_count=missing,
        grounding_downgrade_count=extra_downgrade,
        gate_holds_json="[]",
    )

    holds = result.get("holds", [])

    # Build gate_holds with the fields the frontend renders:
    # sentence, explanation, action_required, tag
    def _hold_obj(h: str) -> dict:
        if "INFERRED" in h or "downgraded" in h.lower():
            return {
                "tag": "INFERRED",
                "sentence": h,
                "explanation": "The AI could not confirm this claim against your service record.",
                "action_required": "Review and confirm or correct this item before export.",
            }
        if "MISSING" in h:
            return {
                "tag": "MISSING",
                "sentence": h,
                "explanation": "No supporting evidence was found in your service record for a required item.",
                "action_required": "Supply the missing information or remove the requirement before export.",
            }
        return {
            "tag": "HOLD",
            "sentence": h,
            "explanation": "",
            "action_required": "Resolve this issue before export.",
        }

    return {
        "gate_status":     result.get("gate_status", "BLOCKED"),
        "summary_message": result.get("message", ""),
        "gate_holds":      [_hold_obj(h) for h in holds],
    }


# ── Internal helpers ─────────────────────────────────────────────────────────

def _source_label(item: dict) -> str:
    """Produce a human-readable italic source sentence for INFERRED/MISSING items."""
    tag = item.get("tag", "").upper()
    if tag == "INFERRED":
        return "Inferred from your service record and specialty code — confirm before use."
    if tag == "MISSING":
        return "Required by the job description; no supporting evidence found in your service record."
    return ""


def _parse_resume(text: str) -> tuple[str, list[str], list[str]]:
    """
    Lightweight resume parser.  Returns (summary_text, exp_texts, skill_tokens).

    Skills are extracted via two passes:
    1. Structured skills blocks (comma/semicolon-separated lists under skills headers
       and subheaders like "Information Technology", "Networking", "Cybersecurity", etc.)
    2. Universal inline scan of ALL lines — including experience, certifications,
       education, and awards — extracting tokens that look like known skill patterns
       (cert names, tool names, technologies, programming languages, etc.)
    """
    import re

    # A section header is one of:
    #   (a) ALL-CAPS, 2+ words: "TECHNICAL SKILLS", "EDUCATION & TRAINING"
    #   (b) Single ALL-CAPS word that is a known section keyword: "EXPERIENCE", "AWARDS"
    #   (c) Any case ending with a colon: "Technical Skills:", "Experience:"
    # Single all-caps acronyms (DNS, DHCP, TCP/IP) and mixed-case skill names are content.
    _SECTION_KEYWORDS = re.compile(
        r'^(SUMMARY|EXPERIENCE|EMPLOYMENT|EDUCATION|TRAINING|SKILLS|CERTIFICATIONS?'
        r'|AWARDS?|HONORS?|CLEARANCE|REFERENCES?|OBJECTIVE|PROFILE|PUBLICATIONS?'
        r'|VOLUNTEER|PROJECTS?|ACHIEVEMENTS?|HIGHLIGHTS?|QUALIFICATIONS?)$'
    )
    HEADER_RE = re.compile(
        r'^(?:'
        r'[A-Z][A-Z0-9&/\-]*(?:\s+[A-Z0-9&/\-]+)+'  # ALL-CAPS, 2+ words
        r'|[A-Za-z0-9 &/\-]{2,60}:'                   # any case ending with colon
        r')\s*$'
    )

    # Headers that signal a structured skills section (and their IT subheaders)
    SKILLS_HDR = re.compile(
        r'\b(skill|qualification|certification|competenc|proficienc|technical|tool|technolog'
        r'|networking|network|cybersecurity|cyber|information technology|system admin'
        r'|operating system|database|cloud|software|hardware|security|leadership|operation'
        r'|programming|language|platform|infrastructure)\b',
        re.IGNORECASE
    )

    # Inline label pattern: "Label: content"
    INLINE_LABEL = re.compile(r'^[A-Za-z0-9 &/\-]{2,50}[:\uff1a][\s\xa0]+(.+)$')

    # Action verb stems that begin experience bullets — not skills.
    # Matched against the first word of a token (case-insensitive).
    # Pattern: stem + optional conjugation endings (e, ed, ing, s, d).
    _ACTION_VERB_RE = re.compile(
        r'^(install(ed|s)?|configur(ed|e|es|ing)?|maintain(ed|s)?|manag(ed|e|es|ing)?'
        r'|resolv(ed|e|es|ing)?|document(ed|s)?|monitor(ed|s)?|perform(ed|s)?'
        r'|support(ed|s)?|deploy(ed|s)?|creat(ed|e|es|ing)?|conduct(ed|s)?'
        r'|operat(ed|e|es|ing)?|troubleshoot(ed|s|ing)?|repair(ed|s)?|led|lead(s)?'
        r'|ensur(ed|e|es|ing)?|develop(ed|s)?|train(ed|s)?|coordinat(ed|e|es|ing)?'
        r'|implement(ed|s)?|execut(ed|e|es|ing)?|identif(ied|y|ies)?|analyz(ed|e|es|ing)?'
        r'|assess(ed|es)?|prepar(ed|e|es|ing)?|updat(ed|e|es|ing)?|test(ed|s)?'
        r'|review(ed|s)?|establish(ed|es)?|provid(ed|e|es|ing)?|handl(ed|e|es|ing)?'
        r'|mitigat(ed|e|es|ing)?|inspect(ed|s)?|track(ed|s)?|audit(ed|s)?'
        r'|report(ed|s)?|communic(ated|ate|ates|ating)?|collaborat(ed|e|es|ing)?'
        r'|supervis(ed|e|es|ing)?|overhaul(ed|s)?|integrat(ed|e|es|ing)?'
        r'|automat(ed|e|es|ing)?|built|build(s)?|design(ed|s)?|patch(ed|es)?'
        r'|scan(ned|s)?|harden(ed|s)?|encrypt(ed|s)?|back(ed|s)?|restor(ed|e|es|ing)?'
        r'|migrat(ed|e|es|ing)?|consolid(ated|ate|ates|ating)?|verif(ied|y|ies)?'
        r'|validat(ed|e|es|ing)?|enforc(ed|e|es|ing)?|respond(ed|s)?|detect(ed|s)?'
        r'|prevent(ed|s)?|protect(ed|s)?|secur(ed|e|es|ing)?|control(led|s)?'
        r'|process(ed|es)?|schedul(ed|e|es|ing)?|delegat(ed|e|es|ing)?|prioritiz(ed|e|es|ing)?'
        r'|manag(ed|e|es|ing)?|set(up)?|load(ed|s)?|input|output)\b',
        re.IGNORECASE
    )

    def _is_noise_tok(tok: str) -> bool:
        """Return True if tok is noise and should not be added as a skill."""
        if not tok or not (2 <= len(tok) <= 60):
            return True
        # Bracket/template artefacts: "if applicable]", "State]January 2021"
        if '[' in tok or ']' in tok:
            return True
        words = tok.split()
        if len(words) >= 6:                                 # sentence-length fragment
            return True
        if tok.endswith('.') and len(words) >= 3:           # sentence fragment ending with period
            return True
        if re.fullmatch(r'[A-Za-z]\.?', tok):              # single letter
            return True
        if re.fullmatch(r'([A-Za-z])\1{2,}\.?', tok):      # repeated same char: OOO, nnn, 000
            return True
        if re.fullmatch(r'[\d\s\.\-\+\(\)\/\\]+', tok):   # purely numeric/punctuation: "000.", "3.5"
            return True
        if re.match(r'^\d+[\+\-]?\s*(years?|yrs?|months?)\b', tok, re.IGNORECASE):
            return True                                     # "5+ years"
        if re.match(r'^\d+\s*[\+\-]?\s*(users?|people|personnel|staff|technician)', tok, re.IGNORECASE):
            return True                                     # "500+ users"
        # Date fragments: "January 2021", "2021 – Present", month names alone
        if re.search(
            r'\b(january|february|march|april|may|june|july|august|september'
            r'|october|november|december|present)\b',
            tok, re.IGNORECASE
        ):
            return True
        # Leading conjunctions: "and switches", "and repaired"
        if words[0].lower() in ('and', 'or', 'but', 'with', 'including', 'such', 'as'):
            return True
        # Gerund-led tokens (any length): "managing Active Directory", "maintaining LAN/WAN"
        # Also catches bare gerunds: "troubleshooting", "maintaining"
        if re.match(r'^[A-Za-z]+ing\b', words[0]) and words[0].lower() not in (
            'networking', 'computing', 'engineering', 'programming',
        ):
            return True
        # Bare single-word action verbs from experience bullets: "Installed", "configured"
        # Only applied to single-word tokens — multi-word phrases like "patch management"
        # are legitimate skills and must not be blocked by a verb first-word test.
        if len(words) == 1 and _ACTION_VERB_RE.match(tok):
            return True
        # Multi-word verb phrases: "resolve technical problems", "document IT procedures"
        # Drop any multi-word token whose first word matches the action verb list.
        if len(words) >= 2 and _ACTION_VERB_RE.match(words[0]):
            return True
        # Sub-section heading phrases: "Primary Responsibilities and Accomplishments",
        # "Selected Leadership Accomplishments", "Duties and Responsibilities", etc.
        if re.search(
            r'\b(responsibilities|accomplishments|duties|highlights|overview'
            r'|selected|primary|additional|key responsibilities|scope of duties)\b',
            tok, re.IGNORECASE
        ):
            return True
        return False

    def _add_token(tok: str, skill_tokens: list, seen: set) -> None:
        tok = tok.strip().strip('-–—').strip()
        if _is_noise_tok(tok):
            return
        key = tok.lower()
        if key not in seen:
            seen.add(key)
            skill_tokens.append(tok)

    # Patterns that mark a line as resume metadata rather than an accomplishment.
    # Applied to the WHOLE line — if any pattern matches, the line is skipped.
    # Rank terms only fire when the line is SHORT (≤10 words); long narrative sentences
    # that mention a rank in passing (e.g. professional summaries) are kept.
    _META_ALWAYS = re.compile(
        r'(?:'
        r'\b(rank|mos|afsc|rating|nec|clearance|years of service|unit|battalion'
        r'|brigade|installation|duty station|branch of service)\s*[:=]'  # labeled field: "Rank: E-5"
        r'|\[.{2,60}\]'                    # template bracket anywhere in line
        r'|\b(january|february|march|april|may|june|july|august|september'
        r'|october|november|december)\s+\d{4}'   # month-year date in line
        r'|\bpresent\b'                    # "– Present" / "to Present"
        r'|\be-[1-9]\b|\bo-[1-9]\b|\bw-[1-5]\b'  # pay-grade codes E-5, O-3, W-2
        r')',
        re.IGNORECASE
    )
    # Rank/title terms that identify a line as metadata ONLY when line is short (≤10 words)
    _META_SHORT_LINE = re.compile(
        r'\b(sergeant|corporal|specialist|private|staff sergeant|master sergeant'
        r'|command sergeant|chief|general|admiral|colonel|major|captain|lieutenant'
        r'|warrant officer|petty officer|airman|seaman|lance corporal)\b',
        re.IGNORECASE
    )

    def _split_line(raw_line: str) -> list[str]:
        line = raw_line.replace('\xa0', ' ').replace('\u2009', ' ').replace('\u200b', '').strip()
        # Skip resume metadata lines — job titles, rank, MOS, dates, unit names, brackets.
        if _META_ALWAYS.search(line):
            return []
        if len(line.split()) <= 10 and _META_SHORT_LINE.search(line):
            return []
        m = INLINE_LABEL.match(line)
        if m:
            line = m.group(1).strip()
        parts = re.split(r'\s*[•·–—]\s*', line)
        # Only return fragments that are substantial prose (≥8 words) or contain a verb —
        # this filters out bare job-title lines and org-name lines that slipped through.
        result = []
        for p in parts:
            p = p.strip()
            if len(p) < 10:
                continue
            words = p.split()
            if len(words) >= 8:
                result.append(p)   # long enough to be a sentence
            elif re.search(
                r'\b(managed|led|trained|deployed|operated|supported|maintained|'
                r'installed|configured|conducted|performed|developed|executed|'
                r'coordinated|supervised|established|provided|ensured|delivered|'
                r'achieved|reduced|increased|improved|created|designed|implemented|'
                r'monitored|tracked|audited|inspected|responded|detected|secured|'
                r'hardened|migrated|automated|integrated|built|restored|recovered|'
                r'collaborated|communicated|reported|scheduled|prioritized)\b',
                p, re.IGNORECASE
            ):
                result.append(p)   # has a past-tense action verb → likely an accomplishment
        return result

    # Regex: headers that mean "not a skills section" — education, training, awards.
    # Uses prefix-only word boundary (\b before each word) to match plurals/variants:
    # e.g. "awards" matches "award", "certifications" matches "certification".
    EDU_AWARDS_HDR = re.compile(
        r'\b(educat|train|school|certif|licens|award|honor|decorat'
        r'|achieve|commend|recognit|clearance|volunteer|reference)',
        re.IGNORECASE
    )

    # ── Pass 1: parse lines into blocks ──────────────────────────────────────
    lines = text.replace('\xa0', ' ').split('\n')
    last_hdr = ''
    in_skills_section = False
    in_edu_awards = False
    blocks: list[dict] = []
    cur: dict | None = None

    for raw in lines:
        t = raw.strip()
        if not t:
            if cur and cur['lines']:
                blocks.append(cur); cur = None
            continue
        if HEADER_RE.match(t) or _SECTION_KEYWORDS.match(t):
            if cur and cur['lines']:
                blocks.append(cur); cur = None
            last_hdr = t.rstrip(':').lower()
            # EDU_AWARDS_HDR takes precedence over SKILLS_HDR (e.g. "CERTIFICATIONS" is edu, not skills)
            if EDU_AWARDS_HDR.search(last_hdr):
                in_skills_section = False
                in_edu_awards = True
            elif re.search(r'\b(experience|employment|work history)\b', last_hdr, re.IGNORECASE):
                in_skills_section = False
                in_edu_awards = False
            elif SKILLS_HDR.search(last_hdr):
                in_skills_section = True
                in_edu_awards = False
            continue
        if cur is None:
            hint = (last_hdr + ' skill') if in_skills_section else last_hdr
            cur = {'hint': hint, 'lines': [], 'is_edu_awards': in_edu_awards}
        cur['lines'].append(t)

    if cur and cur['lines']:
        blocks.append(cur)

    # ── Pass 2: classify blocks and extract content ───────────────────────────
    summary_text = ''
    exp_texts: list[str] = []
    skill_tokens: list[str] = []
    seen: set[str] = set()

    for b in blocks:
        is_edu_awards = b.get('is_edu_awards', False)
        has_skills_hint = bool(SKILLS_HDR.search(b['hint']))
        short_line_ratio = (
            sum(1 for l in b['lines'] if len(l.split()) <= 4) / len(b['lines'])
            if b['lines'] else 0
        )
        is_skills = has_skills_hint or short_line_ratio >= 0.7

        if is_skills and not is_edu_awards:
            # Structured skills block: split on commas/semicolons, extract each token
            for l in b['lines']:
                m_label = re.match(r'^[A-Za-z0-9 /&\-]{2,40}:\s*(.+)$', l)
                content = m_label.group(1) if m_label else l
                for tok in re.split(r'[,;•·]\s*', content):
                    _add_token(tok, skill_tokens, seen)
            continue

        if is_edu_awards:
            # Education/awards/training block: only extract known cert/tool names.
            # Do NOT do broad comma-split — these lines contain training courses,
            # award citations, school names, etc. that look like skills but aren't.
            for l in b['lines']:
                tok = l.strip()
                if re.search(
                    r'\b(CompTIA|CISSP|CEH|CCNA|CCNP|CISM|CISA|Security\+|Network\+|A\+'
                    r'|AWS|Azure|GCP|Linux\+|CySA\+|PenTest\+|CASP\+|OSCP|GIAC'
                    r'|ITIL|PMP|CAPM|Scrum|Agile|NIST|RMF|STIG)\b',
                    tok, re.IGNORECASE
                ):
                    _add_token(tok, skill_tokens, seen)
            continue

        # Experience / narrative block: extract summary/bullets AND scan inline for skills
        for raw_line in b['lines']:
            for fragment in _split_line(raw_line):
                if not summary_text:
                    summary_text = fragment
                else:
                    exp_texts.append(fragment)
            # Inline skill scan: pull cert names and tool names from experience lines.
            # Only scan comma-separated parts that contain known tech keywords.
            line_norm = raw_line.replace('\xa0', ' ').strip()
            m_label = re.match(r'^[A-Za-z0-9 /&\-]{2,40}:\s*(.+)$', line_norm)
            scan_content = m_label.group(1) if m_label else line_norm

            parts = re.split(r'[,;]\s*', scan_content)
            if len(parts) >= 2:
                # Comma-delimited: only keep short (≤3 words) parts that look like
                # tech terms — not generic nouns or activity descriptions.
                for tok in parts:
                    tok = tok.strip()
                    if len(tok.split()) <= 3 and re.search(
                        r'\b(TCP|UDP|IP|DNS|DHCP|SSH|SSL|TLS|VPN|LAN|WAN|VLAN|HTTP|HTTPS'
                        r'|SMTP|LDAP|AD|GPO|SNMP|BGP|OSPF|MPLS|QoS|NAT|PAT|ACL|DMZ'
                        r'|router|switch|firewall|server|desktop|laptop|printer|NAS|SAN'
                        r'|Linux|Windows|macOS|Unix|Android|iOS|VMware|Hyper-V|ESXi'
                        r'|Python|Bash|PowerShell|SQL|JavaScript|Java|C\+\+|C#|Go|Rust'
                        r'|Docker|Kubernetes|Ansible|Terraform|Git|Jenkins|Splunk'
                        r'|Wireshark|Nessus|Nmap|Metasploit|CrowdStrike|Tanium|SolarWinds'
                        r'|ServiceNow|Jira|Confluence|SharePoint|Office 365|Azure|AWS|GCP'
                        r'|Active Directory|Group Policy|SCCM|WSUS|Nagios|Zabbix)\b',
                        tok, re.IGNORECASE
                    ):
                        _add_token(tok, skill_tokens, seen)
            # No single-item inline scan for narrative blocks —
            # single-item lines from experience are caught via the structured skills path.

    return summary_text, exp_texts, skill_tokens


# ── USAJobs job search proxy ─────────────────────────────────────────────────

_USAJOBS_API_BASE = "https://data.usajobs.gov/api/search"

# OPM occupational series that cover IT/cyber/engineering roles used by this app.
# USAJobs "JobCategoryCode" accepts semicolon-separated series codes.
# Series reference: https://www.opm.gov/policy-data-oversight/classification-qualifications/
_CAREER_PATH_TO_SERIES: dict[str, list[str]] = {
    "IT Infrastructure":    ["2210", "0854", "0391"],
    "IT Operations":        ["2210", "0391", "0854"],
    "IT Support":           ["2210", "0335", "0303"],
    "Network Engineering":  ["2210", "0854", "0391"],
    "Network Infrastructure":["2210", "0854"],
    "Telecommunications":   ["0391", "0394", "2210"],
    "Cybersecurity":        ["2210", "1550", "0080"],
    "Cyber Engineering":    ["2210", "0854", "1550"],
    "Software Development": ["2210", "1550", "0854"],
    "Software Engineering": ["2210", "1550", "0854"],
    "Cloud Infrastructure": ["2210", "0854"],
    "Enterprise Systems":   ["2210", "0854", "0391"],
    "Hardware Engineering": ["0854", "0856", "0855"],
    "Project Management":   ["2210", "0340", "0301"],
    "Program Management":   ["2210", "0340", "0301"],
    "Data Analytics":       ["2210", "1550", "1515"],
}
# Fallback series when no career path matches — still IT-focused
_DEFAULT_SERIES = ["2210", "0854", "1550", "0391"]

async def _step_search_jobs(inp: dict) -> dict:
    """
    Proxy a job search to the USAJobs API and return a normalised list of
    postings for the user to pick from in step 3.

    Expected input:
        target_role   (str)  — e.g. "Network Administrator"
        career_path   (str)  — e.g. "IT Infrastructure"

    Returns:
        { jobs: [ { id, title, agency, location, grade, url, description } ] }
        or { error: "..." } when credentials are missing or the API fails.
    """
    api_key    = os.environ.get("USAJOBS_API_KEY", "").strip()
    user_agent = os.environ.get("USAJOBS_USER_AGENT", "").strip()

    missing = []
    if not api_key:    missing.append("USAJOBS_API_KEY")
    if not user_agent: missing.append("USAJOBS_USER_AGENT")
    if missing:
        return {
            "error": (
                f"USAJobs API credentials missing: {', '.join(missing)}. "
                "Add them to your Railway environment variables "
                "(Settings → Variables) or your local .env file."
            )
        }

    target_role = (inp.get("target_role") or "").strip()
    career_path = (inp.get("career_path") or "").strip()

    # Combine role + path as keyword for tighter text matching
    keyword_parts = [p for p in [target_role, career_path] if p]
    keyword = " ".join(keyword_parts) if keyword_parts else "IT"

    # Map career path to OPM series codes; fall back to general IT series
    series_codes = _CAREER_PATH_TO_SERIES.get(career_path, _DEFAULT_SERIES)
    job_category = ";".join(series_codes)

    params = {
        "Keyword":         keyword,
        "JobCategoryCode": job_category,
        "ResultsPerPage":  "10",
        "Fields":          "min",
        "SortField":       "OpenDate",
        "SortDirection":   "Desc",
    }

    headers = {
        "Host":           "data.usajobs.gov",
        "User-Agent":     user_agent,
        "Authorization-Key": api_key,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(_USAJOBS_API_BASE, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPStatusError as e:
        return {"error": f"USAJobs API returned {e.response.status_code}: {e.response.text[:200]}"}
    except Exception as e:
        return {"error": f"USAJobs API request failed: {str(e)}"}

    items = (
        data.get("SearchResult", {})
            .get("SearchResultItems", [])
    )

    jobs = []
    for item in items:
        mv = item.get("MatchedObjectDescriptor", {})

        # Location: prefer first listed duty station
        locations = mv.get("PositionLocation", [])
        location  = locations[0].get("LocationName", "") if locations else ""

        # Pay grade range (e.g. "GS-09 to GS-13")
        grades = mv.get("JobGrade", [])
        grade_str = ""
        if grades:
            codes = [g.get("Code", "") for g in grades if g.get("Code")]
            low   = mv.get("PositionSchedule", [{}])[0].get("Code", "")
            # UserArea has the grade range more reliably
            ua   = mv.get("UserArea", {}).get("Details", {})
            low  = ua.get("LowGrade", "")
            high = ua.get("HighGrade", "")
            if low and high and low != high:
                grade_str = f"GS-{low} to GS-{high}"
            elif low:
                grade_str = f"GS-{low}"
            elif codes:
                grade_str = "/".join(codes)

        # Full job description text — concatenate all QualificationSummary fields
        qual = mv.get("QualificationSummary", "")
        user_area_desc = (
            mv.get("UserArea", {})
              .get("Details", {})
              .get("JobSummary", "")
        )
        description = (qual + "\n\n" + user_area_desc).strip() or "(No description available)"

        jobs.append({
            "id":          mv.get("PositionID", ""),
            "title":       mv.get("PositionTitle", ""),
            "agency":      mv.get("OrganizationName", mv.get("DepartmentName", "")),
            "location":    location,
            "grade":       grade_str,
            "url":         mv.get("PositionURI", ""),
            "description": description,
        })

    return {"jobs": jobs}
