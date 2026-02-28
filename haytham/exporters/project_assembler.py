"""Assemble an ExportableProject from persisted session JSON files.

Reads structured JSON from the session directory and builds the unified
ExportableProject model consumed by project-level exporters (OpenSpec, Spec Kit).
All transformations are deterministic (no LLM calls).
"""

import json
import logging
from pathlib import Path

from haytham.exporters.project_model import (
    ExportableCapability,
    ExportableDecision,
    ExportableProject,
    ExportableScopeItem,
)
from haytham.workflow.contracts.execution_contract import ExecutionContract

logger = logging.getLogger("haytham")

# Session-relative paths for each JSON file
_CONTRACT_PATH = Path("story-generation") / "execution_contract.json"
_CAPABILITY_PATH = Path("capability-model") / "output.json"
_ARCHITECTURE_PATH = Path("architecture-decisions") / "output.json"
_BUILD_BUY_PATH = Path("build-buy-analysis") / "output.json"


def _load_json(path: Path) -> dict | None:
    """Load and parse a JSON file, returning None if missing or malformed."""
    if not path.exists():
        logger.warning("Expected JSON file not found: %s", path)
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("Malformed JSON in %s, treating as missing", path)
        return None


def _build_capabilities(
    cap_data: dict,
) -> tuple[list[ExportableCapability], list[ExportableCapability]]:
    """Build functional and non-functional ExportableCapability lists from capability model JSON."""
    functional: list[ExportableCapability] = []
    non_functional: list[ExportableCapability] = []

    caps = cap_data.get("capabilities", {})

    for cap in caps.get("functional", []):
        functional.append(
            ExportableCapability(
                id=cap["id"],
                name=cap["name"],
                description=cap.get("description", ""),
                serves_scope_item=cap.get("serves_scope_item"),
                priority=cap.get("priority", "P1"),
                is_functional=True,
                acceptance_criteria=cap.get("acceptance_criteria", []),
            )
        )

    for cap in caps.get("non_functional", []):
        non_functional.append(
            ExportableCapability(
                id=cap["id"],
                name=cap["name"],
                description=cap.get("description") or cap.get("requirement", ""),
                is_functional=False,
                serves_scope_item=None,
                acceptance_criteria=[],
            )
        )

    return functional, non_functional


def _build_decisions(arch_data: dict) -> list[ExportableDecision]:
    """Build ExportableDecision list from architecture decisions JSON."""
    decisions: list[ExportableDecision] = []

    for dec in arch_data.get("decisions", []):
        decisions.append(
            ExportableDecision(
                id=dec["id"],
                title=dec.get("name", ""),
                description=dec.get("description", ""),
                rationale=dec.get("rationale", ""),
                serves_capabilities=dec.get("serves_capabilities", []),
                implements=dec.get("implements_recommendation", ""),
                alternatives_considered=dec.get("alternatives_considered", []),
            )
        )

    return decisions


def _build_scope_items(
    cap_data: dict,
    functional_caps: list[ExportableCapability],
    stories: list,
) -> list[ExportableScopeItem]:
    """Group capabilities and stories by scope item.

    Resolution order for scope item names:
    1. traceability.scope_items_covered (primary, from capability model JSON)
    2. Unique serves_scope_item values across functional capabilities (fallback)

    For each scope item, capability IDs are those where cap.serves_scope_item
    matches the name, and story IDs are those where story.implements contains
    any of those capability IDs. Stories not assigned to any scope item are
    collected into a synthetic "Infrastructure" scope item.
    """
    # 1. Determine scope item names
    traceability = cap_data.get("traceability", {})
    scope_names: list[str] = traceability.get("scope_items_covered", [])

    if not scope_names:
        # Fallback: derive from unique serves_scope_item values
        seen: set[str] = set()
        for cap in functional_caps:
            if cap.serves_scope_item and cap.serves_scope_item not in seen:
                seen.add(cap.serves_scope_item)
                scope_names.append(cap.serves_scope_item)

    # 2. Build scope items with linked caps and stories
    assigned_story_ids: set[str] = set()
    scope_items: list[ExportableScopeItem] = []

    for name in scope_names:
        # Find capabilities for this scope item
        linked_caps = [c for c in functional_caps if c.serves_scope_item == name]
        cap_ids = [c.id for c in linked_caps]

        # Synthesize description from linked capability descriptions
        description = ". ".join(c.description for c in linked_caps if c.description)

        # Find story IDs where story.implements overlaps with cap_ids
        cap_id_set = set(cap_ids)
        story_ids: list[str] = []
        for story in stories:
            impl = story.implements if hasattr(story, "implements") else []
            if cap_id_set & set(impl):
                story_ids.append(story.id)
                assigned_story_ids.add(story.id)

        scope_items.append(
            ExportableScopeItem(
                name=name,
                description=description,
                capabilities=cap_ids,
                stories=story_ids,
            )
        )

    # 3. Orphan stories go into synthetic "Infrastructure" scope item
    orphan_ids = [s.id for s in stories if s.id not in assigned_story_ids]
    if orphan_ids:
        scope_items.append(
            ExportableScopeItem(
                name="Infrastructure",
                capabilities=[],
                stories=orphan_ids,
            )
        )

    return scope_items


def assemble_exportable_project(session_dir: Path) -> ExportableProject:
    """Assemble an ExportableProject from persisted session JSON files.

    Reads:
        - story-generation/execution_contract.json (required)
        - capability-model/output.json (optional)
        - architecture-decisions/output.json (optional)
        - build-buy-analysis/output.json (optional)

    Args:
        session_dir: Path to the session directory (e.g., ``<base>/session``).

    Returns:
        A fully populated ExportableProject.

    Raises:
        FileNotFoundError: If the execution contract JSON is missing.
    """
    # 1. Load execution contract (required)
    contract_path = session_dir / _CONTRACT_PATH
    contract_json = _load_json(contract_path)
    if contract_json is None:
        raise FileNotFoundError(
            f"Execution contract not found at {contract_path}. "
            "Run the story pipeline before exporting."
        )
    contract = ExecutionContract.model_validate(contract_json)

    # 2. Load capability model (optional)
    cap_data = _load_json(session_dir / _CAPABILITY_PATH)
    if cap_data is not None:
        functional_caps, nf_caps = _build_capabilities(cap_data)
    else:
        functional_caps, nf_caps = [], []

    # 3. Load architecture decisions (optional)
    arch_data = _load_json(session_dir / _ARCHITECTURE_PATH)
    decisions = _build_decisions(arch_data) if arch_data is not None else []

    # 4. Load build-buy analysis (optional, passed as raw dict)
    build_buy = _load_json(session_dir / _BUILD_BUY_PATH)

    # 5. Build scope items from capability model traceability
    if cap_data is not None:
        scope_items = _build_scope_items(cap_data, functional_caps, contract.stories)
    else:
        scope_items = []

    # 6. Extract short project name from capability model summary
    project_name = ""
    if cap_data is not None:
        project_name = cap_data.get("summary", {}).get("system_name", "")

    # 7. Assemble the project
    return ExportableProject(
        project_name=project_name,
        idea_summary=contract.metadata.idea_summary,
        appetite=contract.metadata.appetite,
        generated_at=contract.metadata.generated_at,
        system_traits=dict(contract.system_traits),
        scope_items=scope_items,
        capabilities=functional_caps,
        decisions=decisions,
        non_functional_capabilities=nf_caps,
        build_buy=build_buy,
        stories=list(contract.stories),
    )
