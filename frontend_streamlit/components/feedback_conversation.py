"""Feedback Conversation Component - Chat-based feedback using intelligent agent.

This component provides an interactive chat interface powered by an AI agent
that can answer questions, discuss improvements, and make changes when requested.
"""

from pathlib import Path

import streamlit as st


def init_feedback_chat(workflow_type: str) -> None:
    """Initialize session state for feedback chat.

    Args:
        workflow_type: The workflow type (used as key prefix)
    """
    key = f"feedback_chat_{workflow_type}"
    if key not in st.session_state:
        st.session_state[key] = {
            "messages": [],
            "processing": False,
            "pending_input": None,
            "conversation": None,  # Will hold the FeedbackConversation instance
        }


def get_chat_state(workflow_type: str) -> dict:
    """Get the chat state for a workflow."""
    key = f"feedback_chat_{workflow_type}"
    return st.session_state.get(key, {"messages": [], "processing": False})


def add_message(workflow_type: str, role: str, content: str) -> None:
    """Add a message to the conversation history."""
    key = f"feedback_chat_{workflow_type}"
    if key not in st.session_state:
        init_feedback_chat(workflow_type)

    st.session_state[key]["messages"].append({"role": role, "content": content})


def render_chat_messages(workflow_type: str) -> None:
    """Render the conversation history as chat messages."""
    state = get_chat_state(workflow_type)
    messages = state.get("messages", [])

    if not messages:
        # Compact welcome: assistant message + collapsed tips
        with st.chat_message("assistant"):
            st.markdown("How can I help you refine these results?")
            with st.expander("View tips for refining"):
                st.markdown(
                    '- **Ask questions** — "Why is the risk level high?"\n'
                    '- **Discuss ideas** — "Help me think about pivoting"\n'
                    '- **Request changes** — "Add competitor X to the analysis"'
                )
        return

    # Render messages
    for msg in messages:
        role = msg["role"]
        content = msg["content"]

        if role == "user":
            # User message - right aligned with avatar
            with st.chat_message("user"):
                st.markdown(content)
        else:
            # Assistant message - left aligned with avatar
            with st.chat_message("assistant"):
                st.markdown(content)


def get_or_create_conversation(
    workflow_type: str,
    session_dir: Path,
    workflow_stages: list[str],
    system_goal: str,
):
    """Get or create the FeedbackConversation instance."""
    from haytham.feedback.feedback_agent import (
        FeedbackAgentContext,
        FeedbackConversation,
    )

    key = f"feedback_chat_{workflow_type}"
    state = st.session_state.get(key, {})

    if state.get("conversation") is None:
        # Create new conversation with context
        context = FeedbackAgentContext(
            session_dir=session_dir,
            workflow_type=workflow_type,
            workflow_stages=workflow_stages,
            system_goal=system_goal,
        )
        conversation = FeedbackConversation(context=context)
        st.session_state[key]["conversation"] = conversation

    return st.session_state[key]["conversation"]


def render_feedback_conversation(
    workflow_type: str,
    workflow_display_name: str,
    on_accept: callable,
    stage_slugs: list[str],
    system_goal: str,
    session_dir: Path | None = None,
    next_stage_name: str | None = None,
    download_data: tuple[bytes, str, str] | None = None,
) -> None:
    """Render the complete feedback conversation interface.

    Args:
        workflow_type: Workflow identifier (e.g., "idea-validation")
        workflow_display_name: Human-readable name (e.g., "Idea Validation")
        on_accept: Callback when user accepts and continues
        stage_slugs: List of stage slugs for this workflow
        system_goal: The original system goal/idea
        session_dir: Path to session directory (defaults to ../session)
        next_stage_name: Human-readable name of the next stage (shown on button)
        download_data: Optional (pdf_bytes, filename, mime_type) for a download button
    """
    # Resolve session directory
    if session_dir is None:
        session_dir = Path(__file__).parent.parent.parent / "session"

    # Initialize chat state
    init_feedback_chat(workflow_type)
    state = get_chat_state(workflow_type)

    st.markdown("#### Refine Your Results")
    st.markdown(f"Use the chat below to iterate on the **{workflow_display_name}** results.")

    # Chat container
    chat_container = st.container()

    with chat_container:
        render_chat_messages(workflow_type)

    # Process pending input if any
    if state.get("processing") and state.get("pending_input"):
        pending = state["pending_input"]
        st.session_state[f"feedback_chat_{workflow_type}"]["pending_input"] = None

        # Add user message to display
        add_message(workflow_type, "user", pending)

        # Show processing indicator
        with st.spinner("Thinking..."):
            try:
                # Get or create conversation
                conversation = get_or_create_conversation(
                    workflow_type=workflow_type,
                    session_dir=session_dir,
                    workflow_stages=stage_slugs,
                    system_goal=system_goal,
                )

                # Send message to agent
                response = conversation.send_message(pending)

                # Add assistant response
                add_message(workflow_type, "assistant", response)

            except Exception as e:
                error_msg = f"I encountered an issue: {e}. Could you try rephrasing your request?"
                add_message(workflow_type, "assistant", error_msg)

        st.session_state[f"feedback_chat_{workflow_type}"]["processing"] = False
        st.rerun()

    # Chat input - inline text input (not st.chat_input which is fixed at bottom)
    if state.get("processing"):
        st.info("Processing your message...")
    else:
        # Use a form so Enter key submits
        with st.form(key=f"chat_form_{workflow_type}", clear_on_submit=True):
            input_col, btn_col = st.columns([6, 1])
            with input_col:
                user_input = st.text_input(
                    "Chat",
                    placeholder="Ask a question or tell me what you'd like to change...",
                    key=f"chat_input_{workflow_type}",
                    label_visibility="collapsed",
                )
            with btn_col:
                submitted = st.form_submit_button("➤", use_container_width=True)

        if submitted and user_input and user_input.strip():
            st.session_state[f"feedback_chat_{workflow_type}"]["processing"] = True
            st.session_state[f"feedback_chat_{workflow_type}"]["pending_input"] = user_input.strip()
            st.rerun()

    st.divider()

    # Accept section with optional download button
    if download_data:
        col1, col_dl, col2 = st.columns([2, 1, 1])
    else:
        col1, col2 = st.columns([2, 1])

    with col1:
        messages_count = len(state.get("messages", []))
        if messages_count > 0:
            st.caption(
                f"{messages_count // 2} exchange{'s' if messages_count > 2 else ''} so far. "
                "Click Accept when you're satisfied with the results."
            )
        else:
            st.caption(
                "Review the results above. Chat with me if you have questions or want changes, "
                "or click Accept to continue."
            )

    if download_data:
        pdf_bytes, filename, mime_type = download_data
        with col_dl:
            st.download_button(
                "Download Report",
                data=pdf_bytes,
                file_name=filename,
                mime=mime_type,
                type="primary",
                use_container_width=True,
            )

    with col2:
        button_label = f"Continue to {next_stage_name}" if next_stage_name else "Accept & Continue"
        if st.button(
            button_label,
            type="primary",
            use_container_width=True,
        ):
            on_accept()


def clear_chat_history(workflow_type: str) -> None:
    """Clear the conversation history for a workflow."""
    key = f"feedback_chat_{workflow_type}"
    if key in st.session_state:
        st.session_state[key] = {
            "messages": [],
            "processing": False,
            "pending_input": None,
            "conversation": None,
        }
