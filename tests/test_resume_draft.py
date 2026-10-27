# tests/test_resume_draft.py
# Mission Veteran AI — a Golden Gate Glory project
# Unit tests: build_resume_draft — PII guard, output schema, grounding warnings,
#             grounding_downgrade_count derivation.
# LLM calls are mocked — no live API calls or credentials required.
#
# Run with:   pytest tests/test_resume_draft.py -v

import json
import sys
import os
from unittest.mock import patch, MagicMock, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_VALID_SECTIONS = {
    "summary": [
        {"tag": "EVIDENCED", "text": "Results-driven supply chain professional."}
    ],
    "experience": [
        {"tag": "EVIDENCED", "text": "Led a 12-member logistics team."},
        {"tag": "INFERRED",  "text": "Applied lean methodology."},
        {"tag": "MISSING",   "text": "Managed ERP system configuration."},
    ],
    "skills": [
        {"tag": "EVIDENCED", "text": "Logistics Coordination"},
        {"tag": "EVIDENCED", "text": "Inventory Management"},
    ],
    "education_certifications": [],
}

# Grounding check that confirms all items
_ALL_CONFIRMED_VERDICTS = [
    {"section": "summary",    "index": 0, "verdict": "CONFIRMED", "reason": ""},
    {"section": "experience", "index": 0, "verdict": "CONFIRMED", "reason": ""},
    {"section": "skills",     "index": 0, "verdict": "CONFIRMED", "reason": ""},
    {"section": "skills",     "index": 1, "verdict": "CONFIRMED", "reason": ""},
]

# Grounding check that downgrades one EVIDENCED item
_ONE_DOWNGRADE_VERDICTS = [
    {"section": "summary",    "index": 0, "verdict": "CONFIRMED", "reason": ""},
    {"section": "experience", "index": 0, "verdict": "DOWNGRADE",
     "reason": "Claim not supported by service summary."},
    {"section": "skills",     "index": 0, "verdict": "CONFIRMED", "reason": ""},
    {"section": "skills",     "index": 1, "verdict": "CONFIRMED", "reason": ""},
]

_VALID_KWARGS = dict(
    service_branch="Army",
    specialty_code="92A",
    service_summary="Led a 12-member logistics team managing $2.1M inventory.",
    translated_bullets_json=json.dumps(["Led team improving delivery 82%→96%."]),
    skill_inventory_json=json.dumps([{"skill_name": "Logistics", "category": "Operations"}]),
    job_analysis_json=json.dumps({"required_skills": ["logistics"], "role_level": "Mid"}),
)


def _make_model_mock(draft_response, check_response):
    """Return a ModelInference class mock that returns different values per call."""
    instance = MagicMock()
    instance.generate_text.side_effect = [
        json.dumps(draft_response),
        json.dumps(check_response),
    ]
    return instance


_PATCHES = [
    patch("toolkits.plan_builder.build_plan.APIClient"),
    patch("toolkits.plan_builder.build_plan.get_credentials",
          return_value={"api_key": "x", "url": "https://x", "project_id": "x"}),
    patch("toolkits.plan_builder.build_plan.log_inference"),
    patch("toolkits.plan_builder.build_plan.get_subscription_ids", return_value={}),
]


def _apply_patches(test_fn):
    """Decorator that applies all non-model patches."""
    import functools
    @functools.wraps(test_fn)
    def wrapper(*args, **kwargs):
        patches = [p.start() for p in _PATCHES]
        try:
            return test_fn(*args, **kwargs)
        finally:
            for p in _PATCHES:
                p.stop()
    return wrapper


# ---------------------------------------------------------------------------
# PII guard — no LLM call made
# ---------------------------------------------------------------------------

def test_build_resume_pii_returns_warning():
    from toolkits.plan_builder.build_plan import build_resume_draft
    result = build_resume_draft(
        service_branch="Army",
        specialty_code="92A",
        service_summary="SSN 123-45-6789 led a logistics team.",
        translated_bullets_json="[]",
        skill_inventory_json="[]",
        job_analysis_json="{}",
    )
    assert result["pii_warning"] is not None
    assert result["resume_sections"] is None


# ---------------------------------------------------------------------------
# Output schema — all confirmed, no downgrades
# ---------------------------------------------------------------------------

@patch("toolkits.plan_builder.build_plan.ModelInference")
@patch("toolkits.plan_builder.build_plan.APIClient")
@patch("toolkits.plan_builder.build_plan.get_credentials",
       return_value={"api_key": "x", "url": "https://x", "project_id": "x"})
@patch("toolkits.plan_builder.build_plan.log_inference")
@patch("toolkits.plan_builder.build_plan.get_subscription_ids", return_value={})
def test_build_resume_output_schema(mock_subs, mock_log, mock_creds, mock_client, mock_model_cls):
    mock_model_cls.return_value = _make_model_mock(
        _VALID_SECTIONS, _ALL_CONFIRMED_VERDICTS
    )
    from toolkits.plan_builder.build_plan import build_resume_draft
    result = build_resume_draft(**_VALID_KWARGS)

    assert result["error"] is None
    assert result["pii_warning"] is None
    assert isinstance(result["resume_sections"], dict)
    assert "summary" in result["resume_sections"]
    assert "experience" in result["resume_sections"]
    assert "skills" in result["resume_sections"]
    assert isinstance(result["evidenced_count"], int)
    assert isinstance(result["inferred_count"], int)
    assert isinstance(result["missing_count"], int)
    assert isinstance(result["grounding_warnings"], list)
    assert isinstance(result["disclaimer"], str)


@patch("toolkits.plan_builder.build_plan.ModelInference")
@patch("toolkits.plan_builder.build_plan.APIClient")
@patch("toolkits.plan_builder.build_plan.get_credentials",
       return_value={"api_key": "x", "url": "https://x", "project_id": "x"})
@patch("toolkits.plan_builder.build_plan.log_inference")
@patch("toolkits.plan_builder.build_plan.get_subscription_ids", return_value={})
def test_build_resume_tag_counts_accurate(mock_subs, mock_log, mock_creds, mock_client, mock_model_cls):
    mock_model_cls.return_value = _make_model_mock(
        _VALID_SECTIONS, _ALL_CONFIRMED_VERDICTS
    )
    from toolkits.plan_builder.build_plan import build_resume_draft
    result = build_resume_draft(**_VALID_KWARGS)

    # _VALID_SECTIONS has: 3 EVIDENCED (summary[0], experience[0], skills[0,1]) = 4,
    # 1 INFERRED (experience[1]), 1 MISSING (experience[2])
    assert result["evidenced_count"] == 4
    assert result["inferred_count"] == 1
    assert result["missing_count"] == 1
    assert result["grounding_warnings"] == []


# ---------------------------------------------------------------------------
# Grounding check — one downgrade applied
# ---------------------------------------------------------------------------

@patch("toolkits.plan_builder.build_plan.ModelInference")
@patch("toolkits.plan_builder.build_plan.APIClient")
@patch("toolkits.plan_builder.build_plan.get_credentials",
       return_value={"api_key": "x", "url": "https://x", "project_id": "x"})
@patch("toolkits.plan_builder.build_plan.log_inference")
@patch("toolkits.plan_builder.build_plan.get_subscription_ids", return_value={})
def test_build_resume_grounding_downgrade_applied(mock_subs, mock_log, mock_creds, mock_client, mock_model_cls):
    mock_model_cls.return_value = _make_model_mock(
        _VALID_SECTIONS, _ONE_DOWNGRADE_VERDICTS
    )
    from toolkits.plan_builder.build_plan import build_resume_draft
    result = build_resume_draft(**_VALID_KWARGS)

    # experience[0] was EVIDENCED but got downgraded → INFERRED
    assert len(result["grounding_warnings"]) == 1
    w = result["grounding_warnings"][0]
    assert w["section"] == "experience"
    assert "Claim not supported" in w["reason"]
    # INFERRED count should now include the downgraded item
    assert result["inferred_count"] == 2  # original 1 + 1 downgraded


@patch("toolkits.plan_builder.build_plan.ModelInference")
@patch("toolkits.plan_builder.build_plan.APIClient")
@patch("toolkits.plan_builder.build_plan.get_credentials",
       return_value={"api_key": "x", "url": "https://x", "project_id": "x"})
@patch("toolkits.plan_builder.build_plan.log_inference")
@patch("toolkits.plan_builder.build_plan.get_subscription_ids", return_value={})
def test_build_resume_grounding_warning_has_required_keys(mock_subs, mock_log, mock_creds, mock_client, mock_model_cls):
    mock_model_cls.return_value = _make_model_mock(
        _VALID_SECTIONS, _ONE_DOWNGRADE_VERDICTS
    )
    from toolkits.plan_builder.build_plan import build_resume_draft
    result = build_resume_draft(**_VALID_KWARGS)

    for w in result["grounding_warnings"]:
        assert "section" in w
        assert "text" in w
        assert "reason" in w


# ---------------------------------------------------------------------------
# LLM error path
# ---------------------------------------------------------------------------

@patch("toolkits.plan_builder.build_plan.ModelInference")
@patch("toolkits.plan_builder.build_plan.APIClient")
@patch("toolkits.plan_builder.build_plan.get_credentials",
       return_value={"api_key": "x", "url": "https://x", "project_id": "x"})
@patch("toolkits.plan_builder.build_plan.log_inference")
@patch("toolkits.plan_builder.build_plan.get_subscription_ids", return_value={})
def test_build_resume_model_error_returns_error_key(mock_subs, mock_log, mock_creds, mock_client, mock_model_cls):
    mock_instance = MagicMock()
    mock_instance.generate_text.side_effect = RuntimeError("timeout")
    mock_model_cls.return_value = mock_instance
    from toolkits.plan_builder.build_plan import build_resume_draft
    result = build_resume_draft(**_VALID_KWARGS)

    assert result["error"] is not None
    assert "timeout" in result["error"]
    assert result["resume_sections"] is None
    assert result["evidenced_count"] == 0
    assert result["inferred_count"] == 0
    assert result["missing_count"] == 0
