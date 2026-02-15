# ADR-004: Multi-Phase Workflow Architecture — Workflow Boundaries and State Handoff

## Status
**Proposed** — 2026-01-10 (Revised 2026-01-11, v4)

## Context

### Current State
The Haytham system implements a single Burr workflow (`haytham-validation`) that covers the Discovery & Validation phase:

```
┌─────────────────────────────────────────────────────────────────┐
│                  CURRENT: Single Burr Workflow                   │
├─────────────────────────────────────────────────────────────────┤
│ idea_analysis → market_context → risk_assessment →              │
│ [pivot_strategy] → validation_summary → mvp_scope →             │
│                                         capability_model        │
│                                              ↓                  │
│                                    Writes to VectorDB           │
└─────────────────────────────────────────────────────────────────┘
```

With [ADR-003](./ADR-003-system-state-evolution.md), the `capability_model` stage outputs structured capabilities to a LanceDB vector database. The `mvp_scope` stage constrains the capability model to focus on MVP-critical capabilities only.

### The Challenge
The concept paper ([concept-paper.md](../concept-paper.md)) envisions Haytham as covering the full software development lifecycle:

1. **Discovery & Validation** — Problem framing, market analysis, risk assessment *(Product Owner role)*
2. **Technical Translation** — Architecture decisions, story generation *(Software Architect role)*
3. **Implementation** — Story execution with coding agents *(Developer/AI Agent role)*
4. **Operation & Feedback** — Deployment, monitoring, production signals *(Future)*

#### Key Questions
1. Should all phases be a single Burr workflow or separate workflows per phase?
2. How should state be passed between phases?
3. How do we track which capabilities are implemented?

### Related Prior Art
- **ADR-003**: Established vector database for queryable system state
- **ADR-002**: Established Backlog.md for task management
- **Burr Documentation**: Supports parent-child workflow relationships

---

## Decision

### Separate Burr Workflows per Phase

We will implement **separate Burr workflows for each major phase**, connected by the shared vector database and Backlog.md.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      MULTI-PHASE WORKFLOW ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ WORKFLOW 1: Discovery & Validation (Product Owner)                  │   │
│  │ app_id: "haytham-discovery-{project_id}"                              │   │
│  │                                                                     │   │
│  │ idea_analysis → market_context → risk_assessment →                  │   │
│  │ [pivot_strategy] → validation_summary → mvp_scope → capability_model│   │
│  │                                                        ↓            │   │
│  │                                              Writes to VectorDB     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                          │                                  │
│                                          ▼                                  │
│                              ┌──────────────────────┐                       │
│                              │     VECTOR DB        │                       │
│                              │ • Capabilities       │                       │
│                              │ • Decisions          │                       │
│                              │ • Entities           │                       │
│                              └──────────────────────┘                       │
│                                          │                                  │
│                                          ▼                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ WORKFLOW 2: Technical Translation (Software Architect)              │   │
│  │ app_id: "haytham-architect-{project_id}"                              │   │
│  │                                                                     │   │
│  │ architecture_decisions → component_boundaries →                     │   │
│  │ story_generation → story_validation → dependency_ordering           │   │
│  │                              ↓                                      │   │
│  │            Writes Decisions to VectorDB                             │   │
│  │            Writes Stories to Backlog.md                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                          │                                  │
│                                          ▼                                  │
│                              ┌──────────────────────┐                       │
│                              │     BACKLOG.MD       │                       │
│                              │ • Stories            │                       │
│                              │ • Dependency order   │                       │
│                              │ • implements: CAP-*  │                       │
│                              └──────────────────────┘                       │
│                                          │                                  │
│                                          ▼                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ WORKFLOW 3: Implementation (Coding Agents)                          │   │
│  │ Handoff to external agents (Claude Code, Cursor, etc.)              │   │
│  │ [Details deferred to ADR-004b]                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Design Rationale

#### Why Separate Workflows?

| Factor | Single Workflow | Separate Workflows (Chosen) |
|--------|-----------------|----------------------------|
| **State manageability** | State grows very large over project lifetime | Focused state per phase |
| **Role alignment** | One size fits all | Phase-specific roles (PO, Architect, Dev) |
| **Resume granularity** | Resume anywhere, but complex | Resume within phase is natural |
| **Modular evolution** | Changes affect entire workflow | Can evolve phases independently |
| **Different timescales** | Forced single session model | Days between phases is normal |
| **Failure isolation** | Failure affects entire workflow | Failure contained to phase |

#### Why Vector DB as the Bridge?

The vector database acts as the **durable shared memory** between workflows:

1. **Semantic queryability** — Agents in Workflow 2 can query: "Find all capabilities related to authentication"
2. **Temporal traceability** — Each entry tracks its source stage and supersede chain
3. **Decoupled lifecycles** — Workflows don't need to know each other's internal state
4. **Immutable definitions** — Capabilities are definitions, not work items

---

### Workflow Definitions

#### Workflow 1: Discovery & Validation

**Role:** Product Owner / Business Analyst

**Purpose:** Validate the idea and define MVP scope before investing in architecture.

| Stage | Action | Output |
|-------|--------|--------|
| 1 | `idea_analysis` | Problem, users, UVP |
| 2 | `market_context` | Market size, competitors |
| 3 | `risk_assessment` | Risks, validation |
| 3b | `pivot_strategy` | (Conditional) Alternatives |
| 4 | `validation_summary` | Go/No-go recommendation |
| 5 | `mvp_scope` | The One Thing, boundaries, core flows |
| 6 | `capability_model` | Capabilities → VectorDB |

**Exit Condition:** `capability_model_status == "completed"`

**Exit Artifact:** Capabilities (CAP-F-*, CAP-NF-*) stored in VectorDB

---

#### Workflow 2: Technical Translation

**Role:** Software Architect

**Purpose:** Translate capabilities into implementable, dependency-ordered stories for coding agents.

| Stage | Action | Description | Output |
|-------|--------|-------------|--------|
| 1 | `architecture_decisions` | Define key technical decisions | DEC-* entries → VectorDB |
| 2 | `component_boundaries` | Define component structure and domain entities | ENT-* entries → VectorDB |
| 3 | `story_generation` | Generate stories for uncovered capabilities | Stories (in memory) |
| 4 | `story_validation` | Basic label validation (non-blocking) | Validated stories |
| 5 | `dependency_ordering` | Order stories by dependencies, create draft tasks | Draft tasks → Backlog.md |

**Important:** Stories are generated in memory and only written to Backlog.md at the end of `dependency_ordering`. This ensures only validated, ordered stories become tasks.

**Entry Conditions:**
- `capability_model_status == "completed"` in Workflow 1
- At least 1 functional capability exists in VectorDB
- MVP Scope document exists

**Stage Input Context:**

The `architecture_decisions` stage receives full upstream context:
- **Capabilities** (functional + non-functional) — What must be built
- **MVP Scope** — Constraints, appetite, core user flows
- **Validation Summary** — Risk context to inform technology choices
- **System Goal** — Original idea for grounding
- **Existing Decisions** (DEC-*) — Previously made architecture decisions from VectorDB
- **Existing Entities** (ENT-*) — Previously defined domain entities from VectorDB

This ensures architecture decisions align with MVP constraints, mitigate identified risks, and respect existing architecture.

**Architecture Awareness: Diff-Based Approach**

Instead of discrete modes (greenfield/incremental/revision), we compute a **diff** that tells the agent exactly what needs attention. The agent applies the same logic regardless of whether it's the first run or the hundredth.

#### Decision Data Model

Decisions must explicitly track which capabilities they serve:

```python
@dataclass
class Decision:
    id: str                         # DEC-001
    name: str
    description: str
    rationale: str
    serves_capabilities: list[str]  # [CAP-F-001, CAP-F-002] ← Required
    superseded_by: str | None
    source_stage: str               # "architecture-decisions"
```

This enables traceability: every decision answers "why does this exist?" by linking to capabilities.

#### Architecture Diff

The diff tells the agent what needs attention:

```python
@dataclass
class ArchitectureDiff:
    """Computed diff - what needs attention."""

    # Capabilities with no active decisions serving them
    uncovered_capabilities: list[str]

    # Active decisions that serve superseded capabilities
    affected_decisions: list[str]

    # Entities referenced by affected decisions
    affected_entities: list[str]

    # Stories implementing superseded capabilities
    affected_stories: list[str]
```

#### Diff Computation

```python
def compute_architecture_diff(
    capabilities: list[dict],  # Capabilities from VectorDB (get_capabilities)
    decisions: list[dict],     # Decisions from VectorDB (get_decisions)
    entities: list[dict],      # Entities from VectorDB (get_entities)
    stories: list[dict],       # Stories from Backlog.md (task_list)
) -> ArchitectureDiff:
    """Compute what needs attention - pure function, easily testable.

    Note: All inputs are dicts, not dataclasses:
    - capabilities/decisions/entities: VectorDB returns dicts
    - stories: Backlog.md task_list returns dicts
    """

    # Identify superseded capabilities
    superseded_cap_ids = {
        c["id"] for c in capabilities if c.get("superseded_by")
    }
    active_cap_ids = {
        c["id"] for c in capabilities if not c.get("superseded_by")
    }

    # Find capabilities not served by any active decision
    served_cap_ids = set()
    for d in decisions:
        if not d.get("superseded_by"):  # Only count active decisions
            served_cap_ids.update(d.get("serves_capabilities", []))

    uncovered = active_cap_ids - served_cap_ids

    # Find decisions affected by superseded capabilities
    affected_decisions = [
        d["id"] for d in decisions
        if not d.get("superseded_by")  # Active decision
        and any(cap_id in superseded_cap_ids for cap_id in d.get("serves_capabilities", []))
    ]

    # Find entities referenced by affected decisions
    # Helper: looks up entities mentioned in decision metadata
    affected_entities = [
        e["id"] for e in entities
        if any(d_id in e.get("referenced_by", []) for d_id in affected_decisions)
    ]

    # Find stories implementing superseded capabilities
    # Stories are dicts from Backlog.md task_list with "labels" key
    affected_stories = [
        s["id"] for s in stories
        if any(f"implements:{cap_id}" in s.get("labels", []) for cap_id in superseded_cap_ids)
    ]

    return ArchitectureDiff(
        uncovered_capabilities=list(uncovered),
        affected_decisions=affected_decisions,
        affected_entities=affected_entities,
        affected_stories=affected_stories,
    )
```

#### Example: Uncovered Capabilities Computation

```
Capabilities (active):
  - CAP-F-001 (Quick Capture)
  - CAP-F-002 (Note Retrieval)
  - CAP-F-003-v2 (Authenticated Sharing)  ← NEW
  - CAP-NF-001 (Response Time)

Decisions (active):
  - DEC-001 serves [CAP-F-001, CAP-F-002]
  - DEC-002 serves [CAP-F-002]
  - DEC-003 serves [CAP-F-001, CAP-F-002, CAP-NF-001]

Computation:
  active_cap_ids = {CAP-F-001, CAP-F-002, CAP-F-003-v2, CAP-NF-001}
  served_cap_ids = {CAP-F-001, CAP-F-002, CAP-NF-001}
  uncovered = active_cap_ids - served_cap_ids = {CAP-F-003-v2}

Result: CAP-F-003-v2 is uncovered — needs new decisions.
```

#### Why Diff-Based Is Better Than Modes

| Aspect | Mode-Based | Diff-Based (Chosen) |
|--------|------------|---------------------|
| **Edge cases** | Ambiguous (new + superseded?) | Handled naturally in diff |
| **Agent logic** | Mode-specific branches | Single unified logic |
| **Testability** | Test mode determination + behavior | Test diff computation (pure function) |
| **Debugging** | "Why is it in revision mode?" | "What's in the diff?" |
| **Emergent behavior** | Explicit labels | Same algorithm handles all scenarios |

The "mode" becomes emergent:
- All capabilities uncovered → behaves like "greenfield"
- Some uncovered, none affected → behaves like "incremental"
- Has affected decisions → behaves like "revision"
- Empty diff → nothing to do

But we don't label it — the agent just processes the diff.

#### Workflow Run Registry (For Audit)

We still track workflow runs, but for **audit purposes only**, not for determining behavior:

```python
@dataclass
class WorkflowRunContext:
    """Tracks workflow execution for audit trail."""
    run_id: str
    workflow_type: str             # "discovery" | "architect" | "implementation"
    project_id: str
    trigger: WorkflowTrigger
    run_number: int
    created_at: datetime
    status: str                    # "running" | "completed" | "failed"

@dataclass
class WorkflowTrigger:
    """What triggered this workflow run - for audit, not behavior."""
    type: str                      # "user_initiated" | "change_request"
    source_workflow: str | None    # Which workflow triggered this
    # Note: No change_type - the diff tells us what changed
```

**Stage Outputs:**

| Stage | Outputs | Storage |
|-------|---------|---------|
| `architecture_decisions` | DEC-* entries (e.g., "Use OAuth 2.0", "PostgreSQL for persistence") | VectorDB |
| `component_boundaries` | Component diagram + ENT-* domain entities | VectorDB |
| `story_generation` | Stories with `implements:CAP-*`, `uses:DEC-*`, `touches:ENT-*` labels | In-memory (passed to next stage) |
| `story_validation` | Basic label check (non-blocking per ADR-005) | In-memory |
| `dependency_ordering` | Ordered stories → Draft tasks with traceability labels | Backlog.md (drafts) |

**Data Flow:**
```
VectorDB (read)        In-Memory Pipeline              Backlog.md (write)
──────────────        ──────────────────               ─────────────────
Capabilities    →     story_generation
Decisions       →          ↓
Entities        →     story_validation
                           ↓
                      dependency_ordering  ──────────→  Draft Tasks
```

**Exit Artifact:** Ordered stories in Backlog.md with capability traceability labels

**Why no sprint planning?** Sprints are a human time-boxing concept. AI coding agents don't need time constraints—they need:
- Dependency ordering (what must be built first)
- Rational sequencing (foundation before features)
- Clear handoff context

**Why no complexity estimation?** Story complexity is deliberately omitted. Coding agents discover true complexity during implementation. Front-loading estimation adds overhead without improving agent execution.

---

#### Workflow 3: Implementation (Future — ADR-004b)

**Role:** Coding Agents (Claude Code, Cursor, etc.)

**Purpose:** Execute stories and produce working code.

This workflow hands off to external coding agents. Details deferred to ADR-004b, which will define:
- Handoff protocol to external agents
- Context packaging for coding agents
- Feedback loop from execution to design

---

### Capability-to-Story Traceability

#### The Core Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     CAPABILITY LIFECYCLE                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  VectorDB                         Backlog.md                    Code        │
│  ─────────                        ──────────                    ────        │
│                                                                             │
│  CAP-F-001 ─────────────────────→ STORY-001 ───────────────→ auth.py       │
│       (capability)                  (implements: CAP-F-001)     (working)   │
│                                                                             │
│  CAP-F-002 ─────────────────────→ STORY-002 ───────────────→ ???           │
│                                     (In Progress)                           │
│                                                                             │
│  CAP-F-003 ─────────────────────→ STORY-003 ───────────────→              │
│                                     (To Do)                                 │
│                                                                             │
│  CAP-F-004 ─────────────────────→ ???                                       │
│       (no stories yet)                                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Key Principle: Capabilities Are Immutable Definitions

| Concept | Where | Mutable? | Has Status? |
|---------|-------|----------|-------------|
| Capability | VectorDB | No (supersede only) | No |
| Story | Backlog.md | Yes | Yes (To Do → In Progress → Done) |
| Code | Repository | Yes | N/A |

**Capability status is DERIVED, not stored.** We compute it by querying which capabilities have stories and what those stories' statuses are.

#### Story → Capability Link

Each story in Backlog.md uses **labels** for traceability:

```yaml
---
title: Implement Quick Capture
labels:
  - implements:CAP-F-001    # Primary capability
  - uses:DEC-001            # OAuth 2.0 decision
  - uses:DEC-003            # Redis session storage
  - touches:ENT-001         # User entity
  - touches:ENT-002         # Session entity
status: To Do
---

## Acceptance Criteria
- [ ] User can initiate OAuth flow with Google
- [ ] Successful auth creates Session record
- [ ] Session token returned to client
```

**Why labels instead of custom fields?**
- Labels are already supported by Backlog.md MCP
- Easy to query: `task_list(labels=["implements:CAP-F-001"])`
- Keeps story title clean and human-readable
- Supports multiple capabilities per story without title clutter

This format makes stories **effective prompts for coding agents** — they contain all the technical context needed.

#### Capability Coverage Query

```python
def get_capability_coverage(db: SystemStateDB, backlog: BacklogClient) -> dict:
    """Compute capability implementation status (derived, not stored)."""

    capabilities = db.get_capabilities()

    coverage = {}

    for cap in capabilities:
        cap_id = cap["id"]

        # Find stories implementing this capability via labels
        implementing_stories = backlog.task_list(
            labels=[f"implements:{cap_id}"]
        )

        if not implementing_stories:
            status = "no_stories"
        elif all(s["status"] == "Done" for s in implementing_stories):
            status = "implemented"
        elif any(s["status"] == "In Progress" for s in implementing_stories):
            status = "in_progress"
        else:
            status = "pending"  # Stories exist but not started

        coverage[cap_id] = {
            "capability": cap["name"],
            "status": status,
            "stories": [s["id"] for s in implementing_stories],
        }

    return coverage
```

#### Coverage Report

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     CAPABILITY COVERAGE REPORT                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  FUNCTIONAL CAPABILITIES                                                    │
│  ───────────────────────                                                    │
│  ✅ CAP-F-001  Quick Capture      [IMPLEMENTED]  STORY-001 (Done)           │
│  🔄 CAP-F-002  Note Retrieval     [IN PROGRESS]  STORY-002 (In Progress)    │
│  ⏳ CAP-F-003  Note Organization  [PENDING]      STORY-003 (To Do)          │
│  ❌ CAP-F-004  Note Sharing       [NO STORIES]   —                          │
│                                                                             │
│  NON-FUNCTIONAL CAPABILITIES                                                │
│  ──────────────────────────                                                 │
│  ⏳ CAP-NF-001 Response Time      [PENDING]      STORY-007 (To Do)          │
│  ❌ CAP-NF-002 Data Security      [NO STORIES]   —                          │
│                                                                             │
│  SUMMARY: 6 capabilities | 1 implemented | 1 in progress | 2 pending | 2 gaps│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Edge Cases

| Scenario | Rule |
|----------|------|
| One capability → multiple stories | Capability is "implemented" only when ALL stories are Done |
| One story → multiple capabilities | Story completion updates coverage for ALL linked capabilities |
| Capability superseded after stories created | Stories flagged with `needs-review:superseded` label (see below) |

#### Supersede Detection and Handling

When a capability is superseded (via Change Workflow), affected stories must be identified and flagged:

```
┌─────────────────────────────────────────────────────────────────┐
│                   SUPERSEDE DETECTION FLOW                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Change Workflow creates new capability CAP-F-001-v2         │
│     with metadata: supersedes: CAP-F-001                        │
│                                                                 │
│  2. System queries Backlog.md for stories with                  │
│     label: implements:CAP-F-001                                 │
│                                                                 │
│  3. Affected stories get label: needs-review:superseded         │
│                                                                 │
│  4. User notified: "2 stories reference superseded capability"  │
│                                                                 │
│  5. Resolution options:                                         │
│     a) Update story label to implements:CAP-F-001-v2            │
│     b) Archive story (capability no longer needed)              │
│     c) Generate new stories for new capability                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Implementation:** The supersede detection runs as a pre-check when entering Workflow 2, and can be triggered manually via Chainlit UI.

---

### Feedback Loop Requirement (Workflow 3 → Workflow 2)

**Status:** Requirement documented; implementation deferred to ADR-004b.

#### The Problem

Workflow 3 (Implementation) may discover issues that require changes to Workflow 2 outputs:

| Discovery | Required Action |
|-----------|-----------------|
| Story is impossible as specified | Revise story or architecture decision |
| Missing capability identified | Add capability, regenerate stories |
| Decision (DEC-*) proves unworkable | Revise decision, update affected stories |
| Entity model incomplete | Add entities, update affected stories |

Without a feedback mechanism, coding agents either:
- Get stuck (no path forward)
- Make undocumented changes (drift from design)
- Produce code that doesn't match capability model

#### Why This Matters

The system's value proposition is **end-to-end automation**. A one-way pipeline that breaks at implementation defeats this purpose. The feedback loop ensures:

1. **Self-correction** — System can recover from design gaps
2. **Traceability maintained** — Changes flow through proper channels
3. **User visibility** — User is notified of significant design changes
4. **Learning** — Patterns in feedback improve future Workflow 2 outputs

#### Proposed Mechanism (High-Level)

```
Coding Agent → discovers issue → creates "feedback" task in Backlog.md
                                        ↓
                              System detects feedback task
                                        ↓
                              User notified: "Implementation feedback requires attention"
                                        ↓
                              User triggers Workflow 2 revision OR manual resolution
```

**Detailed design deferred to ADR-004b.**

---

### Workflow Immutability and Change Management

#### Principle: Workflows Are One-Shot

Each workflow runs once for a given project phase. Re-running Workflow 1 does not happen; instead, changes are managed through a dedicated **Change Workflow**.

| Scenario | Approach |
|----------|----------|
| User wants to modify MVP scope | Change Workflow: `scope_revision` → updates capabilities |
| New risk identified post-validation | Change Workflow: `risk_update` → may trigger pivot |
| Stakeholder adds requirement | Change Workflow: `requirement_addition` → new capability |

This preserves:
- **Audit trail** — Original workflow outputs remain intact
- **Traceability** — Changes are explicit, not silent overwrites
- **Simplicity** — No complex "resume and replay" logic

#### Change Workflow (Future)

The Change Workflow is a separate Burr workflow that:
1. Accepts change requests
2. Identifies affected artifacts (capabilities, decisions, stories)
3. Creates new/revised entries with `supersedes:` links
4. Triggers supersede detection for downstream artifacts

**Detailed design deferred to future ADR.**

---

### User Interaction Model

#### Workflow Triggers

Users control workflow transitions via Chainlit UI:

| Transition | Trigger | UI Element |
|------------|---------|------------|
| Start Workflow 1 | User submits startup idea | Text input + "Validate Idea" button |
| Start Workflow 2 | User approves Workflow 1 output | "Start Technical Translation" button |
| Start Workflow 3 | User approves Workflow 2 output | "Begin Implementation" button |
| Trigger Change Workflow | User requests modification | "Request Change" button |

#### Pause Points

Workflows pause for user approval at phase boundaries:
- After Workflow 1: Review capabilities before architecture
- After Workflow 2: Review stories before coding begins

Within a workflow, stages execute automatically unless a stage explicitly requests user input (e.g., pivot decision).

---

### State Handoff Protocol

#### Helper Functions

```python
def count_capabilities(db: SystemStateDB) -> int:
    """Count current (non-superseded) capabilities."""
    return len(db.get_capabilities())
```

#### Between Workflow 1 → Workflow 2

```python
# End of Workflow 1
def on_workflow_1_complete(state: State, session_manager):
    """Finalize Workflow 1 and prepare handoff."""

    # 1. Ensure all capabilities are stored in VectorDB
    assert state.get("capability_model_status") == "completed"

    # 2. Create workflow transition record
    db = SystemStateDB(session_manager.session_dir / "vector_db")
    db.add_entry(SystemStateEntry(
        type="decision",
        name="Workflow 1 Complete",
        description="Discovery & Validation phase completed successfully.",
        rationale=f"Stored {count_capabilities(db)} capabilities.",
        source_stage="workflow-transition",
        metadata={
            "from_workflow": "haytham-discovery",
            "to_workflow": "haytham-architect",
            "transition_time": datetime.utcnow().isoformat(),
        },
    ))

    return {
        "workflow_status": "completed",
        "next_workflow": "haytham-architect",
        "capabilities_count": count_capabilities(db),
    }


# Start of Workflow 2
import json
import uuid
from datetime import datetime

def create_architect_workflow(
    session_manager,
    project_id: str,
    trigger: WorkflowTrigger,
) -> Application:
    """Create Workflow 2 with diff-based architecture awareness.

    Args:
        session_manager: Session state manager
        project_id: Project identifier
        trigger: What triggered this workflow run (for audit trail)
    """
    db = SystemStateDB(session_manager.session_dir / "vector_db")
    backlog = BacklogClient()

    # 1. Create and store workflow run context (for audit)
    # NOTE: Workflow runs can be stored as:
    #   - VectorDB entries with type="workflow_run" (queryable, semantic search)
    #   - JSON file in session directory (simpler, direct access)
    # Decision: Use JSON file for MVP (simpler). Migrate to VectorDB if querying needs arise.
    run_context_file = session_manager.session_dir / "workflow_runs.json"
    previous_runs = json.loads(run_context_file.read_text()) if run_context_file.exists() else []
    architect_runs = [r for r in previous_runs if r.get("workflow_type") == "architect"]
    run_number = len(architect_runs) + 1

    run_context = {
        "run_id": str(uuid.uuid4()),
        "workflow_type": "architect",
        "project_id": project_id,
        "trigger": {"type": trigger.type, "source_workflow": trigger.source_workflow},
        "run_number": run_number,
        "created_at": datetime.utcnow().isoformat(),
        "status": "running",
    }
    previous_runs.append(run_context)
    run_context_file.write_text(json.dumps(previous_runs, indent=2))

    # 2. Load all data from VectorDB and Backlog.md
    # Note: VectorDB uses explicit getter methods, not query()
    capabilities = db.get_capabilities()          # All current (non-superseded) capabilities
    decisions = db.get_decisions()                # All current decisions
    entities = db.get_entities()                  # All current entities
    stories = backlog.task_list()                 # All stories from Backlog.md (dicts)

    # 3. Validate entry conditions
    # Note: Capabilities use "subtype" (functional, non_functional, operational), not "category"
    functional_caps = [c for c in capabilities if c.get("subtype") == "functional"]
    if not functional_caps:
        raise ValueError("Entry condition failed: No functional capabilities in VectorDB")

    # NOTE: load_stage_output() is a proposed SessionManager method.
    # Implementation: Reads stage output from session_dir/{stage}/output.md
    mvp_scope = session_manager.load_stage_output("mvp-scope")
    validation_summary = session_manager.load_stage_output("validation-summary")
    system_goal = session_manager.get_system_goal()

    if not mvp_scope:
        raise ValueError("Entry condition failed: MVP Scope not found")

    # 4. Compute architecture diff (the key step - no modes!)
    diff = compute_architecture_diff(
        capabilities=capabilities,
        decisions=decisions,
        entities=entities,
        stories=stories,
    )

    # 5. Build initial state
    initial_state = State({
        "project_id": project_id,
        "system_goal": system_goal,
        "mvp_scope": mvp_scope,
        "validation_summary": validation_summary,
        "session_manager": session_manager,

        # All data for context
        "capabilities": capabilities,
        "existing_decisions": decisions,
        "existing_entities": entities,

        # The diff tells the agent what to do
        "architecture_diff": diff,

        # Audit trail
        "workflow_run": run_context,
    })

    # 6. Create workflow
    return (
        ApplicationBuilder()
        .with_actions(
            architecture_decisions,
            component_boundaries,
            story_generation,
            story_validation,
            dependency_ordering,
        )
        .with_transitions(
            ("architecture_decisions", "component_boundaries"),
            ("component_boundaries", "story_generation"),
            ("story_generation", "story_validation"),
            ("story_validation", "dependency_ordering"),
        )
        .with_entrypoint("architecture_decisions")
        .with_state(initial_state)
        .with_identifiers(app_id=f"haytham-architect-{project_id}-run{run_number}")
        .build()
    )


# Usage examples:

# Any run - the diff determines what happens, not the trigger
trigger = WorkflowTrigger(
    type="user_initiated",
    source_workflow="discovery",
)
app = create_architect_workflow(session_manager, project_id, trigger)

# After Change Workflow - same code, diff will reflect new/changed capabilities
trigger = WorkflowTrigger(
    type="change_request",
    source_workflow="change",
)
app = create_architect_workflow(session_manager, project_id, trigger)
```

#### Between Workflow 2 → Workflow 3

Stories in Backlog.md are the handoff artifact. Each story contains labels for traceability:
- `implements:CAP-F-001` — What capability this addresses
- `uses:DEC-001` — Technical decisions used
- `touches:ENT-001` — Domain entities touched
- Acceptance criteria — Testable requirements
- Build order — Dependency-aware sequence

This matches the label format defined in the Story → Capability Link section above.

This format is directly usable as a coding agent prompt.

---

### User Experience Design

#### Phase Visibility
- Show current phase prominently: **"Phase 2: Technical Translation"**
- Display role context: **"Software Architect View"**
- Show capability count: **"Translating 5 capabilities into implementable stories"**

#### Phase Transitions

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PHASE TRANSITION UI                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ✅ Phase 1: Discovery & Validation — Complete                              │
│                                                                             │
│  Summary:                                                                   │
│  • Recommendation: PROCEED                                                  │
│  • 5 capabilities defined (3 functional, 2 non-functional)                  │
│  • MVP scope: Quick note capture for busy professionals                     │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Ready to proceed to Technical Translation.                          │   │
│  │                                                                     │   │
│  │ In this phase (Software Architect), we'll:                          │   │
│  │ • Make key architecture decisions                                   │   │
│  │ • Define component boundaries                                       │   │
│  │ • Generate implementation-ready stories                             │   │
│  │ • Order stories by dependencies                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  [🏗️ Start Technical Translation]     [📄 Download Validation Report]      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Implementation Checklist

#### Phase 1: Immediate (This ADR)
- [x] Document multi-workflow architecture *(this ADR)*
- [x] Implement `mvp_scope` stage in Workflow 1
- [x] Implement capability storage in VectorDB
- [ ] Add `workflow_phase` field to session state
- [ ] Implement `on_workflow_complete` hook for handoff metadata
- [ ] Add "Start Technical Translation" button to Chainlit UI

#### Phase 2: Workflow 2 Implementation

**Data Model Updates:**
- [ ] Add `serves_capabilities: list[str]` field to Decision schema (VectorDB metadata)
- [ ] Add `load_stage_output(stage_slug: str)` method to SessionManager
- [ ] Store workflow runs in JSON file (MVP choice; see code comments)

**Core Components:**
- [ ] Implement `ArchitectureDiff` dataclass (uncovered_capabilities, affected_decisions, etc.)
- [ ] Implement `compute_architecture_diff()` pure function
- [ ] Create `create_architect_workflow()` factory with diff computation

**Agents:**
- [ ] Implement `architecture_decisions` agent (processes diff, outputs decisions with serves_capabilities)
- [ ] Implement `component_boundaries` agent
- [ ] Implement `story_generation` agent (outputs stories with `implements:CAP-*` labels)
- [ ] Implement `story_validation` stage (basic label check, non-blocking per ADR-005)
- [ ] Implement `dependency_ordering` agent

**Validation & Queries:**
- [ ] Add quality evaluation for stories (per ADR-005/ADR-006)
- [ ] Implement capability coverage query using Backlog.md labels
- [ ] Implement Workflow 2 entry condition validation

**Notes:**
- Capabilities use `subtype` (functional, non_functional, operational), not `category`
- Stories are Backlog.md dicts (from `task_list()`), not VectorDB entries
- VectorDB API uses explicit getters: `get_capabilities()`, `get_decisions()`, `get_entities()`
- `capability_model` stage already respects MVP scope limits (receives mvp_scope as input)

#### Phase 2.5: Change Management
- [ ] Implement supersede detection query
- [ ] Add `needs-review:superseded` label handling
- [ ] Add user notification for superseded capabilities
- [ ] Design Change Workflow (separate ADR)

#### Phase 3: Workflow 3 (Future — ADR-004b)
- [ ] Create ADR-004b: Implementation Workflow and Coding Agent Handoff
- [ ] Define story-to-prompt translation
- [ ] Define feedback loop mechanism (feedback tasks in Backlog.md)
- [ ] Define user notification for implementation feedback

---

## Consequences

### Positive
1. **Role alignment** — Each phase maps to a recognizable role (PO, Architect, Dev)
2. **Clear phase boundaries** — Natural pause points for review
3. **Focused state per phase** — Easier to debug and maintain
4. **Traceable coverage** — Always know which capabilities have stories/implementation
5. **Agent-ready output** — Stories structured as effective coding prompts
6. **No artificial time constraints** — Dependency ordering, not sprints
7. **Immutable audit trail** — Changes through Change Workflow preserve history
8. **Label-based traceability** — Uses existing Backlog.md infrastructure

### Negative
1. **State loading overhead** — Must load from VectorDB at phase start
2. **Multiple app IDs** — Need to track which workflow is current
3. **Cross-system queries** — Coverage requires VectorDB + Backlog.md
4. **Deferred complexity** — Feedback loop and Change Workflow add future implementation burden

### Risks
1. **Superseded capabilities** — Change Workflow creates new capabilities that supersede old ones
   - **Mitigation:** Supersede detection flags affected stories with `needs-review:superseded` label; user notified for resolution
2. **Story drift** — Stories edited manually may lose `implements:` label
   - **Mitigation:** Quality evaluation (ADR-006) flags stories without proper labels
3. **Implementation feedback ignored** — Coding agents discover issues but no feedback path exists
   - **Mitigation:** ADR-004b will define feedback mechanism; until then, manual intervention required
4. **Entry condition failure** — Workflow 2 started without proper Workflow 1 completion
   - **Mitigation:** Explicit entry condition validation before workflow creation

---

## Alternatives Considered

### Alternative A: Single Monolithic Workflow

**Rejected because:**
- State becomes unmanageable over project lifetime
- Different phases have different roles and interaction patterns
- Single failure point for entire project

### Alternative B: Store Capability Status in VectorDB

Add a `status` field to capabilities: `defined`, `has_stories`, `implemented`.

**Rejected because:**
- Violates principle that capabilities are immutable definitions
- Creates sync issues between VectorDB and Backlog.md
- Derived status is always consistent

### Alternative C: Sprint-Based Delivery Planning

Include `sprint_planning` stage in Workflow 2.

**Rejected because:**
- Sprints are a human time-boxing concept
- AI agents need dependency ordering, not time constraints
- Simpler model: ordered backlog IS the delivery plan

---

## References

- [ADR-002: Backlog.md Integration](./ADR-002-backlog-md-integration.md)
- [ADR-003: System State Evolution](./ADR-003-system-state-evolution.md)
- [ADR-005: Quality Evaluation Pattern](./ADR-005-quality-evaluation-pattern.md)
- [ADR-006: Story Generation Quality Evaluation](./ADR-006-story-generation-quality-evaluation.md)
- [Project Haytham Concept Paper](../concept-paper.md)
- [Burr Documentation](https://burr.dagworks.io/concepts/state-machine/)
