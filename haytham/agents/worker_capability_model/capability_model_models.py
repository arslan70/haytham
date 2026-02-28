"""Pydantic models for structured Capability Model output.

These models define the schema for the capability_model agent's output,
ensuring type-safe, validated responses with traceability back to MVP scope items.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CapabilitySummary(BaseModel):
    """High-level summary of the system being modelled."""

    system_name: str = Field(default="", description="Name of the system")
    system_purpose: str = Field(default="", description="One-sentence purpose")
    primary_user_segment: str = Field(
        default="", description="Behavioral description of the primary user segment"
    )
    input_method: str = Field(default="", description="How users provide input (from MVP Scope)")
    mvp_scope_respected: bool = Field(
        default=True,
        description="Whether all capabilities trace to IN SCOPE items",
    )


class FunctionalCapability(BaseModel):
    """A single functional capability tied to an IN SCOPE item."""

    id: str = Field(description="Capability identifier (e.g., 'CAP-F-001')")
    name: str = Field(description="Short name for the capability")
    description: str = Field(description="What users can DO (not how it works)")
    serves_scope_item: str = Field(description="Exact IN SCOPE item this implements")
    user_flow: str = Field(default="", description="Flow reference (e.g., 'Flow 1')")
    acceptance_criteria: list[str] = Field(
        default_factory=list, description="Testable acceptance criteria"
    )
    rationale: str = Field(default="", description="Why essential for MVP")


class NonFunctionalCapability(BaseModel):
    """A single non-functional capability (quality attribute)."""

    id: str = Field(description="Capability identifier (e.g., 'CAP-NF-001')")
    name: str = Field(description="Short name for the quality attribute")
    description: str = Field(default="", description="Quality attribute description")
    category: str = Field(
        default="performance",
        description="Category: performance, security, usability, etc.",
    )
    requirement: str = Field(default="", description="Measurable requirement")
    measurement: str = Field(default="", description="How to verify")
    rationale: str = Field(default="", description="Why critical for this product's success")


class Capabilities(BaseModel):
    """Container for functional and non-functional capabilities."""

    functional: list[FunctionalCapability] = Field(
        default_factory=list, description="Functional capabilities"
    )
    non_functional: list[NonFunctionalCapability] = Field(
        default_factory=list, description="Non-functional capabilities"
    )


class Traceability(BaseModel):
    """Traceability section linking capabilities back to scope items."""

    scope_items_covered: list[str] = Field(
        default_factory=list, description="IN SCOPE items covered by capabilities"
    )
    scope_items_not_covered: list[str] = Field(
        default_factory=list,
        description="IN SCOPE items without capabilities (with explanation)",
    )
    flows_covered: list[str] = Field(default_factory=list, description="User flows covered")


class CapabilityModelMetadata(BaseModel):
    """Counts and metadata for the capability model."""

    functional_count: int = Field(default=0, description="Number of functional capabilities")
    non_functional_count: int = Field(
        default=0, description="Number of non-functional capabilities"
    )


class CapabilityModelOutput(BaseModel):
    """Complete capability model output with traceability to MVP scope.

    This model validates the JSON produced by the capability_model agent,
    ensuring required structure is present before downstream consumption.
    """

    summary: CapabilitySummary = Field(
        default_factory=CapabilitySummary,
        description="High-level system summary",
    )
    capabilities: Capabilities = Field(description="Functional and non-functional capabilities")
    traceability: Traceability = Field(
        default_factory=Traceability,
        description="Scope item and flow traceability",
    )
    metadata: CapabilityModelMetadata = Field(
        default_factory=CapabilityModelMetadata,
        description="Capability counts",
    )
