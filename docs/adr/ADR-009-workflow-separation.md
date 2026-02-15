# ADR-009: Workflow Separation — Validation, MVP Specification, and Story Generation

## Status
**Proposed** — 2026-01-16

## Context

### Current State

ADR-004 defined a multi-phase workflow architecture with two main workflows:

```
┌─────────────────────────────────────────────────────────────────┐
│ CURRENT: Workflow 1 (Discovery & Validation)                    │
├─────────────────────────────────────────────────────────────────┤
│ idea_analysis → market_context → risk_assessment →              │
│ [pivot_strategy] → validation_summary → mvp_scope →             │
│                                         capability_model        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ CURRENT: Workflow 2 (Technical Translation)                     │
├─────────────────────────────────────────────────────────────────┤
│ architecture_decisions → component_boundaries →                 │
│ story_generation → story_validation → dependency_ordering       │
└─────────────────────────────────────────────────────────────────┘
```

### The Problem

Workflow 1 is too large. It conflates two distinct user intents:

| Intent | Question | Current Stages |
|--------|----------|----------------|
| **Validation** | "Is this idea worth pursuing?" | 1-4 (idea → validation_summary) |
| **Specification** | "What should we build?" | 5-6 (mvp_scope → capability_model) |

**Issues with the current design:**

1. **Forced commitment** — Users must complete MVP specification even if they just want to validate an idea
2. **Long feedback loop** — ~15-20 minutes before getting a GO/NO-GO answer
3. **Wrong decision point** — Users should decide whether to proceed BEFORE defining MVP scope
4. **Mixed personas** — Entrepreneurs exploring ideas don't need capability models
5. **Wasted computation** — Generating MVP specs for ideas that will be rejected

### User Personas and Their Needs

| Persona | Primary Need | Current Pain |
|---------|--------------|--------------|
| **Entrepreneur exploring** | "Is this idea viable?" | Must wait through MVP spec |
| **Founder ready to build** | "What exactly should I build?" | Must re-run validation |
| **Investor evaluating** | "Should I fund this?" | Only needs validation |
| **Technical founder** | "Give me stories to implement" | Needs all three |

---

## Decision

### Split into Three Focused Workflows

We will restructure the system into three separate, focused workflows with clear decision gates between them.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      PROPOSED: THREE-WORKFLOW ARCHITECTURE                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ WORKFLOW 1: IDEA VALIDATION                                         │   │
│  │ Role: Product Owner / Entrepreneur                                  │   │
│  │ Question: "Is this idea worth pursuing?"                            │   │
│  │ Duration: ~5 minutes                                                │   │
│  │                                                                     │   │
│  │ idea_analysis → market_context → risk_assessment →                  │   │
│  │                 [pivot_strategy] → validation_summary               │   │
│  │                                                                     │   │
│  │ OUTPUT: GO / NO-GO / PIVOT recommendation                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                          │                                  │
│                              ┌───────────┴───────────┐                      │
│                              │    DECISION GATE 1    │                      │
│                              │  Proceed to MVP Spec? │                      │
│                              │   [Yes] [No] [Pivot]  │                      │
│                              └───────────┬───────────┘                      │
│                                          │                                  │
│                                          ▼                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ WORKFLOW 2: MVP SPECIFICATION                                       │   │
│  │ Role: Product Manager / Business Analyst                            │   │
│  │ Question: "What should we build first?"                             │   │
│  │ Duration: ~5 minutes                                                │   │
│  │                                                                     │   │
│  │ mvp_scope → capability_model                                        │   │
│  │                                                                     │   │
│  │ OUTPUT: MVP boundaries + Capability model (CAP-F-*, CAP-NF-*)       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                          │                                  │
│                              ┌───────────┴───────────┐                      │
│                              │    DECISION GATE 2    │                      │
│                              │ Proceed to Stories?   │                      │
│                              │     [Yes] [Refine]    │                      │
│                              └───────────┬───────────┘                      │
│                                          │                                  │
│                                          ▼                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ WORKFLOW 3: STORY GENERATION                                        │   │
│  │ Role: Software Architect                                            │   │
│  │ Question: "How do we implement these capabilities?"                 │   │
│  │ Duration: ~5-10 minutes                                             │   │
│  │                                                                     │   │
│  │ architecture_decisions → story_generation →                         │   │
│  │ story_validation → dependency_ordering                              │   │
│  │                                                                     │   │
│  │ OUTPUT: Ordered stories in Backlog.md with traceability labels      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                          │                                  │
│                              ┌───────────┴───────────┐                      │
│                              │    DECISION GATE 3    │                      │
│                              │    Start Building?    │                      │
│                              │   [Yes] [Evaluate]    │                      │
│                              └───────────┬───────────┘                      │
│                                          │                                  │
│                                          ▼                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ WORKFLOW 4: IMPLEMENTATION (External)                               │   │
│  │ Handoff to coding agents (Claude Code, Cursor, etc.)                │   │
│  │ [Unchanged from ADR-004]                                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Workflow Definitions

#### Workflow 1: Idea Validation

**Purpose:** Answer "Is this idea worth pursuing?" with a clear recommendation.

**Role:** Product Owner / Entrepreneur

**Duration:** ~5 minutes

| Stage | Agent(s) | Output |
|-------|----------|--------|
| 1. Idea Analysis | concept_expansion | Problem, users, UVP, initial business indicators |
| 2. Market Context | market_intelligence, competitor_analysis (parallel) | Market size, trends, competitive landscape |
| 3. Risk Assessment | startup_validator | Validated claims, risk score, mitigation strategies |
| 3b. Pivot Strategy | pivot_strategy (conditional: if HIGH risk) | Alternative directions |
| 4. Validation Summary | validation_summary | GO / NO-GO / PIVOT recommendation |

**Exit Artifact:** Validation Report with clear recommendation

**Decision Gate Options:**
- **Proceed** → Start Workflow 2 (MVP Specification)
- **Pivot** → Re-run Workflow 1 with modified idea
- **Stop** → End session, download report

---

#### Workflow 2: MVP Specification

**Purpose:** Define what to build first — boundaries, constraints, and capabilities.

**Role:** Product Manager / Business Analyst

**Duration:** ~5 minutes

**Entry Conditions:**
- Workflow 1 completed with GO or PIVOT+GO recommendation
- Validation summary exists

| Stage | Agent(s) | Output |
|-------|----------|--------|
| 1. MVP Scope | mvp_scope | The One Thing, boundaries (in/out), success criteria, core flows |
| 2. Capability Model | capability_model | Functional capabilities (CAP-F-*), Non-functional capabilities (CAP-NF-*) |

**Exit Artifact:**
- MVP Scope document
- Capabilities stored in VectorDB

**Decision Gate Options:**
- **Proceed** → Start Workflow 3 (Story Generation)
- **Refine** → Adjust MVP scope, re-run capability model
- **Download** → Export MVP specification

---

#### Workflow 3: Story Generation

**Purpose:** Translate capabilities into implementable, dependency-ordered stories.

**Role:** Software Architect

**Duration:** ~5-10 minutes

**Entry Conditions:**
- Workflow 2 completed
- At least 1 functional capability in VectorDB
- MVP Scope document exists

| Stage | Agent(s) | Output |
|-------|----------|--------|
| 1. Architecture Decisions | architecture_decisions | Key technical decisions (DEC-*) |
| 2. Story Generation | story_generation | Stories with `implements:CAP-*` labels |
| 3. Story Validation | story_validation | Validated stories (non-blocking per ADR-005) |
| 4. Dependency Ordering | dependency_ordering | Ordered draft tasks in Backlog.md |

**Exit Artifact:** Ordered stories in Backlog.md with full traceability

**Decision Gate Options:**
- **Start Building** → Handoff to coding agents (Workflow 4)
- **Evaluate** → Run AI Judge evaluation (per ADR-005/ADR-006)
- **Refine** → Return to Workflow 2 to adjust capabilities

---

### Design Rationale

#### Why Three Workflows Instead of Two?

| Factor | Two Workflows (Current) | Three Workflows (Proposed) |
|--------|------------------------|---------------------------|
| **Feedback speed** | 15-20 min to validation | 5 min to validation |
| **Decision points** | 1 gate (after everything) | 3 gates (natural pauses) |
| **User control** | All or nothing | Incremental commitment |
| **Wasted work** | MVP spec for rejected ideas | Only validate first |
| **Persona fit** | One size fits all | Right depth for each need |

#### Why Separate MVP Specification from Story Generation?

These answer different questions for different roles:

| Workflow | Question | Role | Artifact |
|----------|----------|------|----------|
| MVP Specification | "What should we build?" | Product Manager | Capability model |
| Story Generation | "How should we build it?" | Software Architect | Implementation stories |

A Product Manager may want to iterate on MVP scope without generating stories. A Software Architect may want to regenerate stories for the same capabilities.

---

### State Handoff Between Workflows

```
┌─────────────────────────────────────────────────────────────────┐
│                     STATE FLOW                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Workflow 1 outputs:                                            │
│  └─► session/idea-analysis/concept_expansion.md                 │
│  └─► session/market-context/market_intelligence.md              │
│  └─► session/market-context/competitor_analysis.md              │
│  └─► session/risk-assessment/startup_validator.md               │
│  └─► session/validation-summary/validation_summary.md           │
│                                                                 │
│  Workflow 2 reads: All Workflow 1 outputs                       │
│  Workflow 2 outputs:                                            │
│  └─► session/mvp-scope/mvp_scope.md                             │
│  └─► session/capability-model/capability_model.md               │
│  └─► VectorDB: CAP-F-*, CAP-NF-* entries                        │
│                                                                 │
│  Workflow 3 reads: VectorDB capabilities + MVP scope            │
│  Workflow 3 outputs:                                            │
│  └─► VectorDB: DEC-* entries                                    │
│  └─► Backlog.md: Ordered stories with labels                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### User Experience

#### Workflow 1 Completion UI

```
┌─────────────────────────────────────────────────────────────────┐
│  ✅ IDEA VALIDATION COMPLETE                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ## Recommendation: GO ✅                                       │
│                                                                 │
│  Your idea shows strong potential:                              │
│  • Market size: $2.3B and growing                               │
│  • Competition: Moderate (3 direct competitors)                 │
│  • Risk level: MEDIUM (2 critical risks identified)             │
│                                                                 │
│  ### Key Insights                                               │
│  • Strong problem-solution fit for target segment               │
│  • Differentiation opportunity in [specific area]               │
│  • Primary risk: [risk summary]                                 │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  [🚀 Define MVP]  [📄 Download Report]  [🔄 Try Different Idea] │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Workflow 2 Completion UI

```
┌─────────────────────────────────────────────────────────────────┐
│  ✅ MVP SPECIFICATION COMPLETE                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ## The One Thing                                               │
│  [Core value proposition summary]                               │
│                                                                 │
│  ## Capabilities Defined                                        │
│  • 4 Functional capabilities (CAP-F-001 to CAP-F-004)           │
│  • 2 Non-functional capabilities (CAP-NF-001, CAP-NF-002)       │
│                                                                 │
│  ## MVP Boundaries                                              │
│  ✅ In scope: [summary]                                         │
│  ❌ Out of scope: [summary]                                     │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  [🏗️ Generate Stories]  [📄 Download Spec]  [✏️ Refine Scope]  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### Mini-Product Opportunities

This separation enables standalone products:

| Product | Workflows Used | Target User |
|---------|---------------|-------------|
| **Idea Validator** | Workflow 1 only | Entrepreneurs, investors |
| **MVP Architect** | Workflows 1 + 2 | Product managers |
| **Full Stack Builder** | Workflows 1 + 2 + 3 | Technical founders |
| **Story Generator** | Workflow 3 only (with manual capability input) | Dev teams with existing specs |

---

### Implementation Changes

#### Stage Configuration Updates

```python
# haytham/phases/stage_config.py

# Workflow 1: Idea Validation (Stages 1-4)
VALIDATION_STAGES = [
    "idea-analysis",
    "market-context",
    "risk-assessment",
    "pivot-strategy",      # Conditional
    "validation-summary",
]

# Workflow 2: MVP Specification (Stages 5-6)
MVP_SPEC_STAGES = [
    "mvp-scope",
    "capability-model",
]

# Workflow 3: Story Generation (Stages 7-10)
STORY_GEN_STAGES = [
    "architecture-decisions",
    "story-generation",
    "story-validation",
    "dependency-ordering",
]
```

#### Workflow Registry

```python
# haytham/workflow/workflow_registry.py

from enum import Enum

class WorkflowType(Enum):
    IDEA_VALIDATION = "idea-validation"
    MVP_SPECIFICATION = "mvp-specification"
    STORY_GENERATION = "story-generation"
    IMPLEMENTATION = "implementation"  # External

WORKFLOW_CONFIGS = {
    WorkflowType.IDEA_VALIDATION: {
        "name": "Idea Validation",
        "role": "Product Owner",
        "stages": VALIDATION_STAGES,
        "entry_conditions": [],
        "exit_artifact": "Validation Report",
    },
    WorkflowType.MVP_SPECIFICATION: {
        "name": "MVP Specification",
        "role": "Product Manager",
        "stages": MVP_SPEC_STAGES,
        "entry_conditions": ["validation_summary_completed"],
        "exit_artifact": "Capability Model",
    },
    WorkflowType.STORY_GENERATION: {
        "name": "Story Generation",
        "role": "Software Architect",
        "stages": STORY_GEN_STAGES,
        "entry_conditions": ["capability_model_completed", "mvp_scope_exists"],
        "exit_artifact": "Ordered Stories",
    },
}
```

#### Session Manager Updates

```python
# Track workflow completion separately
def get_completed_workflows(self) -> list[str]:
    """Return list of completed workflow types."""

def is_workflow_complete(self, workflow_type: str) -> bool:
    """Check if a specific workflow has been completed."""

def get_available_workflows(self) -> list[str]:
    """Return workflows that can be started based on entry conditions."""
```

---

### Migration Path

1. **Phase 1: Split stage configuration**
   - Separate STAGES into VALIDATION_STAGES, MVP_SPEC_STAGES, STORY_GEN_STAGES
   - Update stage_config.py with workflow groupings

2. **Phase 2: Add decision gates**
   - Update Chainlit UI to show decision gates after each workflow
   - Add "proceed to next workflow" actions

3. **Phase 3: Update Burr workflows**
   - Create separate Burr applications per workflow
   - Update chainlit_adapter.py to handle workflow transitions

4. **Phase 4: Update session management**
   - Track workflow completion status
   - Implement entry condition validation

---

## Consequences

### Positive

1. **Faster validation** — Users get GO/NO-GO in ~5 minutes
2. **Natural decision points** — Users control when to proceed
3. **Reduced waste** — No MVP specs for rejected ideas
4. **Better persona fit** — Right depth for each user type
5. **Product optionality** — Can offer workflows as separate products
6. **Cleaner architecture** — Single responsibility per workflow

### Negative

1. **More transitions** — Users must explicitly proceed between workflows
2. **State complexity** — Must track 3 workflow states instead of 1
3. **UI changes** — Significant updates to decision gate UI

### Risks

1. **User confusion** — Too many steps might confuse users
   - **Mitigation:** Clear progress indicators, optional "run all" mode

2. **Context loss** — Users may forget context between workflows
   - **Mitigation:** Show summary of previous workflow outputs

---

## Alternatives Considered

### Alternative A: Keep Two Workflows, Add Early Exit

Add a "validation only" early exit after Stage 4.

**Rejected because:**
- Doesn't address the mixed-purpose problem
- MVP Specification and Story Generation are still coupled
- Less clean architecture

### Alternative B: Four Workflows (Split Story Generation)

Separate architecture_decisions from story_generation.

**Rejected because:**
- Too granular — architecture decisions naturally flow into stories
- Adds unnecessary decision gate

---

## References

- [ADR-004: Multi-Phase Workflow Architecture](./ADR-004-multi-phase-workflow-architecture.md)
- [ADR-005: Quality Evaluation Pattern](./ADR-005-quality-evaluation-pattern.md)
- [ADR-006: Story Generation Quality Evaluation](./ADR-006-story-generation-quality-evaluation.md)
