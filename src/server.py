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
    extracted skill tokens.

    Expected input:
        resume_text, service_branch, specialty_code, target_role, career_path

    Returns:
        { summary, bullets[], resume_skills[] }
    """
    resume_text: str = inp.get("resume_text", "").strip()
    target_role: str = inp.get("target_role", "general civilian")

    if not resume_text:
        return {"error": "resume_text is required"}

    # ── Parse the resume into sections ──────────────────────────────────────
    summary_text, exp_texts, resume_skills = _parse_resume(resume_text)

    if not summary_text and not exp_texts:
        return {"error": "Could not identify any content in the resume."}

    if not summary_text and exp_texts:
        summary_text = exp_texts.pop(0)

    # ── Translate each experience block ──────────────────────────────────────
    bullets: list[str] = []
    for block in exp_texts:
        result = translate_accomplishment(
            bullet=block,
            target_role=target_role,
        )
        if result.get("error"):
            return {"error": result["error"]}
        if result.get("pii_warning"):
            return {"error": result["pii_warning"]}
        translated = result.get("translated_bullet") or block
        bullets.append(translated)

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
    raw_skills = result.get("skills") or []
    skills = [
        {
            "skill_name": s.get("skill", s.get("skill_name", "")),
            "category":   s.get("category", ""),
            "confidence": "High" if not s.get("evidence", "").startswith("O*NET crosswalk") else "Medium",
            "evidence":   s.get("evidence", ""),
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

    if result.get("error"):
        return {"error": result["error"]}
    if result.get("pii_warning"):
        return {"error": result["pii_warning"]}

    gap_skills = result.get("gap_skills") or []
    covered    = result.get("covered_skills") or []

    # Normalize gap_skills to the shape the frontend renders
    # frontend expects: [{skill_name, priority, courses[{title, credential_type, hours_estimate, url}]}]
    sb_recs = {
        c["course_title"]: c
        for c in (result.get("skillsbuild_recommendations") or [])
    }

    gap_skills_normalized = []
    for skill in gap_skills:
        # Find any course that tags this skill
        matching_courses = [
            {
                "title":            c["course_title"],
                "credential_type":  c.get("credential", "Badge"),
                "hours_estimate":   c.get("estimated_hours", 0),
                "url":              c.get("url", "https://skillsbuild.org"),
            }
            for c in (result.get("skillsbuild_recommendations") or [])
            if any(skill.lower() in tag.lower() or tag.lower() in skill.lower()
                   for tag in c.get("skill_tags", []))
        ]
        gap_skills_normalized.append({
            "skill_name": skill,
            "priority":   "High",
            "courses":    matching_courses[:2],
        })

    return {
        "gap_skills":                 gap_skills_normalized,
        "matched_skills":             covered,
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

    inferred = draft.get("inferred_count", 0)
    missing  = draft.get("missing_count", 0)
    warnings = draft.get("grounding_warnings", [])

    result = evaluate_export_gate(
        inferred_count=inferred,
        missing_count=missing,
        grounding_downgrade_count=len(warnings),
        gate_holds_json="[]",
    )

    holds = result.get("holds", [])
    return {
        "gate_status":     result.get("gate_status", "BLOCKED"),
        "summary_message": result.get("message", ""),
        "gate_holds": [
            {"tag": "INFERRED" if "INFERRED" in h else "MISSING", "text": h}
            for h in holds
        ],
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
    This mirrors the mock parser but runs server-side so the AI can work on
    clean, pre-structured input.
    """
    import re

    HEADER_RE  = re.compile(r'^[A-Za-z0-9 &/\-]{1,50}:?\s*$')
    SKILLS_HDR = re.compile(r'\b(skill|qualification|certification|competenc|proficienc|technical|tool|technolog)', re.IGNORECASE)

    lines   = text.split('\n')
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
        is_skills = bool(SKILLS_HDR.search(b['hint'])) or (
            b['lines'] and
            sum(1 for l in b['lines'] if len(l.split()) <= 5) / len(b['lines']) >= 0.7
        )
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

        block_text = ' '.join(b['lines'])
        if not summary_text:
            summary_text = block_text
        elif len(block_text) > 15:
            exp_texts.append(block_text)

    return summary_text, exp_texts, skill_tokens
