"""Anchor Review Component - Review and edit concept anchor at Gate 1 (ADR-022 Part 1c).

Surfaces the extracted anchor to the user for confirmation before it propagates
to downstream stages. Users can correct misextracted constraints.
"""

import json
from pathlib import Path

import streamlit as st


def load_anchor(session_dir: Path) -> dict | None:
    """Load the concept anchor from session directory."""
    anchor_file = session_dir / "concept_anchor.json"
    if anchor_file.exists():
        try:
            return json.loads(anchor_file.read_text())
        except Exception:
            return None
    return None


def save_anchor(session_dir: Path, anchor_data: dict) -> bool:
    """Save the modified anchor back to session directory."""
    anchor_file = session_dir / "concept_anchor.json"
    try:
        # Rebuild the anchor_str from the modified anchor
        anchor = anchor_data.get("anchor", {})
        anchor_str = _build_anchor_string(anchor)
        anchor_data["anchor_str"] = anchor_str
        anchor_file.write_text(json.dumps(anchor_data, indent=2))
        return True
    except Exception as e:
        st.error(f"Failed to save anchor: {e}")
        return False


def _build_anchor_string(anchor: dict) -> str:
    """Build the anchor context string from the anchor dict."""
    intent = anchor.get("intent", {})
    invariants = anchor.get("invariants", [])
    identity = anchor.get("identity", [])

    lines = ["## Concept Anchor (MUST HONOR)", ""]

    # Intent section
    lines.append("### Intent")
    lines.append(f"**Goal:** {intent.get('goal', '')}")
    lines.append("")

    if intent.get("explicit_constraints"):
        lines.append("**Explicit Constraints:**")
        for c in intent["explicit_constraints"]:
            lines.append(f"- {c}")
        lines.append("")

    if intent.get("non_goals"):
        lines.append("**Non-Goals (do NOT add these):**")
        for ng in intent["non_goals"]:
            lines.append(f"- {ng}")
        lines.append("")

    # Invariants section
    if invariants:
        lines.append("### Invariants (MUST preserve)")
        for inv in invariants:
            lines.append(f"- **{inv.get('property', '')}**: {inv.get('value', '')}")
            if inv.get("source"):
                lines.append(f'  - Source: "{inv["source"]}"')
        lines.append("")

    # Identity section
    if identity:
        lines.append("### Identity Features (do NOT genericize)")
        for feat in identity:
            lines.append(f"- **{feat.get('feature', '')}**")
            if feat.get("why_distinctive"):
                lines.append(f"  - Risk: {feat['why_distinctive']}")
        lines.append("")

    # Concept health signals
    concept_health = anchor.get("concept_health")
    if concept_health and any(
        concept_health.get(k) for k in ("pain_clarity", "trigger_strength", "willingness_to_pay")
    ):
        lines.append("### Concept Health Signals")
        if concept_health.get("pain_clarity"):
            lines.append(f"- **Pain Clarity:** {concept_health['pain_clarity']}")
        if concept_health.get("trigger_strength"):
            lines.append(f"- **Trigger Strength:** {concept_health['trigger_strength']}")
        if concept_health.get("willingness_to_pay"):
            lines.append(f"- **Willingness to Pay:** {concept_health['willingness_to_pay']}")
        if concept_health.get("notes"):
            lines.append(f"- **Note:** {concept_health['notes']}")
        lines.append("")

    return "\n".join(lines)


_SIGNAL_COLORS = {
    "Clear": ("#E8F5E9", "#2E7D32", "#4CAF50"),  # green
    "Strong": ("#E8F5E9", "#2E7D32", "#4CAF50"),
    "Present": ("#E8F5E9", "#2E7D32", "#4CAF50"),
    "Ambiguous": ("#FFF8E1", "#F57C00", "#FFC107"),  # amber
    "Moderate": ("#FFF8E1", "#F57C00", "#FFC107"),
    "Unclear": ("#FFF8E1", "#F57C00", "#FFC107"),
    "Weak": ("#FFEBEE", "#C62828", "#EF5350"),  # red
    "Absent": ("#FFEBEE", "#C62828", "#EF5350"),
}


def _render_health_signals(concept_health: dict) -> None:
    """Render concept health signal badges."""
    for label, key in [
        ("Pain Clarity", "pain_clarity"),
        ("Trigger Strength", "trigger_strength"),
        ("Willingness to Pay", "willingness_to_pay"),
    ]:
        value = concept_health.get(key, "")
        if not value:
            continue
        bg, text_color, border = _SIGNAL_COLORS.get(value, ("#F5F5F5", "#555", "#999"))
        st.markdown(
            f"""<div style="background: {bg}; padding: 8px 12px; border-radius: 6px;
                       margin: 4px 0; border-left: 3px solid {border};">
                <span style="color: {text_color}; font-weight: 500;">{label}</span>
                <span style="color: #555;">: {value}</span>
            </div>""",
            unsafe_allow_html=True,
        )
    if concept_health.get("notes"):
        st.caption(concept_health["notes"])


def render_anchor_condensed(session_dir: Path) -> None:
    """Render a condensed anchor view: Constraints, Non-Goals, Concept Health only."""
    anchor_data = load_anchor(session_dir)
    if not anchor_data:
        st.caption("No concept anchor extracted yet.")
        return

    anchor = anchor_data.get("anchor", {})
    intent = anchor.get("intent", {})

    # Explicit Constraints
    constraints = intent.get("explicit_constraints", [])
    if constraints:
        st.markdown("##### Explicit Constraints")
        for constraint in constraints:
            st.markdown(f"- {constraint}")

    # Non-Goals
    non_goals = intent.get("non_goals", [])
    if non_goals:
        st.markdown("##### Non-Goals")
        st.caption("Things the system should NOT add")
        for ng in non_goals:
            st.markdown(f"- {ng}")

    # Concept Health Signals
    concept_health = anchor.get("concept_health")
    if concept_health and any(
        concept_health.get(k) for k in ("pain_clarity", "trigger_strength", "willingness_to_pay")
    ):
        st.markdown("##### Concept Health Signals")
        _render_health_signals(concept_health)


def render_anchor_review(
    session_dir: Path, expanded: bool = True, use_expander: bool = True
) -> bool:
    """Render the full anchor review component with clarification for ambiguous invariants.

    Args:
        session_dir: Path to session directory
        expanded: Whether to expand the review section by default
        use_expander: Whether to wrap content in an expander (False when inside a tab)

    Returns:
        True if there are unresolved ambiguities that need clarification
    """
    anchor_data = load_anchor(session_dir)

    if not anchor_data:
        return False

    anchor = anchor_data.get("anchor", {})
    intent = anchor.get("intent", {})
    invariants = anchor.get("invariants", [])
    identity = anchor.get("identity", [])

    # Check for low-confidence invariants that need clarification
    ambiguous_invariants = [
        inv
        for inv in invariants
        if inv.get("confidence", 1.0) < 0.7 and inv.get("clarification_options")
    ]
    has_unresolved = len(ambiguous_invariants) > 0

    # Header with explanation - different styling if clarification needed
    if has_unresolved:
        st.markdown(
            """
<div style="background: #FFF3E0; padding: 12px 16px; border-radius: 8px; margin: 12px 0;
            border-left: 4px solid #FF9800;">
    <div style="font-size: 13px; font-weight: 600; color: #E65100;">
        Clarification Needed
    </div>
    <div style="font-size: 12px; color: #666; margin-top: 4px;">
        Some constraints are ambiguous. Please clarify below before proceeding.
    </div>
</div>
""",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
<div style="background: #FFF8E1; padding: 12px 16px; border-radius: 8px; margin: 12px 0;
            border-left: 4px solid #FFC107;">
    <div style="font-size: 13px; font-weight: 600; color: #F57C00;">
        Extracted Constraints
    </div>
    <div style="font-size: 12px; color: #666; margin-top: 4px;">
        These constraints were extracted from your idea. They will guide all downstream stages
        and be verified at each phase gate.
    </div>
</div>
""",
            unsafe_allow_html=True,
        )

    container = st.expander("Concept Anchor", expanded=expanded) if use_expander else st.container()
    with container:
        # Goal
        st.markdown("##### Goal")
        st.info(intent.get("goal", "No goal extracted"))

        # Explicit Constraints
        st.markdown("##### Explicit Constraints")
        st.caption("Requirements you stated or strongly implied")
        constraints = intent.get("explicit_constraints", [])
        if constraints:
            for constraint in constraints:
                st.markdown(f"- {constraint}")
        else:
            st.caption("None extracted")

        st.markdown("---")

        # Non-Goals
        st.markdown("##### Non-Goals")
        st.caption("Things you did NOT ask for (inferred from constraints)")
        non_goals = intent.get("non_goals", [])
        if non_goals:
            for ng in non_goals:
                st.markdown(f"- {ng}")
        else:
            st.caption("None inferred")

        st.markdown("---")

        # Invariants
        st.markdown("##### Invariants (Must-Preserve Properties)")
        st.caption("These constraints will be checked at every phase gate")
        if invariants:
            for idx, inv in enumerate(invariants):
                confidence = inv.get("confidence", 1.0)
                is_ambiguous = confidence < 0.7 and inv.get("clarification_options")

                if is_ambiguous:
                    # Ambiguous invariant - show with warning styling and clarification options
                    st.markdown(
                        f"""<div style="background: #FFF3E0; padding: 10px 12px; border-radius: 6px;
                                   margin: 4px 0; border-left: 3px solid #FF9800;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="color: #E65100; font-weight: 500;">{inv.get("property", "")}</span>
                                <span style="font-size: 11px; color: #FF9800; background: #FFF8E1;
                                            padding: 2px 6px; border-radius: 4px;">
                                    {int(confidence * 100)}% confident
                                </span>
                            </div>
                            <div style="color: #555; margin-top: 4px;">{inv.get("value", "")}</div>
                        </div>""",
                        unsafe_allow_html=True,
                    )
                    if inv.get("ambiguity"):
                        st.caption(f"? {inv['ambiguity']}")

                    # Show clarification options
                    options = inv.get("clarification_options", [])
                    if options:
                        selected = st.radio(
                            f"Clarify: {inv.get('property', '')}",
                            options=options,
                            key=f"clarify_{idx}",
                            label_visibility="collapsed",
                        )
                        # Store selection in session state for later save
                        if f"anchor_clarification_{idx}" not in st.session_state:
                            st.session_state[f"anchor_clarification_{idx}"] = None
                        if selected:
                            st.session_state[f"anchor_clarification_{idx}"] = selected
                else:
                    # High-confidence invariant - show normally
                    st.markdown(
                        f"""<div style="background: #E8F5E9; padding: 8px 12px; border-radius: 6px;
                                   margin: 4px 0; border-left: 3px solid #4CAF50;">
                            <span style="color: #2E7D32; font-weight: 500;">{inv.get("property", "")}</span>
                            <span style="color: #555;">: {inv.get("value", "")}</span>
                        </div>""",
                        unsafe_allow_html=True,
                    )
                    if inv.get("source"):
                        st.caption(f'Source: "{inv["source"]}"')
        else:
            st.caption("None extracted")

        st.markdown("---")

        # Identity Features
        st.markdown("##### Identity Features (What Makes This Unique)")
        st.caption("Distinctive elements that should not be replaced with generic patterns")
        if identity:
            for feat in identity:
                st.markdown(
                    f"""<div style="background: #E3F2FD; padding: 8px 12px; border-radius: 6px;
                               margin: 4px 0; border-left: 3px solid #2196F3;">
                        <span style="color: #1565C0; font-weight: 500;">{feat.get("feature", "")}</span>
                    </div>""",
                    unsafe_allow_html=True,
                )
                if feat.get("why_distinctive"):
                    st.caption(f"Risk: {feat['why_distinctive']}")
        else:
            st.caption("None extracted")

        # Concept Health Signals
        concept_health = anchor.get("concept_health")
        if concept_health and any(
            concept_health.get(k)
            for k in ("pain_clarity", "trigger_strength", "willingness_to_pay")
        ):
            st.markdown("---")
            st.markdown("##### Concept Health Signals")
            st.caption("Honest assessment of idea strength — surfaces weaknesses early")
            _render_health_signals(concept_health)

        # Confirm clarifications button if there are ambiguities
        if has_unresolved:
            st.markdown("---")
            if st.button("Confirm Clarifications", type="primary", use_container_width=True):
                # Update invariants with clarified values
                updated = False
                for idx, inv in enumerate(invariants):
                    clarified = st.session_state.get(f"anchor_clarification_{idx}")
                    if clarified and inv.get("confidence", 1.0) < 0.7:
                        inv["value"] = clarified
                        inv["confidence"] = 1.0  # Now it's confirmed
                        inv["ambiguity"] = None
                        inv["clarification_options"] = None
                        inv["user_clarified"] = True
                        updated = True

                if updated:
                    if save_anchor(session_dir, anchor_data):
                        st.success("Clarifications saved! Constraints updated.")
                        st.rerun()
                else:
                    st.warning("Please select an option for each ambiguous constraint.")

    return has_unresolved
