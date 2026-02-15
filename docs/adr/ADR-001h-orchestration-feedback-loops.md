# ADR-001h: Orchestration & Feedback Loops

**Status**: Proposed
**Date**: 2025-01-02
**Parent**: [ADR-001: Story-to-Implementation Pipeline](./ADR-001-story-to-implementation-pipeline.md)
**Depends On**: All previous ADRs (001a through 001g)
**Scope**: End-to-end coordination, session management, and feedback integration

---

## POC Simplifications

- **Orchestration**: Burr workflow manages the pipeline (extends existing graph)
- **Session State**: Single state.json file, saved after each operation
- **No Checkpoints**: State is saved continuously; no snapshot/recovery system
- **No Batching**: Approvals presented one at a time as they arise
- **Sequential Processing**: One story at a time through the pipeline
- **Test Case**: Notes App with 4 stories (Create, List, Search, Delete)

**Example for Notes App:**
```
Pipeline flow:
1. MVP spec → Stack selection (user picks Python/FastAPI + React)
2. Initialize state.json with 4 stories
3. Process S-001 (Create Note): interpret → design → tasks → execute
4. Process S-002, S-003, S-004 the same way
5. Done → working Notes App
```

---

## Context

The previous ADRs define individual stages of the pipeline. This ADR defines how these stages work together via Burr.

---

## Decision

Extend the existing Burr workflow graph to orchestrate the story-to-implementation pipeline:

1. Add new actions after `mvp_specification`
2. Process stories sequentially through all chunks
3. Present approvals to user at each human gate
4. Save state.json after each operation

---

## Burr Workflow Extension

```
[Existing Burr Graph]
        │
        ▼
┌───────────────────┐
│ mvp_specification │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ stack_selection   │ ◄── Human gate: choose stack
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ initialize_state  │ ◄── Create state.json
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ process_story     │ ◄── Loop: interpret → design → tasks → execute
└─────────┬─────────┘
          │
    ┌─────┴─────┐
    ▼           ▼
┌───────┐   ┌───────────┐
│ done  │   │ next_story│──┐
└───────┘   └───────────┘  │
                    ▲      │
                    └──────┘
```

---

## Human Gates

Approvals are presented one at a time as they arise:

| Gate | When | User Action |
|------|------|-------------|
| Stack Selection | After MVP spec | Choose platform/stack |
| Ambiguity Resolution | Story has ambiguities | Answer questions |
| Design Approval | New entities/capabilities | Approve or modify |
| Task Approval | Tasks generated | Approve breakdown |
| Technical Discovery | During implementation | Decide how to proceed |

### Example: Ambiguity Resolution

```markdown
## Story S-003: Search Notes

I need a decision to continue:

**What fields should the search include?**
- A) Title only
- B) Title and content (recommended)
- C) Full-text search

Your choice: _
```

---

## Story Processing

Stories are processed sequentially in priority order (P0 first).

```json
{
  "stories": [
    {"id": "S-001", "title": "Create Note", "priority": "P0", "status": "pending"},
    {"id": "S-002", "title": "List Notes", "priority": "P0", "status": "pending"},
    {"id": "S-003", "title": "Search Notes", "priority": "P0", "status": "pending"},
    {"id": "S-004", "title": "Delete Note", "priority": "P0", "status": "pending"}
  ]
}
```

Processing order:
1. Get next pending story (by priority, then by ID)
2. Process through all chunks (interpret → design → tasks → execute)
3. Mark as completed
4. Repeat until all stories done

---

## State Persistence

State is saved to `session/state.json` after each operation.

```
session/
└── state.json    # Single state file (see ADR-001c)
```

State is saved after:
- Each story status change
- Each task completion
- Each decision is recorded

If interrupted, re-run from the last saved state.

---

## Feedback Handling

### Technical Discovery

If implementation discovers something unexpected:
1. Pause execution
2. Present discovery to user
3. User decides: add task, modify approach, or skip
4. Continue

### Design Issues

If design conflicts arise:
1. Present conflict to user
2. User makes decision
3. Update state.json with decision
4. Continue

No automatic retroactive coherence for POC - user manually handles any rework needed.

---

## Progress Visibility

Simple progress tracking in state.json:

```json
{
  "current_story": "S-003",
  "current_stage": "execute_tasks",
  "stories_completed": 2,
  "stories_total": 4,
  "current_task": "T-005"
}
```

---

## Consequences

### Positive

1. **Simple**: Burr manages flow, state.json tracks everything
2. **Recoverable**: Can resume from saved state
3. **Transparent**: Clear progress through stories

### Negative

1. **Sequential only**: No parallel story processing
2. **Manual recovery**: User handles conflicts and rework

---

## Next Steps

Upon approval:

1. Add new Burr actions for story processing
2. Implement human gate prompts
3. Create state persistence layer
4. Test end-to-end with Notes App

---

## Related Documents

- [ADR-001: Story-to-Implementation Pipeline](./ADR-001-story-to-implementation-pipeline.md) (parent)
- All previous chunk ADRs (001a through 001g)
