"""Factory functions that build ReportConfig from session data.

Each report type (idea validation, MVP spec, etc.) has its own factory
function.  Adding a new report type requires only a new factory here —
zero changes to pdf_report.py.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from .metric_patterns import (
    RE_COMPOSITE,
    RE_CONFIDENCE,
    RE_RECOMMENDATION,
    RE_RISK_LEVEL,
)
from .pdf_report import (
    CoverConfig,
    ReportConfig,
    ReportSection,
    SectionType,
)

_HEADING_RE = re.compile(r"^(#{2,3})\s+", re.MULTILINE)

# Keywords for MI sections that overlap with Competitive Landscape
_MI_OVERLAP_KEYWORDS = re.compile(
    r"competitor|competitive|switching|sentiment|opportunit",
    re.IGNORECASE,
)

# Keywords for Concept Expansion sections already rendered elsewhere
_CE_STRIP_KEYWORDS = re.compile(r"Lean Canvas|Concept Health", re.IGNORECASE)

# Sections to strip from Risk Assessment (redundant with scorecard)
_RA_STRIP_KEYWORDS = re.compile(r"Human Summary", re.IGNORECASE)

# Confirmation Bias Check / Pre-Submission Validation (metadata, not insight)
_BIAS_CHECK_KEYWORDS = re.compile(r"Confirmation Bias|Pre-Submission", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _strip_sections(text: str, keyword_pattern: re.Pattern[str]) -> str:
    """Remove markdown sections whose headings match a keyword pattern.

    Strips H2/H3 headings and all nested content below them until the
    next heading at the same or higher level.  Used at report-assembly
    time only — session files retain the full text.
    """
    lines = text.split("\n")
    result: list[str] = []
    skip = False
    skip_level = 0
    for line in lines:
        heading_match = _HEADING_RE.match(line)
        if heading_match:
            level = len(heading_match.group(1))
            if keyword_pattern.search(line):
                skip = True
                skip_level = level
                continue
            elif skip and level <= skip_level:
                skip = False
        if not skip:
            result.append(line)
    return "\n".join(result).strip()


def _load_markdown(session_dir: Path, stage_slug: str, filename: str) -> str | None:
    """Load a markdown file from a stage directory, stripping output headers."""
    path = session_dir / stage_slug / filename
    if not path.exists():
        return None
    text = path.read_text()
    # Strip leading "# Output" or "# <Title>" header
    text = re.sub(r"^#+ Output\s*\n+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^# (?!#).+\n+", "", text.strip())
    return text.strip() or None


def _load_system_goal(session_dir: Path) -> str:
    """Load the startup idea text from project.yaml."""
    project_file = session_dir / "project.yaml"
    if project_file.exists():
        try:
            data = yaml.safe_load(project_file.read_text())
            return data.get("system_goal", "")
        except (yaml.YAMLError, OSError):
            pass
    return ""


def _extract_verdict(summary_text: str | None, session_dir: Path) -> str | None:
    """Extract recommendation verdict (GO / NO-GO / PIVOT)."""
    # Try recommendation.json first
    meta_path = session_dir / "recommendation.json"
    if meta_path.exists():
        try:
            data = json.loads(meta_path.read_text())
            rec = data.get("recommendation", "").upper().strip()
            if rec in ("GO", "NO-GO", "PIVOT"):
                return rec
        except (json.JSONDecodeError, OSError):
            pass
    # Fallback to regex
    if summary_text:
        m = RE_RECOMMENDATION.search(summary_text)
        if m:
            return m.group(1).upper()
    return None


def _extract_section(text: str, heading: str) -> str | None:
    """Extract the body of a markdown section by ## heading."""
    pattern = rf"^## {re.escape(heading)}\s*\n(.*?)(?=\n## |\Z)"
    m = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    return m.group(1).strip() if m else None


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------


def _build_executive_summary(summary_text: str, verdict: str | None) -> list[ReportSection]:
    """Build Executive Summary + metric badges."""

    sections: list[ReportSection] = []

    # Executive summary text (metric badges moved to cover page)
    exec_text = _extract_section(summary_text, "Executive Summary")
    if exec_text:
        sections.append(ReportSection("Executive Summary", SectionType.MARKDOWN, exec_text))

    return sections


def _build_problem_analysis(session_dir: Path) -> ReportSection | None:
    """Build Problem & User Analysis section from concept expansion."""

    text = _load_markdown(session_dir, "idea-analysis", "concept_expansion.md")
    if not text:
        return None
    text = _strip_sections(text, _CE_STRIP_KEYWORDS)
    if not text:
        return None
    return ReportSection("Problem & User Analysis", SectionType.MARKDOWN, text)


def _build_market_context(session_dir: Path) -> ReportSection | None:
    """Build Market Context section."""

    text = _load_markdown(session_dir, "market-context", "market_intelligence.md")
    if not text:
        return None
    # Strip leading "## Market Intelligence" heading (redundant with section title)
    text = re.sub(r"^## Market Intelligence\s*\n+", "", text)
    text = _strip_sections(text, _MI_OVERLAP_KEYWORDS)
    text = _strip_sections(text, _BIAS_CHECK_KEYWORDS)
    if not text:
        return None
    return ReportSection("Market Context", SectionType.MARKDOWN, text)


def _build_competitive_landscape(session_dir: Path) -> ReportSection | None:
    """Build Competitive Landscape section."""

    text = _load_markdown(session_dir, "market-context", "competitor_analysis.md")
    if not text:
        return None
    text = _strip_sections(text, _BIAS_CHECK_KEYWORDS)
    if not text:
        return None
    return ReportSection("Competitive Landscape", SectionType.MARKDOWN, text)


def _build_risk_assessment(session_dir: Path) -> ReportSection | None:
    """Build Risk Assessment section."""

    text = _load_markdown(session_dir, "risk-assessment", "startup_validator.md")
    if not text:
        return None
    text = _strip_sections(text, _RA_STRIP_KEYWORDS)
    if not text:
        return None
    return ReportSection("Risk Assessment", SectionType.MARKDOWN, text)


def _build_scorecard(summary_text: str) -> ReportSection | None:
    """Build Go/No-Go Scorecard section."""

    scorecard = _extract_section(summary_text, "Go/No-Go Scorecard")
    if not scorecard:
        return None
    return ReportSection("Go/No-Go Scorecard", SectionType.SCORECARD, scorecard)


def _build_next_steps(summary_text: str) -> ReportSection | None:
    """Build Next Steps section."""

    steps = _extract_section(summary_text, "Next Steps")
    if not steps:
        return None
    return ReportSection("Next Steps", SectionType.MARKDOWN, steps)


def _build_pivot_strategy(session_dir: Path) -> ReportSection | None:
    """Build Pivot Strategy section (only present if HIGH risk)."""

    text = _load_markdown(session_dir, "pivot-strategy", "pivot_strategy.md")
    if not text:
        return None
    return ReportSection("Pivot Strategy", SectionType.MARKDOWN, text)


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------


def build_idea_validation_config(session_dir: Path) -> ReportConfig:
    """Build a complete ReportConfig for the Idea Validation report.

    Args:
        session_dir: Path to the session directory containing stage outputs.

    Returns:
        ReportConfig ready to pass to generate_pdf().
    """

    idea_text = _load_system_goal(session_dir)
    summary_text = _load_markdown(session_dir, "validation-summary", "validation_scorer.md")
    validator_text = _load_markdown(session_dir, "risk-assessment", "startup_validator.md")

    # Extract cover-page data
    verdict = _extract_verdict(summary_text, session_dir)
    composite_score = None
    risk_level = None

    if summary_text:
        m = RE_COMPOSITE.search(summary_text)
        if m:
            composite_score = m.group(1)

    if validator_text:
        m = RE_RISK_LEVEL.search(validator_text)
        if m:
            risk_level = m.group(1).upper()

    confidence = None
    if summary_text:
        m = RE_CONFIDENCE.search(summary_text)
        if m:
            confidence = m.group(1).upper()

    cover = CoverConfig(
        title="Idea Validation Report",
        idea_text=idea_text,
        verdict=verdict,
        composite_score=composite_score,
        risk_level=risk_level,
        confidence=confidence,
    )

    # Build sections in order
    sections: list[ReportSection] = []

    if summary_text:
        sections.extend(_build_executive_summary(summary_text, verdict))

    problem = _build_problem_analysis(session_dir)
    if problem:
        sections.append(problem)

    market = _build_market_context(session_dir)
    if market:
        sections.append(market)

    competitive = _build_competitive_landscape(session_dir)
    if competitive:
        sections.append(competitive)

    risk = _build_risk_assessment(session_dir)
    if risk:
        sections.append(risk)

    if summary_text:
        scorecard = _build_scorecard(summary_text)
        if scorecard:
            sections.append(scorecard)

    pivot = _build_pivot_strategy(session_dir)

    # Next Steps is redundant when Pivot Strategy exists (it has its own next steps)
    if not pivot and summary_text:
        steps = _build_next_steps(summary_text)
        if steps:
            sections.append(steps)

    if pivot:
        sections.append(pivot)

    return ReportConfig(cover=cover, sections=sections)
