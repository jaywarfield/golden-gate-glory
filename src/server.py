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
        translate_resume  → parse_resume_text (internal) + translate_accomplishment (per bullet)
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

    # ── Translate each experience block ──────────────────────────────────────
    def _clean_bullet(text: str) -> str:
        """Strip markdown artefacts and deduplicate repeated sentences."""
        # Remove leading list markers: *, -, •, –
        text = _re.sub(r'^\s*[\*\-\•\–]\s+', '', text.strip())
        # Remove any trailing lines that start with # (markdown headings / comments)
        lines = text.splitlines()
        clean_lines = []
        for line in lines:
            if _re.match(r'^\s*#+\s*', line):
                break  # stop at first heading-style line; discard it and everything after
            clean_lines.append(line)
        text = ' '.join(clean_lines).strip()

        # Keep only the FIRST sentence — the prompt asks for one sentence and
        # stops, but as a hard backstop discard everything after the first
        # sentence-ending punctuation followed by a capital letter or end of string.
        first = _re.split(r'(?<=[.!?])\s+(?=[A-Z])', text, maxsplit=1)[0].strip()
        return first

    # Translate only the experience blocks extracted from the resume — no fabrication.
    # If the LLM returns "SKIP" (too vague to translate faithfully), drop that bullet.
    bullets: list[str] = []
    for block in exp_texts:
        result = translate_accomplishment(bullet=block, target_role=target_role)
        if result.get("error"):
            return {"error": result["error"]}
        if result.get("pii_warning"):
            return {"error": result["pii_warning"]}
        raw_bullet = result.get("translated_bullet") or block
        cleaned = _clean_bullet(raw_bullet)
        if cleaned.strip().upper() == "SKIP":
            continue
        bullets.append(cleaned)

    # ── Merge O*NET skills for the specialty code ────────────────────────────
    # Look up the crosswalk entry for this specialty code and pull skills from
    # the matching O*NET occupation record. Deduplicate against resume_skills.
    from shared._common import lookup_crosswalk, load_onet_occupation_skills

    onet_skills: list[str] = []
    crosswalk_hits = lookup_crosswalk(specialty_code, service_branch)
    if crosswalk_hits:
        onet_soc = crosswalk_hits[0].get("onet_soc")
        civilian_title = crosswalk_hits[0].get("civilian_title", "")
        onet_records = load_onet_occupation_skills()

        # Match by onet_soc first, then by career_path as fallback
        occ = next((r for r in onet_records if r.get("onet_soc") == onet_soc), None)
        if not occ and career_path:
            occ = next((r for r in onet_records if r.get("career_path") == career_path), None)

        if occ:
            onet_skills = occ.get("required_skills", [])

    # Merge: resume_skills first, then O*NET skills not already present
    seen_lower = {s.lower() for s in resume_skills}
    for skill in onet_skills:
        if skill.lower() not in seen_lower:
            resume_skills.append(skill)
            seen_lower.add(skill.lower())

    return {
        "summary":       summary_text,
        "bullets":       bullets,
        "resume_skills": resume_skills,
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
    Lightweight resume parser: strip headers, group into blocks, classify as
    summary / experience / skills.  Returns (summary_text, exp_texts, skill_tokens).
    """
    import re

    HEADER_RE  = re.compile(r'^[A-Za-z0-9 &/\-]{1,50}:?\s*$')
    SKILLS_HDR = re.compile(r'\b(skill|qualification|certification|competenc|proficienc|technical|tool|technolog)', re.IGNORECASE)
    # Inline label pattern: "Label Title: content" or "Label Title:\xa0content"
    # Captures everything after the first colon+space/nbsp as the real content.
    INLINE_LABEL = re.compile(r'^[A-Za-z0-9 &/\-]{2,50}[:\uff1a][\s\xa0]+(.+)$')

    def _split_line(raw_line: str) -> list[str]:
        """
        Normalise a single resume line into one or more content strings:
        1. Replace non-breaking spaces (\xa0) and other Unicode spaces with regular space.
        2. Strip inline section labels ("Label: content" → "content").
        3. Split on bullet characters (•, ·, –, —) that separate packed sub-items.
        """
        # Normalise whitespace variants to regular space
        line = raw_line.replace('\xa0', ' ').replace('\u2009', ' ').replace('\u200b', '').strip()
        # Strip inline label prefix if present
        m = INLINE_LABEL.match(line)
        if m:
            line = m.group(1).strip()
        # Split on mid-line bullet separators that pack multiple items onto one line
        parts = re.split(r'\s*[•·–—]\s*', line)
        return [p.strip() for p in parts if len(p.strip()) >= 10]

    # Normalise the whole text: replace \xa0 in line splitting too
    lines = text.replace('\xa0', ' ').split('\n')
    last_hdr = ''
    blocks: list[dict] = []
    cur: dict | None = None

    for raw in lines:
        t = raw.strip()
        if not t:
            if cur and cur['lines']:
                blocks.append(cur); cur = None
            continue
        if HEADER_RE.match(t):
            if cur and cur['lines']:
                blocks.append(cur); cur = None
            last_hdr = t.rstrip(':').lower()
            continue
        if cur is None:
            cur = {'hint': last_hdr, 'lines': []}
        cur['lines'].append(t)

    if cur and cur['lines']:
        blocks.append(cur)

    summary_text = ''
    exp_texts: list[str] = []
    skill_tokens: list[str] = []
    seen: set[str] = set()

    for b in blocks:
        has_skills_hint = bool(SKILLS_HDR.search(b['hint']))
        short_line_ratio = (
            sum(1 for l in b['lines'] if len(l.split()) <= 3) / len(b['lines'])
            if b['lines'] else 0
        )
        is_skills = has_skills_hint or (not has_skills_hint and short_line_ratio >= 0.7)
        if is_skills:
            for l in b['lines']:
                for tok in re.split(r'[,;•·\-–]\s*', l):
                    tok = tok.strip()
                    if 1 < len(tok) < 60:
                        key = tok.lower()
                        if key not in seen:
                            seen.add(key)
                            skill_tokens.append(tok)
            continue

        # Expand each raw line into content fragments (strip inline labels,
        # split on packed bullet separators, normalise whitespace).
        # First fragment overall → summary_text; all others → exp_texts.
        for raw_line in b['lines']:
            for fragment in _split_line(raw_line):
                if not summary_text:
                    summary_text = fragment
                else:
                    exp_texts.append(fragment)

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
