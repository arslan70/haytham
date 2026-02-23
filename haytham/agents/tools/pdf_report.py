"""Generic PDF report renderer using ReportLab.

Data-driven: callers build a `ReportConfig` describing sections,
then `generate_pdf()` renders it to bytes.  The idea validation report
is one factory function; adding MVP Spec later is another factory,
zero changes to this renderer.
"""

from __future__ import annotations

import base64
import io
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Flowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ---------------------------------------------------------------------------
# Brand colours
# ---------------------------------------------------------------------------
PURPLE = colors.HexColor("#6B2D8B")
LIGHT_PURPLE = colors.HexColor("#E8DCF5")
GREEN = colors.HexColor("#4CAF50")
ORANGE = colors.HexColor("#FF9800")
RED = colors.HexColor("#F44336")
ALT_ROW = colors.HexColor("#F5F5F5")

VERDICT_COLORS = {"GO": GREEN, "PIVOT": ORANGE, "NO-GO": RED}
RISK_COLORS = {"LOW": GREEN, "MEDIUM": ORANGE, "HIGH": RED}
STATUS_COLORS = {"PASS": GREEN, "FAIL": RED, "PARTIAL": ORANGE}

# Usable page width: letter (8.5") minus 0.75" margins each side
_USABLE_WIDTH = 7.0 * inch

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class SectionType(Enum):
    MARKDOWN = "markdown"
    TABLE = "table"
    SCORECARD = "scorecard"
    KEY_VALUE = "key_value"
    METRIC_BADGES = "metric_badges"


@dataclass
class MetricBadge:
    label: str
    value: str
    color: str  # hex


@dataclass
class CoverConfig:
    title: str = "Idea Validation Report"
    idea_text: str = ""
    verdict: str | None = None
    composite_score: str | None = None
    risk_level: str | None = None
    summary_fields: list[tuple[str, str]] | None = None
    date: str = field(default_factory=lambda: datetime.now().strftime("%B %d, %Y"))


@dataclass
class ReportSection:
    title: str
    section_type: SectionType
    content: Any = None  # str for MARKDOWN, list[list[str]] for TABLE, etc.


@dataclass
class ReportConfig:
    cover: CoverConfig
    sections: list[ReportSection] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------


def _build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    custom: dict[str, ParagraphStyle] = {}

    custom["body"] = ParagraphStyle(
        "HaythamBody",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=15,
        spaceAfter=8,
    )
    custom["h1"] = ParagraphStyle(
        "HaythamH1",
        parent=base["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        textColor=PURPLE,
        spaceAfter=12,
    )
    custom["h2"] = ParagraphStyle(
        "HaythamH2",
        parent=base["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        textColor=PURPLE,
        spaceBefore=16,
        spaceAfter=8,
    )
    custom["h3"] = ParagraphStyle(
        "HaythamH3",
        parent=base["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=PURPLE,
        spaceBefore=10,
        spaceAfter=6,
    )
    custom["h3_critical"] = ParagraphStyle(
        "HaythamH3Critical",
        parent=base["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=colors.HexColor("#E65100"),
        spaceBefore=14,
        spaceAfter=6,
    )
    custom["bullet"] = ParagraphStyle(
        "HaythamBullet",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=15,
        leftIndent=18,
        bulletIndent=6,
        spaceAfter=5,
    )
    custom["sub_bullet"] = ParagraphStyle(
        "HaythamSubBullet",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=15,
        leftIndent=36,
        bulletIndent=24,
        spaceAfter=4,
    )
    custom["cover_title"] = ParagraphStyle(
        "HaythamCoverTitle",
        parent=base["Title"],
        fontName="Helvetica-Bold",
        fontSize=28,
        textColor=PURPLE,
        spaceAfter=20,
    )
    custom["cover_idea"] = ParagraphStyle(
        "HaythamCoverIdea",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#333333"),
        spaceAfter=0,
    )
    custom["cover_summary"] = ParagraphStyle(
        "HaythamCoverSummary",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#444444"),
        spaceAfter=0,
    )
    custom["cover_label"] = ParagraphStyle(
        "HaythamCoverLabel",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        textColor=PURPLE,
        spaceAfter=4,
    )
    custom["footer"] = ParagraphStyle(
        "HaythamFooter",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=8,
        textColor=colors.HexColor("#999999"),
        alignment=TA_CENTER,
    )
    custom["badge_text"] = ParagraphStyle(
        "HaythamBadge",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        alignment=TA_CENTER,
        textColor=colors.white,
    )
    custom["table_header"] = ParagraphStyle(
        "HaythamTableHeader",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=PURPLE,
    )
    custom["table_cell"] = ParagraphStyle(
        "HaythamTableCell",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
    )
    return custom


# ---------------------------------------------------------------------------
# Cover page accent bar
# ---------------------------------------------------------------------------


class _AccentBar(Flowable):
    """Full-width purple accent bar for the cover page."""

    def __init__(self, width: float, height: float = 6):
        super().__init__()
        self.width = width
        self.height = height

    def draw(self):
        self.canv.setFillColor(PURPLE)
        self.canv.rect(0, 0, self.width, self.height, fill=1, stroke=0)


# ---------------------------------------------------------------------------
# Badge flowable (coloured rounded rect with text)
# ---------------------------------------------------------------------------


class _Badge(Flowable):
    """Small coloured badge showing a value (e.g. 'GO', '4.0/5.0')."""

    def __init__(
        self, text: str, bg_color: colors.HexColor, width: float = 120, height: float = 30
    ):
        super().__init__()
        self.text = text
        self.bg_color = bg_color
        self.width = width
        self.height = height

    def draw(self):
        self.canv.setFillColor(self.bg_color)
        self.canv.roundRect(0, 0, self.width, self.height, 5, fill=1, stroke=0)
        self.canv.setFillColor(colors.white)
        self.canv.setFont("Helvetica-Bold", 13)
        tw = self.canv.stringWidth(self.text, "Helvetica-Bold", 13)
        self.canv.drawString((self.width - tw) / 2, (self.height - 13) / 2 + 2, self.text)


# ---------------------------------------------------------------------------
# Part banner (PART 1: THE OPPORTUNITY, etc.)
# ---------------------------------------------------------------------------


class _PartBanner(Flowable):
    """Full-width purple banner for PART headers."""

    def __init__(self, text: str, width: float, height: float = 28):
        super().__init__()
        self.text = text.upper()
        self.width = width
        self.height = height

    def draw(self):
        self.canv.setFillColor(PURPLE)
        self.canv.roundRect(0, 0, self.width, self.height, 3, fill=1, stroke=0)
        self.canv.setFillColor(colors.white)
        self.canv.setFont("Helvetica-Bold", 11)
        self.canv.drawString(12, (self.height - 11) / 2 + 1, self.text)


# ---------------------------------------------------------------------------
# Markdown → Platypus converter
# ---------------------------------------------------------------------------

_RE_BOLD = re.compile(r"\*\*(.+?)\*\*")
_RE_ITALIC = re.compile(r"\*(.+?)\*")
_RE_MD_TABLE_ROW = re.compile(r"^\|(.+)\|$")
_RE_MD_SEP_ROW = re.compile(r"^\|[-\s|:]+\|$")
_RE_SCORE_BAR = re.compile(r"[█░■□▪▫▓▒]+\s*")  # visual score bars in markdown
_RE_PART_HEADER = re.compile(r"^\*{0,2}(PART\s+\d+:\s*.+?)\*{0,2}$")
_RE_RISK_LEVEL_LINE = re.compile(r"^\*\*Overall Risk Level:\*\*\s*(HIGH|MEDIUM|LOW)", re.IGNORECASE)
_RE_COMPOSITE_LINE = re.compile(r"^\*\*Composite Score:\*\*\s*(\d+\.?\d*)/5\.0")


def _md_inline(text: str) -> str:
    """Convert inline markdown (bold, italic) to ReportLab XML tags."""
    text = _RE_BOLD.sub(r"<b>\1</b>", text)
    text = _RE_ITALIC.sub(r"<i>\1</i>", text)
    # Escape remaining angle brackets that aren't our tags
    text = re.sub(r"<(?!/?(b|i|br|u)\b)", "&lt;", text)
    return text


def _parse_markdown_table(lines: list[str], styles: dict) -> Table | None:
    """Parse a markdown table block into a ReportLab Table."""
    rows: list[list[str]] = []
    for line in lines:
        if _RE_MD_SEP_ROW.match(line.strip()):
            continue
        m = _RE_MD_TABLE_ROW.match(line.strip())
        if m:
            cells = [_RE_SCORE_BAR.sub("", c).strip() for c in m.group(1).split("|")]
            rows.append(cells)

    if not rows:
        return None

    # Convert to Paragraph cells for word-wrapping
    col_count = max(len(r) for r in rows)
    col_width = _USABLE_WIDTH / col_count
    table_data = []
    for ri, row in enumerate(rows):
        # Pad row if fewer cells
        while len(row) < col_count:
            row.append("")
        style = styles["table_header"] if ri == 0 else styles["table_cell"]
        table_data.append([Paragraph(_md_inline(c), style) for c in row])

    t = Table(table_data, colWidths=[col_width] * col_count)
    table_style = [
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_PURPLE),
        ("TEXTCOLOR", (0, 0), (-1, 0), PURPLE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    # Alternating row background
    for i in range(2, len(table_data), 2):
        table_style.append(("BACKGROUND", (0, i), (-1, i), ALT_ROW))
    t.setStyle(TableStyle(table_style))
    return t


def _markdown_to_flowables(text: str, styles: dict) -> list:
    """Convert markdown text to a list of ReportLab flowables."""
    flowables: list = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        # Skip empty lines
        if not line.strip():
            i += 1
            continue

        # PART headers (e.g. "PART 1: THE OPPORTUNITY")
        part_m = _RE_PART_HEADER.match(line.strip())
        if part_m:
            # Page break before parts 2+ (not the first)
            if any(isinstance(f, _PartBanner) for f in flowables):
                flowables.append(PageBreak())
            flowables.append(Spacer(1, 4))
            flowables.append(_PartBanner(part_m.group(1), _USABLE_WIDTH))
            flowables.append(Spacer(1, 12))
            i += 1
            continue

        # Inline metric: Overall Risk Level
        risk_m = _RE_RISK_LEVEL_LINE.match(line.strip())
        if risk_m:
            level = risk_m.group(1).upper()
            c = RISK_COLORS.get(level, colors.gray)
            flowables.append(Spacer(1, 8))
            badge_row = Table(
                [
                    [
                        Paragraph("<b>Overall Risk Level</b>", styles["body"]),
                        _Badge(level, c, width=90, height=26),
                    ]
                ],
                colWidths=[160, 100],
            )
            badge_row.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (0, 0), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            flowables.append(badge_row)
            flowables.append(Spacer(1, 8))
            i += 1
            continue

        # Inline metric: Composite Score
        score_m = _RE_COMPOSITE_LINE.match(line.strip())
        if score_m:
            score_val = score_m.group(1)
            flowables.append(Spacer(1, 8))
            badge_row = Table(
                [
                    [
                        Paragraph("<b>Composite Score</b>", styles["body"]),
                        _Badge(f"{score_val}/5.0", PURPLE, width=100, height=26),
                    ]
                ],
                colWidths=[160, 110],
            )
            badge_row.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (0, 0), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            flowables.append(badge_row)
            flowables.append(Spacer(1, 8))
            i += 1
            continue

        # Headings (with CRITICAL flag detection)
        if line.startswith("#### "):
            heading_text = line[5:].strip()
            style_key = "h3_critical" if "CRITICAL" in heading_text.upper() else "h3"
            flowables.append(Paragraph(_md_inline(heading_text), styles[style_key]))
            i += 1
            continue
        if line.startswith("### "):
            heading_text = line[4:].strip()
            style_key = "h3_critical" if "CRITICAL" in heading_text.upper() else "h3"
            flowables.append(Paragraph(_md_inline(heading_text), styles[style_key]))
            i += 1
            continue
        if line.startswith("## "):
            flowables.append(Paragraph(_md_inline(line[3:].strip()), styles["h2"]))
            i += 1
            continue

        # Horizontal rules
        if re.match(r"^-{3,}$", line.strip()) or re.match(r"^\*{3,}$", line.strip()):
            flowables.append(Spacer(1, 8))
            i += 1
            continue

        # Markdown table block
        if _RE_MD_TABLE_ROW.match(line.strip()):
            table_lines = []
            while i < len(lines) and _RE_MD_TABLE_ROW.match(lines[i].strip()):
                table_lines.append(lines[i])
                i += 1
            tbl = _parse_markdown_table(table_lines, styles)
            if tbl:
                flowables.append(Spacer(1, 4))
                flowables.append(tbl)
                flowables.append(Spacer(1, 6))
            continue

        # Indented sub-bullet points (2+ spaces then - or *)
        sub_m = re.match(r"^(\s{2,})[-*]\s+(.+)$", line)
        if sub_m:
            bullet_text = _RE_SCORE_BAR.sub("", sub_m.group(2).strip())
            flowables.append(
                Paragraph(
                    f"&bull; {_md_inline(bullet_text)}",
                    styles["sub_bullet"],
                )
            )
            i += 1
            continue

        # Bullet points
        if line.startswith("- ") or line.startswith("* "):
            # Strip visual score bars
            bullet_text = _RE_SCORE_BAR.sub("", line[2:].strip())
            flowables.append(
                Paragraph(
                    f"&bull; {_md_inline(bullet_text)}",
                    styles["bullet"],
                )
            )
            i += 1
            continue

        # Numbered lists
        m = re.match(r"^(\d+)[.)]\s+(.+)$", line)
        if m:
            flowables.append(
                Paragraph(
                    f"{m.group(1)}. {_md_inline(m.group(2))}",
                    styles["bullet"],
                )
            )
            i += 1
            continue

        # Regular paragraph
        flowables.append(Paragraph(_md_inline(line.strip()), styles["body"]))
        i += 1

    return flowables


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------


def _render_markdown_section(section: ReportSection, styles: dict) -> list:
    """Render a MARKDOWN section."""
    elems: list = []
    # Skip "Overview" heading -- its content (PART banner) provides its own visual
    if section.title != "Overview":
        elems.append(Paragraph(section.title, styles["h2"]))
    if section.content:
        elems.extend(_markdown_to_flowables(str(section.content), styles))
    return elems


def _render_table_section(section: ReportSection, styles: dict) -> list:
    """Render a TABLE section.  content = list[list[str]]."""
    elems: list = []
    elems.append(Paragraph(section.title, styles["h2"]))
    if not section.content:
        return elems
    rows: list[list[str]] = section.content
    col_count = max(len(r) for r in rows) if rows else 0
    if col_count == 0:
        return elems
    avail = 7.0 * inch
    col_width = avail / col_count
    table_data = []
    for ri, row in enumerate(rows):
        while len(row) < col_count:
            row.append("")
        style = styles["table_header"] if ri == 0 else styles["table_cell"]
        table_data.append([Paragraph(_md_inline(c), style) for c in row])

    t = Table(table_data, colWidths=[col_width] * col_count)
    ts = [
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_PURPLE),
        ("TEXTCOLOR", (0, 0), (-1, 0), PURPLE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    for i in range(2, len(table_data), 2):
        ts.append(("BACKGROUND", (0, i), (-1, i), ALT_ROW))
    t.setStyle(TableStyle(ts))
    elems.append(Spacer(1, 4))
    elems.append(t)
    return elems


def _render_key_value_section(section: ReportSection, styles: dict) -> list:
    """Render a KEY_VALUE section. content = list[tuple[str, str]]."""
    elems: list = []
    elems.append(Paragraph(section.title, styles["h2"]))
    if not section.content:
        return elems
    for key, value in section.content:
        elems.append(Paragraph(f"<b>{_md_inline(key)}:</b> {_md_inline(value)}", styles["body"]))
    return elems


def _render_metric_badges_section(section: ReportSection, styles: dict) -> list:
    """Render a row of metric badges. content = list[MetricBadge]."""
    elems: list = []
    elems.append(Paragraph(section.title, styles["h2"]))
    if not section.content:
        return elems
    badges: list[MetricBadge] = section.content
    badge_data = []
    for b in badges:
        bg = colors.HexColor(b.color)
        badge_data.append(_Badge(f"{b.label}: {b.value}", bg, width=160, height=28))
    # Lay out badges in a table row
    t = Table([badge_data], colWidths=[170] * len(badge_data))
    t.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elems.append(Spacer(1, 6))
    elems.append(t)
    return elems


def _render_scorecard_section(section: ReportSection, styles: dict) -> list:
    """Render a SCORECARD section (markdown with scorecard-specific cleanup)."""
    elems: list = []
    elems.append(Paragraph(section.title, styles["h2"]))
    if section.content:
        elems.extend(_markdown_to_flowables(str(section.content), styles))
    return elems


_SECTION_RENDERERS = {
    SectionType.MARKDOWN: _render_markdown_section,
    SectionType.TABLE: _render_table_section,
    SectionType.KEY_VALUE: _render_key_value_section,
    SectionType.METRIC_BADGES: _render_metric_badges_section,
    SectionType.SCORECARD: _render_scorecard_section,
}


# ---------------------------------------------------------------------------
# Page template (header + footer)
# ---------------------------------------------------------------------------


def _header_footer(canvas, doc):
    """Add header and footer to every content page."""
    canvas.saveState()
    # Header
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#999999"))
    canvas.drawString(0.75 * inch, 10.5 * inch, "Haytham Idea Validation Report")
    canvas.drawRightString(7.75 * inch, 10.5 * inch, f"Page {doc.page}")
    # Thin purple line under header
    canvas.setStrokeColor(PURPLE)
    canvas.setLineWidth(0.5)
    canvas.line(0.75 * inch, 10.45 * inch, 7.75 * inch, 10.45 * inch)
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Cover page builder
# ---------------------------------------------------------------------------


def _build_cover(cover: CoverConfig, styles: dict, page_width: float) -> list:
    """Build flowables for the cover page."""
    elems: list = []
    usable = page_width - 1.5 * inch

    # --- Header area ---
    # Accent bar
    elems.append(_AccentBar(usable, 8))
    elems.append(Spacer(1, 24))

    # Title
    elems.append(Paragraph(cover.title, styles["cover_title"]))

    # Badges row: verdict, score, risk (centered, immediately after title)
    badge_items = []
    if cover.verdict:
        c = VERDICT_COLORS.get(cover.verdict, colors.gray)
        badge_items.append(_Badge(cover.verdict, c, width=100, height=32))
    if cover.composite_score:
        badge_items.append(
            _Badge(f"Score: {cover.composite_score}/5.0", PURPLE, width=140, height=32)
        )
    if cover.risk_level:
        c = RISK_COLORS.get(cover.risk_level, colors.gray)
        badge_items.append(_Badge(f"Risk: {cover.risk_level}", c, width=120, height=32))

    if badge_items:
        gap = 10
        total_desired = sum(b.width + gap for b in badge_items)
        if total_desired > usable:
            scale = usable / total_desired
            for b in badge_items:
                b.width = int(b.width * scale)
        col_widths = [b.width + gap for b in badge_items]
        t = Table([badge_items], colWidths=col_widths)
        t.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        elems.append(t)

    # Date + footer
    elems.append(Spacer(1, 16))
    elems.append(
        Paragraph(
            f"{cover.date}&nbsp;&nbsp;&bull;&nbsp;&nbsp;Powered by Haytham",
            styles["footer"],
        )
    )

    # --- Thin divider between header and content ---
    elems.append(Spacer(1, 16))
    divider = Table([[""]], colWidths=[usable], rowHeights=[1])
    divider.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 0), (-1, 0), 0.5, colors.HexColor("#D0D0D0")),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    elems.append(divider)
    elems.append(Spacer(1, 16))

    # --- Content area ---
    # "THE IDEA" section
    if cover.idea_text:
        elems.append(Paragraph("THE IDEA", styles["cover_label"]))
        idea_para = Paragraph(_md_inline(cover.idea_text), styles["cover_idea"])
        idea_table = Table([[idea_para]], colWidths=[usable - 24])
        idea_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3EDF8")),
                    ("ROUNDEDCORNERS", [6, 6, 6, 6]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("BOX", (0, 0), (-1, -1), 0.5, LIGHT_PURPLE),
                ]
            )
        )
        elems.append(idea_table)
        elems.append(Spacer(1, 14))

    # "AT A GLANCE" structured summary
    if cover.summary_fields:
        elems.append(Paragraph("AT A GLANCE", styles["cover_label"]))
        field_paras = []
        for label, value in cover.summary_fields:
            field_paras.append(
                Paragraph(
                    f"<b>{_md_inline(label)}:</b> {_md_inline(value)}",
                    styles["cover_summary"],
                )
            )
        summary_table = Table([[p] for p in field_paras], colWidths=[usable - 24])
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFAFA")),
                    ("ROUNDEDCORNERS", [6, 6, 6, 6]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ("TOPPADDING", (0, 0), (0, 0), 10),
                    ("BOTTOMPADDING", (-1, -1), (-1, -1), 10),
                    ("TOPPADDING", (0, 1), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -2), 2),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E0E0E0")),
                ]
            )
        )
        elems.append(summary_table)

    # Visual separator before body content
    elems.append(Spacer(1, 36))
    return elems


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_pdf(config: ReportConfig) -> bytes:
    """Render a ReportConfig to PDF bytes.

    Args:
        config: Fully-populated report configuration.

    Returns:
        Raw PDF bytes ready for download or encoding.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    styles = _build_styles()
    page_width = letter[0]

    story: list = _build_cover(config.cover, styles, page_width)

    for idx, section in enumerate(config.sections):
        renderer = _SECTION_RENDERERS.get(section.section_type)
        if renderer:
            story.extend(renderer(section, styles))
            # Thin divider between sections (not after the last one)
            if idx < len(config.sections) - 1:
                story.append(Spacer(1, 12))
                divider = Table([[""]], colWidths=[_USABLE_WIDTH], rowHeights=[1])
                divider.setStyle(
                    TableStyle(
                        [
                            (
                                "LINEBELOW",
                                (0, 0),
                                (-1, 0),
                                0.25,
                                colors.HexColor("#E0E0E0"),
                            ),
                        ]
                    )
                )
                story.append(divider)
                story.append(Spacer(1, 12))

    # First page = cover (no header/footer), subsequent pages get header/footer
    doc.build(story, onLaterPages=_header_footer)
    return buf.getvalue()


def generate_pdf_tool(report_config_json: str) -> str:
    """Tool wrapper: generate a PDF report and return base64-encoded result.

    Args:
        report_config_json: JSON string describing the report config.
            Expected keys: cover (dict), sections (list[dict]).

    Returns:
        Base64-encoded PDF string.
    """
    data = json.loads(report_config_json)

    cover_data = data.get("cover", {})
    cover = CoverConfig(
        title=cover_data.get("title", "Report"),
        idea_text=cover_data.get("idea_text", ""),
        verdict=cover_data.get("verdict"),
        composite_score=cover_data.get("composite_score"),
        risk_level=cover_data.get("risk_level"),
    )

    sections = []
    for s in data.get("sections", []):
        sections.append(
            ReportSection(
                title=s.get("title", ""),
                section_type=SectionType(s.get("section_type", "markdown")),
                content=s.get("content"),
            )
        )

    config = ReportConfig(cover=cover, sections=sections)
    pdf_bytes = generate_pdf(config)
    return base64.b64encode(pdf_bytes).decode("ascii")
