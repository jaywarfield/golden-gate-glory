# toolkits/shared/_common.py
# Mission Veteran AI
# Shared utilities — PII guard + credential helper
# Used by all four toolkits.

import os
import re

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
    return {
        "api_key": os.environ["WATSONX_API_KEY"],
        "url": os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com"),
        "project_id": os.environ["WATSONX_PROJECT_ID"],
    }
