# tests/test_skill_mapper.py
# Mission Veteran AI — a Golden Gate Glory project
# Unit tests: map_military_skills — input validation, PII guard, output schema.
# LLM call is mocked — no live API calls or credentials required.
#
# Run with:   pytest tests/test_skill_mapper.py -v

import json
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Helpers — build a minimal mock toolkit response
# ---------------------------------------------------------------------------

_MOCK_SKILLS = [
    {
        "skill_name": "Logistics Coordination",
        "category": "Operations",
        "evidence": "Led a 12-person logistics team supporting time-sensitive supply operations",
    },
    {
        "skill_name": "Inventory Management",
        "category": "Supply Chain",
        "evidence": "Managed $4.2M in equipment",
    },
    {
        "skill_name": "Team Leadership",
        "category": "Leadership",
        "evidence": "O*NET crosswalk: Logistician",
    },
]


def _mock_model_response(skills=None):
    """Return a mock ModelInference that returns a JSON skill array."""
    if skills is None:
        skills = _MOCK_SKILLS
    mock_model = MagicMock()
    mock_model.generate_text.return_value = json.dumps(skills)
    return mock_model


_VALID_ARGS = dict(
    service_branch="Army",
    specialty_code="92A",
    service_summary=(
        "Led a 12-person logistics team supporting time-sensitive supply operations "
        "across multiple sites. Managed $4.2M in equipment and improved on-time "
        "delivery from 82% to 96%."
    ),
    target_career_path="Logistics",
)


# ---------------------------------------------------------------------------
# PII guard — no LLM call made
# ---------------------------------------------------------------------------

def test_map_skills_pii_detected_ssn():
    from toolkits.skill_mapper.map_military_skills import map_military_skills
    result = map_military_skills(
        service_branch="Army",
        specialty_code="92A",
        service_summary="SSN 123-45-6789 led a logistics team.",
        target_career_path="Logistics",
    )
    assert result["pii_warning"] is not None
    assert result["error"] is None
    assert result["skills"] is None


def test_map_skills_pii_detected_email():
    from toolkits.skill_mapper.map_military_skills import map_military_skills
    result = map_military_skills(
        service_branch="Army",
        specialty_code="92A",
        service_summary="Contact me at soldier@army.mil for details.",
        target_career_path="Logistics",
    )
    assert result["pii_warning"] is not None


# ---------------------------------------------------------------------------
# Output schema — mock the LLM, validate all returned keys
# ---------------------------------------------------------------------------

@patch("toolkits.skill_mapper.map_military_skills.ModelInference")
@patch("toolkits.skill_mapper.map_military_skills.APIClient")
@patch("toolkits.skill_mapper.map_military_skills.get_credentials",
       return_value={"api_key": "x", "url": "https://x", "project_id": "x"})
@patch("toolkits.skill_mapper.map_military_skills.log_inference")
@patch("toolkits.skill_mapper.map_military_skills.get_subscription_ids", return_value={})
def test_map_skills_output_schema(mock_subs, mock_log, mock_creds, mock_client, mock_model_cls):
    mock_model_cls.return_value = _mock_model_response()
    from toolkits.skill_mapper.map_military_skills import map_military_skills
    result = map_military_skills(**_VALID_ARGS)

    assert result["error"] is None
    assert result["pii_warning"] is None
    assert isinstance(result["skills"], list)
    assert result["skill_count"] == len(result["skills"])
    assert isinstance(result["evidence_sourced_count"], int)
    assert isinstance(result["disclaimer"], str)


@patch("toolkits.skill_mapper.map_military_skills.ModelInference")
@patch("toolkits.skill_mapper.map_military_skills.APIClient")
@patch("toolkits.skill_mapper.map_military_skills.get_credentials",
       return_value={"api_key": "x", "url": "https://x", "project_id": "x"})
@patch("toolkits.skill_mapper.map_military_skills.log_inference")
@patch("toolkits.skill_mapper.map_military_skills.get_subscription_ids", return_value={})
def test_map_skills_each_skill_has_required_keys(mock_subs, mock_log, mock_creds, mock_client, mock_model_cls):
    mock_model_cls.return_value = _mock_model_response()
    from toolkits.skill_mapper.map_military_skills import map_military_skills
    result = map_military_skills(**_VALID_ARGS)

    for skill in result["skills"]:
        assert "skill_name" in skill, f"Missing skill_name in: {skill}"
        assert "category" in skill, f"Missing category in: {skill}"
        assert "evidence" in skill, f"Missing evidence in: {skill}"


@patch("toolkits.skill_mapper.map_military_skills.ModelInference")
@patch("toolkits.skill_mapper.map_military_skills.APIClient")
@patch("toolkits.skill_mapper.map_military_skills.get_credentials",
       return_value={"api_key": "x", "url": "https://x", "project_id": "x"})
@patch("toolkits.skill_mapper.map_military_skills.log_inference")
@patch("toolkits.skill_mapper.map_military_skills.get_subscription_ids", return_value={})
def test_map_skills_evidence_sourced_count_correct(mock_subs, mock_log, mock_creds, mock_client, mock_model_cls):
    # 2 of 3 mock skills have direct text evidence; 1 is O*NET crosswalk
    mock_model_cls.return_value = _mock_model_response()
    from toolkits.skill_mapper.map_military_skills import map_military_skills
    result = map_military_skills(**_VALID_ARGS)

    # evidence_sourced_count counts skills whose evidence does NOT start with "O*NET crosswalk:"
    assert result["evidence_sourced_count"] == 2


# ---------------------------------------------------------------------------
# LLM error path — model raises, error returned gracefully
# ---------------------------------------------------------------------------

@patch("toolkits.skill_mapper.map_military_skills.ModelInference")
@patch("toolkits.skill_mapper.map_military_skills.APIClient")
@patch("toolkits.skill_mapper.map_military_skills.get_credentials",
       return_value={"api_key": "x", "url": "https://x", "project_id": "x"})
@patch("toolkits.skill_mapper.map_military_skills.log_inference")
@patch("toolkits.skill_mapper.map_military_skills.get_subscription_ids", return_value={})
def test_map_skills_model_error_returns_error_key(mock_subs, mock_log, mock_creds, mock_client, mock_model_cls):
    mock_instance = MagicMock()
    mock_instance.generate_text.side_effect = RuntimeError("connection refused")
    mock_model_cls.return_value = mock_instance
    from toolkits.skill_mapper.map_military_skills import map_military_skills
    result = map_military_skills(**_VALID_ARGS)

    assert result["error"] is not None
    assert "connection refused" in result["error"]
    assert result["skills"] is None
