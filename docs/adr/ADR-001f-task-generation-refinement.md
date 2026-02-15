# ADR-001f: Task Generation & Refinement

**Status**: Proposed
**Date**: 2025-01-02
**Parent**: [ADR-001: Story-to-Implementation Pipeline](./ADR-001-story-to-implementation-pipeline.md)
**Depends On**: [ADR-001e: System Design Evolution](./ADR-001e-system-design-evolution.md)
**Scope**: Producing actionable technical tasks from designed stories

---

## POC Simplifications

- **Task ID Scheme**: Simple T-XXX (e.g., T-001, T-002) — no HL/LL distinction
- **Task Storage**: Tasks stored in state.json, not separate files
- **Test Case**: Notes App with simple task breakdown
- **Task Format**: Simplified schema focused on essential fields only

**Example for Notes App:**
```
Story S-003 (Search Notes) tasks:
- T-005: Add search endpoint to API
- T-006: Add search input to frontend
- T-007: Write search tests
```

---

## Context

After a story has been interpreted (Chunk 3) and its design impact determined (Chunk 4), we must produce **actionable technical tasks** that can be executed by coding agents or human developers.

The challenge is bridging the gap between:
- **Design level**: "We need a ShareLink entity and Content Sharing capability"
- **Implementation level**: "Create file `src/models/share_link.py` with SQLAlchemy model..."

This bridge must be:
1. **Decomposed appropriately** — Not too coarse (vague), not too fine (micromanagement)
2. **Ordered correctly** — Dependencies respected
3. **Traceable** — Every task links back to stories and design decisions
4. **Verifiable** — Clear criteria for task completion
5. **Executable** — Contains enough detail for implementation

### Approach

For POC, we use a **single-phase task generation**:

1. Generate tasks from designed stories
2. Present task breakdown to user for approval
3. Execute approved tasks with Claude Code

---

## Decision

Implement a **task generation system** that:

1. Generates task breakdown from designed stories
2. Presents tasks to user for approval
3. Stores tasks in state.json
4. Outputs in a format consumable by Claude Code

---

## Task Storage

Tasks are stored in the `tasks` array in state.json (see ADR-001c for full schema).

```json
{
  "tasks": [
    {
      "id": "T-001",
      "story_id": "S-001",
      "title": "Define Note model",
      "status": "completed",
      "description": "Create SQLAlchemy model for Note entity",
      "file_path": "backend/src/models/note.py"
    }
  ]
}
```

---

## Task Generation

### Task Schema

```json
{
  "id": "T-005",
  "story_id": "S-003",
  "title": "Add search endpoint to API",
  "status": "pending",
  "description": "Create GET /api/notes/search endpoint",
  "file_path": null
}
```

### Generation Rules

For each designed story, generate tasks based on:

1. **Backend tasks**: API endpoints, services, models
2. **Frontend tasks**: Components, pages, state
3. **Test tasks**: Unit and integration tests

### Example: Tasks for S-003 (Search Notes)

```json
{
  "tasks": [
    {
      "id": "T-005",
      "story_id": "S-003",
      "title": "Add search endpoint to API",
      "status": "pending",
      "description": "Create GET /api/notes/search?q=keyword endpoint"
    },
    {
      "id": "T-006",
      "story_id": "S-003",
      "title": "Add search input to frontend",
      "status": "pending",
      "description": "Add search bar to notes list page"
    },
    {
      "id": "T-007",
      "story_id": "S-003",
      "title": "Write search tests",
      "status": "pending",
      "description": "Unit tests for search endpoint and component"
    }
  ]
}
```

### User Approval Presentation

```markdown
## Task Breakdown: Search Notes (S-003)

Here's how I plan to build the search feature:

---

### Tasks

1. **T-005: Add search endpoint to API**
   - Create GET /api/notes/search?q=keyword
   - Use SQLite LIKE for matching

2. **T-006: Add search input to frontend**
   - Add search bar to notes list
   - Wire up to API endpoint

3. **T-007: Write search tests**
   - API endpoint tests
   - Component tests

---

[Approve] [Request Changes]
```

---

## Task Execution Order

Tasks are executed sequentially in the order they appear in the tasks array. For POC, we don't implement complex dependency graphs - tasks are simply processed in order.

---

## Task Output for Claude Code

Tasks are passed to Claude Code as simple prompts:

### Prompt Format

```markdown
## Task: T-005 - Add search endpoint to API

**Story**: S-003 (Search Notes)
**Stack**: Python/FastAPI backend, SQLite database

### Description
Create GET /api/notes/search?q=keyword endpoint

### Requirements
1. Accept 'q' query parameter for search term
2. Search Note title and content using LIKE
3. Return matching notes for the current user

### Expected Output
- New endpoint in backend/src/api/routes/notes.py
- Tests in backend/tests/api/test_notes.py
```

---

## Traceability

Each task links back to its story via the `story_id` field. After completion, the `file_path` field records what was created.

---

## Consequences

### Positive

1. **Simple**: Tasks stored in state.json, no separate files
2. **Traceable**: Each task links to its story
3. **Executable**: Clear format for Claude Code

### Negative

1. **Sequential only**: No parallel task execution for POC
2. **Manual recovery**: If task fails, user decides next steps

---

## Next Steps

Upon approval:

1. Implement task generator
2. Create prompt formatter for Claude Code
3. Proceed to ADR-001g (Implementation Execution)

---

## Related Documents

- [ADR-001: Story-to-Implementation Pipeline](./ADR-001-story-to-implementation-pipeline.md) (parent)
- [ADR-001e: System Design Evolution](./ADR-001e-system-design-evolution.md) (input)
- [ADR-001g: Implementation Execution](./ADR-001g-implementation-execution.md) (next stage)
