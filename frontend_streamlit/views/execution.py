"""Execution View - Run workflows with live progress."""

from lib.session_utils import get_session_dir, get_system_goal, load_environment, setup_paths

setup_paths()
load_environment()

import json  # noqa: E402

import streamlit as st  # noqa: E402

SESSION_DIR = get_session_dir()

# Center the Streamlit "running" indicator while workflows execute
# (inspired by streamlit-extras customize_running)
st.markdown(
    """<style>
    div[class*="StatusWidget"] {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%) scale(3);
        width: 50%;
    }
    div[class*="StatusWidget"] button {
        display: none;
    }
    </style>""",
    unsafe_allow_html=True,
)

# =============================================================================
# Workflow Trigger Check
# =============================================================================
# Check which workflow to run
new_idea = st.session_state.get("new_idea")
run_mvp = st.session_state.get("run_mvp_workflow")
run_build_buy = st.session_state.get("run_build_buy_workflow")
run_architecture = st.session_state.get("run_architecture_workflow")
run_story = st.session_state.get("run_story_workflow")

# Check for unrelated redirect state first (before other checks)
unrelated_redirect = st.session_state.get("unrelated_redirect")

if (
    not new_idea
    and not run_mvp
    and not run_build_buy
    and not run_architecture
    and not run_story
    and not unrelated_redirect
):
    st.warning("No workflow to run.")
    if st.button("Go to Project", type="primary"):
        st.switch_page("views/dashboard.py")
    st.stop()

# =============================================================================
# Handle UNRELATED redirect page (must be before new_idea check)
# =============================================================================

if unrelated_redirect:
    # Custom CSS for the cards
    st.markdown(
        """
        <style>
        .idea-card {
            background: white;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            border: 1px solid #eee;
        }
        .idea-card:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.12);
            border-color: #ddd;
        }
        .idea-title {
            font-size: 16px;
            font-weight: 600;
            color: #2D1B59;
            margin-bottom: 4px;
        }
        .idea-desc {
            font-size: 14px;
            color: #666;
            line-height: 1.4;
        }
        .user-input-bubble {
            background: #f0f0f5;
            border-radius: 12px;
            padding: 12px 16px;
            margin-bottom: 20px;
            color: #555;
            font-style: italic;
        }
        .friendly-message {
            font-size: 18px;
            color: #333;
            margin-bottom: 24px;
            line-height: 1.5;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Show what they entered
    st.markdown(
        f'<div class="user-input-bubble">"{unrelated_redirect["original_input"]}"</div>',
        unsafe_allow_html=True,
    )

    # Friendly message
    st.markdown(
        f'<div class="friendly-message">{unrelated_redirect["message"]}</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    # Suggested ideas section
    st.markdown("### Try one of these ideas")

    suggested_ideas = unrelated_redirect.get("suggested_ideas", [])
    if suggested_ideas:
        for i, idea in enumerate(suggested_ideas):
            # Handle both dict and SuggestedIdea objects
            if isinstance(idea, dict):
                title = idea.get("title", "Startup Idea")
                description = idea.get("description", "")
                icon = idea.get("icon", "💡")
            else:
                title = idea.title
                description = idea.description
                icon = idea.icon

            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(
                    f"""
                    <div class="idea-card">
                        <div class="idea-title">{icon} {title}</div>
                        <div class="idea-desc">{description}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with col2:
                if st.button("Use →", key=f"use_idea_{i}", use_container_width=True):
                    # Use this idea
                    st.session_state.new_idea = description
                    del st.session_state.unrelated_redirect
                    st.rerun()

    st.divider()

    # Custom idea input
    st.markdown("### Or describe your own idea")

    with st.form("custom_idea_form", clear_on_submit=True):
        custom_idea = st.text_area(
            "Your startup idea",
            placeholder="Describe a product or service you'd like to build...",
            height=100,
            label_visibility="collapsed",
        )

        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button(
                "Validate This Idea →",
                type="primary",
                use_container_width=True,
            )
        with col2:
            go_back = st.form_submit_button(
                "Start Over",
                use_container_width=True,
            )

        if submit and custom_idea.strip():
            st.session_state.new_idea = custom_idea.strip()
            del st.session_state.unrelated_redirect
            st.rerun()
        elif submit:
            st.warning("Please enter an idea first.")

        if go_back:
            del st.session_state.unrelated_redirect
            if "new_idea" in st.session_state:
                del st.session_state.new_idea
            st.rerun()

    st.stop()

# =============================================================================
# Idea Validation Workflow
# =============================================================================

if new_idea:
    from lib.idea_validator import (
        discover_idea_gaps,
        enrich_idea_with_discovery,
        polish_idea,
        refine_idea_with_answers,
        validate_idea,
    )

    # Check if we're in clarification mode
    clarification_state = st.session_state.get("idea_clarification")

    # Check if we're in polish confirmation mode
    polish_state = st.session_state.get("idea_polish")

    # If not already validated, run validation first
    if not st.session_state.get("idea_validated") and not polish_state:
        st.title("Checking Your Input")
        st.info(f"*{new_idea}*")

        with st.spinner("Analyzing your input..."):
            validation_result = validate_idea(new_idea)

        # Handle based on classification
        if validation_result.classification == "VALID_IDEA":
            # Valid idea - now polish it for clarity
            with st.spinner("Polishing for clarity..."):
                polish_result = polish_idea(new_idea)

            # Store polish state for confirmation
            st.session_state.idea_polish = {
                "original": new_idea,
                "polished": polish_result.polished_idea,
                "changes": polish_result.changes_made,
                "success": polish_result.success,
            }
            st.rerun()

        elif validation_result.classification == "NEEDS_CLARIFICATION":
            # Store state and show clarification form
            st.session_state.idea_clarification = {
                "original_input": new_idea,
                "partial_understanding": validation_result.partial_understanding,
                "questions": validation_result.questions or [],
                "message": validation_result.message,
            }
            st.rerun()

        else:  # UNRELATED
            # Store state for the redirect page
            st.session_state.unrelated_redirect = {
                "original_input": new_idea,
                "message": validation_result.message,
                "suggested_ideas": validation_result.suggested_ideas or [],
            }
            # Clear new_idea to prevent re-validation loop
            del st.session_state.new_idea
            st.rerun()

    # Handle clarification form if in clarification mode
    if clarification_state and not st.session_state.get("idea_validated"):
        st.title("Tell Me More")
        st.markdown(clarification_state["message"])

        if clarification_state.get("partial_understanding"):
            st.info(f"*I understand you want: {clarification_state['partial_understanding']}*")

        st.divider()

        # Show questions with text inputs
        with st.form("clarification_form"):
            answers = []
            for i, question in enumerate(clarification_state["questions"]):
                answer = st.text_input(
                    question,
                    key=f"clarification_q{i}",
                    placeholder="Your answer...",
                )
                answers.append(answer)

            col1, col2 = st.columns(2)
            with col1:
                submit = st.form_submit_button("Continue", type="primary", use_container_width=True)
            with col2:
                start_over = st.form_submit_button("Start Over", use_container_width=True)

            if submit:
                # Check if at least one answer was provided
                if any(a.strip() for a in answers):
                    # Combine original input with answers
                    refined_idea = refine_idea_with_answers(
                        original_input=clarification_state["original_input"],
                        partial_understanding=clarification_state.get("partial_understanding"),
                        questions=clarification_state["questions"],
                        answers=answers,
                    )
                    # Re-validate the refined idea
                    st.session_state.new_idea = refined_idea
                    del st.session_state.idea_clarification
                    st.rerun()
                else:
                    st.warning("Please provide at least one answer to continue.")

            if start_over:
                # Clear state and go back to new project
                if "new_idea" in st.session_state:
                    del st.session_state.new_idea
                if "idea_clarification" in st.session_state:
                    del st.session_state.idea_clarification
                st.rerun()

        st.stop()

    # Handle polish confirmation if in polish mode
    if polish_state and not st.session_state.get("idea_validated"):
        # Show original vs polished
        original = polish_state["original"]
        polished = polish_state["polished"]
        changes = polish_state.get("changes", [])

        # Check if there were actual changes
        ideas_differ = original.strip() != polished.strip()
        no_changes_needed = not ideas_differ or (
            len(changes) == 1 and "no change" in changes[0].lower()
        )

        # If no changes were made, skip confirmation and proceed directly
        if no_changes_needed:
            st.session_state.idea_validated = True
            st.session_state.validated_idea = original
            del st.session_state.idea_polish
            st.rerun()

        st.title("Confirm Your Idea")

        if ideas_differ:
            st.markdown("We've polished your idea for clarity. Please review and confirm:")

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Your original:**")
                st.text_area(
                    "Original",
                    value=original,
                    height=120,
                    disabled=True,
                    label_visibility="collapsed",
                )
            with col2:
                st.markdown("**Polished version:**")
                edited_idea = st.text_area(
                    "Polished (you can edit)",
                    value=polished,
                    height=120,
                    key="polished_idea_edit",
                    label_visibility="collapsed",
                )

            # Show what changed
            if changes and changes != ["No changes needed - original is clear"]:
                with st.expander("What changed?", expanded=False):
                    for change in changes:
                        st.markdown(f"- {change}")
        else:
            st.markdown("Your idea looks clear! Ready to proceed.")
            st.info(f"*{polished}*")
            edited_idea = polished

        st.divider()

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("✓ Use Polished Version", type="primary", use_container_width=True):
                st.session_state.idea_validated = True
                st.session_state.validated_idea = edited_idea.strip() if ideas_differ else polished
                # Store diff for display
                if ideas_differ:
                    st.session_state.idea_diff = {
                        "original": original,
                        "refined": edited_idea.strip(),
                    }
                del st.session_state.idea_polish
                st.rerun()
        with col2:
            if ideas_differ:
                if st.button("Use Original", use_container_width=True):
                    st.session_state.idea_validated = True
                    st.session_state.validated_idea = original
                    del st.session_state.idea_polish
                    st.rerun()
        with col3:
            if st.button("Start Over", use_container_width=True):
                # Clear all state and go back
                for key in ["new_idea", "idea_polish", "idea_validated", "validated_idea"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()

        st.stop()

    # =========================================================================
    # Idea Discovery Step (Lean Canvas gap analysis)
    # =========================================================================
    # Runs after validation+polish, before workflow start.
    # Identifies which Lean Canvas dimensions are ambiguous/missing and asks
    # targeted clarifying questions. Skips automatically if idea is comprehensive.

    if st.session_state.get("idea_validated") and not st.session_state.get(
        "idea_discovery_complete"
    ):
        validated_idea = st.session_state.get("validated_idea", new_idea)
        discovery_state = st.session_state.get("idea_discovery")

        # Run discovery agent if not already done
        if discovery_state is None:
            st.title("Understanding Your Idea")
            st.info(f"*{validated_idea}*")

            with st.spinner("Analyzing idea dimensions..."):
                discovery_result = discover_idea_gaps(validated_idea)

            # Auto-skip if agent failed or no gaps found
            if discovery_result is None:
                st.session_state.idea_discovery_complete = True
                st.rerun()

            has_gaps = any(
                a.coverage in ("partial", "missing") for a in discovery_result.assessments
            )
            if not has_gaps or len(discovery_result.questions) == 0:
                st.session_state.idea_discovery_complete = True
                st.rerun()

            # Store discovery state for question form
            st.session_state.idea_discovery = {
                "result": discovery_result,
                "idea": validated_idea,
            }
            st.rerun()

        # Show question form
        if discovery_state is not None:
            discovery_result = discovery_state["result"]

            st.title("A Few Quick Questions")
            st.markdown("Before we start, a few questions to make sure we build the right thing.")

            with st.expander("What we already understand", expanded=False):
                st.markdown(discovery_result.understood_context)
                for assessment in discovery_result.assessments:
                    if assessment.coverage == "clear":
                        st.markdown(f"- **{assessment.dimension}**: {assessment.evidence}")

            st.divider()

            with st.form("discovery_form"):
                answers = {}
                for i, question in enumerate(discovery_result.questions):
                    answer = st.text_input(
                        question.question,
                        key=f"discovery_q{i}",
                        value=question.placeholder,
                    )
                    answers[question.dimension] = answer

                col1, col2, col3 = st.columns(3)
                with col1:
                    submit = st.form_submit_button(
                        "Continue", type="primary", use_container_width=True
                    )
                with col2:
                    skip = st.form_submit_button("Skip", use_container_width=True)
                with col3:
                    start_over = st.form_submit_button("Start Over", use_container_width=True)

                if submit:
                    # Check if any answers were provided
                    if any(a.strip() for a in answers.values()):
                        enriched = enrich_idea_with_discovery(
                            discovery_state["idea"], discovery_result, answers
                        )
                        st.session_state.validated_idea = enriched
                        st.session_state.idea_diff = {
                            "original": discovery_state["idea"],
                            "refined": enriched,
                        }
                    # Even with no answers, mark complete
                    st.session_state.idea_discovery_complete = True
                    if "idea_discovery" in st.session_state:
                        del st.session_state.idea_discovery
                    st.rerun()

                if skip:
                    st.session_state.idea_discovery_complete = True
                    if "idea_discovery" in st.session_state:
                        del st.session_state.idea_discovery
                    st.rerun()

                if start_over:
                    for key in [
                        "new_idea",
                        "idea_validated",
                        "validated_idea",
                        "idea_discovery",
                        "idea_discovery_complete",
                        "idea_polish",
                        "idea_clarification",
                    ]:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()

            st.stop()

    # =========================================================================
    # Archetype Selection Step
    # =========================================================================
    # After idea discovery, let the user pick the product archetype so
    # downstream agents can calibrate their analysis.

    idea_discovery_complete = st.session_state.get("idea_discovery_complete")
    archetype_selected = st.session_state.get("archetype_selected")

    if idea_discovery_complete and not archetype_selected:
        st.title("What type of product is this?")
        st.markdown("This helps us calibrate the analysis to your product type.")

        archetype_options = [
            "Auto-detect (let the AI classify)",
            "Consumer App",
            "B2B SaaS",
            "Marketplace",
            "Developer Tool",
            "Internal Tool",
        ]
        archetype_values = [
            None,
            "consumer_app",
            "b2b_saas",
            "marketplace",
            "developer_tool",
            "internal_tool",
        ]

        selection = st.selectbox(
            "Product type",
            options=range(len(archetype_options)),
            format_func=lambda i: archetype_options[i],
        )

        if st.button("Continue", type="primary", use_container_width=True):
            st.session_state.idea_archetype = archetype_values[selection]
            st.session_state.archetype_selected = True
            st.rerun()

        st.stop()

    # At this point, idea is validated - proceed with workflow
    validated_idea = st.session_state.get("validated_idea", new_idea)

    st.title("Validating Your Idea")

    # Show idea diff if coming from refinement
    if st.session_state.get("idea_diff"):
        diff = st.session_state.idea_diff
        st.markdown("### Idea Refinement Summary")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Original:**")
            original_text = diff["original"] or ""
            display_original = (
                original_text[:500] + "..." if len(original_text) > 500 else original_text
            )
            st.info(display_original)
        with col2:
            st.markdown("**Refined:**")
            refined_text = diff["refined"] or ""
            display_refined = (
                refined_text[:500] + "..." if len(refined_text) > 500 else refined_text
            )
            st.success(display_refined)
        del st.session_state.idea_diff
        st.divider()

    st.info(f"*{validated_idea}*")

    STAGES = [
        ("idea-analysis", "Idea Analysis", "Expanding and structuring your concept"),
        ("market-context", "Market Context", "Researching market and competitors"),
        ("risk-assessment", "Risk Assessment", "Analyzing viability and risks"),
        ("validation-summary", "Validation Summary", "Generating GO/NO-GO recommendation"),
    ]

    progress_bar = st.progress(0, text="Preparing workflow...")
    st.divider()

    stage_container = st.container()
    stage_placeholders = {}
    with stage_container:
        for slug, name, desc in STAGES:
            stage_placeholders[slug] = st.empty()
            stage_placeholders[slug].markdown(f"Pending: **{name}** - {desc}")

    st.divider()
    status_placeholder = st.empty()

    from lib.workflow_runner import StageProgress, run_idea_validation

    def on_stage_start(progress: StageProgress):
        pct = (progress.current_stage - 1) / progress.total_stages
        progress_bar.progress(pct, text=f"Running {progress.display_name}...")
        if progress.stage_slug in stage_placeholders:
            stage_placeholders[progress.stage_slug].markdown(
                f"Running: **{progress.display_name}**..."
            )

    def on_stage_complete(progress: StageProgress):
        pct = progress.current_stage / progress.total_stages
        progress_bar.progress(pct, text=f"Completed {progress.display_name}")
        if progress.stage_slug in stage_placeholders:
            if progress.status == "completed":
                stage_placeholders[progress.stage_slug].markdown(
                    f"Complete: **{progress.display_name}**"
                )
            else:
                stage_placeholders[progress.stage_slug].markdown(
                    f"Failed: **{progress.display_name}**"
                )

    status_placeholder.info("Starting Idea Validation workflow...")

    result = run_idea_validation(
        system_goal=validated_idea,
        session_dir=SESSION_DIR,
        on_stage_start=on_stage_start,
        on_stage_complete=on_stage_complete,
        clear_existing=True,
        archetype=st.session_state.get("idea_archetype"),
    )

    # Clean up validation state
    for key in [
        "new_idea",
        "idea_validated",
        "validated_idea",
        "idea_clarification",
        "idea_discovery",
        "idea_discovery_complete",
        "archetype_selected",
        "idea_archetype",
    ]:
        if key in st.session_state:
            del st.session_state[key]

    if result.status == "completed":
        progress_bar.progress(1.0, text="Complete!")
        status_placeholder.empty()

        # Read AI-detected archetype from concept anchor (if auto-detect was used)
        archetype_line = ""
        try:
            anchor_file = SESSION_DIR / "concept_anchor.json"
            if anchor_file.exists():
                anchor_data = json.loads(anchor_file.read_text())
                detected = anchor_data.get("anchor", {}).get("archetype")
                if detected:
                    from haytham.workflow.anchor_schema import IdeaArchetype

                    display = IdeaArchetype(detected).display_name
                    archetype_line = f"\n**Product type:** {display}"
        except Exception:
            pass  # Non-critical — skip if anchor not available

        st.success(f"""
## Idea Validation Complete

**Execution time:** {result.execution_time:.1f} seconds
**Recommendation:** {result.recommendation or "See results for details"}{archetype_line}
        """)

        st.info("Redirecting to review results...")

        # Rerun to navigate to results view (Idea Analysis page)
        st.session_state.navigate_to = "discovery"
        st.rerun()
    else:
        progress_bar.progress(1.0, text="Failed")
        status_placeholder.empty()

        # Build error message with stage info if available
        error_header = "## Workflow Failed"
        if hasattr(result, "failed_stage") and result.failed_stage:
            error_header = f"## Workflow Failed at {result.failed_stage}"

        error_msg = result.error or "Unknown error"

        # Check for token limit error and provide helpful guidance
        is_token_error = "token" in error_msg.lower() or "too long" in error_msg.lower()

        st.error(f"""
{error_header}

**Error:** {error_msg}
        """)

        if is_token_error:
            st.warning("""
**Tip:** This error usually means your idea description is too detailed for the model to process.
Try shortening your idea to 2-3 sentences focusing on the core concept.
            """)

        st.info("""
**What now?** Click "Try Again" to resume from where you left off.
Completed stages will be skipped automatically.
        """)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Try Again", type="primary", use_container_width=True):
                st.session_state.new_idea = new_idea
                st.rerun()
        with col2:
            if st.button("Back to Project", use_container_width=True):
                st.rerun()  # Rerun to let Haytham.py handle navigation

    st.stop()

# =============================================================================
# MVP Specification Workflow
# =============================================================================

if run_mvp:
    # Check if this is an override attempt
    force_override = st.session_state.get("force_mvp_override", False)

    if "run_mvp_workflow" in st.session_state:
        del st.session_state.run_mvp_workflow
    if "force_mvp_override" in st.session_state:
        del st.session_state.force_mvp_override

    idea = get_system_goal()
    if not idea:
        st.error("No project found.")
        st.stop()

    st.title("Defining Your MVP")
    st.info(f"*{idea}*")

    STAGES = [
        ("mvp-scope", "MVP Scope", "Defining focused, achievable MVP scope"),
        ("capability-model", "Capability Model", "Extracting business capabilities"),
        ("system-traits", "System Traits", "Classifying system type for story generation"),
    ]

    progress_bar = st.progress(0, text="Preparing workflow...")
    st.divider()

    stage_container = st.container()
    stage_placeholders = {}
    with stage_container:
        for slug, name, desc in STAGES:
            stage_placeholders[slug] = st.empty()
            stage_placeholders[slug].markdown(f"Pending: **{name}** - {desc}")

    st.divider()
    status_placeholder = st.empty()

    from lib.workflow_runner import StageProgress, run_mvp_specification

    def on_stage_start(progress: StageProgress):
        pct = (progress.current_stage - 1) / progress.total_stages
        progress_bar.progress(pct, text=f"Running {progress.display_name}...")
        if progress.stage_slug in stage_placeholders:
            stage_placeholders[progress.stage_slug].markdown(
                f"Running: **{progress.display_name}**..."
            )

    def on_stage_complete(progress: StageProgress):
        pct = progress.current_stage / progress.total_stages
        progress_bar.progress(pct, text=f"Completed {progress.display_name}")
        if progress.stage_slug in stage_placeholders:
            if progress.status == "completed":
                stage_placeholders[progress.stage_slug].markdown(
                    f"Complete: **{progress.display_name}**"
                )
            else:
                stage_placeholders[progress.stage_slug].markdown(
                    f"Failed: **{progress.display_name}**"
                )

    status_placeholder.info("Starting MVP Specification workflow...")

    result = run_mvp_specification(
        session_dir=SESSION_DIR,
        on_stage_start=on_stage_start,
        on_stage_complete=on_stage_complete,
        force_override=force_override,
    )

    if result.status == "completed":
        progress_bar.progress(1.0, text="Complete!")
        status_placeholder.empty()

        st.success(f"""
## MVP Specification Complete

**Execution time:** {result.execution_time:.1f} seconds
        """)

        st.info("Redirecting to review results...")

        # Rerun to navigate to results view (MVP Specification page)
        st.session_state.navigate_to = "mvp_spec"
        st.rerun()
    else:
        progress_bar.progress(1.0, text="Failed")
        status_placeholder.empty()

        error_msg = result.error or "Unknown error"

        # Check if this is an overridable error (NO-GO recommendation)
        if "OVERRIDABLE:" in error_msg:
            st.warning("""
## Validation Returned NO-GO

The idea validation recommended against proceeding. However, you have options:
            """)

            st.markdown("""
**You can:**
- **Review the validation feedback** and refine your idea
- **Proceed anyway** if you believe the validation is too conservative
- **Start over** with a different idea
            """)

            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Review Feedback", type="secondary", use_container_width=True):
                    st.switch_page("views/discovery.py")
            with col2:
                if st.button("Proceed Anyway", type="primary", use_container_width=True):
                    st.session_state.run_mvp_workflow = True
                    st.session_state.force_mvp_override = True
                    st.rerun()
            with col3:
                if st.button("Start Over", use_container_width=True):
                    from lib.session_utils import clear_session

                    clear_session()
                    st.rerun()
        else:
            # Check for token limit error
            is_token_error = "token" in error_msg.lower() or "too long" in error_msg.lower()

            st.error(f"""
## Workflow Failed

**Error:** {error_msg}
            """)

            if is_token_error:
                st.warning("""
**Tip:** This error usually means the input is too large for the model to process.
Try simplifying or shortening the content from previous stages.
                """)

            st.info("Click **Try Again** to resume. Completed stages will be skipped.")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Try Again", type="primary", use_container_width=True):
                    st.session_state.run_mvp_workflow = True
                    st.rerun()
            with col2:
                if st.button("Back to Project", use_container_width=True):
                    st.rerun()  # Rerun to let Haytham.py handle navigation

    st.stop()

# =============================================================================
# Build vs Buy Analysis Workflow (Phase 3a: HOW)
# =============================================================================

if run_build_buy:
    if "run_build_buy_workflow" in st.session_state:
        del st.session_state.run_build_buy_workflow

    idea = get_system_goal()
    if not idea:
        st.error("No project found.")
        st.stop()

    st.title("Build vs Buy Analysis")
    st.caption("Phase 3a: HOW - Analyze build, buy, or hybrid approach for each capability")
    st.info(f"*{idea}*")

    STAGES = [
        ("build-buy-analysis", "Build vs Buy", "Analyzing build, buy, or hybrid approach"),
    ]

    progress_bar = st.progress(0, text="Preparing workflow...")
    st.divider()

    stage_container = st.container()
    stage_placeholders = {}
    with stage_container:
        for slug, name, desc in STAGES:
            stage_placeholders[slug] = st.empty()
            stage_placeholders[slug].markdown(f"Pending: **{name}** - {desc}")

    st.divider()
    status_placeholder = st.empty()

    from lib.workflow_runner import StageProgress, run_build_buy_analysis

    def on_stage_start(progress: StageProgress):
        pct = (progress.current_stage - 1) / progress.total_stages
        progress_bar.progress(pct, text=f"Running {progress.display_name}...")
        if progress.stage_slug in stage_placeholders:
            stage_placeholders[progress.stage_slug].markdown(
                f"Running: **{progress.display_name}**..."
            )

    def on_stage_complete(progress: StageProgress):
        pct = progress.current_stage / progress.total_stages
        progress_bar.progress(pct, text=f"Completed {progress.display_name}")
        if progress.stage_slug in stage_placeholders:
            if progress.status == "completed":
                stage_placeholders[progress.stage_slug].markdown(
                    f"Complete: **{progress.display_name}**"
                )
            else:
                stage_placeholders[progress.stage_slug].markdown(
                    f"Failed: **{progress.display_name}**"
                )

    status_placeholder.info("Starting Build vs Buy Analysis workflow...")

    result = run_build_buy_analysis(
        session_dir=SESSION_DIR,
        on_stage_start=on_stage_start,
        on_stage_complete=on_stage_complete,
    )

    if result.status == "completed":
        progress_bar.progress(1.0, text="Complete!")
        status_placeholder.empty()

        st.success(f"""
## Build vs Buy Analysis Complete

**Execution time:** {result.execution_time:.1f} seconds
        """)

        st.info("Redirecting to review results...")

        # Rerun to navigate to results view (Build vs Buy page)
        st.session_state.navigate_to = "build_buy"
        st.rerun()
    else:
        progress_bar.progress(1.0, text="Failed")
        status_placeholder.empty()

        error_msg = result.error or "Unknown error"
        is_token_error = "token" in error_msg.lower() or "too long" in error_msg.lower()

        st.error(f"""
## Workflow Failed

**Error:** {error_msg}
        """)

        if is_token_error:
            st.warning("**Tip:** Token limit exceeded. Try simplifying the capability model.")

        st.info("Click **Try Again** to resume. Completed stages will be skipped.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Try Again", type="primary", use_container_width=True):
                st.session_state.run_build_buy_workflow = True
                st.rerun()
        with col2:
            if st.button("Back to Project", use_container_width=True):
                st.rerun()  # Rerun to let Haytham.py handle navigation

    st.stop()

# =============================================================================
# Architecture Decisions Workflow (Phase 3b: HOW)
# =============================================================================

if run_architecture:
    if "run_architecture_workflow" in st.session_state:
        del st.session_state.run_architecture_workflow

    idea = get_system_goal()
    if not idea:
        st.error("No project found.")
        st.stop()

    st.title("Architecture Decisions")
    st.caption("Phase 3b: HOW - Define key technical architecture decisions")
    st.info(f"*{idea}*")

    STAGES = [
        ("architecture-decisions", "Architecture Decisions", "Defining key technical decisions"),
    ]

    progress_bar = st.progress(0, text="Preparing workflow...")
    st.divider()

    stage_container = st.container()
    stage_placeholders = {}
    with stage_container:
        for slug, name, desc in STAGES:
            stage_placeholders[slug] = st.empty()
            stage_placeholders[slug].markdown(f"Pending: **{name}** - {desc}")

    st.divider()
    status_placeholder = st.empty()

    from lib.workflow_runner import StageProgress, run_architecture_decisions

    def on_stage_start(progress: StageProgress):
        pct = (progress.current_stage - 1) / progress.total_stages
        progress_bar.progress(pct, text=f"Running {progress.display_name}...")
        if progress.stage_slug in stage_placeholders:
            stage_placeholders[progress.stage_slug].markdown(
                f"Running: **{progress.display_name}**..."
            )

    def on_stage_complete(progress: StageProgress):
        pct = progress.current_stage / progress.total_stages
        progress_bar.progress(pct, text=f"Completed {progress.display_name}")
        if progress.stage_slug in stage_placeholders:
            if progress.status == "completed":
                stage_placeholders[progress.stage_slug].markdown(
                    f"Complete: **{progress.display_name}**"
                )
            else:
                stage_placeholders[progress.stage_slug].markdown(
                    f"Failed: **{progress.display_name}**"
                )

    status_placeholder.info("Starting Architecture Decisions workflow...")

    result = run_architecture_decisions(
        session_dir=SESSION_DIR,
        on_stage_start=on_stage_start,
        on_stage_complete=on_stage_complete,
    )

    if result.status == "completed":
        progress_bar.progress(1.0, text="Complete!")
        status_placeholder.empty()

        st.success(f"""
## Architecture Decisions Complete

**Execution time:** {result.execution_time:.1f} seconds
        """)

        st.info("Redirecting to review results...")

        # Rerun to navigate to results view (Architecture page)
        st.session_state.navigate_to = "architecture"
        st.rerun()
    else:
        progress_bar.progress(1.0, text="Failed")
        status_placeholder.empty()

        error_msg = result.error or "Unknown error"
        is_token_error = "token" in error_msg.lower() or "too long" in error_msg.lower()

        st.error(f"""
## Workflow Failed

**Error:** {error_msg}
        """)

        if is_token_error:
            st.warning("**Tip:** Token limit exceeded. Try simplifying the build/buy analysis.")

        st.info("Click **Try Again** to resume. Completed stages will be skipped.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Try Again", type="primary", use_container_width=True):
                st.session_state.run_architecture_workflow = True
                st.rerun()
        with col2:
            if st.button("Back to Project", use_container_width=True):
                st.rerun()  # Rerun to let Haytham.py handle navigation

    st.stop()

# =============================================================================
# Story Generation Workflow (Phase 4: STORIES)
# =============================================================================

if run_story:
    if "run_story_workflow" in st.session_state:
        del st.session_state.run_story_workflow

    idea = get_system_goal()
    if not idea:
        st.error("No project found.")
        st.stop()

    st.title("Generating User Stories")
    st.caption("Phase 4: STORIES - Generate implementation tasks")
    st.info(f"*{idea}*")

    STAGES = [
        ("story-generation", "Story Generation", "Creating user stories from capabilities"),
        ("story-validation", "Story Validation", "Validating story quality"),
        ("dependency-ordering", "Dependency Ordering", "Ordering stories by dependencies"),
    ]

    progress_bar = st.progress(0, text="Preparing workflow...")
    st.divider()

    stage_container = st.container()
    stage_placeholders = {}
    with stage_container:
        for slug, name, desc in STAGES:
            stage_placeholders[slug] = st.empty()
            stage_placeholders[slug].markdown(f"Pending: **{name}** - {desc}")

    st.divider()
    status_placeholder = st.empty()

    from lib.workflow_runner import StageProgress, run_story_generation

    def on_stage_start(progress: StageProgress):
        pct = (progress.current_stage - 1) / progress.total_stages
        progress_bar.progress(pct, text=f"Running {progress.display_name}...")
        if progress.stage_slug in stage_placeholders:
            stage_placeholders[progress.stage_slug].markdown(
                f"Running: **{progress.display_name}**..."
            )

    def on_stage_complete(progress: StageProgress):
        pct = progress.current_stage / progress.total_stages
        progress_bar.progress(pct, text=f"Completed {progress.display_name}")
        if progress.stage_slug in stage_placeholders:
            if progress.status == "completed":
                stage_placeholders[progress.stage_slug].markdown(
                    f"Complete: **{progress.display_name}**"
                )
            else:
                stage_placeholders[progress.stage_slug].markdown(
                    f"Failed: **{progress.display_name}**"
                )

    status_placeholder.info("Starting Story Generation workflow...")

    result = run_story_generation(
        session_dir=SESSION_DIR,
        on_stage_start=on_stage_start,
        on_stage_complete=on_stage_complete,
    )

    if result.status == "completed":
        progress_bar.progress(1.0, text="Complete!")
        status_placeholder.empty()

        st.success(f"""
## Story Generation Complete

**Execution time:** {result.execution_time:.1f} seconds
**Result:** {result.recommendation or "Stories generated successfully"}
        """)

        st.info("Redirecting to review results...")

        # Rerun to navigate to results view (Stories page)
        st.session_state.navigate_to = "stories"
        st.rerun()
    else:
        progress_bar.progress(1.0, text="Failed")
        status_placeholder.empty()

        error_msg = result.error or "Unknown error"
        is_token_error = "token" in error_msg.lower() or "too long" in error_msg.lower()

        st.error(f"""
## Workflow Failed

**Error:** {error_msg}
        """)

        if is_token_error:
            st.warning(
                "**Tip:** Token limit exceeded. Story generation processes many capabilities - try reducing the capability model scope."
            )

        st.info("Click **Try Again** to resume. Completed stages will be skipped.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Try Again", type="primary", use_container_width=True):
                st.session_state.run_story_workflow = True
                st.rerun()
        with col2:
            if st.button("Back to Project", use_container_width=True):
                st.rerun()  # Rerun to let Haytham.py handle navigation
