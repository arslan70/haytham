# ADR-001g: Implementation Execution

**Status**: Proposed
**Date**: 2025-01-02
**Parent**: [ADR-001: Story-to-Implementation Pipeline](./ADR-001-story-to-implementation-pipeline.md)
**Depends On**: [ADR-001f: Task Generation & Refinement](./ADR-001f-task-generation-refinement.md)
**Scope**: Executing tasks to produce working code

---

## POC Simplifications

- **Coding Agent**: Claude Code only — no multi-agent abstraction
- **Execution**: Sequential task execution, no parallelization
- **Verification**: Run tests after each task; if tests fail, ask Claude Code to fix
- **State Updates**: Update state.json after each completed task
- **Error Handling**: If task fails repeatedly, block and ask user

**Example for Notes App:**
```
Executing T-005 (Add search endpoint to API):
1. Send task prompt to Claude Code
2. Claude Code creates/modifies files
3. Run tests
4. If pass: mark T-005 complete, update state.json
5. If fail: ask Claude Code to fix, retry up to 3 times
```

---

## Context

With tasks generated (Chunk 5), we must now execute them to produce working code using Claude Code.

### Key Challenges

1. **Task Execution**: Process tasks sequentially
2. **Verification**: Ensure tasks are correctly completed
3. **State Updates**: System state must reflect what's been built
4. **Error Handling**: Failures must be managed gracefully

### Constraints

1. **Local Development Only**: All code runs locally
2. **Claude Code Only**: Single coding agent for POC
3. **Testable Output**: All implementations should include tests

---

## Decision

Implement a simple **task execution loop** that:

1. Processes tasks sequentially from state.json
2. Sends each task to Claude Code
3. Runs tests to verify completion
4. Updates state.json with results
5. Retries on failure, escalates to user if stuck

---

## Execution Flow

```
┌─────────────────┐
│  Get next task  │
│  from state.json│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Send prompt to │
│   Claude Code   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Run tests     │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌───────┐  ┌───────┐
│ PASS  │  │ FAIL  │
└───┬───┘  └───┬───┘
    │          │
    ▼          ▼
┌───────┐  ┌────────────┐
│Update │  │Ask Claude  │
│state  │  │Code to fix │
│next   │  │(max 3x)    │
│task   │  └─────┬──────┘
└───────┘        │
                 ▼
           ┌───────────┐
           │Still fail?│
           │Ask user   │
           └───────────┘
```

---

## Claude Code Integration

For POC, we use Claude Code directly via the Burr workflow.

### Task Prompt Format

```markdown
## Task: {task_id} - {task_title}

**Story**: {story_id} ({story_title})
**Stack**: Python/FastAPI backend, React/TypeScript frontend, SQLite database

### Description
{task_description}

### Requirements
{requirements_list}

### Existing Code
{relevant_file_paths}

### Expected Output
- Files to create/modify
- Tests to add

Please implement this task. Run the tests when done.
```

### Example: T-005 (Search Endpoint)

```markdown
## Task: T-005 - Add search endpoint to API

**Story**: S-003 (Search Notes)
**Stack**: Python/FastAPI backend, SQLite database

### Description
Create GET /api/notes/search?q=keyword endpoint

### Requirements
1. Accept 'q' query parameter for search term
2. Search Note title and content using SQLite LIKE
3. Return matching notes for the current user
4. Handle empty search term (return all notes)

### Existing Code
- backend/src/models/note.py (Note model)
- backend/src/api/routes/notes.py (existing note routes)

### Expected Output
- Add search endpoint to backend/src/api/routes/notes.py
- Add test in backend/tests/api/test_notes.py

Please implement this task. Run the tests when done.
```

---

## Task States

Tasks have simple states stored in state.json:

| State | Description |
|-------|-------------|
| `pending` | Not yet started |
| `in_progress` | Currently being executed |
| `completed` | Successfully finished |
| `failed` | Failed after retries, needs user input |

---

## Verification

For POC, verification is simple: **run the tests**.

```bash
# After Claude Code completes a task
pytest backend/tests/ -v
```

If tests pass, the task is marked complete. If tests fail, Claude Code is asked to fix the issue.

---

## Technical Discovery Handling

If Claude Code discovers something unexpected during implementation (missing dependency, design issue, etc.):

1. Claude Code reports the discovery
2. Execution pauses
3. User is presented with the issue
4. User decides: add new task, modify approach, or skip

For POC, this is handled manually - the user decides how to proceed.

---

## State Updates

After each task completes:

1. Update task status to `completed` in state.json
2. Set `file_path` to the main file created/modified
3. Check if all story tasks are complete → update story status

```json
{
  "tasks": [
    {
      "id": "T-005",
      "story_id": "S-003",
      "title": "Add search endpoint to API",
      "status": "completed",
      "file_path": "backend/src/api/routes/notes.py"
    }
  ]
}
```

---

## Error Handling

Simple retry strategy for POC:

1. **Test failure**: Ask Claude Code to fix (up to 3 attempts)
2. **Still failing**: Mark task as `failed`, ask user what to do
3. **User options**:
   - Provide guidance and retry
   - Skip task and continue
   - Abort story implementation

---

## Consequences

### Positive

1. **Simple**: Claude Code only, no agent abstraction
2. **Verified**: Tests run after each task
3. **Recoverable**: User can intervene when stuck

### Negative

1. **Sequential**: No parallel task execution
2. **Manual recovery**: User must decide on failures

---

## Next Steps

Upon approval:

1. Implement task execution loop in Burr
2. Create prompt formatter for Claude Code
3. Add test runner integration
4. Proceed to ADR-001h (Orchestration & Feedback Loops)

---

## Related Documents

- [ADR-001: Story-to-Implementation Pipeline](./ADR-001-story-to-implementation-pipeline.md) (parent)
- [ADR-001f: Task Generation & Refinement](./ADR-001f-task-generation-refinement.md) (input)
- [ADR-001h: Orchestration & Feedback Loops](./ADR-001h-orchestration-feedback-loops.md) (coordination)
