"""Pydantic models for the Execution Contract.

The Execution Contract is a machine-readable representation of the story
pipeline output, built by deterministic code (not the LLM). Downstream
consumers (coding agent, OpenSpec, Spec Kit) validate against this contract.

See ADR-028 for design rationale and ADR-025 for the complexity constraint.
"""

from pydantic import BaseModel, Field


class AcceptanceCriterion(BaseModel):
    """A single acceptance criterion in structured Gherkin format."""

    id: str
    scenario: str
    given: str = ""
    when: str = ""
    then: str = ""


class ContractMetadata(BaseModel):
    """Top-level metadata about the contract generation context."""

    generated_at: str
    idea_summary: str
    appetite: str = ""


class ContractStory(BaseModel):
    """A single story with structured traceability fields."""

    id: str
    title: str
    layer: int
    summary: str
    implements: list[str] = Field(default_factory=list)
    uses: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    acceptance_criteria: list[AcceptanceCriterion] = Field(default_factory=list)
    content: str = ""


class ExecutionContract(BaseModel):
    """Top-level execution contract for downstream consumers.

    Built deterministically from StoryHybrid output + session state.
    The LLM never produces this directly (ADR-025 complexity constraint).
    """

    schema_version: str = "1.0"
    metadata: ContractMetadata
    system_traits: dict[str, str | list[str]] = Field(default_factory=dict)
    stories: list[ContractStory] = Field(default_factory=list)

    def to_json(self) -> str:
        """Return formatted JSON suitable for writing to disk."""
        return self.model_dump_json(indent=2)
