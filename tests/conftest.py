"""Shared test fixtures and helpers.

Centralizes boilerplate that was previously duplicated across test files.
"""

import sys
from unittest import mock

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
