"""MVP Scope Swarm — Strands Swarm replacement for run_mvp_scope_chain().

Replaces manual sequential orchestration of 3 sub-agents with a Strands Swarm
that uses handoffs. Each agent receives the concept anchor via the initial
task prompt and can see prior agents' output in working memory.

Returns: tuple[str, str] — (combined_output, status) for stage_executor compat.
"""

import logging

from burr.core import State

logger = logging.getLogger(__name__)


def run_mvp_scope_swarm(state: State) -> tuple[str, str]:
    """Run the MVP scope stage as a Strands Swarm with handoffs.

    Swarm agents:
    1. mvp_scope_core: The One Thing, user segment, input method, appetite
    2. mvp_scope_boundaries: IN/OUT scope table, success criteria
    3. mvp_scope_flows: Core user flows, scope metadata, consistency check

    The swarm hands off sequentially: core → boundaries → flows.
    Each agent sees all prior output via shared working memory.

    Returns:
        Tuple of (combined_output, status) where status is "completed" or "failed".
    """
    import json

    from strands import Agent
    from strands.multiagent.swarm import Swarm

    from haytham.agents.output_utils import extract_text_from_result
    from haytham.agents.utils.model_provider import create_model
    from haytham.agents.utils.prompt_loader import load_agent_prompt
    from haytham.workflow.burr_actions import render_validation_summary_from_json
    from haytham.workflow.stages.concept_anchor import get_anchor_context_string

    system_goal = state.get("system_goal", "")
    idea_analysis = state.get("idea_analysis", "")
    raw_vs = state.get("validation_summary", "")

    # Parse validation_summary — may be JSON (from output_model) or markdown (legacy)
    try:
        validation_summary = render_validation_summary_from_json(json.loads(raw_vs))
    except (json.JSONDecodeError, TypeError):
        validation_summary = raw_vs

    # ADR-022: Get anchor for all sub-agents
    anchor_context = get_anchor_context_string(state)
    if anchor_context:
        logger.info(f"ADR-022: Anchor loaded ({len(anchor_context)} chars)")
    else:
        logger.warning("ADR-022: NO ANCHOR CONTEXT - scope may drift from original intent!")

    # Build shared context for the initial task
    anchor_section = f"{anchor_context}\n\n---\n\n" if anchor_context else ""
    shared_context = (
        f"{anchor_section}"
        f"## Startup Idea\n{system_goal}\n\n"
        f"## Concept Analysis\n{idea_analysis[:2000]}\n\n"
        f"## Validation Summary\n{validation_summary[:2000]}\n\n"
    )

    try:
        model = create_model()

        # Create the three agents with handoff instructions
        core_prompt = load_agent_prompt("worker_mvp_scope_core")
        core_agent = Agent(
            name="mvp_scope_core",
            system_prompt=(
                f"{core_prompt}\n\n"
                "## SWARM INSTRUCTIONS\n"
                "After completing your output, hand off to 'mvp_scope_boundaries' "
                "with a summary of The One Thing, user segment, input method, and appetite."
            ),
            model=model,
        )

        boundaries_prompt = load_agent_prompt("worker_mvp_scope_boundaries")
        boundaries_agent = Agent(
            name="mvp_scope_boundaries",
            system_prompt=(
                f"{boundaries_prompt}\n\n"
                "## SWARM INSTRUCTIONS\n"
                "After completing your output, hand off to 'mvp_scope_flows' "
                "with a summary of the IN/OUT scope table and success criteria."
            ),
            model=model,
        )

        flows_prompt = load_agent_prompt("worker_mvp_scope_flows")
        flows_agent = Agent(
            name="mvp_scope_flows",
            system_prompt=(
                f"{flows_prompt}\n\n"
                "## SWARM INSTRUCTIONS\n"
                "You are the final agent. After completing your output, do NOT hand off. "
                "Simply output the core user flows, scope metadata, and consistency check."
            ),
            model=model,
        )

        swarm = Swarm(
            [core_agent, boundaries_agent, flows_agent],
            entry_point=core_agent,
            max_handoffs=3,
            max_iterations=4,
            execution_timeout=600.0,
            node_timeout=300.0,
        )

        task = (
            f"{shared_context}"
            "Define The One Thing, primary user segment, primary input method, and appetite. "
            "Honor all constraints from the Concept Anchor above."
        )

        logger.info("Starting MVP scope swarm...")
        result = swarm(task)

        # Extract outputs from each agent in the node_history
        outputs: list[str] = []
        for node in result.node_history:
            agent_name = node.node_id
            node_result = result.results.get(agent_name)
            if node_result is not None:
                agent_results = node_result.get_agent_results()
                for agent_result in agent_results:
                    text = extract_text_from_result(agent_result)
                    if text.strip():
                        outputs.append(text)
                        logger.info(f"{agent_name} completed ({len(text)} chars)")

        if not outputs:
            logger.error("MVP scope swarm produced no output")
            return "Error: MVP scope swarm produced no output", "failed"

        combined = "\n\n".join(outputs)
        logger.info(
            f"MVP scope swarm completed: {len(outputs)} agents, "
            f"{len(combined)} chars total, status={result.status}"
        )
        return combined, "completed"

    except Exception as e:
        logger.error(f"MVP scope swarm failed: {e}", exc_info=True)
        return f"Error in MVP scope swarm: {e}", "failed"
