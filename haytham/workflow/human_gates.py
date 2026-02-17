"""Human gates for the Story-to-Implementation Pipeline.

Human gates are decision points where user input is required
before the pipeline can proceed. This module provides utilities
for presenting choices and capturing user decisions.

Reference: ADR-001b: Platform Options Presentation
"""

from dataclasses import dataclass, field

from haytham.project.stack_templates import (
    STACK_TEMPLATES,
    get_templates_for_platform,
)


@dataclass
class StackChoice:
    """Represents a stack choice option for the user."""

    template_id: str
    platform: str
    backend_summary: str
    frontend_summary: str
    is_recommended: bool = False
    recommendation_reason: str = ""


@dataclass
class StackChoicePresentation:
    """Formatted presentation of stack choices for the user."""

    recommended: StackChoice
    alternatives: list[StackChoice] = field(default_factory=list)
    platform_explanation: str = ""
    formatted_text: str = ""


def format_stack_for_display(template_id: str) -> StackChoice:
    """Format a stack template for user display.

    Args:
        template_id: Stack template ID

    Returns:
        StackChoice with user-friendly descriptions
    """
    stack = STACK_TEMPLATES.get(template_id)
    if not stack:
        return StackChoice(
            template_id=template_id,
            platform="unknown",
            backend_summary="Unknown",
            frontend_summary="Unknown",
        )

    backend_summary = "None"
    if stack.backend:
        backend_summary = f"{stack.backend.language.title()} + {stack.backend.framework.title()}"

    frontend_summary = "None"
    if stack.frontend:
        frontend_summary = f"{stack.frontend.language.title()} + {stack.frontend.framework.title()}"

    return StackChoice(
        template_id=template_id,
        platform=stack.platform,
        backend_summary=backend_summary,
        frontend_summary=frontend_summary,
    )


def get_platform_explanation(platform: str) -> str:
    """Get user-friendly explanation of what a platform means.

    Args:
        platform: Platform type (web_application, cli, api)

    Returns:
        User-friendly explanation
    """
    explanations = {
        "web_application": """**What this means for you:**
- Users access via web browser (Chrome, Safari, Firefox, etc.)
- Works on any device - desktop, tablet, or phone
- No app store approval needed
- Easy to update and deploy changes""",
        "cli": """**What this means for you:**
- Users run commands in terminal/command prompt
- Great for automation and scripting
- No graphical interface needed
- Fast for power users""",
        "api": """**What this means for you:**
- Provides backend services for other applications
- No user interface included
- Other apps/services connect to it
- Good for integrations and mobile app backends""",
    }
    return explanations.get(platform, "No explanation available.")


def present_stack_choices(
    recommended_platform: str,
    recommended_stack: str,
    rationale: str = "",
) -> StackChoicePresentation:
    """Prepare stack choices for user presentation.

    This formats the stack options in user-friendly terms,
    highlighting the recommended choice.

    Args:
        recommended_platform: Recommended platform type
        recommended_stack: Recommended stack template ID
        rationale: Optional rationale for the recommendation

    Returns:
        StackChoicePresentation ready for display
    """
    # Get recommended stack
    recommended = format_stack_for_display(recommended_stack)
    recommended.is_recommended = True
    recommended.recommendation_reason = rationale

    # Get alternatives for the same platform
    platform_stacks = get_templates_for_platform(recommended_platform)
    alternatives = []
    for tid in platform_stacks:
        if tid != recommended_stack:
            alt = format_stack_for_display(tid)
            alternatives.append(alt)

    # Get platform explanation
    platform_explanation = get_platform_explanation(recommended_platform)

    # Format text for display
    formatted_text = _format_choice_text(
        recommended, alternatives, platform_explanation, recommended_platform
    )

    return StackChoicePresentation(
        recommended=recommended,
        alternatives=alternatives,
        platform_explanation=platform_explanation,
        formatted_text=formatted_text,
    )


def _format_choice_text(
    recommended: StackChoice,
    alternatives: list[StackChoice],
    platform_explanation: str,
    platform: str,
) -> str:
    """Format the full choice text for display.

    Args:
        recommended: Recommended stack choice
        alternatives: Alternative choices
        platform_explanation: Explanation of the platform
        platform: Platform type

    Returns:
        Formatted markdown string
    """
    platform_labels = {
        "web_application": "Web Application",
        "cli": "Command-Line Tool",
        "api": "API Service",
    }
    platform_label = platform_labels.get(platform, platform.title())

    lines = [
        "## Platform Decision Required",
        "",
        f"### Recommended: {platform_label}",
        "",
        platform_explanation,
        "",
    ]

    if recommended.recommendation_reason:
        lines.extend(
            [
                "**Why this is recommended:**",
                recommended.recommendation_reason,
                "",
            ]
        )

    lines.extend(
        [
            "### Technology Stack Options",
            "",
            f"**[A] {recommended.template_id}** (Recommended)",
            f"- Backend: {recommended.backend_summary}",
            f"- Frontend: {recommended.frontend_summary}",
            "",
        ]
    )

    for i, alt in enumerate(alternatives):
        letter = chr(ord("B") + i)
        lines.extend(
            [
                f"**[{letter}] {alt.template_id}**",
                f"- Backend: {alt.backend_summary}",
                f"- Frontend: {alt.frontend_summary}",
                "",
            ]
        )

    lines.extend(
        [
            "---",
            "",
            "Which stack would you like to use? Enter A, B, C, etc. or the stack ID.",
        ]
    )

    return "\n".join(lines)


def parse_stack_choice(
    user_input: str,
    recommended_stack: str,
    alternatives: list[str],
) -> str | None:
    """Parse user's stack choice input.

    Handles letter choices (A, B, C) and direct template IDs.

    Args:
        user_input: Raw user input
        recommended_stack: The recommended stack template ID
        alternatives: List of alternative template IDs

    Returns:
        Template ID of chosen stack, or None if invalid input
    """
    input_clean = user_input.strip().upper()

    # Handle letter choices
    all_choices = [recommended_stack, *alternatives]
    if len(input_clean) == 1 and input_clean.isalpha():
        idx = ord(input_clean) - ord("A")
        if 0 <= idx < len(all_choices):
            return all_choices[idx]

    # Handle direct template ID
    input_lower = user_input.strip().lower()
    if input_lower in STACK_TEMPLATES:
        return input_lower

    return None


async def async_present_stack_choice(
    recommended_platform: str,
    recommended_stack: str,
    rationale: str = "",
    input_callback=None,
) -> str:
    """Async version of stack choice presentation.

    For use in async workflows.

    Args:
        recommended_platform: Recommended platform type
        recommended_stack: Recommended stack template ID
        rationale: Optional rationale
        input_callback: Async function to get user input

    Returns:
        Selected stack template ID
    """
    presentation = present_stack_choices(recommended_platform, recommended_stack, rationale)

    if input_callback is None:
        # No callback, just return recommended
        return recommended_stack

    # Get alternatives list
    alt_ids = [alt.template_id for alt in presentation.alternatives]

    # Keep asking until valid input
    while True:
        user_input = await input_callback(presentation.formatted_text)
        choice = parse_stack_choice(user_input, recommended_stack, alt_ids)
        if choice:
            return choice
        # Invalid input, will loop and ask again
