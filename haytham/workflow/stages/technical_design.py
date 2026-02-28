"""Technical-design phase orchestration (HOW).

Functions used by build-buy-analysis and architecture-decisions stage configs.
"""

import json
import logging
import time
from typing import Any

from burr.core import State

from haytham.agents.factory.agent_factory import create_agent_by_name
from haytham.agents.output_utils import extract_text_from_result

logger = logging.getLogger(__name__)


# =============================================================================
# Architecture Decisions Agent Helpers
# =============================================================================


def _run_architect_agent(
    agent_name: str,
    prompt_template: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Execute an architect agent with the given context.

    Uses the agent factory to ensure hooks, OTEL tracing, and model tier
    routing are applied consistently.

    Args:
        agent_name: Name of the agent (must be registered in AGENT_CONFIGS)
        prompt_template: The prompt template to use
        context: Context to inject into the prompt

    Returns:
        Dict with output and metadata
    """
    start_time = time.time()

    try:
        # Build the full prompt with context
        full_prompt = prompt_template

        # Replace context placeholders
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"  # {{key}}
            if placeholder in full_prompt:
                if isinstance(value, (dict, list)):
                    full_prompt = full_prompt.replace(placeholder, json.dumps(value, indent=2))
                else:
                    full_prompt = full_prompt.replace(placeholder, str(value))

        agent = create_agent_by_name(agent_name)
        result = agent(full_prompt)
        output_text = extract_text_from_result(result, output_as_json=True)

        execution_time = time.time() - start_time

        return {
            "output": output_text,
            "status": "completed",
            "execution_time": execution_time,
        }

    except Exception as e:  # Intentional catch-all: agent execution boundary
        execution_time = time.time() - start_time
        logger.error(f"Agent {agent_name} failed: {e}", exc_info=True)

        return {
            "output": f"Error: {str(e)}",
            "status": "failed",
            "error": str(e),
            "execution_time": execution_time,
        }


_ARCHITECTURE_DECISIONS_PROMPT = """You are a Software Architect creating technical decisions for an MVP.

## Context

**System Goal:** {{system_goal}}

**MVP Scope:**
{{mvp_scope}}

**Capability Model (ALL capabilities that need architectural support):**
{{capabilities}}

**Build vs Buy Recommendations (services to use):**
{{build_buy_analysis}}

**Existing Decisions (if any):**
{{existing_decisions}}

## WHAT IS AN ARCHITECTURE DECISION?

Architecture decisions (DEC-*) specify HOW to implement the system using the recommended stack.
They bridge the gap between "what services to use" (Build/Buy) and "how to build features" (Stories).

**Decision Categories to Consider:**

1. **Authentication & Identity (DEC-AUTH-*)**
   - Auth method (email/password, social, magic link)
   - Session management
   - Anonymous handle generation (if applicable)

2. **Data Model & Schema (DEC-DB-*)**
   - Core tables/collections
   - Key constraints and indexes
   - Data integrity rules (e.g., prevent duplicates)

3. **Hosting & Deployment (DEC-DEPLOY-*)**
   - Frontend hosting strategy
   - API/backend deployment
   - Environment configuration

4. **Notifications & Email (DEC-NOTIFY-*)** (if email service recommended)
   - Email triggers and templates
   - Push notification strategy
   - Scheduled jobs/cron

5. **Real-Time & Sync (DEC-REALTIME-*)** (if real-time features needed)
   - Real-time update strategy
   - Subscription patterns
   - Fallback for offline

6. **Data Integrity & Validation (DEC-INTEGRITY-*)**
   - Input validation rules
   - Duplicate prevention constraints
   - Consistency guarantees

## CAPABILITY COVERAGE RULES

Your decisions MUST cover ALL capabilities from the Capability Model.

**Functional Capabilities (CAP-F-*):**
- Each CAP-F-* must appear in at least one decision's serves_capabilities
- These enable user-facing features

**Non-Functional Capabilities (CAP-NF-*):**
- CAP-NF-* capabilities often need DEDICATED decisions
- Data integrity, performance, usability requirements need explicit architectural support
- Do NOT ignore non-functional capabilities

## BUILD/BUY INTEGRATION

For each BUY recommendation in the Build vs Buy analysis, create decisions that specify:
- HOW to integrate the service
- WHAT features of the service to use
- HOW it serves specific capabilities

Example:
- Build/Buy: "Supabase for Database + Auth"
- Decision: "DEC-AUTH-001: Use Supabase Auth with email/password, generate random anonymous handles at registration, serves CAP-F-001, CAP-F-003"

## DECISION COUNT GUIDANCE

- Minimum: One decision per applicable category
- Target: 4-6 decisions for a typical MVP
- Maximum: One decision should not serve more than 4 capabilities (split if broader)

Do NOT artificially limit to 1-3 decisions if more are needed for complete coverage.

## OUTPUT FORMAT

Output valid JSON:

```json
{
  "decisions": [
    {
      "id": "DEC-AUTH-001",
      "name": "Authentication Strategy",
      "description": "What this decision entails - be specific about implementation",
      "rationale": "Why this is the right choice for THIS MVP given appetite and constraints",
      "serves_capabilities": ["CAP-F-001", "CAP-NF-002"],
      "implements_recommendation": "Which Build/Buy recommendation this implements (e.g., Supabase Auth)",
      "alternatives_considered": ["Alternative 1 - why not chosen", "Alternative 2 - why not chosen"]
    }
  ],
  "coverage_check": {
    "functional_capabilities_covered": ["CAP-F-001", "CAP-F-002"],
    "non_functional_capabilities_covered": ["CAP-NF-001"],
    "uncovered_capabilities": []
  },
  "summary": "Brief summary of architectural approach"
}
```

## SELF-CHECK (Required)

Before outputting, verify:
- [ ] Every CAP-F-* from the Capability Model is in at least one decision's serves_capabilities?
- [ ] Every CAP-NF-* from the Capability Model has architectural support?
- [ ] Every BUY recommendation from Build/Buy has a corresponding decision?
- [ ] No decision serves more than 4 capabilities (too broad = split it)?
- [ ] coverage_check.uncovered_capabilities is empty?
- [ ] Each decision has a specific implements_recommendation linking to Build/Buy?

If any check fails, ADD MORE DECISIONS until all capabilities are covered.

## MVP CONSTRAINTS

Remember this is an MVP with limited appetite:
- Prefer simple solutions over perfect solutions
- Use managed services (the BUY recommendations) over custom infrastructure
- One way to do things, not configurable options
- Ship fast, iterate later

Output ONLY valid JSON."""


# =============================================================================
# Stage Functions
# =============================================================================


def run_architecture_decisions(state: State) -> tuple[str, str]:
    """Run architecture decisions stage.

    Returns JSON string. The StageExecutor renders markdown via output_model.to_markdown().
    """
    # Get context from state
    system_goal = state.get("system_goal", "")
    mvp_scope = state.get("mvp_scope", "")
    capability_model = state.get("capability_model", "")
    build_buy_raw = state.get("build_buy_analysis", "")

    # Parse build_buy_analysis - may be JSON (from output_model) or markdown (legacy)
    try:
        bb_data = json.loads(build_buy_raw)
        stack_lines = []
        for svc in bb_data.get("recommended_stack", []):
            name = svc.get("name", "?")
            cat = svc.get("category", "?")
            rec = svc.get("recommendation", "BUY")
            stack_lines.append(f"- {name} ({cat}): {rec}")
        build_buy_analysis = (
            f"System Summary: {bb_data.get('system_summary', '')}\n"
            f"Stack Rationale: {bb_data.get('stack_rationale', '')}\n"
            f"Recommended Stack:\n" + "\n".join(stack_lines)
        )
    except (json.JSONDecodeError, TypeError):
        build_buy_analysis = build_buy_raw

    context = {
        "system_goal": system_goal,
        "mvp_scope": mvp_scope[:3000] if mvp_scope else "",
        "build_buy_analysis": build_buy_analysis[:4000] if build_buy_analysis else "",
        "capabilities": capability_model[:4000] if capability_model else "[]",
        "existing_decisions": "[]",
    }

    result = _run_architect_agent(
        agent_name="architecture_decisions",
        prompt_template=_ARCHITECTURE_DECISIONS_PROMPT,
        context=context,
    )

    if result["status"] == "failed":
        return f"Error: {result.get('error', 'Unknown error')}", "failed"

    # Return JSON directly; StageExecutor renders markdown via output_model.to_markdown()
    return result["output"], "completed"


def analyze_capabilities_for_build_buy(state: State) -> tuple[str, str]:
    """Analyze capabilities for build vs buy recommendations.

    Uses the build_buy_analyzer LLM agent with structured output to provide:
    1. Infrastructure overview - high-level requirements
    2. Recommended stack - services with rationale
    3. Alternatives - other options with pros/cons
    """
    # Get capability model and system goal from state
    capability_model = state.get("capability_model", "")
    mvp_scope = state.get("mvp_scope", "")
    system_goal = state.get("system_goal", "")

    if not capability_model:
        return "Error: No capability model found in state", "failed"

    try:
        # Create the agent with structured output
        agent = create_agent_by_name("build_buy_analyzer")

        # Build the query with context
        query = f"""Analyze the following startup and its capabilities to provide build vs buy recommendations.

## System Goal
{system_goal}

## MVP Scope
{mvp_scope}

## Capability Model
{capability_model}

Based on this information:
1. Identify the high-level infrastructure requirements
2. Recommend a stack of services/build decisions with clear rationale
3. Provide alternatives for key BUY recommendations

Focus on MVP stage - favor services with generous free tiers and quick integration."""

        # Run the agent
        result = agent(query)

        # Return JSON for Burr state; executor renders markdown for disk via output_model
        return extract_text_from_result(result, output_as_json=True), "completed"

    except Exception as e:  # Intentional catch-all: agent execution boundary
        logger.error(f"Build/Buy analysis failed: {e}", exc_info=True)
        return f"Error analyzing capabilities: {str(e)}", "failed"
