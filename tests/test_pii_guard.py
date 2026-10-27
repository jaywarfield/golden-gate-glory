# tests/test_pii_guard.py
# Mission Veteran AI — a Golden Gate Glory project
# Unit tests: PII detection guard in toolkits/shared/_common.py
#
# Run with:   pytest tests/test_pii_guard.py -v

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from toolkits.shared._common import contains_pii, pii_warning_message


# ---------------------------------------------------------------------------
# Positive cases — PII SHOULD be detected
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,label", [
    ("SSN is 123-45-6789",                          "SSN pattern"),
    ("DoD ID: 1234567890",                          "10-digit DoD ID"),
    ("contact me at john.doe@example.com",          "email address"),
    ("call 555-867-5309",                           "phone number (dash)"),
    ("call (555) 867-5309",                         "phone number (parens)"),
    ("call 555.867.5309",                           "phone number (dots)"),
    ("I live at 123 Main Street",                   "street address"),
    ("123 Oak Avenue was my address",               "avenue address"),
])
def test_contains_pii_detected(text, label):
    assert contains_pii(text), f"Expected PII detection for: {label}"


# ---------------------------------------------------------------------------
# Negative cases — clean text SHOULD NOT be flagged
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,label", [
    ("Led a 12-person logistics team supporting time-sensitive supply operations",
     "normal service summary"),
    ("Managed $4.2M in equipment across multiple sites",
     "dollar amounts are not PII"),
    ("Improved on-time delivery from 82% to 96% over 18 months",
     "percentages are not PII"),
    ("Redesigned maintenance scheduling to reduce backlog 38% in 90 days",
     "clean accomplishment bullet"),
    ("Army 92A Automated Logistical Specialist",
     "MOS code is not PII"),
    ("Coordinated with 3 cross-functional teams",
     "team count is not PII"),
    ("Earned top readiness rating for 3 consecutive cycles",
     "rating text is not PII"),
])
def test_contains_pii_clean(text, label):
    assert not contains_pii(text), f"False positive PII detection for: {label}"


# ---------------------------------------------------------------------------
# PII warning message
# ---------------------------------------------------------------------------

def test_pii_warning_message_is_string():
    msg = pii_warning_message()
    assert isinstance(msg, str)
    assert len(msg) > 20


def test_pii_warning_message_mentions_ssn():
    assert "Social Security" in pii_warning_message()


def test_pii_warning_message_mentions_dod():
    assert "DoD" in pii_warning_message()
