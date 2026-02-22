"""Discovery View - View validation workflow outputs with feedback."""

from lib.session_utils import get_session_dir, load_environment, setup_paths

setup_paths()
load_environment()

import json  # noqa: E402
import logging  # noqa: E402
import re  # noqa: E402

logger = logging.getLogger("haytham")  # noqa: E402

import streamlit as st  # noqa: E402
import yaml  # noqa: E402
from components.anchor_review import render_anchor_condensed  # noqa: E402
from components.decision_gate import render_decision_gate  # noqa: E402
from components.feedback_conversation import (  # noqa: E402
    render_feedback_conversation,
)

SESSION_DIR = get_session_dir()

# Known labels that appear in founder-submitted ideas
_IDEA_LABELS = re.compile(
    r"(Problem|Customer Segments?|UVP|Solution|Founder'?s clarifications?)\s*:",
    re.IGNORECASE,
)


def _format_idea_markdown(raw: str) -> str:
    """Turn a raw system_goal string into readable markdown.

    Recognises common labels (Problem, Customer Segments, UVP,
    Founder's clarifications) and renders them as bold headings with
    proper line breaks.
    """
    paragraphs = [p.strip() for p in raw.split("\n") if p.strip()]
    # First pass: collect all label → values, preserving order of first appearance
    preamble_lines: list[str] = []
    label_order: list[str] = []
    label_values: dict[str, list[str]] = {}
    for para in paragraphs:
        parts = _IDEA_LABELS.split(para)
        if len(parts) == 1:
            preamble_lines.append(para)
        else:
            pre = re.sub(r"^[-*\d.]+\s*", "", parts[0]).strip()
            if pre:
                preamble_lines.append(pre)
            i = 1
            while i < len(parts) - 1:
                label = parts[i].strip()
                value = parts[i + 1].strip().lstrip(":").strip()
                key = label.lower()
                if value:
                    if key not in label_values:
                        label_order.append(label)
                        label_values[key] = []
                    label_values[key].append(value)
                i += 2
    # Build output: preamble paragraphs, then merged labels
    lines = list(preamble_lines)
    for label in label_order:
        key = label.lower()
        vals = [v.rstrip(".") for v in label_values[key]]
        merged = ". ".join(vals)
        lines.append(f"**{label}:** {merged}")
    return "\n\n".join(lines)


# Workflow configuration
WORKFLOW_TYPE = "idea-validation"
WORKFLOW_DISPLAY_NAME = "Idea Validation"


def load_startup_idea() -> str | None:
    """Load startup idea from project.yaml."""
    project_file = SESSION_DIR / "project.yaml"
    if project_file.exists():
        try:
            data = yaml.safe_load(project_file.read_text())
            return data.get("system_goal", "")
        except (yaml.YAMLError, OSError):
            pass
    return None


# -----------------------------------------------------------------------------
# Stage Configuration
# -----------------------------------------------------------------------------

# Idea Validation workflow stages only (Workflow 1)
STAGES = [
    {
        "id": "idea-analysis",
        "name": "Idea Analysis",
        "icon": "[1]",
        "description": (
            "Your idea broken down into core problems, target users, and a unique value proposition."
            " This is the foundation every later stage builds on."
        ),
        "output_file": "concept_expansion.md",
    },
    {
        "id": "market-context",
        "name": "Market Context",
        "icon": "[2]",
        "description": (
            "How your idea fits into the broader market — size, trends, competitors,"
            " and jobs your customers are trying to get done."
        ),
        "output_files": ["market_intelligence.md", "competitor_analysis.md"],
    },
    {
        "id": "report-synthesis",
        "name": "Validation Report",
        "icon": "[3]",
        "description": (
            "The final GO / NO-GO / PIVOT verdict with a comprehensive analysis"
            " of risks, market opportunity, feasibility, and next steps."
        ),
        "output_file": "report_synthesis.md",
    },
]

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------


def strip_output_header(content: str) -> str:
    """Strip output headers, H1 document titles, and code fences from content."""
    # Remove "## Output" or "# Output" header at the start
    content = re.sub(r"^#+ Output\s*\n+", "", content, flags=re.MULTILINE)
    # Remove leading H1 title (e.g. "# Validation Results") — it's a document title, not content
    content = re.sub(r"^# (?!#).+\n+", "", content.strip())

    # Strip wrapping code fences if the entire content is wrapped
    # This handles cases where LLM wraps markdown in ```...```
    content = content.strip()
    if content.startswith("```") and content.endswith("```"):
        # Remove opening fence (with optional language specifier)
        content = re.sub(r"^```\w*\n?", "", content)
        # Remove closing fence
        content = re.sub(r"\n?```$", "", content)

    return content.strip()


def load_stage_output(stage_id: str, filename: str) -> str | None:
    """Load a stage output file and strip output header."""
    file_path = SESSION_DIR / stage_id / filename
    if file_path.exists():
        content = file_path.read_text()
        return strip_output_header(content)
    return None


def get_stage_status(stage_id: str) -> bool:
    """Check if a stage has been completed."""
    stage_dir = SESSION_DIR / stage_id
    return stage_dir.exists() and any(stage_dir.glob("*.md"))


def is_workflow_locked() -> bool:
    """Check if the idea-validation workflow is locked."""
    lock_file = SESSION_DIR / f".{WORKFLOW_TYPE}.locked"
    return lock_file.exists()


# -----------------------------------------------------------------------------
# Metrics & Section Helpers
# -----------------------------------------------------------------------------


def extract_metrics() -> dict:
    """Extract the verdict from recommendation.json."""
    metrics: dict = {"verdict": None}

    meta_path = SESSION_DIR / "recommendation.json"
    if meta_path.exists():
        try:
            data = json.loads(meta_path.read_text())
            rec = data.get("recommendation", "").upper().strip()
            if rec in ("GO", "NO-GO", "PIVOT"):
                metrics["verdict"] = rec
        except (json.JSONDecodeError, OSError):
            pass

    return metrics


_VERDICT_COLORS = {
    "GO": "#4CAF50",
    "NO-GO": "#F44336",
    "PIVOT": "#FF9800",
}


_METRIC_DIV_STYLE = (
    "text-align:center; min-height:5rem; margin-bottom:0.75rem; "
    "display:flex; flex-direction:column; justify-content:center; align-items:center;"
)


def render_metrics_dashboard(metrics: dict) -> None:
    """Render the recommendation verdict badge."""
    verdict = metrics.get("verdict")
    color = _VERDICT_COLORS.get(verdict, "#9E9E9E") if verdict else "#9E9E9E"
    st.markdown(
        f'<div style="{_METRIC_DIV_STYLE}">'
        f'<span style="font-size:0.95rem;color:#888;">Verdict</span>'
        f'<span style="background:{color};color:#fff;padding:0.3rem 1.2rem;'
        f'border-radius:0.4rem;font-weight:700;font-size:1.8rem;">'
        f"{verdict or '---'}</span></div>",
        unsafe_allow_html=True,
    )


def split_markdown_sections(content: str) -> list[tuple[str, str]]:
    """Split markdown content into (heading, body) pairs for progressive disclosure."""
    h2_count = len(re.findall(r"^## (?!#)", content, re.MULTILINE))
    h3_count = len(re.findall(r"^### (?!#)", content, re.MULTILINE))

    # Prefer H2 (coarser grain) when available; fall back to H3 only
    level = "### " if h2_count == 0 and h3_count > 0 else "## "
    pattern = rf"(?=^{re.escape(level)})"

    parts = re.split(pattern, content, flags=re.MULTILINE)
    if not parts or (len(parts) == 1 and not parts[0].startswith(level)):
        return [("Full Output", content)]

    sections: list[tuple[str, str]] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if part.startswith(level):
            # Extract heading text (strip markdown markers and bold)
            first_line, _, body = part.partition("\n")
            heading = first_line.lstrip("#").strip().strip("*").strip()
            sections.append((heading, body.strip()))
        elif not sections:
            # Leading content before first heading
            sections.append(("Overview", part))
        else:
            # Append to previous section
            prev_heading, prev_body = sections[-1]
            sections[-1] = (prev_heading, prev_body + "\n\n" + part)

    return sections if sections else [("Full Output", content)]


def _render_sections(content: str) -> None:
    """Render markdown content as sub-expanders split by heading."""
    sections = split_markdown_sections(content)
    # Drop preamble and empty-body sections (e.g. "## Overall Risk Level: MEDIUM" with no content)
    sections = [(h, b) for h, b in sections if h != "Overview" and b.strip()]
    if not sections:
        st.markdown(content)
        return
    # Reverse for progressive disclosure (summary first) unless sections are
    # explicitly numbered or already lead with a summary heading.
    if len(sections) > 1:
        first = sections[0][0]
        is_numbered = bool(re.match(r"^\d+[.\)]", first))
        is_summary_first = "summary" in first.lower()
        if not is_numbered and not is_summary_first:
            sections.reverse()
    if len(sections) == 1:
        st.markdown(sections[0][1] if sections[0][1] else content)
        return
    for idx, (heading, body) in enumerate(sections):
        with st.expander(heading, expanded=(idx == 0)):
            st.markdown(body)


def _render_stage_tab(stage: dict) -> None:
    """Render a single stage's content inside its tab."""
    stage_id = stage["id"]
    if "output_file" in stage:
        content = load_stage_output(stage_id, stage["output_file"])
        if content:
            _render_sections(content)
        else:
            st.warning(f"Output file not found: {stage['output_file']}")
    elif "output_files" in stage:
        sub_tab_labels = [
            f.replace(".md", "").replace("_", " ").title() for f in stage["output_files"]
        ]
        sub_tabs = st.tabs(sub_tab_labels)
        for i, filename in enumerate(stage["output_files"]):
            with sub_tabs[i]:
                content = load_stage_output(stage_id, filename)
                if content:
                    _render_sections(content)
                else:
                    st.warning(f"Output file not found: {filename}")


# -----------------------------------------------------------------------------
# Main Content
# -----------------------------------------------------------------------------

st.title("Idea Validation Results")

# Page-wide readability overrides
st.markdown(
    """<style>
    /* Base font — match Streamlit "sans serif" theme */
    .stMarkdown, .stExpander, .stTabs {
        font-family: "Source Sans Pro", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    /* Headings — Haytham purple with clear size steps */
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
    .stMarkdown h4, .stMarkdown h5 { color: #6B2D8B; }
    .stMarkdown h4, .stMarkdown h5 {
        border-bottom: 2px solid #E8DFF0; padding-bottom: 0.3rem; margin-top: 1.5rem;
    }
    /* Expander header labels */
    .stExpander summary span p { font-size: 1.1rem !important; font-weight: 600; color: #6B2D8B; }
    /* Markdown body text */
    .stMarkdown p { font-size: 1.05rem; line-height: 1.7; color: #333; }
    /* Bold-only paragraphs act as sub-headings (e.g. "Problem 1: ...") */
    .stMarkdown p strong {
        color: #4A1D6A; font-size: 1.08rem;
    }
    /* Bullet lists — left accent + spacing */
    .stMarkdown ul {
        padding-left: 1.4rem; margin: 0.6rem 0 1.4rem;
    }
    .stMarkdown li {
        font-size: 1.05rem; line-height: 1.7; color: #444;
        padding: 0.2rem 0; margin-bottom: 0.15rem;
    }
    /* Bold labels inside list items — darker, slightly smaller */
    .stMarkdown li strong { color: #4A1D6A; font-size: 1.0rem; }
    /* Table cells */
    .stMarkdown td, .stMarkdown th { font-size: 1.0rem; line-height: 1.5; color: #333; }
    .stMarkdown th { color: #6B2D8B; font-weight: 700; }
    .stMarkdown table { border-collapse: collapse; }
    .stMarkdown td, .stMarkdown th { border-bottom: 1px solid #E8DFF0; padding: 0.5rem 0.75rem; }
    /* Tab labels */
    .stTabs [data-baseweb='tab-list'] button p { font-size: 1.1rem; color: #555; }
    .stTabs [data-baseweb='tab-list'] [aria-selected='true'] p { color: #6B2D8B !important; }
    /* Download Report button — purple primary */
    [data-testid="stDownloadButton"] button[kind="primary"] {
        background-color: #6B2D8B !important;
        border-color: #6B2D8B !important;
        color: #fff !important;
    }
    [data-testid="stDownloadButton"] button[kind="primary"]:hover {
        background-color: #5A2476 !important;
        border-color: #5A2476 !important;
    }
    </style>""",
    unsafe_allow_html=True,
)

# Show the idea
idea_text = load_startup_idea()
if idea_text:
    formatted_idea = _format_idea_markdown(idea_text)
    st.markdown("#### Your Idea")
    st.markdown(
        f"""
<div style="background-color: #f0e6f6; padding: 1.2rem 1.4rem; border-radius: 0.5rem; border-left: 4px solid #6B2D8B; margin: 0.5rem 0 1.5rem 0;">

{formatted_idea}

</div>
""",
        unsafe_allow_html=True,
    )

# Check if any stages completed
any_completed = any(get_stage_status(s["id"]) for s in STAGES)

if not any_completed:
    st.info("No validation stages completed yet. Run Idea Validation from the dashboard.")
    st.stop()

# -----------------------------------------------------------------------------
# Metrics Dashboard & Tabbed Stage Views
# -----------------------------------------------------------------------------

# Metrics dashboard (only when report-synthesis is complete)
if get_stage_status("report-synthesis"):
    metrics = extract_metrics()
    render_metrics_dashboard(metrics)
    st.divider()

# Tabbed view for completed stages
completed_stages = [s for s in STAGES if get_stage_status(s["id"])]
if completed_stages:
    # Add Concept Anchor tab when anchor file exists
    anchor_file = SESSION_DIR / "concept_anchor.json"
    show_anchor_tab = anchor_file.exists()
    tab_labels = [s["name"] for s in completed_stages]
    if show_anchor_tab:
        tab_labels.append("Concept Anchor")

    all_tabs = st.tabs(tab_labels)
    for tab, stage in zip(all_tabs[: len(completed_stages)], completed_stages, strict=True):
        with tab:
            st.markdown(
                f'<p style="color:#888;font-size:1.1rem;margin:0 0 1rem;">{stage["description"]}</p>',
                unsafe_allow_html=True,
            )
            _render_stage_tab(stage)

    if show_anchor_tab:
        with all_tabs[-1]:
            st.markdown(
                '<p style="color:#888;font-size:1.1rem;margin:0 0 1rem;">'
                "The non-negotiable constraints extracted from your idea."
                " These guard-rails are checked at every stage to keep the system true to your vision."
                "</p>",
                unsafe_allow_html=True,
            )
            render_anchor_condensed(SESSION_DIR)

# -----------------------------------------------------------------------------
# Feedback / Next Step Section
# -----------------------------------------------------------------------------


def handle_accept() -> None:
    """Handle accept and continue action."""
    from lib.workflow_runner import lock_workflow as _lock_wf

    _lock_wf(WORKFLOW_TYPE, SESSION_DIR)
    st.session_state.run_mvp_workflow = True
    st.rerun()


st.divider()

if is_workflow_locked():
    # Build accomplishments from session artifacts
    accomplishments = ["Idea analyzed and structured"]
    if (SESSION_DIR / "market-context").exists():
        accomplishments.append("Market intelligence gathered")
    if (SESSION_DIR / "report-synthesis").exists():
        accomplishments.append("GO/NO-GO recommendation issued")

    result = render_decision_gate(
        phase_name="Idea Validation",
        accomplishments=accomplishments,
        next_phase_name="MVP Specification",
        next_phase_preview="Define what to build first and break it into concrete capabilities.",
        next_phase_details=[
            "Narrow the idea down to a focused, shippable MVP scope",
            "Extract functional and non-functional capabilities",
            "Map user flows to acceptance criteria",
        ],
        on_continue="Continue to MVP Specification",
        is_locked=True,
    )
    if result == "continue":
        st.session_state.run_mvp_workflow = True
        st.rerun()
else:
    # Workflow not locked - show chat-based feedback with intelligent agent
    stage_slugs = [s["id"] for s in STAGES]

    # Generate PDF download data when report-synthesis is complete
    _pdf_download_data = None
    if get_stage_status("report-synthesis"):
        try:
            from haytham.agents.tools.pdf_report import generate_pdf
            from haytham.agents.tools.report_configs import build_idea_validation_config

            _report_config = build_idea_validation_config(SESSION_DIR)
            _pdf_bytes = generate_pdf(_report_config)
            _pdf_download_data = (
                _pdf_bytes,
                "haytham-idea-validation-report.pdf",
                "application/pdf",
            )
        except ImportError:
            logger.warning(
                "PDF report generation unavailable: missing 'reportlab' package. Run: uv sync"
            )
        except (OSError, ValueError) as e:
            logger.warning("PDF report generation failed: %s", e)

    render_feedback_conversation(
        workflow_type=WORKFLOW_TYPE,
        workflow_display_name=WORKFLOW_DISPLAY_NAME,
        on_accept=handle_accept,
        stage_slugs=stage_slugs,
        system_goal=idea_text or "",
        session_dir=SESSION_DIR,
        next_stage_name="MVP Specification",
        download_data=_pdf_download_data,
    )
