"""Discovery View - View validation workflow outputs with feedback."""

from lib.session_utils import get_session_dir, load_environment, setup_paths

setup_paths()
load_environment()

import json  # noqa: E402
import re  # noqa: E402

import streamlit as st  # noqa: E402
import yaml  # noqa: E402
from components.anchor_review import render_anchor_condensed  # noqa: E402
from components.decision_gate import render_decision_gate  # noqa: E402
from components.feedback_conversation import (  # noqa: E402
    clear_chat_history,
    render_feedback_conversation,
)
from components.idea_refinement import (  # noqa: E402
    clear_refinement_state,
    render_idea_refinement,
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
        "id": "risk-assessment",
        "name": "Risk Assessment",
        "icon": "[3]",
        "description": (
            "Every claim from earlier stages tested against evidence."
            " Shows what holds up, what's partial, and where the real risks are."
        ),
        "output_file": "startup_validator.md",
    },
    {
        "id": "pivot-strategy",
        "name": "Pivot Strategy",
        "icon": "[P]",
        "description": "Alternative directions to consider if the current approach carries high risk.",
        "output_file": "pivot_strategy.md",
    },
    {
        "id": "validation-summary",
        "name": "Validation Summary",
        "icon": "[S]",
        "description": (
            "The final GO / NO-GO verdict with a scored breakdown across problem severity,"
            " market opportunity, feasibility, and revenue viability."
        ),
        "output_file": "validation_scorer.md",
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


def has_pivot_strategy() -> bool:
    """Check if pivot strategy exists (indicates HIGH risk was detected)."""
    pivot_dir = SESSION_DIR / "pivot-strategy"
    if not pivot_dir.exists():
        return False
    # Check if there are any output files (not just metadata)
    for f in pivot_dir.glob("*.md"):
        if f.name not in ("checkpoint.md", "user_feedback.md"):
            return True
    return False


def is_workflow_locked() -> bool:
    """Check if the idea-validation workflow is locked."""
    lock_file = SESSION_DIR / f".{WORKFLOW_TYPE}.locked"
    return lock_file.exists()


# -----------------------------------------------------------------------------
# Metrics & Section Helpers
# -----------------------------------------------------------------------------

# Pre-compiled patterns for metric extraction (shared module — DRY)
from haytham.agents.tools.metric_patterns import (  # noqa: E402
    RE_CLAIMS as _RE_CLAIMS,
)
from haytham.agents.tools.metric_patterns import (
    RE_COMPOSITE as _RE_COMPOSITE,
)
from haytham.agents.tools.metric_patterns import (
    RE_RECOMMENDATION as _RE_RECOMMENDATION,
)
from haytham.agents.tools.metric_patterns import (
    RE_RISK_LEVEL as _RE_RISK_LEVEL,
)


def _read_file_text(stage_id: str, filename: str) -> str | None:
    """Read raw text from a stage output file (no stripping)."""
    path = SESSION_DIR / stage_id / filename
    if path.exists():
        return path.read_text()
    return None


def _extract_section(text: str, heading: str) -> str | None:
    """Extract the body of a markdown section by ## heading."""
    pattern = rf"^## {re.escape(heading)}\s*\n(.*?)(?=\n## |\Z)"
    m = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    return m.group(1).strip() if m else None


def extract_metrics() -> dict:
    """Extract key validation signals and rationale from saved session files."""
    metrics: dict = {
        "verdict": None,
        "composite_score": None,
        "risk_level": None,
        "claims_supported": None,
        "claims_partial": None,
        "claims_total": None,
        # Rationale sections
        "verdict_rationale": None,
        "score_rationale": None,
        "risk_rationale": None,
        "claims_rationale": None,
    }

    # Verdict: try recommendation.json first, fallback to markdown
    meta_path = SESSION_DIR / "recommendation.json"
    if meta_path.exists():
        try:
            data = json.loads(meta_path.read_text())
            rec = data.get("recommendation", "").upper().strip()
            if rec in ("GO", "NO-GO", "PIVOT"):
                metrics["verdict"] = rec
        except (json.JSONDecodeError, OSError):
            pass

    # Parse validation-summary stage output for verdict fallback, confidence, composite
    summary_text = _read_file_text("validation-summary", "validation_scorer.md")
    if summary_text:
        if metrics["verdict"] is None:
            m = _RE_RECOMMENDATION.search(summary_text)
            if m:
                metrics["verdict"] = m.group(1).upper()
        m = _RE_COMPOSITE.search(summary_text)
        if m:
            metrics["composite_score"] = m.group(1)

        # Rationale from Go/No-Go Scorecard subsections
        scorecard = _extract_section(summary_text, "Go/No-Go Scorecard")
        if scorecard:
            # Verdict: knockout criteria + guidance
            verdict_parts = []
            for sub in ("Knockout Criteria", "Guidance"):
                m = re.search(
                    rf"### {sub}\s*\n(.*?)(?=\n### |\Z)",
                    scorecard,
                    re.DOTALL,
                )
                if m:
                    verdict_parts.append(f"**{sub}**\n\n{m.group(1).strip()}")
            if verdict_parts:
                metrics["verdict_rationale"] = "\n\n".join(verdict_parts)

            # Score: scored dimensions + critical gaps
            score_parts = []
            for sub in ("Scored Dimensions", "Critical Gaps"):
                m = re.search(
                    rf"### {sub}\s*\n(.*?)(?=\n### |\Z)",
                    scorecard,
                    re.DOTALL,
                )
                if m:
                    score_parts.append(f"**{sub}**\n\n{m.group(1).strip()}")
            if score_parts:
                metrics["score_rationale"] = "\n\n".join(score_parts)

    # Parse startup_validator.md for risk level and claims
    validator_text = _read_file_text("risk-assessment", "startup_validator.md")
    if validator_text:
        m = _RE_RISK_LEVEL.search(validator_text)
        if m:
            metrics["risk_level"] = m.group(1).upper()
        m = _RE_CLAIMS.search(validator_text)
        if m:
            metrics["claims_total"] = m.group(1)
            metrics["claims_supported"] = m.group(2)
            metrics["claims_partial"] = m.group(3)

        # Risk rationale: identified risks section
        risks = _extract_section(validator_text, "Identified Risks")
        if risks:
            metrics["risk_rationale"] = risks

        # Claims rationale: claims analysis section
        claims = _extract_section(validator_text, "Claims Analysis")
        if claims:
            metrics["claims_rationale"] = claims

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


def _metric_html(label: str, value: str, color: str) -> str:
    """Return centered HTML for a single dashboard metric."""
    return (
        f'<div style="{_METRIC_DIV_STYLE}">'
        f'<span style="font-size:0.95rem;color:#888;">{label}</span>'
        f'<span style="color:{color};font-weight:700;font-size:1.8rem;">'
        f"{value}</span></div>"
    )


def _render_metric_with_rationale(
    label: str,
    value: str,
    color: str,
    rationale: str | None,
    expander_label: str,
    *,
    badge: bool = False,
) -> None:
    """Render a single metric with an optional rationale expander below it."""
    if badge:
        st.markdown(
            f'<div style="{_METRIC_DIV_STYLE}">'
            f'<span style="font-size:0.95rem;color:#888;">{label}</span>'
            f'<span style="background:{color};color:#fff;padding:0.3rem 1.2rem;'
            f'border-radius:0.4rem;font-weight:700;font-size:1.8rem;">'
            f"{value}</span></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(_metric_html(label, value, color), unsafe_allow_html=True)
    if rationale:
        with st.expander(expander_label):
            st.markdown(rationale)


def render_metrics_dashboard(metrics: dict) -> None:
    """Render metrics in a 2x2 grid with inline rationale expanders."""
    # Row 1: Verdict + Score
    left, right = st.columns(2)
    with left:
        verdict = metrics.get("verdict")
        color = _VERDICT_COLORS.get(verdict, "#9E9E9E") if verdict else "#9E9E9E"
        _render_metric_with_rationale(
            "Verdict",
            verdict or "---",
            color,
            metrics.get("verdict_rationale"),
            "Knockout Criteria & Guidance",
            badge=bool(verdict),
        )
    with right:
        score = metrics.get("composite_score")
        # Score color follows the verdict so the two markers stay visually consistent
        color = _VERDICT_COLORS.get(verdict, "#9E9E9E") if verdict else "#9E9E9E"
        _render_metric_with_rationale(
            "Score",
            f"{score} / 5.0" if score else "---",
            color,
            metrics.get("score_rationale"),
            "Dimension Breakdown",
        )

    # Row 2: Risk Level + Claims Validated
    left, right = st.columns(2)
    with left:
        risk = metrics.get("risk_level")
        risk_colors = {"LOW": "#4CAF50", "MEDIUM": "#FF9800", "HIGH": "#F44336"}
        color = risk_colors.get(risk, "#9E9E9E") if risk else "#9E9E9E"
        _render_metric_with_rationale(
            "Risk Level",
            risk or "---",
            color,
            metrics.get("risk_rationale"),
            "Identified Risks",
        )
    with right:
        total = metrics.get("claims_total")
        supported = metrics.get("claims_supported")
        if total and supported:
            ratio = int(supported) / int(total)
            color = "#4CAF50" if ratio >= 0.7 else "#FF9800" if ratio >= 0.4 else "#F44336"
            value = f"{supported}/{total}"
        else:
            color = "#9E9E9E"
            value = "---"
        _render_metric_with_rationale(
            "Claims Validated",
            value,
            color,
            metrics.get("claims_rationale"),
            "Full Claims Analysis",
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

# Metrics dashboard (only when validation-summary is complete)
if get_stage_status("validation-summary"):
    metrics = extract_metrics()
    render_metrics_dashboard(metrics)
    st.divider()

# Tabbed view for completed stages (includes pivot-strategy when present)
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
# Pivot Decision Point (HIGH Risk Flow)
# -----------------------------------------------------------------------------


def handle_refined_idea_accept(refined_idea: str) -> None:
    """Handle acceptance of refined idea."""
    from haytham.session.session_manager import SessionManager

    # Store diff for display in execution view
    st.session_state.idea_diff = {
        "original": idea_text,
        "refined": refined_idea,
    }

    # Update system goal with refined idea
    session_manager = SessionManager(str(SESSION_DIR.parent))
    session_manager.set_system_goal(refined_idea)

    # Clear validation stages for re-run
    session_manager.clear_workflow_stages("idea-validation")

    # Cleanup refinement state
    clear_refinement_state()
    if "refinement_mode" in st.session_state:
        del st.session_state.refinement_mode

    # Store validated idea and trigger workflow
    st.session_state.validated_idea = refined_idea
    st.session_state.new_idea = refined_idea
    st.rerun()


def handle_refinement_cancel() -> None:
    """Handle refinement cancellation."""
    clear_refinement_state()
    if "refinement_mode" in st.session_state:
        del st.session_state.refinement_mode
    st.rerun()


# Check if we're in refinement mode (HIGH risk detected and user chose to refine)
if has_pivot_strategy() and not is_workflow_locked():
    # Check if user is in refinement mode
    if st.session_state.get("refinement_mode"):
        # Render the refinement conversation
        render_idea_refinement(
            original_idea=idea_text or "",
            session_dir=SESSION_DIR,
            on_accept=handle_refined_idea_accept,
            on_cancel=handle_refinement_cancel,
        )
        st.stop()

    # Show decision UI
    st.divider()
    st.warning("### High Risk Detected")
    st.markdown(
        "The validation identified significant risks with your idea. "
        "Review the **Pivot Strategy** tab above for alternative approaches."
    )

    st.markdown("**What would you like to do?**")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Continue Anyway", use_container_width=True):
            # Lock workflow and proceed to MVP spec
            from lib.workflow_runner import lock_workflow as _lock_wf

            _lock_wf(WORKFLOW_TYPE, SESSION_DIR)
            clear_chat_history(WORKFLOW_TYPE)
            st.session_state.run_mvp_workflow = True
            st.rerun()
    with col2:
        if st.button("Refine Idea", type="primary", use_container_width=True):
            st.session_state.refinement_mode = True
            st.rerun()
    with col3:
        if st.button("Start Over", use_container_width=True):
            from lib.session_utils import clear_session

            clear_session()
            st.rerun()

    # Offer report download even on HIGH risk
    if get_stage_status("validation-summary"):
        try:
            from haytham.agents.tools.pdf_report import generate_pdf
            from haytham.agents.tools.report_configs import build_idea_validation_config

            _report_config = build_idea_validation_config(SESSION_DIR)
            _pdf_bytes = generate_pdf(_report_config)
            st.download_button(
                "Download Report",
                data=_pdf_bytes,
                file_name="haytham-idea-validation-report.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )
        except (ImportError, OSError, ValueError):
            pass  # Silently skip if PDF generation fails

    st.stop()

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
    if (SESSION_DIR / "risk-assessment").exists():
        accomplishments.append("Risk assessment completed")
    if (SESSION_DIR / "validation-summary").exists():
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
    stage_slugs = [s["id"] for s in STAGES if s["id"] != "pivot-strategy"]

    # Generate PDF download data when validation-summary is complete
    _pdf_download_data = None
    if get_stage_status("validation-summary"):
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
        except (ImportError, OSError, ValueError):
            pass  # Silently skip if PDF generation fails

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
