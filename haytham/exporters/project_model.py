"""Data models for project-level export.

ExportableProject aggregates the full session context for project-level
exporters (OpenSpec, Spec Kit). Story-level exporters continue using
ExportableStory.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from haytham.workflow.contracts.execution_contract import ContractStory


class ExportableCapability(BaseModel):
    """A capability from the capability model, enriched for export."""

    id: str
    name: str
    description: str
    serves_scope_item: str | None = None
    priority: str = "P1"
    is_functional: bool = True
    acceptance_criteria: list[str] = Field(default_factory=list)


class ExportableDecision(BaseModel):
    """An architecture decision, enriched for export."""

    id: str
    title: str
    description: str
    rationale: str
    serves_capabilities: list[str] = Field(default_factory=list)
    implements: str = ""
    alternatives_considered: list[str] = Field(default_factory=list)


class ExportableScopeItem(BaseModel):
    """An MVP scope item with linked capabilities and stories."""

    name: str
    description: str = ""
    capabilities: list[str] = Field(default_factory=list)
    stories: list[str] = Field(default_factory=list)


class ExportableProject(BaseModel):
    """Aggregated session data for project-level exporters.

    Both OpenSpec and Spec Kit exporters consume this model.
    Assembled by assemble_exportable_project() from persisted JSON files.
    """

    # Metadata
    idea_summary: str
    appetite: str = ""
    generated_at: str = ""

    # Phase outputs
    system_traits: dict[str, Any] = Field(default_factory=dict)
    scope_items: list[ExportableScopeItem] = Field(default_factory=list)
    capabilities: list[ExportableCapability] = Field(default_factory=list)
    decisions: list[ExportableDecision] = Field(default_factory=list)
    non_functional_capabilities: list[ExportableCapability] = Field(default_factory=list)
    build_buy: Any = None

    # Stories (from ExecutionContract)
    stories: list[ContractStory] = Field(default_factory=list)
