"""Domain-agnostic anchor schema for drift prevention in multi-agent pipelines.

The anchor pattern extracts a small, structured, immutable artifact from the original
input that bypasses the agent chain entirely. This artifact is passed to every agent
unchanged, as a constraint they must honor.

See ADR-022 for the full design rationale.
"""

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Default Founder Persona (ADR-023)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FounderPersona:
    """Default founder profile when no explicit one is provided.

    Injected into scorer and validator context so that Execution Feasibility
    and operational risk claims can reference realistic founder constraints.
    """

    age_range: str = "30-40"
    technical_literacy: str = (
        "High — comfortable with modern tech, can evaluate technical tradeoffs"
    )
    domain_expertise: str = "Unknown — not stated in the idea description"
    capital: str = "Some spare capital for bootstrapping; not VC-backed"
    team: str = "Solo founder; open to hiring if the idea validates"
    risk_appetite: str = "Moderate — needs early validation signals before full commitment"
    time_commitment: str = "Part-time initially, full-time if traction emerges"

    def to_context(self) -> str:
        """Format persona for inclusion in agent context."""
        return (
            "## Founder Context\n\n"
            "Default assumed profile (no explicit founder info provided):\n\n"
            f"- **Age range:** {self.age_range}\n"
            f"- **Technical literacy:** {self.technical_literacy}\n"
            f"- **Domain expertise:** {self.domain_expertise}\n"
            f"- **Capital:** {self.capital}\n"
            f"- **Team:** {self.team}\n"
            f"- **Risk appetite:** {self.risk_appetite}\n"
            f"- **Time commitment:** {self.time_commitment}\n"
        )


class IdeaArchetype(StrEnum):
    """Product archetype for calibrating downstream analysis."""

    consumer_app = "consumer_app"
    b2b_saas = "b2b_saas"
    marketplace = "marketplace"
    developer_tool = "developer_tool"
    internal_tool = "internal_tool"
    other = "other"

    @property
    def display_name(self) -> str:
        """Human-readable display name."""
        names = {
            "consumer_app": "Consumer App",
            "b2b_saas": "B2B SaaS",
            "marketplace": "Marketplace",
            "developer_tool": "Developer Tool",
            "internal_tool": "Internal Tool",
            "other": "Other",
        }
        return names.get(self.value, self.value)


class Invariant(BaseModel):
    """A property that must be true in every downstream agent's output."""

    property: str = Field(description="Name of the invariant (e.g., 'group_structure')")
    value: str = Field(description="The required value or condition")
    source: str = Field(description="Exact quote or paraphrase from the original input")
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence in this extraction (0-1). Low confidence (<0.7) means ambiguous.",
    )
    ambiguity: str | None = Field(
        default=None,
        description="If confidence < 0.7, explain what's ambiguous and what clarification is needed.",
    )
    clarification_options: list[str] | None = Field(
        default=None,
        description="If ambiguous, list 2-3 concrete options for the user to choose from.",
    )


class IdentityFeature(BaseModel):
    """What makes this input different from the generic/default case."""

    feature: str = Field(description="The distinctive element")
    why_distinctive: str = Field(
        description="Why an LLM is likely to genericize this into a common pattern"
    )


class Intent(BaseModel):
    """What the user said, distilled to core constraints."""

    goal: str = Field(description="One sentence describing the user's actual ask")
    explicit_constraints: list[str] = Field(
        default_factory=list,
        description="Things the user explicitly stated or implied as requirements",
    )
    non_goals: list[str] = Field(
        default_factory=list,
        description="Things the user did NOT ask for (inferred from constraints)",
    )


class ConceptHealth(BaseModel):
    """Health signals from concept expansion — surfaces idea weaknesses early.

    These are self-assessed by the concept expansion agent and propagated
    unchanged to downstream stages (especially risk assessment).
    """

    pain_clarity: str = Field(
        default="",
        description="Clear | Ambiguous | Weak — is there a specific pain users actively solve today?",
    )
    trigger_strength: str = Field(
        default="",
        description="Strong | Moderate | Weak — would users reach for this at a recurring moment?",
    )
    willingness_to_pay: str = Field(
        default="",
        description="Present | Unclear | Absent — evidence users would pay?",
    )
    notes: str = Field(
        default="",
        description="Brief explanation when signals are weak (e.g., 'aspiration-driven, not pain-driven')",
    )


class ConceptAnchor(BaseModel):
    """Structured anchor for concept fidelity in multi-agent pipelines.

    The anchor has three properties that make it effective:
    1. Small and fixed-size (~300-500 tokens regardless of pipeline complexity)
    2. Immutable - no downstream agent modifies the anchor
    3. Extractable by a focused LLM call

    The three sections serve different enforcement purposes:
    - intent: Prevents scope expansion
    - invariants: Prevents constraint loss
    - identity: Prevents genericization
    - concept_health: Surfaces idea weaknesses for downstream risk analysis
    """

    intent: Intent = Field(description="Core intent distilled from the original input")
    invariants: list[Invariant] = Field(
        default_factory=list,
        description="Properties that must remain true across all pipeline stages",
    )
    identity: list[IdentityFeature] = Field(
        default_factory=list,
        description="Distinctive features that differentiate this from generic solutions",
    )
    archetype: IdeaArchetype | None = Field(
        default=None,
        description="Product archetype for calibrating downstream analysis (e.g., marketplace, b2b_saas)",
    )
    concept_health: ConceptHealth | None = Field(
        default=None,
        description="Health signals from concept expansion (pain clarity, trigger strength, willingness to pay)",
    )

    def to_context_string(self) -> str:
        """Format anchor for inclusion in agent context."""
        lines = ["## Concept Anchor (MUST HONOR)", ""]

        # Intent section
        lines.append("### Intent")
        lines.append(f"**Goal:** {self.intent.goal}")
        if self.intent.explicit_constraints:
            lines.append("\n**Explicit Constraints:**")
            for constraint in self.intent.explicit_constraints:
                lines.append(f"- {constraint}")
        if self.intent.non_goals:
            lines.append("\n**Non-Goals (do NOT add these):**")
            for non_goal in self.intent.non_goals:
                lines.append(f"- {non_goal}")

        # Archetype section
        if self.archetype:
            lines.append("\n### Product Archetype")
            lines.append(f"**Type:** {self.archetype.display_name}")

        # Invariants section
        if self.invariants:
            lines.append("\n### Invariants (MUST preserve)")
            for inv in self.invariants:
                lines.append(f"- **{inv.property}**: {inv.value}")
                lines.append(f'  - Source: "{inv.source}"')

        # Identity section
        if self.identity:
            lines.append("\n### Identity Features (do NOT genericize)")
            for feat in self.identity:
                lines.append(f"- **{feat.feature}**")
                lines.append(f"  - Risk: {feat.why_distinctive}")

        # Health signals section
        if self.concept_health and (
            self.concept_health.pain_clarity or self.concept_health.trigger_strength
        ):
            lines.append("\n### Concept Health Signals (from idea analysis)")
            if self.concept_health.pain_clarity:
                lines.append(f"- **Pain Clarity:** {self.concept_health.pain_clarity}")
            if self.concept_health.trigger_strength:
                lines.append(f"- **Trigger Strength:** {self.concept_health.trigger_strength}")
            if self.concept_health.willingness_to_pay:
                lines.append(f"- **Willingness to Pay:** {self.concept_health.willingness_to_pay}")
            if self.concept_health.notes:
                lines.append(f"- **Note:** {self.concept_health.notes}")

        return "\n".join(lines)


class InvariantOverride(BaseModel):
    """Explicit override of an anchor invariant with justification."""

    invariant: str = Field(description="Which invariant property is being overridden")
    reason: str = Field(description="Why the override is necessary")
    user_impact: str = Field(description="What the user should know about this change")


class AnchorComplianceReport(BaseModel):
    """Self-reported compliance with the concept anchor.

    Note: This is self-reported by agents. Phase-boundary verifiers independently
    validate these claims against the actual output content.
    """

    invariants_preserved: list[str] = Field(
        default_factory=list, description="Invariant property names that were honored"
    )
    invariants_overridden: list[InvariantOverride] = Field(
        default_factory=list,
        description="Invariants that were deliberately overridden with justification",
    )
    identity_features_preserved: list[str] = Field(
        default_factory=list, description="Identity features that remain in output"
    )
    identity_features_genericized: list[str] = Field(
        default_factory=list,
        description="Identity features that were genericized (should be empty or justified)",
    )
