"""Idea Validator - Pre-workflow validation for startup ideas.

This module provides input validation before the main workflow starts,
ensuring that the user has entered a valid product/startup idea.
"""

import json
import logging
import re
from dataclasses import dataclass
from typing import Literal

from lib.session_utils import load_environment, setup_paths

setup_paths()
load_environment()

from haytham.agents.factory.agent_factory import create_agent_by_name  # noqa: E402
from haytham.agents.worker_idea_discovery.discovery_models import (  # noqa: E402
    IdeaDiscoveryOutput,
)

logger = logging.getLogger(__name__)


@dataclass
class SuggestedIdea:
    """A suggested startup idea for UNRELATED responses."""

    title: str
    description: str
    icon: str


@dataclass
class ValidationResult:
    """Result of idea validation."""

    classification: Literal["VALID_IDEA", "NEEDS_CLARIFICATION", "UNRELATED"]
    confidence: float
    reasoning: str
    message: str
    # For VALID_IDEA
    extracted_idea: str | None = None
    # For NEEDS_CLARIFICATION
    questions: list[str] | None = None
    partial_understanding: str | None = None
    # For UNRELATED
    suggested_ideas: list[SuggestedIdea] | None = None
    extracted_themes: list[str] | None = None


def _get_default_suggested_ideas() -> list[SuggestedIdea]:
    """Return default suggested ideas when we can't parse the agent response."""
    return [
        SuggestedIdea(
            title="AI Meeting Assistant",
            description="A tool that joins video calls, takes notes, extracts action items, and sends follow-ups.",
            icon="🤝",
        ),
        SuggestedIdea(
            title="Local Service Marketplace",
            description="An app connecting homeowners with vetted local service providers for repairs and maintenance.",
            icon="🏠",
        ),
        SuggestedIdea(
            title="Personal Finance Coach",
            description="An AI app that analyzes spending habits and provides personalized financial advice.",
            icon="💰",
        ),
    ]


def _extract_agent_response(result) -> str:
    """Extract text output from Strands agent result.

    Handles various response formats from the Strands SDK.
    """
    output_text = ""

    # Handle AgentResult from strands
    if hasattr(result, "message"):
        msg = result.message

        # Dict with content array
        if isinstance(msg, dict) and "content" in msg:
            content = msg["content"]
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        output_text += item["text"]
                    elif hasattr(item, "text"):
                        output_text += item.text
            else:
                output_text = str(content)

        # Message object with content attribute
        elif hasattr(msg, "content"):
            content = msg.content
            if isinstance(content, list):
                for block in content:
                    if hasattr(block, "text"):
                        output_text += block.text
                    elif isinstance(block, dict) and "text" in block:
                        output_text += block["text"]
            else:
                output_text = str(content)
        else:
            output_text = str(msg)

    # Direct string result
    elif isinstance(result, str):
        output_text = result

    # Dict result
    elif isinstance(result, dict):
        if "content" in result:
            content = result["content"]
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        output_text += item["text"]
            else:
                output_text = str(content)
        elif "output" in result:
            output_text = str(result["output"])
        elif "text" in result:
            output_text = result["text"]
        else:
            output_text = str(result)
    else:
        output_text = str(result)

    return output_text.strip()


def validate_idea(user_input: str) -> ValidationResult:
    """Validate if user input is a valid startup/product idea.

    Args:
        user_input: The raw user input to validate

    Returns:
        ValidationResult with classification and appropriate response fields
    """
    try:
        agent = create_agent_by_name("idea_gatekeeper")

        # Run the agent
        result = agent(user_input)

        # Extract the response text using robust extraction
        response_text = _extract_agent_response(result)

        logger.info(f"Gatekeeper response length: {len(response_text)} chars")
        logger.debug(f"Gatekeeper response: {response_text[:500]}...")

        if not response_text:
            logger.warning("Empty response from gatekeeper agent")
            # Return UNRELATED with defaults for empty response
            return ValidationResult(
                classification="UNRELATED",
                confidence=0.5,
                reasoning="Empty response from validation agent",
                message="Hey there! I'm Haytham, a startup idea validator. Let me help you build something great!",
                suggested_ideas=_get_default_suggested_ideas(),
                extracted_themes=[],
            )

        # Parse JSON from response
        return _parse_gatekeeper_response(response_text)

    except Exception as e:
        logger.error(f"Idea validation failed: {e}", exc_info=True)
        # On error, return UNRELATED with defaults so user can retry
        return ValidationResult(
            classification="UNRELATED",
            confidence=0.5,
            reasoning=f"Validation check encountered an error: {e}",
            message="Hey there! I'm Haytham, a startup idea validator. I help entrepreneurs turn ideas into validated products.",
            suggested_ideas=_get_default_suggested_ideas(),
            extracted_themes=[],
        )


def _parse_gatekeeper_response(response_text: str) -> ValidationResult:
    """Parse the JSON response from the gatekeeper agent."""
    try:
        # Try to extract JSON from the response
        # Look for JSON block markers first
        json_match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find raw JSON
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                raise ValueError("No JSON found in response")

        data = json.loads(json_str)

        classification = data.get("classification", "VALID_IDEA")
        confidence = data.get("confidence", 0.8)
        reasoning = data.get("reasoning", "")
        response = data.get("response", {})

        if classification == "VALID_IDEA":
            return ValidationResult(
                classification="VALID_IDEA",
                confidence=confidence,
                reasoning=reasoning,
                message=response.get("message", "Your idea is ready for validation."),
                extracted_idea=response.get("extracted_idea"),
            )
        elif classification == "NEEDS_CLARIFICATION":
            return ValidationResult(
                classification="NEEDS_CLARIFICATION",
                confidence=confidence,
                reasoning=reasoning,
                message=response.get("message", "Could you tell me more about your idea?"),
                questions=response.get("questions", []),
                partial_understanding=response.get("partial_understanding"),
            )
        else:  # UNRELATED
            # Parse suggested ideas
            suggested_ideas = None
            raw_ideas = response.get("suggested_ideas", [])
            if raw_ideas:
                suggested_ideas = [
                    SuggestedIdea(
                        title=idea.get("title", "Startup Idea"),
                        description=idea.get("description", ""),
                        icon=idea.get("icon", "💡"),
                    )
                    for idea in raw_ideas
                    if isinstance(idea, dict)
                ]

            return ValidationResult(
                classification="UNRELATED",
                confidence=confidence,
                reasoning=reasoning,
                message=response.get(
                    "message",
                    "I'm Haytham, a startup idea validator. Let me help you build something great!",
                ),
                suggested_ideas=suggested_ideas,
                extracted_themes=response.get("extracted_themes", []),
            )

    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Failed to parse gatekeeper response as JSON: {e}")
        logger.debug(f"Response text: {response_text}")

        # Fallback: try to infer from text content
        lower_response = response_text.lower()
        if "unrelated" in lower_response or "not a product" in lower_response:
            return ValidationResult(
                classification="UNRELATED",
                confidence=0.7,
                reasoning="Inferred from response text",
                message="Hey there! I'm Haytham, a startup idea validator. I help entrepreneurs turn ideas into validated products.",
                suggested_ideas=_get_default_suggested_ideas(),
                extracted_themes=[],
            )
        elif "clarif" in lower_response or "more detail" in lower_response:
            return ValidationResult(
                classification="NEEDS_CLARIFICATION",
                confidence=0.7,
                reasoning="Inferred from response text",
                message="I'd love to help validate your idea. Could you tell me a bit more?",
                questions=[
                    "Who would use this product or service?",
                    "What problem are you trying to solve?",
                    "What would the product/service actually do?",
                ],
            )
        else:
            # Default to UNRELATED with defaults so user can provide a proper idea
            return ValidationResult(
                classification="UNRELATED",
                confidence=0.6,
                reasoning="Could not parse response, showing suggestions",
                message="Hey there! I'm Haytham, a startup idea validator. I help entrepreneurs turn ideas into validated products.",
                suggested_ideas=_get_default_suggested_ideas(),
                extracted_themes=[],
            )


def refine_idea_with_answers(
    original_input: str,
    partial_understanding: str | None,
    questions: list[str],
    answers: list[str],
) -> str:
    """Combine original input with clarifying answers into a refined idea.

    Args:
        original_input: The user's original input
        partial_understanding: What the agent understood so far
        questions: The clarifying questions that were asked
        answers: The user's answers to those questions

    Returns:
        A refined idea statement combining all context
    """
    parts = []

    if partial_understanding:
        parts.append(f"Idea context: {partial_understanding}")

    parts.append(f"Original input: {original_input}")

    if questions and answers:
        clarifications = []
        for q, a in zip(questions, answers, strict=False):
            if a.strip():
                clarifications.append(f"- {q}: {a}")
        if clarifications:
            parts.append("Clarifications:\n" + "\n".join(clarifications))

    return "\n\n".join(parts)


@dataclass
class PolishResult:
    """Result of idea polishing."""

    polished_idea: str
    changes_made: list[str]  # Summary of changes for transparency
    success: bool
    change_significance: Literal["none", "cosmetic", "substantive"] = "none"
    error: str | None = None


def polish_idea(original_idea: str) -> PolishResult:
    """Polish the idea text for clarity without changing its meaning.

    Fixes typos, grammar errors, and improves clarity while preserving
    the core concept, features, and constraints specified by the user.

    Args:
        original_idea: The user's original idea text

    Returns:
        PolishResult with polished text and summary of changes
    """
    from haytham.agents.utils._bedrock_config import create_bedrock_model
    from strands import Agent

    # Conservative prompt that emphasizes preserving meaning
    system_prompt = """You are a copy editor preparing startup idea descriptions for AI analysis.

Your task is to polish the text for clarity while STRICTLY preserving the original meaning.

ALLOWED changes:
- Fix spelling mistakes and typos
- Fix grammar errors
- Improve sentence clarity and flow
- Standardize punctuation

FORBIDDEN changes:
- Do NOT add new features or capabilities
- Do NOT remove any features or constraints mentioned
- Do NOT change the scope (broader or narrower)
- Do NOT add technical assumptions not in the original
- Do NOT make it longer - keep it concise
- Do NOT change the target audience unless correcting obvious typos
- Do NOT add marketing language or hype

OUTPUT FORMAT:
Return a JSON object with exactly these fields:
```json
{
  "polished_idea": "The polished version of the idea",
  "changes_made": ["Change 1", "Change 2"],
  "change_significance": "none | cosmetic | substantive"
}
```

CHANGE SIGNIFICANCE (choose one):
- "none": The original is already clear — no changes made at all.
- "cosmetic": Only minor fixes that any reader would agree don't change meaning (typos, punctuation, grammar, trivial word substitutions like 'draws from' → 'is based on'). The user does NOT need to review these.
- "substantive": Changes that restructure sentences, add clarity that alters understanding, or could surprise the user. The user SHOULD review these.

When in doubt, classify as "cosmetic". Only use "substantive" when the polished version reads meaningfully differently from the original.

IMPORTANT: The polished idea should be recognizably the same idea. A reader should not notice any difference in meaning, only improved readability."""

    try:
        model = create_bedrock_model(max_tokens=1000)
        agent = Agent(model=model, system_prompt=system_prompt)

        result = agent(f"Polish this startup idea:\n\n{original_idea}")

        # Extract response text
        response_text = _extract_agent_response(result)

        if not response_text:
            logger.warning("Empty response from polish agent")
            return PolishResult(
                polished_idea=original_idea,
                changes_made=["Could not polish - using original"],
                success=False,
                error="Empty response from polish agent",
            )

        # Parse JSON from response
        return _parse_polish_response(response_text, original_idea)

    except Exception as e:
        logger.error(f"Idea polishing failed: {e}", exc_info=True)
        return PolishResult(
            polished_idea=original_idea,
            changes_made=["Polishing failed - using original"],
            success=False,
            error=str(e),
        )


def _normalize_text(text: str) -> str:
    """Normalize text for comparison (lowercase, collapse whitespace)."""
    return " ".join(text.lower().split())



def _parse_polish_response(response_text: str, original_idea: str) -> PolishResult:
    """Parse the JSON response from the polish agent."""
    try:
        # Try to extract JSON from the response
        json_match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                raise ValueError("No JSON found in response")

        data = json.loads(json_str)

        polished = data.get("polished_idea", original_idea)
        changes = data.get("changes_made", [])
        significance = data.get("change_significance", "cosmetic")

        # Ensure changes is a list
        if isinstance(changes, str):
            changes = [changes]

        # Normalize significance value
        if significance not in ("none", "cosmetic", "substantive"):
            significance = "cosmetic"

        polished_stripped = polished.strip()
        logger.debug(f"Polish change_significance: {significance}")

        # Determine if changes need user confirmation.
        # Only "substantive" changes warrant showing the confirmation dialog.
        no_confirmation_needed = (
            significance in ("none", "cosmetic")
            # Fallback: explicit "no changes" message from agent
            or any("no change" in c.lower() for c in changes)
            # Fallback: text is literally identical
            or _normalize_text(polished_stripped) == _normalize_text(original_idea)
        )

        if no_confirmation_needed:
            # Silently apply cosmetic fixes without user confirmation
            return PolishResult(
                polished_idea=polished_stripped,
                changes_made=["No changes needed - idea is already clear"],
                change_significance=significance,
                success=True,
            )

        return PolishResult(
            polished_idea=polished_stripped,
            changes_made=changes,
            change_significance="substantive",
            success=True,
        )

    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Failed to parse polish response as JSON: {e}")
        # If we can't parse, return original
        return PolishResult(
            polished_idea=original_idea,
            changes_made=["Could not parse response - using original"],
            success=False,
            error=str(e),
        )


def discover_idea_gaps(validated_idea: str) -> IdeaDiscoveryOutput | None:
    """Run Lean Canvas gap analysis on the validated idea.

    Calls the discovery agent to assess coverage of 4 dimensions
    (Problem, Customer Segments, UVP, Solution) and generate targeted
    clarifying questions for any gaps.

    Args:
        validated_idea: The polished/validated idea text

    Returns:
        IdeaDiscoveryOutput with assessments and questions, or None on failure
    """
    try:
        agent = create_agent_by_name("idea_discovery")
        result = agent(validated_idea)

        # Prefer structured output (Strands SDK)
        if hasattr(result, "structured_output") and result.structured_output is not None:
            if isinstance(result.structured_output, IdeaDiscoveryOutput):
                return result.structured_output

        # Fallback: parse JSON from text response
        response_text = _extract_agent_response(result)
        if not response_text:
            logger.warning("Empty response from discovery agent")
            return None

        json_match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                logger.warning("No JSON found in discovery response")
                return None

        data = json.loads(json_str)
        return IdeaDiscoveryOutput(**data)

    except Exception as e:
        logger.error(f"Idea discovery failed: {e}", exc_info=True)
        return None


def enrich_idea_with_discovery(
    validated_idea: str,
    discovery_result: IdeaDiscoveryOutput,
    answers: dict[str, str],
) -> str:
    """Combine original idea with founder's answers to discovery questions.

    Args:
        validated_idea: The original validated idea text
        discovery_result: The discovery agent output with questions
        answers: Mapping of dimension name to founder's answer

    Returns:
        Enriched idea text with founder's clarifications appended
    """
    # Filter to only answered questions
    clarifications = []
    for question in discovery_result.questions:
        answer = answers.get(question.dimension, "").strip()
        if answer:
            clarifications.append(f"- {question.dimension}: {answer}")

    if not clarifications:
        return validated_idea

    return validated_idea + "\n\nFounder's clarifications:\n" + "\n".join(clarifications)
