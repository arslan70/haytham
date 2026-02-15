# ADR-001: Story-to-Implementation Pipeline

**Status**: Proposed
**Date**: 2025-01-02
**Deciders**: System Architect, Product Owner
**Scope**: Post-MVP Specification phase through Implementation

---

## POC Context

This pipeline is being built as a **Proof of Concept** to demonstrate end-to-end story-to-code transformation. Key POC decisions:

- **Integration**: Extends the existing Burr workflow graph after `mvp_specification` phase
- **Test Case**: Simple Notes App ("A simple notes app where users can create, organize, and search their notes")
- **State Model**: Single JSON file (simplified from multi-file YAML)
- **Coding Agent**: Claude Code only (no multi-agent abstraction)
- **Retroactive Coherence**: Deferred (focus on happy path; if interpretation is wrong, refine specs and retry)
- **ID Scheme**: 4 core IDs only (S-XXX stories, T-XXX tasks, E-XXX entities, D-XXX decisions)

---

## Context

Haytham currently transforms startup ideas into validated MVP specifications through a multi-agent workflow. The MVP specification stage produces user stories with acceptance criteria, UI/UX notes, and data requirements from a user-centric perspective.

The next phase requires transforming these user stories into running software. This presents a fundamental problem:

**How do we reliably transform high-level user stories into concrete, implementable technical tasks in an environment where no continuous human engineering team exists, while preserving global system coherence over time?**

### The Problem Space

The problem involves managing multiple types of uncertainty simultaneously:

#### 1. Semantic Uncertainty (Local)
Each user story is incomplete, ambiguous, and user-centric. For example:
- "Integrates with external systems" — which systems? what APIs? what data formats?
- "Real-time updates" — what latency is acceptable? WebSocket or polling?
- "Personalized recommendations" — what algorithm? what inputs? what data?
- "User can share content" — share where? with whom? what permissions?

These ambiguities cannot be eliminated upfront and must be surfaced and managed.

#### 2. Contextual Uncertainty (Global)
User stories describe desired behavior, not system architecture. The system may not exist, may exist partially, or may have constraints from earlier decisions. Without explicit shared understanding of system state, successive story interpretations will drift, creating an incoherent aggregate.

#### 3. Asymmetry of Judgment
Some decisions are low-cost and reversible (variable naming, file organization). Others have high, irreversible impact (database schema, authentication model, API contracts). Without a human team, the system must identify and escalate high-impact decisions rather than making them implicitly.

#### 4. Temporal Evolution
The system is not static. Stories arrive incrementally. Earlier interpretations affect context for later ones. The system must distinguish between introducing something new versus extending/modifying what exists. Retroactive coherence is required — later stories may reveal that earlier interpretations need revision.

#### 5. Dual-Source Story Generation
Stories come from two sources:
- **User-provided**: Original MVP spec stories and subsequent additions
- **System-generated**: Prerequisites discovered during interpretation, technical necessities discovered during implementation, proactive suggestions based on patterns

All system-generated stories require user approval before processing.

### Constraints

1. **Human Authority**: The original prompt creator is the ultimate authority. They may have technical literacy but decisions should be framed in user-impact terms when possible.

2. **Local Development**: Infrastructure decisions are out of scope. All outputs must be locally runnable and testable.

3. **Platform Agnostic**: Target platform (web, mobile, CLI, API) is not predetermined. System proposes options; user decides.

4. **Incremental Processing**: Stories arrive over time. The system must handle additions without full reprocessing.

5. **Traceability**: Every technical task must trace back to its originating story and the decisions made during interpretation.

---

## Decision

We will implement a **staged pipeline architecture** with explicit human approval gates, decomposed into 8 distinct concerns (Chunks 0-7). Each chunk has a single responsibility and well-defined inputs/outputs.

### Architecture Overview

```
                                    ┌──────────────────┐
                                    │   User/System    │
                                    │  Story Source    │
                                    └────────┬─────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MVP SPECIFICATION                                    │
│                    (Enhanced - Chunk 0)                                      │
│  Structured format optimized for downstream processing                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PLATFORM & STACK PROPOSAL                                 │
│                         (Chunk 1)                                            │
│  Analyze requirements → Propose options → User decides                       │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ HUMAN DECISION GATE: Platform and technology stack selection        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       SYSTEM STATE MODEL                                     │
│                         (Chunk 2)                                            │
│  Initialize and maintain the "ground truth" of what exists                   │
│  Versioned, queryable, evolvable                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         STORY PROCESSING LOOP                                │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                  STORY INTERPRETATION ENGINE                          │  │
│  │                        (Chunk 3)                                      │  │
│  │  Parse → Identify ambiguities → Classify decisions → Check conflicts  │  │
│  │                                                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │ HUMAN ESCALATION: High-impact ambiguities requiring decision    │ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│                                    ▼                                         │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                  SYSTEM DESIGN EVOLUTION                              │  │
│  │                        (Chunk 4)                                      │  │
│  │  Map to capabilities → Detect conflicts → Retroactive coherence       │  │
│  │                                                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │ HUMAN APPROVAL: Significant architectural changes               │ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                       │  │
│  │  May generate: Prerequisite stories → Back to interpretation         │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│                                    ▼                                         │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                  TASK GENERATION & REFINEMENT                         │  │
│  │                        (Chunk 5)                                      │  │
│  │                                                                       │  │
│  │  Phase A: High-level tasks                                            │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │ HUMAN APPROVAL: Task breakdown and approach                     │ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  │  Phase B: Low-level refinement (files, functions, tests)              │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
└────────────────────────────────────┼─────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     IMPLEMENTATION EXECUTION                                 │
│                         (Chunk 6)                                            │
│  Task → Code → Test → Verify                                                 │
│  Integration with coding agents (Claude Code, etc.)                          │
│                                                                              │
│  May generate: Technical necessity stories → Back to interpretation          │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ HUMAN APPROVAL: System-discovered technical requirements            │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  Feedback: Implementation results update System State                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                   ORCHESTRATION & FEEDBACK LOOPS                             │
│                         (Chunk 7)                                            │
│  End-to-end flow control • Session management • Progress visibility          │
│  Human interaction patterns • Incremental story handling                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Chunk Summary

| Chunk | Name | Responsibility | Human Gates |
|-------|------|----------------|-------------|
| 0 | MVP Spec Enhancement | Define structured format for downstream optimization | None (design-time) |
| 1 | Platform & Stack Proposal | Analyze requirements, propose platform options | Platform/stack selection |
| 2 | System State Model | Maintain ground truth of system capabilities | None (automated) |
| 3 | Story Interpretation | Parse stories, surface ambiguities, classify decisions | High-impact ambiguities |
| 4 | System Design Evolution | Map stories to system changes, maintain coherence | Architectural changes |
| 5 | Task Generation | Produce implementable work items | Task approach approval |
| 6 | Implementation Execution | Execute tasks via coding agents | Technical necessities |
| 7 | Orchestration | Control flow, session management, progress | None (coordination) |

### Story Lifecycle

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   PENDING    │────▶│ INTERPRETING │────▶│   DESIGNED   │────▶│    TASKED    │
│              │     │              │     │              │     │              │
│ Awaiting     │     │ Ambiguities  │     │ System state │     │ Tasks        │
│ processing   │     │ being        │     │ updated      │     │ generated    │
│              │     │ resolved     │     │              │     │              │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                            │                                         │
                            ▼                                         ▼
                     ┌──────────────┐                          ┌──────────────┐
                     │   BLOCKED    │                          │ IMPLEMENTING │
                     │              │                          │              │
                     │ Awaiting     │                          │ Code being   │
                     │ human input  │                          │ written      │
                     └──────────────┘                          └──────────────┘
                                                                      │
                                                                      ▼
                                                               ┌──────────────┐
                                                               │  COMPLETED   │
                                                               │              │
                                                               │ Implemented  │
                                                               │ and verified │
                                                               └──────────────┘
```

*Note: CONFLICTED state removed for POC. If conflicts arise, user manually triggers re-interpretation.*

### System-Generated Stories

The system may generate stories from three sources:

1. **Prerequisite Discovery** (Chunk 3-4): During interpretation, the system discovers unstated dependencies
   - Example: "Feature X requires user authentication" → generates auth story
   - Example: "Multi-user feature requires user accounts" → generates user management story

2. **Technical Necessity** (Chunk 6): During implementation, technical requirements emerge
   - Example: "Data model changes require migration system" → generates migration story
   - Example: "File uploads require storage abstraction" → generates storage story

3. **Proactive Suggestions** (Chunk 4): Pattern-based recommendations
   - Example: "Success metrics defined but no tracking" → suggests analytics story
   - Example: "User-facing errors but no logging" → suggests observability story

All system-generated stories enter the pipeline as PENDING and require explicit user approval before processing.

---

## Consequences

### Positive

1. **Explicit Uncertainty Handling**: Ambiguities are surfaced and resolved rather than silently assumed
2. **Human Control**: High-impact decisions always escalate to the user
3. **Coherence**: Single system state model prevents interpretation drift
4. **Traceability**: Every task traces back through decisions to original stories
5. **Incremental**: Supports story arrival over time without full reprocessing
6. **Modular**: Each chunk can be developed, tested, and refined independently
7. **High Granularity**: 8 chunks enable testing of small iterations

### Negative

1. **Complexity**: 8 interacting components require careful orchestration
2. **Latency**: Human approval gates introduce waiting time (acceptable for POC)
3. **State Management**: Single state file must be kept consistent

### Risks

1. **Scope Creep**: System-generated stories could expand scope indefinitely
2. **AI Quality**: Claude Code may produce incorrect implementations

### Mitigations

1. **Scope Guards**: Require explicit user confirmation for scope-expanding suggestions
2. **Iterative Refinement**: If AI produces wrong code, refine specifications and retry

---

## Implementation Plan

Each chunk will be detailed in a separate mini-ADR:

| Document | Chunk | Status | Dependencies |
|----------|-------|--------|--------------|
| [ADR-001a](./ADR-001a-mvp-spec-enhancement.md) | MVP Spec Enhancement | Proposed | None |
| [ADR-001b](./ADR-001b-platform-stack-proposal.md) | Platform & Stack Proposal | Pending | ADR-001a |
| [ADR-001c](./ADR-001c-system-state-model.md) | System State Model | Pending | ADR-001a |
| [ADR-001d](./ADR-001d-story-interpretation-engine.md) | Story Interpretation | Pending | ADR-001c |
| [ADR-001e](./ADR-001e-system-design-evolution.md) | System Design Evolution | Pending | ADR-001c, ADR-001d |
| [ADR-001f](./ADR-001f-task-generation-refinement.md) | Task Generation | Pending | ADR-001e |
| [ADR-001g](./ADR-001g-implementation-execution.md) | Implementation Execution | Pending | ADR-001f |
| [ADR-001h](./ADR-001h-orchestration-feedback-loops.md) | Orchestration | Pending | All above |

### Recommended Order

1. **ADR-001a** (MVP Spec Enhancement) — Defines input format for all downstream chunks
2. **ADR-001c** (System State Model) — Defines the ground truth all chunks reference
3. **ADR-001b** (Platform & Stack) — First runtime decision point
4. **ADR-001d** through **ADR-001h** — Sequential based on data flow

---

## Related Documents

- [Architecture Overview](../architecture.md)
- [MVP Specification Stage](../../haytham/phases/README.md)
- [Burr Workflow Engine](../phased-workflow.md)

---

## Resolved Questions

1. **Approval Batching Strategy**: ~~How do we group decisions?~~ → **No batching for POC**. Sequential approvals are acceptable.

2. **Retroactive Coherence Bounds**: ~~How far back should revisions propagate?~~ → **Deferred for POC**. If interpretation is wrong, user manually triggers re-interpretation.

3. **Coding Agent Selection**: ~~Multiple agents or one?~~ → **Claude Code only** for POC. No multi-agent abstraction.

4. **State Model Complexity**: ~~Multi-file YAML?~~ → **Single JSON file** for simplicity.

## Resolved Questions (POC)

1. **System-Generated Story Limits**: ~~Should there be guardrails?~~ → **Yes, max 3 system-generated stories per user story.** Each requires explicit user approval.

---

## Out of Scope for POC

The following features are explicitly excluded from POC to minimize complexity:

- **User authentication / authorization** — Apps are single-user or no auth
- **Multi-tenancy** — Single tenant only
- **Mobile apps** — Web only (single platform)
- **Cloud hosting / deployment** — Local development only
- **Real-time features** — No WebSockets, polling acceptable
- **File uploads / media handling** — Text data only
- **Email / notifications** — No external messaging
- **Payment processing** — No financial transactions
- **Analytics / telemetry** — No tracking infrastructure
- **Third-party API integrations** — No external service dependencies
- **Background jobs / queues** — Synchronous processing only
- **Full-text search** — Basic filtering only, no FTS infrastructure

If a startup idea requires any of these, the system should:
1. Flag it as an uncertainty during interpretation
2. Ask user to simplify or confirm it's truly needed
3. If confirmed, warn that implementation may be incomplete

---

## Future Enhancements

- Batch approval of multiple decisions at once
- Parallel story processing
- Learning from user decisions to auto-resolve similar ambiguities
- Multi-platform support (web + mobile)
- Version history and rollback

---

## Decision Outcome

**Status**: Proposed (POC Simplifications Applied)

**Progress**:
- ADR-001 (Master): Proposed ✓
- ADR-001a (MVP Spec Enhancement): Proposed ✓
- ADR-001b (Platform & Stack Proposal): Proposed ✓
- ADR-001c (System State Model): Proposed ✓
- ADR-001d (Story Interpretation Engine): Proposed ✓
- ADR-001e (System Design Evolution): Proposed ✓
- ADR-001f (Task Generation & Refinement): Proposed ✓
- ADR-001g (Implementation Execution): Proposed ✓
- ADR-001h (Orchestration & Feedback Loops): Proposed ✓

**POC Test Case**: Simple Notes App
- 3-4 P0 stories (Create note, List notes, Search notes, Delete note)
- 2 entities (User, Note)
- Minimal ambiguity surface for clean demonstration

**Next Step**: Extend existing Burr workflow by:
1. Renaming `create_validation_workflow()` to reflect full pipeline scope
2. Adding new actions after `mvp_specification`: `stack_selection` → `initialize_state` → story processing loop
3. Modifying `worker_mvp_specification` agent to output enhanced format with IDs and entities
