"""Idea Refinement Component - Help users refine their idea after HIGH risk detection.

This component provides an interactive chat interface for refining startup ideas
when the risk assessment identifies significant risks.
"""

from pathlib import Path

import streamlit as st


def init_refinement_state() -> None:
    """Initialize session state for idea refinement."""
    if "refinement_chat" not in st.session_state:
        st.session_state.refinement_chat = {
            "messages": [],
            "processing": False,
            "pending_input": None,
            "conversation": None,
            "refined_idea": None,
        }


def get_refinement_state() -> dict:
    """Get the refinement chat state."""
    return st.session_state.get(
        "refinement_chat",
        {
            "messages": [],
            "processing": False,
            "pending_input": None,
            "conversation": None,
            "refined_idea": None,
        },
    )


def add_refinement_message(role: str, content: str) -> None:
    """Add a message to the refinement conversation history."""
    if "refinement_chat" not in st.session_state:
        init_refinement_state()

    st.session_state.refinement_chat["messages"].append({"role": role, "content": content})


def clear_refinement_state() -> None:
    """Clear the refinement conversation state."""
    if "refinement_chat" in st.session_state:
        del st.session_state.refinement_chat


def _load_context_for_refinement(session_dir: Path) -> dict:
    """Load risk assessment and pivot strategy context for refinement.

    Args:
        session_dir: Path to the session directory

    Returns:
        Dict with risk_assessment and pivot_strategy content
    """
    context = {"risk_assessment": None, "pivot_strategy": None}

    # Load risk assessment
    risk_dir = session_dir / "risk-assessment"
    if risk_dir.exists():
        for f in risk_dir.glob("*.md"):
            if f.name not in ["checkpoint.md", "user_feedback.md"]:
                try:
                    context["risk_assessment"] = f.read_text()
                    break
                except Exception:
                    pass

    # Load pivot strategy
    pivot_dir = session_dir / "pivot-strategy"
    if pivot_dir.exists():
        for f in pivot_dir.glob("*.md"):
            if f.name not in ["checkpoint.md", "user_feedback.md"]:
                try:
                    context["pivot_strategy"] = f.read_text()
                    break
                except Exception:
                    pass

    return context


def _extract_refined_idea(response: str) -> str | None:
    """Extract refined idea from agent response.

    The agent should format the refined idea with a specific marker.

    Args:
        response: The agent's response text

    Returns:
        The extracted refined idea, or None if not found
    """
    import re

    # Look for "**Refined Idea:**" followed by the idea text
    patterns = [
        r"\*\*Refined Idea:\*\*\s*(.+?)(?:\n\n|\Z)",
        r"\*\*Refined Idea\*\*:\s*(.+?)(?:\n\n|\Z)",
        r"Refined Idea:\s*(.+?)(?:\n\n|\Z)",
    ]

    for pattern in patterns:
        match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
        if match:
            idea = match.group(1).strip()
            # Clean up any trailing markers or formatting
            idea = re.sub(r"\*+$", "", idea).strip()
            if idea:
                return idea

    return None


def _create_refinement_system_prompt(original_idea: str, session_dir: Path) -> str:
    """Create the system prompt for the refinement agent.

    Args:
        original_idea: The original startup idea
        session_dir: Path to session directory

    Returns:
        The system prompt string
    """
    context_data = _load_context_for_refinement(session_dir)

    return f"""You are helping a user refine their startup idea after risk analysis identified significant concerns.

## Original Idea
{original_idea}

## Risk Assessment Context
{context_data.get("risk_assessment", "No risk assessment available.")}

## Pivot Strategy Suggestions
{context_data.get("pivot_strategy", "No pivot strategy available.")}

## Your Role
1. Help the user understand the identified risks
2. Collaboratively refine the idea to address these risks
3. Suggest specific modifications that could improve viability
4. When the user is satisfied, format the refined idea clearly

## Important Instructions
- Focus on constructive improvements, not just criticism
- Keep the core of what the user wants to build
- Be conversational and supportive
- When the user seems happy with a direction, summarize the refined idea

## CRITICAL: When presenting a refined idea, you MUST use this exact format:

**Refined Idea:** [Write the complete refined idea as a single paragraph here]

This format is required so the system can extract the refined idea for re-validation.

## Examples of Good Responses

User: "What if I focus on small businesses instead of enterprises?"
You: "That's a great pivot! Small businesses often have simpler needs and faster decision cycles. Let me summarize how this changes your idea:

**Refined Idea:** A subscription-based inventory management platform specifically designed for small retail businesses, offering simplified setup, affordable pricing tiers, and integration with common POS systems that small businesses already use."

User: "Help me understand the market risk"
You: "The risk assessment flagged market risk because [explain based on context]. Here are some ways we could address this: [suggestions]"
"""


def _get_or_create_refinement_agent(original_idea: str, session_dir: Path):
    """Get or create the refinement agent instance."""
    from strands import Agent

    from haytham.agents.factory.agent_factory import get_bedrock_model_id
    from haytham.agents.utils.model_provider import create_model

    state = get_refinement_state()

    if state.get("conversation") is None:
        # Create the model
        model_id = get_bedrock_model_id()
        model = create_model(
            model_id=model_id,
            max_tokens=1000,
        )

        # Create agent with refinement-focused prompt
        system_prompt = _create_refinement_system_prompt(original_idea, session_dir)
        agent = Agent(
            system_prompt=system_prompt,
            name="idea_refinement_agent",
            model=model,
        )

        # Store agent and message history
        st.session_state.refinement_chat["conversation"] = {
            "agent": agent,
            "history": [],
        }

    return st.session_state.refinement_chat["conversation"]


def _send_refinement_message(original_idea: str, session_dir: Path, user_message: str) -> str:
    """Send a message to the refinement agent.

    Args:
        original_idea: The original startup idea
        session_dir: Session directory path
        user_message: The user's message

    Returns:
        The agent's response
    """
    import logging

    logger = logging.getLogger(__name__)

    conv = _get_or_create_refinement_agent(original_idea, session_dir)
    agent = conv["agent"]
    history = conv["history"]

    try:
        # Call the agent with history
        result = agent(user_message, history=history if history else None)

        # Extract response text
        response = _extract_agent_response(result)

        # Update history
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": response})

        return response

    except Exception as e:
        logger.error(f"Error in refinement agent: {e}")
        return f"I encountered an error: {e}. Could you try rephrasing?"


def _extract_agent_response(result) -> str:
    """Extract text from Strands SDK agent result."""
    from haytham.agents.output_utils import extract_text_from_result

    try:
        return extract_text_from_result(result)

        return str(result)
    except Exception:
        return str(result)


def render_idea_refinement(
    original_idea: str,
    session_dir: Path,
    on_accept: callable,
    on_cancel: callable,
) -> None:
    """Render the idea refinement conversation interface.

    Args:
        original_idea: The original startup idea
        session_dir: Path to the session directory
        on_accept: Callback when user accepts refined idea - receives refined_idea string
        on_cancel: Callback when user cancels refinement
    """
    init_refinement_state()
    state = get_refinement_state()

    st.markdown("### Refine Your Idea")

    # Show original idea
    st.markdown("**Your original idea:**")
    st.info(original_idea)

    st.markdown(
        "Let's work together to address the identified risks. "
        "I can help you refine your idea while keeping your core vision intact."
    )

    # Chat container
    chat_container = st.container()

    with chat_container:
        messages = state.get("messages", [])

        if not messages:
            # Show initial guidance
            st.markdown(
                """
                <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                            padding: 1.5rem; border-radius: 12px; color: white; margin-bottom: 1rem;">
                    <h4 style="margin: 0 0 0.5rem 0;">Let's address the risks together</h4>
                    <p style="margin: 0; opacity: 0.9;">
                        I've reviewed the risk assessment. Here's how I can help:
                    </p>
                    <ul style="margin: 0.5rem 0 0 1rem; opacity: 0.9;">
                        <li><strong>Understand risks</strong> - "Why is the market risk high?"</li>
                        <li><strong>Explore options</strong> - "What if I focus on a niche market?"</li>
                        <li><strong>Refine the idea</strong> - "Help me reframe this for B2B"</li>
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            # Render conversation
            for msg in messages:
                role = msg["role"]
                content = msg["content"]

                if role == "user":
                    with st.chat_message("user"):
                        st.markdown(content)
                else:
                    with st.chat_message("assistant"):
                        st.markdown(content)

    # Process pending input
    if state.get("processing") and state.get("pending_input"):
        pending = state["pending_input"]
        st.session_state.refinement_chat["pending_input"] = None

        # Add user message
        add_refinement_message("user", pending)

        # Show processing indicator
        with st.spinner("Thinking..."):
            try:
                response = _send_refinement_message(
                    original_idea=original_idea,
                    session_dir=session_dir,
                    user_message=pending,
                )

                # Add assistant response
                add_refinement_message("assistant", response)

                # Check if response contains a refined idea
                refined = _extract_refined_idea(response)
                if refined:
                    st.session_state.refinement_chat["refined_idea"] = refined

            except Exception as e:
                error_msg = f"I encountered an issue: {e}. Could you try rephrasing?"
                add_refinement_message("assistant", error_msg)

        st.session_state.refinement_chat["processing"] = False
        st.rerun()

    # Input area
    st.divider()

    if state.get("processing"):
        st.info("Processing your message...")
    else:
        user_input = st.chat_input(
            placeholder="Tell me how you'd like to refine your idea...",
            key="refinement_chat_input",
        )

        if user_input:
            st.session_state.refinement_chat["processing"] = True
            st.session_state.refinement_chat["pending_input"] = user_input
            st.rerun()

    # Action buttons
    st.divider()

    # Check if we have a refined idea
    refined_idea = state.get("refined_idea")

    if refined_idea:
        st.success("A refined idea has been identified!")
        st.markdown("**Refined Idea:**")
        st.info(refined_idea)

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button(
                "Accept & Re-validate",
                type="primary",
                use_container_width=True,
            ):
                on_accept(refined_idea)
        with col2:
            if st.button(
                "Keep Refining",
                use_container_width=True,
            ):
                # Clear the refined idea and continue conversation
                st.session_state.refinement_chat["refined_idea"] = None
                st.rerun()
        with col3:
            if st.button(
                "Cancel",
                use_container_width=True,
            ):
                on_cancel()
    else:
        col1, col2 = st.columns(2)
        with col1:
            messages_count = len(state.get("messages", []))
            if messages_count > 0:
                st.caption(
                    f"{messages_count // 2} exchange{'s' if messages_count > 2 else ''} so far. "
                    "When you're happy with the direction, ask me to summarize the refined idea."
                )
            else:
                st.caption(
                    "Start chatting to explore how we can improve your idea. "
                    "Ask me to summarize when you've refined it enough."
                )
        with col2:
            if st.button(
                "Cancel Refinement",
                use_container_width=True,
            ):
                on_cancel()
