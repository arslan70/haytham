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

from .metric_patterns import RE_COMPOSITE, RE_RISK_LEVEL
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


def _extract_verdict(session_dir: Path) -> str | None:
    """Extract recommendation verdict (GO / NO-GO / PIVOT) from recommendation.json."""
    meta_path = session_dir / "recommendation.json"
    if meta_path.exists():
        try:
            data = json.loads(meta_path.read_text())
            rec = data.get("recommendation", "").upper().strip()
            if rec in ("GO", "NO-GO", "PIVOT"):
                return rec
        except (json.JSONDecodeError, OSError):
            pass


def _extract_composite_score(session_dir: Path) -> str | None:
    """Extract composite score (e.g. '3.4') from report-synthesis markdown."""
    text = _load_markdown(session_dir, "report-synthesis", "report_synthesis.md")
    if not text:
        return None
    m = RE_COMPOSITE.search(text)
    return m.group(1) if m else None


def _extract_risk_level(session_dir: Path) -> str | None:
    """Extract overall risk level (HIGH/MEDIUM/LOW) from report-synthesis markdown."""
    text = _load_markdown(session_dir, "report-synthesis", "report_synthesis.md")
    if not text:
        return None
    m = RE_RISK_LEVEL.search(text)
    return m.group(1).upper() if m else None


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------


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


def _extract_executive_summary(session_dir: Path) -> dict:
    """Extract the structured executive summary from recommendation.json.

    Returns a dict with the 6 AT A GLANCE fields, or an empty dict
    if not available.
    """
    meta_path = session_dir / "recommendation.json"
    if meta_path.exists():
        try:
            data = json.loads(meta_path.read_text())
            summary = data.get("executive_summary", {})
            if isinstance(summary, dict) and summary:
                return summary
        except (json.JSONDecodeError, OSError):
            pass
    return {}


# Labels for the AT A GLANCE structured summary (order matters for PDF rendering)
_SUMMARY_FIELD_LABELS = [
    ("idea_in_one_line", "In a nutshell"),
    ("strongest_point", "Strongest point"),
    ("recommendation_summary", "Our call"),
    ("recommendation_reasoning", "The reason"),
    ("competitive_snapshot", "The competition"),
    ("closing_remark", "What's next"),
]


def _build_report_synthesis(session_dir: Path) -> list[ReportSection]:
    """Build sections from the report synthesis markdown.

    The report-synthesis stage produces a single markdown document covering
    all validation findings. This function parses it into sections by H2
    heading so each becomes a separate report section in the PDF.
    """
    text = _load_markdown(session_dir, "report-synthesis", "report_synthesis.md")
    if not text:
        return []

    # Strip preamble: to_markdown() outputs "## Recommendation: ...\n\n..."
    # before the actual report body. Find "# Validation Report" and take
    # everything after it.
    report_start = re.search(r"^# Validation Report\s*$", text, flags=re.MULTILINE)
    if report_start:
        text = text[report_start.end() :].strip()
    else:
        # Fallback: strip known preamble patterns individually
        text = re.sub(
            r"^## Recommendation:\s*(?:GO|NO-GO|PIVOT)\s*\n+",
            "",
            text,
            flags=re.MULTILINE | re.IGNORECASE,
        )
        text = re.sub(r"^# (?!#).+\n+", "", text.strip(), flags=re.MULTILINE)

    # Split by ## headings into separate ReportSections
    sections: list[ReportSection] = []
    parts = re.split(r"(?=^## )", text, flags=re.MULTILINE)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if part.startswith("## "):
            first_line, _, body = part.partition("\n")
            heading = first_line.lstrip("#").strip()
            if body.strip():
                sections.append(ReportSection(heading, SectionType.MARKDOWN, body.strip()))
        elif not sections:
            # Leading content before first heading — skip if it's just
            # horizontal rules (---) or whitespace (common after preamble strip)
            if re.sub(r"^-{3,}\s*$", "", part, flags=re.MULTILINE).strip():
                sections.append(ReportSection("Overview", SectionType.MARKDOWN, part))

    # If no sections parsed, return the whole text as one section
    if not sections:
        sections.append(ReportSection("Validation Report", SectionType.MARKDOWN, text))

    return sections


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------


def build_idea_validation_config(session_dir: Path) -> ReportConfig:
    """Build a complete ReportConfig for the Idea Validation report.

    ADR-026: The report-synthesis stage produces a self-contained report
    covering all 8 sections in 4 narrative parts (opportunity, evidence,
    numbers, path forward). The PDF uses only the report-synthesis output
    to avoid duplicating content from upstream stages.

    Args:
        session_dir: Path to the session directory containing stage outputs.

    Returns:
        ReportConfig ready to pass to generate_pdf().
    """
    idea_text = _load_system_goal(session_dir)
    verdict = _extract_verdict(session_dir)
    exec_summary = _extract_executive_summary(session_dir)
    composite_score = _extract_composite_score(session_dir)
    risk_level = _extract_risk_level(session_dir)

    # Build structured summary_fields from ExecutiveSummary dict
    summary_fields: list[tuple[str, str]] | None = None
    if exec_summary:
        summary_fields = [
            (label, str(exec_summary.get(key, "")))
            for key, label in _SUMMARY_FIELD_LABELS
            if exec_summary.get(key)
        ] or None

    cover = CoverConfig(
        title="Idea Validation Report",
        idea_text=idea_text,
        summary_fields=summary_fields,
        verdict=verdict,
        composite_score=composite_score,
        risk_level=risk_level,
    )

    # Report synthesis covers all sections (ADR-026 single-agent report)
    sections: list[ReportSection] = _build_report_synthesis(session_dir)

    return ReportConfig(cover=cover, sections=sections)
