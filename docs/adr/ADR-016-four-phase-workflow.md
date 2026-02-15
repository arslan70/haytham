# ADR-016: Four-Phase Workflow Architecture — WHY, WHAT, HOW, Stories

## Status
**Proposed** — 2026-01-24

**Milestone**: Genesis (M1) — Phases 1-4 of 6

## Context

### The Problem

The current system has **misaligned layers** that create confusion and bugs:

1. **Dual Workflow Systems**: Workflows 1 & 2 use new `workflow_factories.py`, but Workflow 3 (Story Generation) uses legacy `phases/workflow_2/factory.py`

2. **Incorrect Stage Ordering**: Build vs Buy was implemented as Stage 7 in `stage_registry.py` but the legacy factory ignores it — stories are generated BEFORE knowing what to build vs buy

3. **Mixed Phase Boundaries**: ADR-009 proposed 3 workflows, but the logical separation should be 4 phases:
   - Current Workflow 3 combines HOW (architecture) with Stories (implementation tasks)
   - These answer different questions and should have a decision gate between them

4. **No Single Source of Truth**: Stage definitions in `stage_registry.py` don't match execution in `phases/workflow_2/factory.py` or navigation in `Haytham.py`

### Root Cause

The system evolved incrementally without aligning all layers:
- **Documentation** (ADR-009) proposes 3 workflows
- **Code** (`stage_registry.py`) defines stages 1-11 with WorkflowTypes
- **Execution** (`workflow_runner.py`) calls two different factory functions
- **UI** (`Haytham.py`) shows Stories, Roadmap, Build vs Buy as siblings after stories exist

When changes are made to one layer, the others fall out of sync.

### The Bigger Picture: Genesis → Evolution → Sentience

This ADR addresses **Phases 1-4 of the Genesis milestone**. To understand why this matters, we must understand Haytham's ultimate goal.

**Haytham exists to transform a startup idea into a self-improving, autonomous system.** This is achieved through three major milestones:

| Milestone | Name | Goal | Status |
|-----------|------|------|--------|
| M1 | **Genesis** | Idea → Working, validated MVP | IN PROGRESS |
| M2 | **Evolution** | MVP + change request → Updated system | PLANNED |
| M3 | **Sentience** | Running MVP → Autonomous improvement | VISION |

### Genesis: The Complete Picture

Genesis requires **6 phases** to close the loop from idea to validated MVP:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      GENESIS: COMPLETE WORKFLOW                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ THIS ADR: Phases 1-4 (Planning & Design)                            │    │
│  │                                                                     │    │
│  │  Phase 1: WHY ──▶ Phase 2: WHAT ──▶ Phase 3: HOW ──▶ Phase 4: STORIES│   │
│  │  (Validate)      (Specify)         (Design)         (Plan)          │    │
│  │                                                                     │    │
│  │  Output: Ordered stories with BUILD/BUY context, ready for coding   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                        ┌───────────┴───────────┐                            │
│                        │    DECISION GATE 4    │                            │
│                        │  Proceed to Build?    │                            │
│                        └───────────┬───────────┘                            │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ FUTURE: Phases 5-6 (Execution & Verification)                       │    │
│  │                                                                     │    │
│  │  Phase 5: IMPLEMENTATION ──────────▶ Phase 6: VALIDATION            │    │
│  │  (Code via Claude Code)              (Verify against capabilities)  │    │
│  │                                                                     │    │
│  │  Output: Working, validated MVP                                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ═══════════════════════════════════════════════════════════════════════    │
│                         GENESIS COMPLETE                                     │
│                    (Working MVP ready for Evolution)                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### This ADR's Scope

| Phase | Name | Question | Output | This ADR |
|-------|------|----------|--------|----------|
| 1 | WHY | Is this worth building? | GO / NO-GO / PIVOT | ✅ Covered |
| 2 | WHAT | What should we build first? | Capabilities (CAP-*) | ✅ Covered |
| 3 | HOW | How should we build it? | BUILD/BUY + Architecture | ✅ Covered |
| 4 | STORIES | What are the tasks? | Ordered stories | ✅ Covered |
| 5 | IMPLEMENTATION | Build the code | Working features | ❌ Future ADR |
| 6 | VALIDATION | Does it work? | Validated MVP | ❌ Future ADR |

**This ADR focuses on Phases 1-4** because:
1. These phases produce the **input** for the coding agent (Phase 5)
2. Clean phase boundaries enable proper **handoff** to Claude Code
3. Capability traceability (CAP-* → Story → Code) enables **validation** (Phase 6)

**Why This Matters for Future Milestones:**

Without clean phase boundaries, we cannot:
- Hand off stories correctly to a coding agent (missing build vs buy context)
- Validate implementations against capabilities (no clear capability→story→code traceability)
- Support Evolution mode (no understanding of what exists to change)
- Enable Sentience (no metrics to observe, no change mechanism)

The four-phase architecture is **foundational infrastructure** for completing Genesis and enabling Evolution and Sentience.

For the full vision, see [VISION.md](../../VISION.md).

---

## Decision

### Four Logical Phases with Decision Gates

We restructure the system into **four distinct phases**, each answering a specific question:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FOUR-PHASE WORKFLOW ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ╔═══════════════════════════════════════════════════════════════════════╗  │
│  ║ PHASE 1: WHY                                                           ║  │
│  ║ Question: "Is this idea worth pursuing?"                               ║  │
│  ║ Role: Product Owner / Entrepreneur                                     ║  │
│  ║                                                                        ║  │
│  ║ Stages: idea_analysis → market_context → risk_assessment →             ║  │
│  ║         [pivot_strategy] → validation_summary                          ║  │
│  ║                                                                        ║  │
│  ║ Output: GO / NO-GO / PIVOT recommendation                              ║  │
│  ╚═══════════════════════════════════════════════════════════════════════╝  │
│                                    │                                         │
│                        ┌───────────┴───────────┐                            │
│                        │    DECISION GATE 1    │                            │
│                        │   Proceed to WHAT?    │                            │
│                        └───────────┬───────────┘                            │
│                                    ▼                                         │
│  ╔═══════════════════════════════════════════════════════════════════════╗  │
│  ║ PHASE 2: WHAT                                                          ║  │
│  ║ Question: "What should we build first?"                                ║  │
│  ║ Role: Product Manager                                                  ║  │
│  ║                                                                        ║  │
│  ║ Stages: mvp_scope → capability_model                                   ║  │
│  ║                                                                        ║  │
│  ║ Output: MVP boundaries + Capabilities (CAP-F-*, CAP-NF-*)              ║  │
│  ╚═══════════════════════════════════════════════════════════════════════╝  │
│                                    │                                         │
│                        ┌───────────┴───────────┐                            │
│                        │    DECISION GATE 2    │                            │
│                        │   Proceed to HOW?     │                            │
│                        └───────────┬───────────┘                            │
│                                    ▼                                         │
│  ╔═══════════════════════════════════════════════════════════════════════╗  │
│  ║ PHASE 3: HOW                                                           ║  │
│  ║ Question: "How should we build each capability?"                       ║  │
│  ║ Role: Software Architect                                               ║  │
│  ║                                                                        ║  │
│  ║ Stages: build_buy_analysis → architecture_decisions                    ║  │
│  ║                                                                        ║  │
│  ║ Output: BUILD/BUY/HYBRID per capability + Architecture decisions       ║  │
│  ╚═══════════════════════════════════════════════════════════════════════╝  │
│                                    │                                         │
│                        ┌───────────┴───────────┐                            │
│                        │    DECISION GATE 3    │                            │
│                        │ Proceed to Stories?   │                            │
│                        └───────────┬───────────┘                            │
│                                    ▼                                         │
│  ╔═══════════════════════════════════════════════════════════════════════╗  │
│  ║ PHASE 4: STORIES                                                       ║  │
│  ║ Question: "What are the implementation tasks?"                         ║  │
│  ║ Role: Technical Lead                                                   ║  │
│  ║                                                                        ║  │
│  ║ Stages: story_generation → story_validation → dependency_ordering      ║  │
│  ║                                                                        ║  │
│  ║ Output: Ordered stories with BUILD (impl) or BUY (integration) focus   ║  │
│  ╚═══════════════════════════════════════════════════════════════════════╝  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Why Four Phases Instead of Three?

| Aspect | ADR-009 (3 Workflows) | This ADR (4 Phases) |
|--------|----------------------|---------------------|
| HOW vs Stories | Combined in Workflow 3 | Separate phases |
| Build vs Buy | Not explicitly placed | Explicit Phase 3 entry point |
| Decision points | 2 gates | 3 gates |
| Role clarity | Architect does architecture + stories | Architect does HOW, Tech Lead does Stories |

**Key insight**: Architecture decisions (HOW) and Story generation answer different questions:
- HOW: "Use Stripe for payments, PostgreSQL for persistence"
- Stories: "As a user, I can enter my credit card" (depends on Stripe decision)

Generating stories BEFORE knowing build vs buy creates waste — implementation stories for bought capabilities, or integration stories for built capabilities.

---

## Phase Definitions

### Phase 1: WHY (Idea Validation)

| Stage | Slug | Agent(s) | Output |
|-------|------|----------|--------|
| 1 | idea-analysis | concept_expansion | Problem, users, UVP |
| 2 | market-context | market_intelligence, competitor_analysis | Market size, competitors |
| 3 | risk-assessment | startup_validator | Risks, validation |
| 3b | pivot-strategy | pivot_strategy (conditional) | Alternative directions |
| 4 | validation-summary | validation_summary | GO / NO-GO / PIVOT |

**Terminal Stage**: `validation-summary`
**Lock File**: `.idea-validation.locked`

### Phase 2: WHAT (MVP Specification)

| Stage | Slug | Agent(s) | Output |
|-------|------|----------|--------|
| 5 | mvp-scope | mvp_scope | The One Thing, boundaries, core flows |
| 6 | capability-model | capability_model | CAP-F-*, CAP-NF-* capabilities |

**Terminal Stage**: `capability-model`
**Lock File**: `.mvp-specification.locked`

### Phase 3: HOW (Technical Design)

| Stage | Slug | Agent(s) | Output |
|-------|------|----------|--------|
| 7 | build-buy-analysis | build_buy_advisor | BUILD/BUY/HYBRID per capability |
| 8 | architecture-decisions | architecture_decisions | DEC-* decisions + component structure |

**Terminal Stage**: `architecture-decisions`
**Lock File**: `.technical-design.locked` (NEW)

### Phase 4: STORIES (Implementation Planning)

| Stage | Slug | Agent(s) | Output |
|-------|------|----------|--------|
| 9 | story-generation | story_generation | Stories with implements:CAP-* labels |
| 10 | story-validation | story_validation | Validated stories |
| 11 | dependency-ordering | dependency_ordering | Ordered tasks in Backlog.md |

**Terminal Stage**: `dependency-ordering`
**Lock File**: `.story-generation.locked`

---

## Implementation Plan

### Part 1: Align Stage Registry (Single Source of Truth)

**File**: `haytham/workflow/stage_registry.py`

Update WorkflowType enum and stage assignments:

```python
class WorkflowType(Enum):
    IDEA_VALIDATION = "idea-validation"      # Phase 1: WHY
    MVP_SPECIFICATION = "mvp-specification"  # Phase 2: WHAT
    TECHNICAL_DESIGN = "technical-design"    # Phase 3: HOW (NEW)
    STORY_GENERATION = "story-generation"    # Phase 4: STORIES

# Update build-buy-analysis stage:
StageMetadata(
    slug="build-buy-analysis",
    workflow_type=WorkflowType.TECHNICAL_DESIGN,  # Changed from STORY_GENERATION
    ...
)

# Add architecture-decisions as stage 8:
StageMetadata(
    slug="architecture-decisions",
    action_name="architecture_decisions",
    display_name="Architecture Decisions",
    display_index=8,
    workflow_type=WorkflowType.TECHNICAL_DESIGN,  # Same phase as build-buy
    ...
)
```

### Part 2: Consolidate Workflow Factories

**Goal**: Eliminate dual system — all workflows use `workflow_factories.py`

**File**: `haytham/workflow/workflow_factories.py`

1. Add `create_technical_design_workflow()` for Phase 3
2. Update `create_story_generation_workflow()` for Phase 4
3. Migrate architecture diff logic from `phases/workflow_2/factory.py`

**File**: `haytham/phases/workflow_2/factory.py`

- Mark as deprecated
- Redirect to `workflow_factories.py`

**File**: `frontend_streamlit/lib/workflow_runner.py`

- Update `run_story_generation()` to call correct factory
- Add `run_technical_design()` for Phase 3

### Part 3: Update Streamlit Navigation

**File**: `frontend_streamlit/Haytham.py`

Update navigation to reflect 4 phases:

```python
# Phase 1: WHY
if has_idea_validation():
    pages.append(st.Page("views/discovery.py", title="Idea Analysis"))

# Phase 2: WHAT
if is_workflow_locked("idea-validation") and has_mvp_specification():
    pages.append(st.Page("views/mvp_spec.py", title="MVP Specification"))

# Phase 3: HOW (NEW section)
if is_workflow_locked("mvp-specification") and has_technical_design():
    pages.append(st.Page("views/build_buy.py", title="Build vs Buy"))
    pages.append(st.Page("views/architecture.py", title="Architecture"))

# Phase 4: STORIES
if is_workflow_locked("technical-design") and has_stories():
    pages.append(st.Page("views/stories.py", title="Stories"))
    pages.append(st.Page("views/roadmap.py", title="Roadmap"))
```

### Part 4: Update View Pages

**File**: `frontend_streamlit/views/build_buy.py`

- Load from stage output (not re-analyze stories)
- Add "Continue to Architecture" button
- Move to Phase 3 section in navigation

**File**: `frontend_streamlit/views/architecture.py` (NEW)

- Display architecture decisions from DEC-* entries
- Add "Continue to Stories" button
- Terminal view for Phase 3

**File**: `frontend_streamlit/views/mvp_spec.py`

- Update "Continue" button to go to Technical Design (not Stories)

### Part 5: Add Entry Conditions

**File**: `haytham/workflow/entry_conditions.py`

Add validation for Phase 3:

```python
def check_technical_design_conditions(session_manager) -> tuple[bool, str]:
    """Validate Phase 3 (HOW) entry conditions."""
    if not is_workflow_locked("mvp-specification"):
        return False, "MVP Specification must be completed first"
    if not has_capabilities():
        return False, "No capabilities found in VectorDB"
    return True, ""
```

### Part 6: Update Session Manager

**File**: `haytham/session/session_manager.py`

Add methods for new phase:

```python
def is_technical_design_complete(self) -> bool:
    """Check if Phase 3 (HOW) is complete."""
    return self.is_workflow_locked("technical-design")

def get_phase(self) -> str:
    """Get current phase name."""
    if not self.is_workflow_locked("idea-validation"):
        return "WHY"
    if not self.is_workflow_locked("mvp-specification"):
        return "WHAT"
    if not self.is_workflow_locked("technical-design"):
        return "HOW"
    return "STORIES"
```

---

## Files to Modify

| Layer | File | Change |
|-------|------|--------|
| **Registry** | `stage_registry.py` | Add TECHNICAL_DESIGN WorkflowType, reassign stages |
| **Registry** | `phases/stage_config.py` | Update WorkflowType enum |
| **Factory** | `workflow_factories.py` | Add create_technical_design_workflow |
| **Factory** | `phases/workflow_2/factory.py` | Deprecate, redirect |
| **Runner** | `workflow_runner.py` | Add run_technical_design, update imports |
| **Conditions** | `entry_conditions.py` | Add check_technical_design_conditions |
| **Session** | `session_manager.py` | Add is_technical_design_complete, get_phase |
| **UI/Nav** | `Haytham.py` | Update navigation for 4 phases |
| **UI/View** | `mvp_spec.py` | Change "Continue" destination |
| **UI/View** | `build_buy.py` | Add Phase 3 context, "Continue" button |
| **UI/View** | `architecture.py` | NEW: Architecture decisions view |
| **UI/View** | `execution.py` | Add Phase 3 execution handling |
| **Docs** | `ADR-016-four-phase-workflow.md` | This ADR |
| **Docs** | `CLAUDE.md` | Update architecture section |

---

## Migration Steps

1. **Create ADR-016** in `docs/adr/` (this document)

2. **Update stage_registry.py**:
   - Add `TECHNICAL_DESIGN` to WorkflowType
   - Reassign build-buy-analysis to TECHNICAL_DESIGN
   - Add architecture-decisions stage if missing

3. **Update phases/stage_config.py**:
   - Add `TECHNICAL_DESIGN` to WorkflowType enum

4. **Create create_technical_design_workflow()**:
   - In workflow_factories.py
   - Entry: build_buy_analysis
   - Terminal: architecture_decisions
   - Migrate diff logic from legacy factory

5. **Update workflow_runner.py**:
   - Add `run_technical_design()` function
   - Update `run_story_generation()` to require Phase 3 completion

6. **Update UI navigation (Haytham.py)**:
   - Add Phase 3 section between MVP Spec and Stories
   - Update visibility conditions

7. **Update view pages**:
   - mvp_spec.py: Button goes to Phase 3
   - build_buy.py: Add context, "Continue" button
   - Create architecture.py for DEC-* display

8. **Deprecate legacy factory**:
   - Add deprecation warning to phases/workflow_2/factory.py
   - Update imports to use workflow_factories.py

---

## Verification

### Unit Tests

```bash
# Test stage registry has correct WorkflowTypes
pytest tests/test_stage_registry.py -v

# Test workflow factories
pytest tests/test_workflow_factories.py -v

# Test entry conditions
pytest tests/test_entry_conditions.py -v
```

### Integration Test

```bash
# Run full workflow through all 4 phases
pytest tests/test_four_phase_workflow.py -v
```

### Manual Test

1. Start Haytham: `streamlit run frontend_streamlit/Haytham.py`
2. Enter a startup idea
3. Complete Phase 1 (WHY) → See "Proceed to MVP Specification" button
4. Complete Phase 2 (WHAT) → See "Proceed to Technical Design" button (NEW)
5. Complete Phase 3 (HOW) → See Build vs Buy + Architecture
6. Complete Phase 4 (STORIES) → See Stories + Roadmap

### Verify Phase Boundaries

- [ ] Discovery page shows Phase 1 context
- [ ] MVP Spec page shows Phase 2 context
- [ ] Build vs Buy page shows Phase 3 context
- [ ] Stories page shows Phase 4 context
- [ ] Each phase has its own lock file
- [ ] Cannot skip phases (entry conditions enforced)

---

## Consequences

### Positive

1. **Single source of truth** — Stage registry defines all stages and their phases
2. **Correct ordering** — Build vs Buy runs BEFORE stories
3. **Clear decision gates** — 3 explicit pause points for user review
4. **Role alignment** — Each phase maps to a recognizable role
5. **Reduced waste** — No implementation stories for bought capabilities
6. **Maintainable** — One workflow factory system instead of two

### Negative

1. **More transitions** — Users must explicitly proceed between phases
2. **Migration effort** — Must update all layers simultaneously
3. **Breaking change** — Existing sessions may need migration

### Risks

1. **Incomplete migration** — Some layer not updated
   - **Mitigation**: Checklist-based implementation, integration tests

2. **User confusion** — Extra phase adds cognitive load
   - **Mitigation**: Clear phase indicators in UI, progress bar

---

## What's Next: Completing Genesis

This ADR establishes the foundation for **Phases 1-4**. To complete the Genesis milestone, future ADRs will address:

### Phase 5: Implementation (Future ADR)

**Question**: "Execute the implementation plan"

| Input | Process | Output |
|-------|---------|--------|
| Ordered stories with BUILD/BUY labels | Claude Code implements each story | Working code artifacts |

Key requirements:
- Stories handed to coding agent in dependency order
- Each story tagged with `implements:CAP-*` for traceability
- BUILD stories → implementation code
- BUY stories → integration code
- Implementation artifacts tracked in session

### Phase 6: Validation (Future ADR)

**Question**: "Does the implementation satisfy the capabilities?"

| Input | Process | Output |
|-------|---------|--------|
| Implemented code + Capabilities | Validate each CAP-* | Pass / Fail + remediation |

Key requirements:
- Each capability validated against its implementation
- Functional capabilities: Does it work as specified?
- Non-functional capabilities: Performance, security, etc.
- Failures generate remediation stories → loop back to Phase 5
- All capabilities pass → Genesis complete

### After Genesis: Evolution and Sentience

Once Genesis is complete (working, validated MVP exists), the system is ready for:

- **Evolution** (M2): User requests changes → Haytham generates targeted stories → validates no regressions
- **Sentience** (M3): Haytham observes running MVP → proposes improvements autonomously

See [VISION.md](../../VISION.md) for full details on these future milestones.

---

## References

- [VISION.md](../../VISION.md) — Complete roadmap (Genesis → Evolution → Sentience)
- [ADR-017: UX Design for Four-Phase Workflow](./ADR-017-ux-design-four-phase-workflow.md) — User experience design
- [ADR-009: Workflow Separation](./ADR-009-workflow-separation.md) — Previous 3-workflow proposal
- [ADR-004: Multi-Phase Workflow Architecture](./ADR-004-multi-phase-workflow-architecture.md) — Original architecture
- [ADR-013: Build vs Buy Recommendations](./ADR-013-build-vs-buy-recommendations.md) — Build vs Buy feature
