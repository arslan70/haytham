"""MVP-specification phase orchestration (WHAT).

Functions used by mvp-scope, capability-model, and system-traits stage configs.
"""

import json
import logging
import re
from typing import Any

from burr.core import State

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# MVP Scope chain executor (3 sub-agents: core → boundaries → flows)
# ---------------------------------------------------------------------------


def run_mvp_scope_chain(state: State) -> tuple[str, str]:
    """Run the MVP scope stage as a chain of 3 focused sub-agents.

    Sub-agent chain:
    1. mvp_scope_core: The One Thing, user segment, input method, appetite
    2. mvp_scope_boundaries: IN/OUT scope table, success criteria
    3. mvp_scope_flows: Core user flows, scope metadata, consistency check

    Each subsequent agent receives the output of previous agents as context.
    ADR-022: All sub-agents receive the concept anchor to prevent drift.

    Returns:
        Tuple of (combined_output, status) where status is "completed" or "failed".
    """
    from haytham.agents.factory.agent_factory import create_agent_by_name
    from haytham.agents.output_utils import extract_text_from_result
    from haytham.workflow.context_builder import render_validation_summary_from_json
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

    # Debug: Log anchor presence
    if anchor_context:
        logger.info(
            f"ADR-022: Anchor loaded ({len(anchor_context)} chars), first 200: {anchor_context[:200]}"
        )
    else:
        logger.warning("ADR-022: NO ANCHOR CONTEXT - scope may drift from original intent!")

    outputs: list[str] = []

    # --- Sub-agent 1: Core ---
    try:
        core_agent = create_agent_by_name("mvp_scope_core")
        # ADR-022: Include anchor at the TOP so agent sees constraints first
        anchor_section = f"{anchor_context}\n\n---\n\n" if anchor_context else ""
        core_context = (
            f"{anchor_section}"
            f"## Startup Idea\n{system_goal}\n\n"
            f"## Concept Analysis\n{idea_analysis[:2000]}\n\n"
            f"## Validation Summary\n{validation_summary[:2000]}\n\n"
            "Define The One Thing, primary user segment, primary input method, and appetite. "
            "Honor all constraints from the Concept Anchor above."
        )
        core_result = core_agent(core_context)
        core_output = extract_text_from_result(core_result)
        outputs.append(core_output)
        logger.info(f"mvp_scope_core completed ({len(core_output)} chars)")
    except Exception as e:
        logger.error(f"mvp_scope_core failed: {e}", exc_info=True)
        return f"Error in mvp_scope_core: {e}", "failed"

    # --- Sub-agent 2: Boundaries ---
    try:
        boundaries_agent = create_agent_by_name("mvp_scope_boundaries")
        # ADR-022: Include anchor - non-goals inform OUT scope
        boundaries_context = (
            f"{anchor_section}"
            f"## Startup Idea\n{system_goal}\n\n"
            f"## Core MVP Identity (from previous agent)\n{core_output}\n\n"
            "Define MVP boundaries (IN/OUT scope table) and success criteria. "
            "Non-Goals from the Concept Anchor MUST appear in OUT scope."
        )
        boundaries_result = boundaries_agent(boundaries_context)
        boundaries_output = extract_text_from_result(boundaries_result)
        outputs.append(boundaries_output)
        logger.info(f"mvp_scope_boundaries completed ({len(boundaries_output)} chars)")
    except Exception as e:
        logger.error(f"mvp_scope_boundaries failed: {e}", exc_info=True)
        # Return partial output from core + error
        partial = core_output + f"\n\nError in mvp_scope_boundaries: {e}"
        return partial, "failed"

    # --- Sub-agent 3: Flows ---
    try:
        flows_agent = create_agent_by_name("mvp_scope_flows")
        # ADR-022: Include anchor - identity features inform user flows
        flows_context = (
            f"{anchor_section}"
            f"## Startup Idea\n{system_goal}\n\n"
            f"## Core MVP Identity\n{core_output}\n\n"
            f"## MVP Boundaries & Success Criteria\n{boundaries_output}\n\n"
            "Define core user flows, scope metadata, and run the internal consistency check. "
            "User flows must reflect Identity Features from the Concept Anchor."
        )
        flows_result = flows_agent(flows_context)
        flows_output = extract_text_from_result(flows_result)
        outputs.append(flows_output)
        logger.info(f"mvp_scope_flows completed ({len(flows_output)} chars)")
    except Exception as e:
        logger.error(f"mvp_scope_flows failed: {e}", exc_info=True)
        # Return partial output from core + boundaries + error
        partial = "\n\n".join(outputs) + f"\n\nError in mvp_scope_flows: {e}"
        return partial, "failed"

    # Concatenate all outputs
    combined = "\n\n".join(outputs)
    logger.info(f"mvp_scope chain completed ({len(combined)} chars total)")
    return combined, "completed"


# ---------------------------------------------------------------------------
# Agent factories
# ---------------------------------------------------------------------------


def create_mvp_scope_agent():
    """Factory for MVP scope agent."""
    from haytham.agents.factory.agent_factory import create_agent_by_name

    return create_agent_by_name("mvp_scope")


def create_capability_model_agent():
    """Factory for capability model agent."""
    from haytham.agents.factory.agent_factory import create_agent_by_name

    return create_agent_by_name("capability_model")


def create_system_traits_agent():
    """Factory for system traits agent."""
    from haytham.agents.factory.agent_factory import create_agent_by_name

    return create_agent_by_name("system_traits")


# ---------------------------------------------------------------------------
# Custom context builders (eliminate _execute_custom_agent if/elif branching)
# ---------------------------------------------------------------------------


def build_mvp_scope_context(state: State) -> dict[str, Any]:
    """Build context for the MVP scope agent.

    Returns a dict with ``_context_str`` — the fully-formatted prompt string
    ready for the custom agent.
    """
    system_goal = state["system_goal"]
    idea_analysis = state.get("idea_analysis", "")
    raw_vs = state.get("validation_summary", "")

    context_str = f"## Startup Idea\n{system_goal}\n\n"
    context_str += f"## Concept Analysis\n{idea_analysis[:2000]}\n\n"

    # Parse validation_summary — may be JSON (from output_model) or markdown (legacy)
    from haytham.workflow.context_builder import render_validation_summary_from_json

    try:
        context_str += (
            f"## Validation Summary\n{render_validation_summary_from_json(json.loads(raw_vs))}\n\n"
        )
    except (json.JSONDecodeError, TypeError):
        context_str += f"## Validation Summary\n{raw_vs[:2000]}\n\n"

    return {"system_goal": system_goal, "_context_str": context_str}


def build_capability_model_context(state: State) -> dict[str, Any]:
    """Build context for the capability model agent.

    Returns a dict with ``_context_str`` — the fully-formatted prompt string
    ready for the custom agent.  Returns ``_error`` if required data is missing.

    ADR-022: Includes concept anchor to prevent capability drift.
    """
    from haytham.workflow.stages.concept_anchor import get_anchor_context_string

    system_goal = state["system_goal"]
    mvp_scope = state.get("mvp_scope", "")

    if not mvp_scope:
        return {
            "system_goal": system_goal,
            "_error": "Error: MVP Scope not found - cannot generate capability model",
        }

    # ADR-022: Get anchor for capability alignment
    anchor_context = get_anchor_context_string(state)

    # Build context with anchor at the top
    context_str = ""
    if anchor_context:
        context_str += f"{anchor_context}\n\n---\n\n"

    context_str += f"## Startup Idea\n{system_goal}\n\n"
    context_str += f"## MVP Scope (PRIMARY INPUT - trace all capabilities to this)\n{mvp_scope}\n\n"
    context_str += "IMPORTANT: Your capabilities MUST trace to the IN SCOPE items listed above. "
    context_str += "Do NOT invent scope items. Quote actual IN SCOPE items in serves_scope_item. "
    context_str += "Capabilities must honor the Invariants from the Concept Anchor above.\n"

    return {"system_goal": system_goal, "_context_str": context_str}


def build_system_traits_context(state: State) -> dict[str, Any]:
    """Build context for the system traits agent.

    Returns a dict with ``_context_str`` — the fully-formatted prompt string
    ready for the custom agent.  Returns ``_error`` if required data is missing.

    ADR-022: Includes concept anchor - invariants inform trait classification.
    """
    from haytham.workflow.stages.concept_anchor import get_anchor_context_string

    system_goal = state["system_goal"]
    idea_analysis = state.get("idea_analysis", "")
    mvp_scope = state.get("mvp_scope", "")
    capability_model = state.get("capability_model", "")

    if not capability_model:
        return {
            "system_goal": system_goal,
            "_error": "Error: Capability Model not found - cannot classify system traits",
        }

    # ADR-022: Get anchor for trait alignment
    anchor_context = get_anchor_context_string(state)

    # Build context with anchor at the top
    context_str = ""
    if anchor_context:
        context_str += f"{anchor_context}\n\n---\n\n"

    context_str += f"## Startup Idea\n{system_goal}\n\n"
    if idea_analysis:
        context_str += f"## Idea Analysis\n{idea_analysis[:2000]}\n\n"
    if mvp_scope:
        context_str += f"## MVP Scope\n{mvp_scope}\n\n"
    context_str += f"## Capability Model\n{capability_model}\n\n"
    context_str += (
        "Classify the system traits based on the above context. "
        "Traits must align with the Invariants from the Concept Anchor "
        "(e.g., if anchor says 'closed community', auth should reflect that).\n"
    )

    return {"system_goal": system_goal, "_context_str": context_str}


# ---------------------------------------------------------------------------
# Post-processors / additional-save helpers
# ---------------------------------------------------------------------------


def extract_json_from_output(output: str) -> str:
    """Extract JSON from agent output that may contain markdown code blocks.

    Note: Returns the raw JSON *string* (not parsed dict) for backward compat.
    """
    from haytham.agents.output_utils import extract_json_from_text

    parsed = extract_json_from_text(output)
    if parsed is not None:
        return json.dumps(parsed)
    return output


def store_capabilities_in_vector_db(session_manager: Any, output: str) -> None:
    """Store capability model output in the vector database.

    This function parses the JSON capability model output and stores
    each capability in the vector DB using StateWriterAgent.

    Per ADR-004: System State Implementation.
    """
    if session_manager is None:
        logger.warning("No session manager - skipping vector DB storage")
        return

    try:
        # Parse JSON from output
        json_str = extract_json_from_output(output)
        capability_data = json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.warning(f"Could not parse capability model JSON: {e}")
        logger.info("Capabilities will not be stored in vector DB")
        return

    try:
        # Import state infrastructure
        from haytham.agents.state_writer.state_writer_agent import StateWriterAgent
        from haytham.state import DuplicateEntryError, SystemStateDB, get_embedder

        # Initialize vector DB
        db_path = session_manager.session_dir / "vector_db"
        embedder = get_embedder()
        db = SystemStateDB(db_path, embedder=embedder)
        writer = StateWriterAgent(db)

        stored_ids = []
        skipped_count = 0

        # Store functional capabilities
        for cap in capability_data.get("capabilities", {}).get("functional", []):
            try:
                cap_id = writer.create_functional_capability(
                    name=cap.get("name", ""),
                    description=cap.get("description", ""),
                    source_stage="capability-model",
                    rationale=cap.get("rationale"),
                    acceptance_criteria=cap.get("acceptance_criteria"),
                    user_segment=capability_data.get("summary", {}).get("primary_user_segment"),
                )
                stored_ids.append(cap_id)
                logger.info(f"Stored functional capability: {cap_id}")
            except DuplicateEntryError:
                logger.info(f"Skipping existing capability: {cap.get('name', '')}")
                skipped_count += 1

        # Store non-functional capabilities
        for cap in capability_data.get("capabilities", {}).get("non_functional", []):
            try:
                cap_id = writer.create_non_functional_capability(
                    name=cap.get("name", ""),
                    description=cap.get("description", ""),
                    category=cap.get("category", "performance"),
                    requirement=cap.get("requirement", ""),
                    source_stage="capability-model",
                    rationale=cap.get("rationale"),
                    measurement=cap.get("measurement"),
                )
                stored_ids.append(cap_id)
                logger.info(f"Stored non-functional capability: {cap_id}")
            except DuplicateEntryError:
                logger.info(f"Skipping existing capability: {cap.get('name', '')}")
                skipped_count += 1

        logger.info(f"Stored {len(stored_ids)} capabilities in vector DB: {stored_ids}")
        if skipped_count > 0:
            logger.info(f"Skipped {skipped_count} existing capabilities (idempotent)")

    except ImportError as e:
        logger.warning(f"State infrastructure not available: {e}")
    except Exception as e:
        logger.error(f"Failed to store capabilities in vector DB: {e}", exc_info=True)


def extract_system_traits_processor(output: str, state: State) -> dict[str, Any]:
    """Post-processor to extract system traits from agent output.

    Primary path: parse from structured output JSON (SystemTraitsOutput).
    Fallback: regex from markdown (legacy sessions or non-structured agents).

    Runs cross-trait validation (warning rules from ADR-019) either way.

    Returns dict with:
    - system_traits_parsed: dict of trait name -> value(s)
    - system_traits_warnings: list of warning strings
    """
    traits: dict[str, Any] = {}
    warnings: list[str] = []

    # Primary path: try to parse as SystemTraitsOutput JSON
    parsed_from_json = False
    try:
        data = json.loads(output)
        from haytham.agents.worker_system_traits.system_traits_models import (
            SystemTraitsOutput,
        )

        model = SystemTraitsOutput.model_validate(data)
        traits = model.to_traits_dict()
        parsed_from_json = True
        logger.info("System traits parsed from structured output JSON")
    except (json.JSONDecodeError, TypeError, Exception):
        pass

    # Fallback: regex from markdown output
    if not parsed_from_json:
        trait_pattern = re.compile(r"\*\*(\w+):\*\*\s*(.+?)(?:\n|$)", re.IGNORECASE)

        for match in trait_pattern.finditer(output):
            trait_name = match.group(1).strip().lower()
            raw_value = match.group(2).strip()

            # Parse multi-select (bracket notation)
            bracket_match = re.match(r"\[(.+?)\]", raw_value)
            if bracket_match:
                values = [v.strip() for v in bracket_match.group(1).split(",")]
                traits[trait_name] = values
            else:
                # Single value - strip any trailing "(ambiguous)" marker
                clean_value = re.sub(r"\s*\(ambiguous\)\s*$", "", raw_value).strip()
                traits[trait_name] = clean_value

    # Cross-trait validation rules (from ADR-019)
    interface = traits.get("interface", [])
    if isinstance(interface, str):
        interface = [interface]

    auth = traits.get("auth", "")
    deployment = traits.get("deployment", [])
    if isinstance(deployment, str):
        deployment = [deployment]

    data_layer = traits.get("data_layer", "")
    realtime = traits.get("realtime", "")

    # Rule 1: No UI + multi_user auth is unusual
    if "none" in interface and auth == "multi_user":
        warnings.append(
            "No user interface but multi_user auth detected — "
            "headless services typically use API keys, not user accounts."
        )

    # Rule 2: terminal-only + realtime is unusual
    if interface == ["terminal"] and realtime == "true":
        warnings.append(
            "Terminal interface with realtime requirement — "
            "ensure the CLI supports streaming output or watch mode."
        )

    # Rule 3: api_only + remote_db without cloud_hosted
    if "api_only" in interface and data_layer == "remote_db" and "cloud_hosted" not in deployment:
        warnings.append(
            "API-only service with remote DB but no cloud_hosted deployment — "
            "consider whether cloud hosting is needed."
        )

    # Rule 4: package_registry deployment without terminal or none interface
    if "package_registry" in deployment and not any(
        i in interface for i in ["terminal", "none", "api_only"]
    ):
        warnings.append(
            "Package registry deployment with browser/GUI interface — "
            "packages are typically CLI tools or libraries."
        )

    # New trait validation rules
    communication = traits.get("communication", "none")
    payments = traits.get("payments", "none")
    scheduling = traits.get("scheduling", "none")

    # Rule 5: video/audio communication requires realtime
    if communication in ["video", "audio"] and realtime != "true":
        warnings.append(
            f"communication: {communication} typically requires realtime: true — "
            "video/audio calls need real-time infrastructure."
        )

    # Rule 6: video communication with terminal interface is unusual
    if communication == "video" and interface == ["terminal"]:
        warnings.append(
            "Video communication with terminal-only interface is unusual — "
            "video typically requires a browser or native app."
        )

    # Rule 7: payments without multi_user auth
    if payments in ["required", "optional"] and auth != "multi_user":
        warnings.append(
            f"payments: {payments} typically requires auth: multi_user — "
            "payment processing needs user accounts for transaction records."
        )

    # Rule 8: scheduling without remote_db
    if scheduling == "required" and data_layer not in ["remote_db"]:
        warnings.append(
            "scheduling: required typically needs data_layer: remote_db — "
            "appointment data should persist in a cloud database."
        )

    if warnings:
        logger.info(f"System traits cross-validation warnings: {warnings}")

    # ADR-022 Part 2b: Extract constraints for downstream validation
    from haytham.workflow.validators.trait_propagation import extract_constraints

    anchor_str = state.get("concept_anchor_str", "")
    constraints = extract_constraints(output, anchor_str)
    logger.info(
        f"Extracted constraints: realtime={constraints.realtime}, auth={constraints.authentication}"
    )

    return {
        "system_traits_parsed": traits,
        "system_traits_warnings": warnings,
        "constraints": constraints.to_dict(),  # ADR-022: For downstream validation
    }
