"""Artifacts View - Browse capabilities, decisions, entities."""

from lib.session_utils import get_session_dir, setup_paths

setup_paths()

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

SESSION_DIR = get_session_dir()

# -----------------------------------------------------------------------------
# Data Loading Functions
# -----------------------------------------------------------------------------


@st.cache_data(ttl=60)
def load_capabilities():
    """Load capabilities from VectorDB."""
    try:
        from haytham.state.vector_db import SystemStateDB

        db_path = SESSION_DIR / "vector_db"
        if db_path.exists():
            db = SystemStateDB(str(db_path))
            caps = db.get_capabilities()
            return caps
    except Exception as e:
        st.error(f"Error loading capabilities: {e}")
    return []


@st.cache_data(ttl=60)
def load_decisions():
    """Load decisions from VectorDB."""
    try:
        from haytham.state.vector_db import SystemStateDB

        db_path = SESSION_DIR / "vector_db"
        if db_path.exists():
            db = SystemStateDB(str(db_path))
            return db.get_decisions()
    except Exception as e:
        st.error(f"Error loading decisions: {e}")
    return []


@st.cache_data(ttl=60)
def load_entities():
    """Load entities from VectorDB."""
    try:
        from haytham.state.vector_db import SystemStateDB

        db_path = SESSION_DIR / "vector_db"
        if db_path.exists():
            db = SystemStateDB(str(db_path))
            return db.get_entities()
    except Exception as e:
        st.error(f"Error loading entities: {e}")
    return []


# -----------------------------------------------------------------------------
# Sidebar
# -----------------------------------------------------------------------------

with st.sidebar:
    st.title("Artifacts")

    st.divider()

    # Summary counts
    caps = load_capabilities()
    decs = load_decisions()
    ents = load_entities()

    st.metric("Capabilities", len(caps))
    st.metric("Decisions", len(decs))
    st.metric("Entities", len(ents))

    st.divider()

    if st.button("Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# -----------------------------------------------------------------------------
# Main Content
# -----------------------------------------------------------------------------

st.title("Artifact Browser")

# Tabs for different artifact types
tab1, tab2, tab3 = st.tabs(["Capabilities", "Decisions", "Entities"])

# -----------------------------------------------------------------------------
# Capabilities Tab
# -----------------------------------------------------------------------------

with tab1:
    st.subheader("Capabilities")

    # Helpful description
    with st.container():
        st.markdown("""
        **What are Capabilities?**

        Capabilities are the business requirements extracted from your startup idea during the Discovery phase.
        They represent *what* your product needs to do to deliver value to users.

        - **CAP-F-xxx**: Functional capabilities (features users interact with)
        - **CAP-NF-xxx**: Non-functional capabilities (quality attributes like security, performance)

        Each capability will be implemented by one or more **Stories** in the implementation phase.
        """)

    st.divider()

    caps = load_capabilities()

    if not caps:
        st.info("No capabilities found. Run the Discovery workflow first.")
    else:
        # Search filter
        search = st.text_input("Search capabilities", key="cap_search")

        # Filter by search
        if search:
            caps = [
                c
                for c in caps
                if search.lower() in c.get("name", "").lower()
                or search.lower() in c.get("description", "").lower()
            ]

        # Display as expandable cards
        for cap in caps:
            cap_id = cap.get("id", "Unknown")
            cap_name = cap.get("name", "Unnamed")
            cap_type = cap.get("type", "unknown")
            cap_desc = cap.get("description", "No description")

            # Color-code by type
            type_colors = {
                "functional": "[F]",
                "non-functional": "[NF]",
                "technical": "[T]",
            }
            type_icon = type_colors.get(cap_type, "[?]")

            with st.expander(f"{type_icon} **{cap_id}**: {cap_name}"):
                st.markdown(f"**Type:** {cap_type}")
                st.markdown(f"**Description:** {cap_desc}")

                # Show raw JSON in a code block
                with st.popover("View Raw JSON"):
                    st.json(cap)

        # Also show as a sortable table
        st.divider()
        st.markdown("### Table View")

        df = pd.DataFrame(caps)
        if not df.empty:
            # Select columns to display
            display_cols = ["id", "name", "type", "description"]
            display_cols = [c for c in display_cols if c in df.columns]
            st.dataframe(
                df[display_cols],
                use_container_width=True,
                hide_index=True,
            )

# -----------------------------------------------------------------------------
# Decisions Tab
# -----------------------------------------------------------------------------

with tab2:
    st.subheader("Architecture Decisions")

    # Helpful description
    with st.container():
        st.markdown("""
        **What are Architecture Decisions?**

        Architecture Decisions (DEC-*) are the technical choices made during the Architect phase.
        They define *how* your capabilities will be implemented.

        Each decision includes:
        - **Title**: What was decided
        - **Rationale**: Why this choice was made
        - **Related Capabilities**: Which CAP-* items this enables

        Decisions inform the **Infrastructure Stories** (Layer 3) that set up your technical foundation.
        """)

    st.divider()

    decs = load_decisions()

    if not decs:
        st.info("No decisions found. Run the Technical Translation workflow first.")
    else:
        # Search filter
        search = st.text_input("Search decisions", key="dec_search")

        if search:
            decs = [
                d
                for d in decs
                if search.lower() in d.get("title", "").lower()
                or search.lower() in d.get("rationale", "").lower()
            ]

        for dec in decs:
            dec_id = dec.get("id", "Unknown")
            dec_title = dec.get("title", "Unnamed")
            dec_rationale = dec.get("rationale", "No rationale")
            dec_category = dec.get("category", "unknown")

            with st.expander(f"**{dec_id}**: {dec_title}"):
                st.markdown(f"**Category:** {dec_category}")
                st.markdown(f"**Rationale:** {dec_rationale}")

                # Show related capabilities
                related_caps = dec.get("related_capabilities", [])
                if related_caps:
                    st.markdown(f"**Implements:** {', '.join(related_caps)}")

                with st.popover("View Raw JSON"):
                    st.json(dec)

        # Table view
        st.divider()
        st.markdown("### Table View")

        df = pd.DataFrame(decs)
        if not df.empty:
            display_cols = ["id", "title", "category", "rationale"]
            display_cols = [c for c in display_cols if c in df.columns]
            st.dataframe(
                df[display_cols],
                use_container_width=True,
                hide_index=True,
            )

# -----------------------------------------------------------------------------
# Entities Tab
# -----------------------------------------------------------------------------

with tab3:
    st.subheader("Domain Entities")

    # Helpful description
    with st.container():
        st.markdown("""
        **What are Domain Entities?**

        Domain Entities (ENT-*) are the core data models that represent your business domain.
        They define *what data* your system will store and manage.

        Each entity includes:
        - **Attributes**: The fields/columns (e.g., name, email, created_at)
        - **Relationships**: How entities connect (e.g., Member belongs to Gym)

        Entities become **Entity Model Stories** (Layer 2) that create your database schema.
        """)

    st.divider()

    ents = load_entities()

    if not ents:
        st.info("No entities found. Run the Technical Translation workflow first.")
    else:
        # Search filter
        search = st.text_input("Search entities", key="ent_search")

        if search:
            ents = [
                e
                for e in ents
                if search.lower() in e.get("name", "").lower()
                or search.lower() in str(e.get("attributes", [])).lower()
            ]

        for ent in ents:
            ent_id = ent.get("id", "Unknown")
            ent_name = ent.get("name", "Unnamed")
            ent_desc = ent.get("description", "No description")
            attributes = ent.get("attributes", [])
            relationships = ent.get("relationships", [])

            with st.expander(f"**{ent_id}**: {ent_name}"):
                st.markdown(f"**Description:** {ent_desc}")

                # Attributes table
                if attributes:
                    st.markdown("**Attributes:**")
                    attr_df = pd.DataFrame(attributes)
                    st.dataframe(attr_df, use_container_width=True, hide_index=True)

                # Relationships
                if relationships:
                    st.markdown("**Relationships:**")
                    for rel in relationships:
                        st.markdown(
                            f"- {rel.get('type', 'relates to')} -> **{rel.get('target', 'Unknown')}**"
                        )

                with st.popover("View Raw JSON"):
                    st.json(ent)

        # Table view
        st.divider()
        st.markdown("### Table View")

        df = pd.DataFrame(ents)
        if not df.empty:
            display_cols = ["id", "name", "description"]
            display_cols = [c for c in display_cols if c in df.columns]
            st.dataframe(
                df[display_cols],
                use_container_width=True,
                hide_index=True,
            )
