"""Decision Gate Card - Shown at the end of each phase before proceeding.

Full-width card with purple border showing phase accomplishments and next-phase preview.
"""

import json
from pathlib import Path

import streamlit as st
from lib.session_utils import get_session_dir


def load_verification_result(phase: str, session_dir: Path | None = None) -> dict | None:
    """Load verification result from session directory.

    Args:
        phase: Phase name (e.g., "WHAT")
        session_dir: Session directory path

    Returns:
        Dict with verification data or None if not found
    """
    if session_dir is None:
        session_dir = get_session_dir()

    filepath = session_dir / f"verification_{phase.lower()}.json"
    if filepath.exists():
        try:
            return json.loads(filepath.read_text())
        except Exception:
            return None
    return None


def _get_confidence_label(confidence: int) -> tuple[str, str]:
    """Get human-readable confidence label and description."""
    if confidence >= 90:
        return "High", "Strong alignment with original concept"
    elif confidence >= 70:
        return "Good", "Most distinctive features preserved"
    elif confidence >= 50:
        return "Moderate", "Some drift detected - review recommended"
    elif confidence >= 30:
        return "Low", "Significant drift from original concept"
    else:
        return "Very Low", "Major concerns - manual review required"


def _humanize_invariant(name: str) -> str:
    """Convert technical invariant names to human-readable labels."""
    mappings = {
        "target_audience": "Target Audience",
        "session_structure": "Session Structure",
        "interaction_model": "Interaction Model",
        "group_structure": "Group Structure",
        "community_model": "Community Model",
        "orchestrator_role": "Orchestrator Role",
        "patient_base": "Patient Base",
        "timing_constraint": "Timing Constraint",
    }
    return mappings.get(name, name.replace("_", " ").title())


def render_verification_summary(verification: dict, anchor: dict | None = None) -> None:
    """Render verification summary in the UI.

    Args:
        verification: Verification result dict
        anchor: Optional anchor dict for showing source context
    """
    confidence = verification.get("confidence_score", 0)
    rationale = verification.get("confidence_rationale", "")
    passed = verification.get("passed", True)

    # Get counts for summary
    invariants_honored = verification.get("invariants_honored", [])
    invariants_violated = verification.get("invariants_violated", [])
    identity_preserved = verification.get("identity_preserved", [])
    identity_genericized = verification.get("identity_genericized", [])
    warnings = verification.get("warnings", [])

    total_invariants = len(invariants_honored) + len(invariants_violated)
    total_identity = len(identity_preserved) + len(identity_genericized)

    # Color based on confidence
    if confidence >= 80:
        conf_color = "#4CAF50"  # Green
        conf_bg = "#E8F5E9"
    elif confidence >= 50:
        conf_color = "#FF9800"  # Orange
        conf_bg = "#FFF3E0"
    else:
        conf_color = "#F44336"  # Red
        conf_bg = "#FFEBEE"

    status_text = "PASSED" if passed else "ISSUES FOUND"
    status_color = "#4CAF50" if passed else "#F44336"

    # Get confidence interpretation
    conf_label, conf_desc = _get_confidence_label(confidence)

    # Build summary badges
    inv_badge_color = "#4CAF50" if not invariants_violated else "#F44336"
    id_badge_color = "#4CAF50" if not identity_genericized else "#FF9800"

    # Render main card with summary badges inline
    st.markdown(
        f"""
<div style="background: {conf_bg}; padding: 16px 20px; border-radius: 10px; margin: 12px 0;
            border-left: 4px solid {conf_color};">
    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
        <div>
            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                <span style="font-size: 13px; font-weight: 600; color: #666; text-transform: uppercase;">
                    Concept Fidelity Check
                </span>
                <span style="font-size: 11px; background: {status_color}; color: white;
                            padding: 2px 8px; border-radius: 4px;">
                    {status_text}
                </span>
            </div>
            <div style="display: flex; gap: 12px; margin-top: 10px; flex-wrap: wrap;">
                <span style="font-size: 12px; background: rgba(76,175,80,0.15); color: {inv_badge_color};
                            padding: 4px 10px; border-radius: 12px; font-weight: 500;">
                    {len(invariants_honored)}/{total_invariants} Invariants
                </span>
                <span style="font-size: 12px; background: rgba(76,175,80,0.15); color: {id_badge_color};
                            padding: 4px 10px; border-radius: 12px; font-weight: 500;">
                    {len(identity_preserved)}/{total_identity} Identity
                </span>
            </div>
        </div>
        <div style="text-align: right;">
            <div style="font-size: 28px; font-weight: 700; color: {conf_color};">
                {confidence}%
            </div>
            <div style="font-size: 11px; color: #666; font-weight: 500;">{conf_label} Confidence</div>
        </div>
    </div>
</div>
""",
        unsafe_allow_html=True,
    )

    # Show details in expander with improved layout
    has_issues = bool(invariants_violated or identity_genericized or warnings)

    with st.expander(
        "What was verified?" if not has_issues else "Review verification details",
        expanded=has_issues,
    ):
        # Invariants section
        if invariants_honored or invariants_violated:
            st.markdown("##### 🔒 Invariants (Must-Preserve Constraints)")
            st.caption(
                "These are explicit requirements from the original idea that must be honored."
            )

            for inv in invariants_honored:
                inv_label = _humanize_invariant(inv) if isinstance(inv, str) else inv
                st.markdown(
                    f"""<div style="background: #E8F5E9; padding: 8px 12px; border-radius: 6px;
                               margin: 4px 0; border-left: 3px solid #4CAF50;">
                        <span style="color: #2E7D32; font-weight: 500;">✓ {inv_label}</span>
                    </div>""",
                    unsafe_allow_html=True,
                )

            for v in invariants_violated:
                severity = v.get("severity", "warning")
                border_color = "#F44336" if severity == "blocking" else "#FF9800"
                icon = "✗" if severity == "blocking" else "⚠"
                inv_name = _humanize_invariant(v.get("invariant_name", "Unknown"))
                desc = v.get("violation_description", "")[:150]
                st.markdown(
                    f"""<div style="background: #FFEBEE; padding: 10px 12px; border-radius: 6px;
                               margin: 4px 0; border-left: 3px solid {border_color};">
                        <div style="color: {border_color}; font-weight: 500;">{icon} {inv_name}</div>
                        <div style="font-size: 12px; color: #666; margin-top: 4px;">{desc}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )

        # Identity section
        if identity_preserved or identity_genericized:
            st.markdown("##### 🎯 Identity Features (What Makes This Unique)")
            st.caption("Distinctive elements that differentiate this from generic solutions.")

            for feat in identity_preserved:
                st.markdown(
                    f"""<div style="background: #E3F2FD; padding: 8px 12px; border-radius: 6px;
                               margin: 4px 0; border-left: 3px solid #2196F3;">
                        <span style="color: #1565C0; font-weight: 500;">✓ {feat}</span>
                    </div>""",
                    unsafe_allow_html=True,
                )

            for g in identity_genericized:
                original = g.get("original_feature", "")
                replacement = g.get("generic_replacement", "")
                st.markdown(
                    f"""<div style="background: #FFF3E0; padding: 10px 12px; border-radius: 6px;
                               margin: 4px 0; border-left: 3px solid #FF9800;">
                        <div style="color: #E65100; font-weight: 500;">⚠ Genericization Detected</div>
                        <div style="font-size: 12px; color: #666; margin-top: 4px;">
                            <strong>{original}</strong> → {replacement}
                        </div>
                    </div>""",
                    unsafe_allow_html=True,
                )

        # Warnings
        if warnings:
            st.markdown("##### ⚠️ Warnings")
            for w in warnings[:5]:
                st.warning(w)

        # Notes/rationale at the bottom
        if rationale:
            st.markdown("---")
            st.caption(f"**Verifier notes:** {rationale}")


def render_decision_gate(
    phase_name: str,
    accomplishments: list[str],
    next_phase_name: str | None = None,
    next_phase_preview: str | None = None,
    next_phase_details: list[str] | None = None,
    on_continue: str | None = None,
    is_locked: bool = False,
    coming_soon: bool = False,
    verification_phase: str | None = None,
) -> str | None:
    """Render a decision gate card between phases.

    Args:
        phase_name: Name of the completed phase (e.g., "Idea Validation")
        accomplishments: List of accomplishments from this phase
        next_phase_name: Name of the next phase
        next_phase_preview: Description of what the next phase does
        next_phase_details: Optional bullet points about what the next phase covers
        on_continue: Label for the continue button
        is_locked: Whether the phase has been accepted/locked
        coming_soon: If True, shows "Coming Soon" instead of continue button
        verification_phase: Phase name to load verification results for (e.g., "WHAT")

    Returns:
        Button key that was clicked, or None
    """
    # Accomplishments list
    acc_html = ""
    for acc in accomplishments:
        acc_html += (
            '<div style="display: flex; align-items: center; gap: 10px; '
            'margin-bottom: 6px; padding: 4px 0;">'
            '<span style="color: #4CAF50; font-size: 16px; flex-shrink: 0;">&#10003;</span>'
            f'<span style="font-size: 14px; color: #444;">{acc}</span>'
            "</div>"
        )

    # Next phase preview
    next_html = ""
    if next_phase_name:
        details_html = ""
        if next_phase_details:
            items = "".join(
                f'<li style="margin-bottom: 4px; color: #555; font-size: 13px;">{d}</li>'
                for d in next_phase_details
            )
            details_html = f'<ul style="margin: 8px 0 0 0; padding-left: 18px;">{items}</ul>'

        preview_text = ""
        if next_phase_preview:
            preview_text = (
                f'<div style="font-size: 13px; color: #666; margin-top: 4px;">'
                f"{next_phase_preview}</div>"
            )

        next_html = (
            '<div style="margin-top: 16px; padding: 12px 16px; '
            "background: #F8F5FB; border-radius: 6px; "
            'border-left: 3px solid #8B5FAF;">'
            '<div style="font-size: 12px; font-weight: 600; color: #6B2D8B; '
            'text-transform: uppercase; letter-spacing: 0.5px;">'
            f"Up Next: {next_phase_name}</div>"
            f"{preview_text}"
            f"{details_html}"
            "</div>"
        )

    status_badge = ""
    if is_locked:
        status_badge = (
            '<span style="font-size: 11px; background: #E8F5E9; color: #4CAF50; '
            "padding: 3px 10px; border-radius: 4px; font-weight: 600; "
            'letter-spacing: 0.5px;">ACCEPTED</span>'
        )

    card_html = (
        '<div style="border: 2px solid #E8DCF5; border-radius: 10px; '
        'padding: 20px 24px; margin: 16px 0; background: white;">'
        '<div style="display: flex; align-items: center; justify-content: space-between; '
        'margin-bottom: 16px;">'
        f'<span style="font-size: 15px; font-weight: 600; color: #6B2D8B;">'
        f"{phase_name} Complete</span>"
        f"{status_badge}"
        "</div>"
        f"{acc_html}"
        "</div>"
    )
    st.markdown(card_html, unsafe_allow_html=True)

    # Show verification results if available
    if verification_phase:
        verification = load_verification_result(verification_phase)
        if verification:
            render_verification_summary(verification)

    # Next phase preview (rendered separately to allow verification in between)
    if next_html:
        st.markdown(next_html, unsafe_allow_html=True)

    # Action buttons
    if coming_soon:
        st.info("Implementation (BUILD) and Validation (VALIDATE) phases are coming soon.")
        return None

    if is_locked and next_phase_name and on_continue:
        if st.button(on_continue, type="primary", use_container_width=True):
            return "continue"
    return None
