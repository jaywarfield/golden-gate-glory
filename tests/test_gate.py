# tests/test_gate.py
# Mission Veteran AI — a Golden Gate Glory project
# Unit tests: evaluate_export_gate in toolkits/plan_builder/build_plan.py
#
# No live API calls — gate is pure logic with no LLM dependency.
#
# Run with:   pytest tests/test_gate.py -v

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from toolkits.plan_builder.build_plan import evaluate_export_gate


# ---------------------------------------------------------------------------
# Gate OPEN cases
# ---------------------------------------------------------------------------

def test_gate_open_all_clean():
    result = evaluate_export_gate(
        inferred_count=0,
        missing_count=0,
        grounding_downgrade_count=0,
    )
    assert result["gate_status"] == "OPEN"
    assert result["holds"] == []
    assert result["grounding_downgrade_count"] == 0
    assert "OPEN" in result["message"]


def test_gate_open_message_mentions_grounding():
    result = evaluate_export_gate(inferred_count=0, missing_count=0)
    assert "grounding" in result["message"].lower()


# ---------------------------------------------------------------------------
# Gate BLOCKED — individual triggers
# ---------------------------------------------------------------------------

def test_gate_blocked_by_inferred():
    result = evaluate_export_gate(
        inferred_count=2,
        missing_count=0,
        grounding_downgrade_count=0,
    )
    assert result["gate_status"] == "BLOCKED"
    assert any("INFERRED" in h for h in result["holds"])
    assert len(result["holds"]) == 1


def test_gate_blocked_by_missing():
    result = evaluate_export_gate(
        inferred_count=0,
        missing_count=1,
        grounding_downgrade_count=0,
    )
    assert result["gate_status"] == "BLOCKED"
    assert any("MISSING" in h for h in result["holds"])


def test_gate_blocked_by_grounding_downgrade():
    result = evaluate_export_gate(
        inferred_count=0,
        missing_count=0,
        grounding_downgrade_count=3,
    )
    assert result["gate_status"] == "BLOCKED"
    assert result["grounding_downgrade_count"] == 3
    # Grounding holds surface FIRST
    assert "grounding" in result["holds"][0].lower()


# ---------------------------------------------------------------------------
# Gate BLOCKED — combined triggers
# ---------------------------------------------------------------------------

def test_gate_blocked_all_three():
    result = evaluate_export_gate(
        inferred_count=1,
        missing_count=2,
        grounding_downgrade_count=1,
    )
    assert result["gate_status"] == "BLOCKED"
    # Should have 3 holds: grounding + inferred + missing
    assert len(result["holds"]) == 3
    # Grounding hold is first
    assert "grounding" in result["holds"][0].lower()


def test_gate_blocked_message_mentions_grounding():
    result = evaluate_export_gate(
        inferred_count=1,
        missing_count=0,
        grounding_downgrade_count=1,
    )
    assert "grounding" in result["message"].lower()


# ---------------------------------------------------------------------------
# Explicit holds JSON passthrough
# ---------------------------------------------------------------------------

def test_gate_explicit_holds_appended():
    explicit = json.dumps(["Custom hold from reviewer"])
    result = evaluate_export_gate(
        inferred_count=0,
        missing_count=0,
        grounding_downgrade_count=0,
        gate_holds_json=explicit,
    )
    assert result["gate_status"] == "BLOCKED"
    assert "Custom hold from reviewer" in result["holds"]


def test_gate_malformed_holds_json_handled():
    # Malformed JSON should not raise — falls back to []
    result = evaluate_export_gate(
        inferred_count=0,
        missing_count=0,
        gate_holds_json="not valid json",
    )
    assert result["gate_status"] == "OPEN"


# ---------------------------------------------------------------------------
# grounding_downgrade_count round-trips
# ---------------------------------------------------------------------------

def test_gate_open_returns_grounding_count_zero():
    result = evaluate_export_gate(inferred_count=0, missing_count=0)
    assert result["grounding_downgrade_count"] == 0


def test_gate_blocked_returns_correct_grounding_count():
    result = evaluate_export_gate(
        inferred_count=0,
        missing_count=0,
        grounding_downgrade_count=5,
    )
    assert result["grounding_downgrade_count"] == 5
