"""Stories View - View implementation stories with feedback."""

import json
from datetime import datetime as _datetime

from lib.session_utils import get_session_dir, load_environment, setup_paths

setup_paths()
load_environment()

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
import yaml  # noqa: E402
from components.decision_gate import render_decision_gate  # noqa: E402
from components.feedback_conversation import (  # noqa: E402
    clear_chat_history,
    render_feedback_conversation,
)

from haytham.exporters import (  # noqa: E402
    CSVExporter,
    ExportOptions,
    JiraExporter,
    LinearExporter,
    MarkdownExporter,
    load_stories_from_json,
)

SESSION_DIR = get_session_dir()

# Workflow configuration
WORKFLOW_TYPE = "story-generation"
WORKFLOW_DISPLAY_NAME = "Story Generation"

# Stage slugs for story generation workflow
STORY_STAGES = [
    "story-generation",
    "story-validation",
    "dependency-ordering",
]


def load_startup_idea() -> str | None:
    """Load startup idea from project.yaml."""
    project_file = SESSION_DIR / "project.yaml"
    if project_file.exists():
        try:
            data = yaml.safe_load(project_file.read_text())
            return data.get("system_goal", "")
        except Exception:
            pass
    return None


# -----------------------------------------------------------------------------
# Data Loading
# -----------------------------------------------------------------------------


def parse_stories_from_markdown(content: str) -> list[dict]:
    """Parse stories from markdown format.

    Handles multiple formats:
    - YAML frontmatter format: ---\nid: STORY-001\ntitle: ...\n---
    - Header format: ### STORY-001: Title
    - Old format: ## Story N: Title
    """
    import re

    stories = []

    # Try YAML frontmatter format first
    # Strip standalone code fence lines (stories may be wrapped in ``` blocks)
    cleaned = re.sub(r"^```\s*$", "", content, flags=re.MULTILINE)

    # Split on YAML frontmatter opening markers (--- followed by id: STORY-NNN)
    parts = re.split(r"(?=^---\s*\nid:\s*STORY-)", cleaned, flags=re.MULTILINE)

    for part in parts:
        part = part.strip()
        if not part or not part.startswith("---"):
            continue

        # Split frontmatter from body at the closing ---
        fm_match = re.match(r"^---\s*\n(.*?)\n---\s*$(.*)", part, re.DOTALL | re.MULTILINE)
        if not fm_match:
            continue

        frontmatter_text = fm_match.group(1)
        body = fm_match.group(2).strip()

        # Remove trailing --- that acts as a story separator
        body = re.sub(r"\n---\s*$", "", body).strip()

        story = {}

        # Extract YAML frontmatter fields
        id_match = re.search(r"^id:\s*(.+)$", frontmatter_text, re.MULTILINE)
        title_match = re.search(r"^title:\s*(.+)$", frontmatter_text, re.MULTILINE)
        layer_match = re.search(r"^layer:\s*(\d+)", frontmatter_text, re.MULTILINE)
        implements_match = re.search(r"^implements:\s*\[([^\]]*)\]", frontmatter_text, re.MULTILINE)
        depends_match = re.search(r"^depends_on:\s*\[([^\]]*)\]", frontmatter_text, re.MULTILINE)

        if id_match:
            story["id"] = id_match.group(1).strip()
        if title_match:
            story["title"] = title_match.group(1).strip()
        if layer_match:
            story["layer"] = int(layer_match.group(1))
            story["labels"] = [f"layer:{layer_match.group(1)}"]
        if implements_match:
            implements_str = implements_match.group(1)
            implements_list = [
                x.strip().strip("'\"") for x in implements_str.split(",") if x.strip()
            ]
            if "labels" not in story:
                story["labels"] = []
            story["labels"].extend([f"implements:{impl}" for impl in implements_list])
        if depends_match:
            depends_str = depends_match.group(1)
            story["depends_on"] = [
                x.strip().strip("'\"") for x in depends_str.split(",") if x.strip()
            ]

        # Extract description from body (after the frontmatter)
        desc_section = re.search(r"## Description\s*\n(.+?)(?=\n##|\Z)", body, re.DOTALL)
        if desc_section:
            story["description"] = desc_section.group(1).strip()

        # Extract acceptance criteria from body
        criteria = []
        for ac_match in re.finditer(r"- \[[ x]\]\s*(.+)", body):
            criteria.append(ac_match.group(1).strip())
        if criteria:
            story["acceptance_criteria"] = criteria

        # Store full content for detail view
        story["content"] = body

        if story.get("id"):
            stories.append(story)

    if stories:
        return stories

    # Try header format: ### STORY-XXX: Title
    story_blocks = re.split(r"(?=###\s*STORY-\d+:)", content)

    for block in story_blocks:
        if not block.strip():
            continue

        story_match = re.search(r"###\s*(STORY-\d+):\s*(.+)", block)
        if not story_match:
            continue

        story = {}
        story["id"] = story_match.group(1)
        story["title"] = story_match.group(2).strip()

        desc_match = re.search(r"\*\*Description:\*\*\s*(.+)", block)
        if desc_match:
            story["description"] = desc_match.group(1).strip()

        impl_match = re.search(r"\*\*Implements:\*\*\s*(.+)", block)
        if impl_match:
            implements = impl_match.group(1).strip()
            story["labels"] = [f"implements:{impl.strip()}" for impl in implements.split(",")]

        deps_match = re.search(r"\*\*Depends On:\*\*\s*(.+)", block)
        if deps_match:
            deps = deps_match.group(1).strip()
            story["depends_on"] = [d.strip() for d in deps.split(",")]

        layer_match = re.search(r"## Layer (\d+):", content[: content.find(block)])
        if layer_match:
            story["layer"] = int(layer_match.group(1))

        criteria = []
        for match in re.finditer(r"- \[[ x]\]\s*(.+)", block):
            criteria.append(match.group(1).strip())
        if criteria:
            story["acceptance_criteria"] = criteria

        stories.append(story)

    # If no stories found, try old format: ## Story N: Title
    if not stories:
        story_blocks = re.split(r"(?=## Story \d+:)", content)
        for block in story_blocks:
            if not block.strip() or not block.startswith("## Story"):
                continue

            story = {}
            title_match = re.search(r"## Story (\d+):\s*(.+)", block)
            if title_match:
                story["id"] = f"STORY-{int(title_match.group(1)):03d}"
                story["title"] = title_match.group(2).strip()

            impl_match = re.search(r"\*\*implements:\*\*\s*(.+)", block, re.IGNORECASE)
            if impl_match:
                story["labels"] = [f"implements:{impl_match.group(1).strip()}"]

            desc_match = re.search(r"\*\*Description:\*\*\s*(.+)", block)
            if desc_match:
                story["description"] = desc_match.group(1).strip()

            criteria = []
            for match in re.finditer(r"- \[[ x]\]\s*(.+)", block):
                criteria.append(match.group(1).strip())
            if criteria:
                story["acceptance_criteria"] = criteria

            if story.get("title"):
                stories.append(story)

    return stories


def _enrich_story(story: dict) -> dict:
    """Enrich a story dict loaded from JSON with derived fields for display.

    Extracts 'description' and 'acceptance_criteria' from the 'content' field
    so the view layer can access them directly.
    """
    import re

    content = story.get("content", "")

    # Strip wrapping code fences (detail agents sometimes wrap output in ```markdown ... ```)
    if content:
        content = re.sub(r"^```\w*\s*\n?", "", content)
        content = re.sub(r"\n?```\s*$", "", content)
        content = content.strip()
        story["content"] = content

    # Extract description from ## Description section
    if "description" not in story and content:
        desc_match = re.search(r"## Description\s*\n(.+?)(?=\n##|\Z)", content, re.DOTALL)
        if desc_match:
            story["description"] = desc_match.group(1).strip()

    # Extract acceptance criteria from checklist items
    if "acceptance_criteria" not in story and content:
        criteria = []
        for ac_match in re.finditer(r"- \[[ x]\]\s*(.+)", content):
            criteria.append(ac_match.group(1).strip())
        if criteria:
            story["acceptance_criteria"] = criteria

    return story


@st.cache_data(ttl=60)
def load_stories():
    """Load stories from stories.json (preferred) or fall back to markdown parsing."""
    # Primary: structured JSON from hybrid output (no parsing needed)
    stories_json = SESSION_DIR / "story-generation" / "stories.json"
    if stories_json.exists():
        try:
            stories = json.loads(stories_json.read_text())
            if stories:
                return [_enrich_story(s) for s in stories]
        except Exception as e:
            st.warning(f"Error loading stories.json: {e}")

    # Fallback: parse from markdown (old sessions)
    story_md = SESSION_DIR / "story-generation" / "story_generation.md"
    if story_md.exists():
        try:
            content = story_md.read_text()
            stories = parse_stories_from_markdown(content)
            if stories:
                return stories
        except Exception as e:
            st.warning(f"Error parsing story markdown: {e}")

    # Legacy fallback
    stories_file = SESSION_DIR / "generated_stories.json"
    if stories_file.exists():
        try:
            return json.loads(stories_file.read_text())
        except Exception as e:
            st.error(f"Error loading stories: {e}")
    return []


def get_story_layer(story):
    """Extract layer from story."""
    # First check direct layer attribute
    if "layer" in story:
        return story["layer"]
    # Fallback to labels
    labels = story.get("labels", [])
    for label in labels:
        if label.startswith("layer:"):
            return int(label.split(":")[1])
    return 0


def get_story_type(story):
    """Extract type from story labels."""
    labels = story.get("labels", [])
    for label in labels:
        if label.startswith("type:"):
            return label.split(":")[1]
    return "unknown"


# -----------------------------------------------------------------------------
# Main Content
# -----------------------------------------------------------------------------

st.title("Implementation Stories")

# Show the idea
idea_text = load_startup_idea()
if idea_text:
    st.markdown(
        f"""
<div style="background-color: #f0e6f6; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #6B2D8B; margin: 0.5rem 0 1.5rem 0;">
    <p style="font-size: 1rem; line-height: 1.5; margin: 0; color: #333;">{idea_text}</p>
</div>
""",
        unsafe_allow_html=True,
    )

stories = load_stories()

if not stories:
    st.info("No stories found. Run the Story Generation stage from the MVP Specification page.")
    st.stop()

# Summary metrics
layer_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
for story in stories:
    layer = get_story_layer(story)
    if layer in layer_counts:
        layer_counts[layer] += 1

col1, col2, col3 = st.columns(3)
col1.metric("Total Stories", len(stories))
col2.metric("Layers", len([ly for ly, cnt in layer_counts.items() if cnt > 0]))
col3.metric("Capabilities", sum(len(s.get("implements", [])) for s in stories))

st.divider()

# View toggle
view_mode = st.radio("View Mode", ["By Layer", "Table View", "Dependency Graph"], horizontal=True)

st.divider()

# -----------------------------------------------------------------------------
# By Layer View
# -----------------------------------------------------------------------------

if view_mode == "By Layer":
    # Group stories by layer
    layers: dict[int, list] = {}
    for story in stories:
        layer = get_story_layer(story)
        if layer not in layers:
            layers[layer] = []
        layers[layer].append(story)

    layer_info = {
        0: ("Layer 0: Foundation", "Project setup, dependencies, database schema, config"),
        1: ("Layer 1: Authentication", "Auth setup, middleware, route protection"),
        2: ("Layer 2: Integrations", "Third-party services, access control, deployment"),
        3: ("Layer 3: Core Functionality", "API endpoints, business logic, input validation"),
        4: ("Layer 4: User Interface", "Pages, components, navigation, responsive layout"),
        5: ("Layer 5: Real-Time", "Subscriptions, websockets, live updates"),
    }

    for layer_num in sorted(layers.keys()):
        layer_stories = layers[layer_num]
        if not layer_stories:
            continue

        title, desc = layer_info.get(layer_num, (f"Layer {layer_num}", ""))

        st.subheader(f"{title} ({len(layer_stories)} stories)")
        st.caption(desc)

        for story in layer_stories:
            story_title = story.get("title", "Untitled")
            story_id = story.get("id", "")
            story_content = story.get("content", "")
            story_implements = story.get("implements", [])
            story_depends = story.get("depends_on", [])
            story_priority = story.get("priority", "medium")
            story_order = story.get("order", 0)

            # Priority indicator
            priority_icons = {"high": "[!]", "medium": "[=]", "low": "[-]"}
            priority_icon = priority_icons.get(story_priority, "[?]")

            with st.expander(f"{priority_icon} **{story_order}. {story_title}**"):
                # Metadata bar
                meta_parts = []
                if story_id:
                    meta_parts.append(f"`{story_id}`")
                if story_implements:
                    meta_parts.append(
                        "Implements: " + ", ".join(f"`{x}`" for x in story_implements)
                    )
                if story_depends:
                    meta_parts.append("Depends on: " + ", ".join(f"`{x}`" for x in story_depends))
                if meta_parts:
                    st.markdown(" | ".join(meta_parts))

                # Full content as markdown
                if story_content:
                    st.markdown(story_content)
                else:
                    st.markdown(story.get("description", "No description"))

        st.divider()

# -----------------------------------------------------------------------------
# Table View
# -----------------------------------------------------------------------------

elif view_mode == "Table View":
    # Convert to DataFrame
    table_data = []
    for story in stories:
        table_data.append(
            {
                "Order": story.get("order", 0),
                "Title": story.get("title", ""),
                "Layer": get_story_layer(story),
                "Type": get_story_type(story),
                "Priority": story.get("priority", "medium"),
                "Dependencies": len(story.get("dependencies", [])),
                "Acceptance Criteria": len(story.get("acceptance_criteria", [])),
            }
        )

    df = pd.DataFrame(table_data)
    df = df.sort_values("Order")

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        layer_filter = st.multiselect("Filter by Layer", [1, 2, 3, 4])
    with col2:
        type_filter = st.multiselect("Filter by Type", df["Type"].unique().tolist())
    with col3:
        priority_filter = st.multiselect("Filter by Priority", ["high", "medium", "low"])

    # Apply filters
    if layer_filter:
        df = df[df["Layer"].isin(layer_filter)]
    if type_filter:
        df = df[df["Type"].isin(type_filter)]
    if priority_filter:
        df = df[df["Priority"].isin(priority_filter)]

    # Display
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Order": st.column_config.NumberColumn("Order", width="small"),
            "Layer": st.column_config.NumberColumn("Layer", width="small"),
            "Priority": st.column_config.TextColumn("Priority", width="small"),
        },
    )

    # Summary stats
    st.divider()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Stories", len(df))
    with col2:
        st.metric("High Priority", len(df[df["Priority"] == "high"]))
    with col3:
        st.metric("Total AC", df["Acceptance Criteria"].sum())
    with col4:
        st.metric("Avg Dependencies", f"{df['Dependencies'].mean():.1f}")

# -----------------------------------------------------------------------------
# Dependency Graph View
# -----------------------------------------------------------------------------

elif view_mode == "Dependency Graph":
    st.info("Dependency graph visualization would go here. Could use graphviz or mermaid.")

    # Simple text-based dependency view
    st.subheader("Story Dependencies")

    for story in sorted(stories, key=lambda s: s.get("order", 0)):
        title = story.get("title", "Untitled")
        deps = story.get("dependencies", [])
        order = story.get("order", 0)

        if deps:
            dep_str = " -> ".join(deps)
            st.markdown(f"**{order}. {title}**")
            st.markdown(f"   depends on: {dep_str}")
        else:
            st.markdown(f"**{order}. {title}** (no dependencies)")

    # Mermaid diagram (if we want to add it)
    st.divider()
    st.subheader("Mermaid Diagram")

    mermaid_lines = ["graph TD"]
    for story in stories:
        title = story.get("title", "").replace(" ", "_")[:20]
        order = story.get("order", 0)
        node_id = f"S{order}"

        for dep in story.get("dependencies", []):
            dep_clean = dep.replace(" ", "_")[:20]
            # Find the order of the dependency
            dep_order = next((s.get("order", 0) for s in stories if s.get("title") == dep), 0)
            dep_id = f"S{dep_order}"
            mermaid_lines.append(f"    {dep_id}[{dep_clean}] --> {node_id}[{title}]")

    st.code("\n".join(mermaid_lines), language="mermaid")

# -----------------------------------------------------------------------------
# Feedback / Completion Section
# -----------------------------------------------------------------------------


def is_workflow_locked() -> bool:
    """Check if the story-generation workflow is locked."""
    lock_file = SESSION_DIR / f".{WORKFLOW_TYPE}.locked"
    return lock_file.exists()


def lock_workflow() -> None:
    """Lock the story-generation workflow."""
    lock_file = SESSION_DIR / f".{WORKFLOW_TYPE}.locked"
    lock_data = {
        "locked_at": _datetime.utcnow().isoformat() + "Z",
        "workflow_type": WORKFLOW_TYPE,
    }
    lock_file.write_text(json.dumps(lock_data, indent=2))
    # Clear chat history when locking
    clear_chat_history(WORKFLOW_TYPE)


def handle_accept() -> None:
    """Handle accept and finalize action."""
    lock_workflow()
    st.success(f"{WORKFLOW_DISPLAY_NAME} locked and saved!")
    st.rerun()


st.divider()

if is_workflow_locked():
    # Decision gate - Coming Soon for BUILD/VALIDATE
    accomplishments = [f"{len(stories)} implementation stories generated"]
    layer_counts_summary = {k: v for k, v in layer_counts.items() if v > 0}
    if layer_counts_summary:
        accomplishments.append(f"{len(layer_counts_summary)} implementation layers organized")
    accomplishments.append("Stories validated and dependency-ordered")

    render_decision_gate(
        phase_name="Story Generation",
        accomplishments=accomplishments,
        next_phase_name="Implementation (BUILD)",
        next_phase_preview="Automatically generate working code from your ordered stories.",
        next_phase_details=[
            "Scaffold project structure from architecture decisions",
            "Implement each story in dependency order",
            "Validate generated code against acceptance criteria",
        ],
        coming_soon=True,
        is_locked=True,
    )

    # Export Panel

    # Export format selection
    export_format = st.selectbox(
        "Export Format",
        options=["Linear (CSV)", "Jira (CSV)", "Markdown", "Generic CSV", "JSON"],
        help="Choose the format that matches your project management tool",
    )

    # Export options in an expander
    with st.expander("Export Options", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            include_ac = st.checkbox("Include Acceptance Criteria", value=True)
            include_deps = st.checkbox("Include Dependencies", value=True)
        with col2:
            include_labels = st.checkbox("Include Labels", value=True)
            story_prefix = st.text_input("Story ID Prefix", value="STORY")

        # Layer filter
        st.markdown("**Filter by Layer:**")
        layer_cols = st.columns(4)
        layer_filters = []
        with layer_cols[0]:
            if st.checkbox("Layer 1: Bootstrap", value=True):
                layer_filters.append(1)
        with layer_cols[1]:
            if st.checkbox("Layer 2: Entities", value=True):
                layer_filters.append(2)
        with layer_cols[2]:
            if st.checkbox("Layer 3: Infrastructure", value=True):
                layer_filters.append(3)
        with layer_cols[3]:
            if st.checkbox("Layer 4: Features", value=True):
                layer_filters.append(4)

    # Build export options
    export_options = ExportOptions(
        include_acceptance_criteria=include_ac,
        include_dependencies=include_deps,
        include_labels=include_labels,
        story_id_prefix=story_prefix,
        filter_layers=layer_filters if layer_filters else None,
    )

    # Transform stories
    exportable_stories = load_stories_from_json(stories, export_options)

    # Filter by layers
    if export_options.filter_layers:
        exportable_stories = [
            s for s in exportable_stories if s.layer in export_options.filter_layers
        ]

    # Export buttons
    if export_format == "Linear (CSV)":
        exporter = LinearExporter(export_options)
        content = exporter.export(exportable_stories)
        filename = exporter.get_filename("project")
        mime = exporter.mime_type
        st.download_button(
            "📥 Download for Linear",
            content,
            file_name=filename,
            mime=mime,
            type="primary",
            use_container_width=True,
        )
        st.caption("Import this file into Linear: Settings → Import → CSV Import")

    elif export_format == "Jira (CSV)":
        exporter = JiraExporter(export_options)
        content = exporter.export(exportable_stories)
        filename = exporter.get_filename("project")
        mime = exporter.mime_type
        st.download_button(
            "📥 Download for Jira",
            content,
            file_name=filename,
            mime=mime,
            type="primary",
            use_container_width=True,
        )
        st.caption("Import this file into Jira: Project Settings → Import → CSV")

    elif export_format == "Markdown":
        exporter = MarkdownExporter(export_options)
        content = exporter.export(exportable_stories)
        filename = exporter.get_filename("project")
        mime = exporter.mime_type
        st.download_button(
            "📥 Download Markdown",
            content,
            file_name=filename,
            mime=mime,
            type="primary",
            use_container_width=True,
        )
        st.caption("Human-readable format, great for documentation or Claude Code")

    elif export_format == "Generic CSV":
        exporter = CSVExporter(export_options)
        content = exporter.export(exportable_stories)
        filename = exporter.get_filename("project")
        mime = exporter.mime_type
        st.download_button(
            "📥 Download CSV",
            content,
            file_name=filename,
            mime=mime,
            type="primary",
            use_container_width=True,
        )
        st.caption("Universal format for spreadsheets or custom imports")

    else:  # JSON
        stories_json = json.dumps(stories, indent=2)
        st.download_button(
            "📥 Download JSON",
            stories_json,
            file_name="stories.json",
            mime="application/json",
            type="primary",
            use_container_width=True,
        )
        st.caption("Raw JSON format with all original data")

    # Show preview
    with st.expander(f"Preview ({len(exportable_stories)} stories)"):
        if export_format in ["Linear (CSV)", "Jira (CSV)", "Generic CSV"]:
            st.code(content[:2000] + ("..." if len(content) > 2000 else ""), language="csv")
        elif export_format == "Markdown":
            st.markdown(content[:3000] + ("..." if len(content) > 3000 else ""))
        else:
            st.json(stories[:3])

else:
    # Workflow not locked - show chat-based feedback with intelligent agent
    render_feedback_conversation(
        workflow_type=WORKFLOW_TYPE,
        workflow_display_name=WORKFLOW_DISPLAY_NAME,
        on_accept=handle_accept,
        stage_slugs=STORY_STAGES,
        system_goal=idea_text or "",
        session_dir=SESSION_DIR,
    )
