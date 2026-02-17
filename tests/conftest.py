"""Shared test fixtures and helpers.

Centralizes boilerplate that was previously duplicated across test files.
"""

import sys
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# reportlab mock — must run at module level before test modules are collected.
# Several test files import from haytham.agents.tools, whose __init__.py
# triggers an import chain that eventually reaches pdf_report.py (which
# imports reportlab at the top level).  reportlab is an optional dependency
# not installed in the test environment.
# ---------------------------------------------------------------------------

_REPORTLAB_SUBMODULES = [
    "reportlab",
    "reportlab.lib",
    "reportlab.lib.colors",
    "reportlab.lib.pagesizes",
    "reportlab.lib.styles",
    "reportlab.lib.units",
    "reportlab.lib.enums",
    "reportlab.platypus",
    "reportlab.platypus.doctemplate",
    "reportlab.platypus.frames",
    "reportlab.platypus.paragraph",
    "reportlab.platypus.spacer",
    "reportlab.platypus.table",
    "reportlab.platypus.flowables",
    "reportlab.pdfgen",
]

if "reportlab" not in sys.modules:
    _rl_mock = mock.MagicMock()
    for _sub in _REPORTLAB_SUBMODULES:
        sys.modules.setdefault(_sub, _rl_mock)


# ---------------------------------------------------------------------------
# Synthetic fixtures for test_agent_output_quality.py
#
# These provide minimal but realistic data that exercises the validation
# logic in the quality tests.  They can be overridden in a local
# conftest.py or by a recorded-fixtures conftest to test against real
# agent output.
# ---------------------------------------------------------------------------

_SYNTHETIC_MVP_SCOPE = """\
# MVP Scope — Gym Leaderboard

## IN SCOPE (MVP v1)
- User registration and login
- Workout logging
- Leaderboard ranking

## OUT OF SCOPE (Future)
- Social messaging
- Video coaching
- Payment processing

## User Flows

### Flow 1: Register and Log Workout
**Trigger:** User opens app for the first time
1. User creates account
2. User logs a workout
3. System records workout data

### Flow 2: View Leaderboard
**Trigger:** User taps leaderboard tab
1. System calculates rankings
2. User views top performers
3. User filters by workout type
"""

_SYNTHETIC_CAPABILITY_MODEL = {
    "capabilities": {
        "functional": [
            {
                "id": "CAP-001",
                "name": "User Authentication",
                "serves_scope_item": "User registration and login",
                "user_flow": "Flow 1",
            },
            {
                "id": "CAP-002",
                "name": "Workout Recording",
                "serves_scope_item": "Workout logging",
                "user_flow": "Flow 1",
            },
            {
                "id": "CAP-003",
                "name": "Ranking Engine",
                "serves_scope_item": "Leaderboard ranking",
                "user_flow": "Flow 2",
            },
        ],
        "non_functional": [
            {"id": "NFR-001", "name": "Sub-second leaderboard load"},
        ],
    }
}

_SYNTHETIC_BUILD_BUY = {
    "recommended_stack": [
        {
            "name": "Supabase",
            "category": "Authentication & Database",
            "capabilities_served": ["CAP-001", "CAP-002"],
            "rationale": "Provides auth and Postgres in one managed service.",
        },
        {
            "name": "Vercel",
            "category": "Hosting & Deployment",
            "capabilities_served": ["CAP-001", "CAP-002", "CAP-003"],
            "rationale": "Zero-config deployment for web applications.",
        },
        {
            "name": "Upstash Redis",
            "category": "Caching",
            "capabilities_served": ["CAP-003"],
            "rationale": "Serverless Redis for low-latency leaderboard queries.",
        },
    ],
    "alternatives": [
        {
            "for": "Authentication & Database",
            "alternatives": [
                {"name": "Firebase", "rationale": "Good alternative with real-time DB."},
            ],
        },
    ],
}


@pytest.fixture
def mvp_scope():
    """Synthetic MVP scope for agent output quality tests."""
    return _SYNTHETIC_MVP_SCOPE


@pytest.fixture
def capability_model():
    """Synthetic capability model for agent output quality tests."""
    return _SYNTHETIC_CAPABILITY_MODEL


@pytest.fixture
def build_buy_output():
    """Synthetic build/buy output for agent output quality tests."""
    return _SYNTHETIC_BUILD_BUY
