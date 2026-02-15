# ADR-001c: System State Model

**Status**: Proposed
**Date**: 2025-01-02
**Parent**: [ADR-001: Story-to-Implementation Pipeline](./ADR-001-story-to-implementation-pipeline.md)
**Depends On**: [ADR-001a: MVP Spec Enhancement](./ADR-001a-mvp-spec-enhancement.md)
**Scope**: Defining the "ground truth" representation of system state

---

## POC Simplifications

- **Single JSON File**: All state in one `state.json` file (not multi-file YAML)
- **No Snapshots/Versioning**: State is saved after each operation; no rollback mechanism
- **No Checksums**: Trust the file system
- **Retroactive Coherence**: Deferred — if state is wrong, user manually triggers re-interpretation
- **Simplified IDs**: Only S-XXX, E-XXX, T-XXX, D-XXX

---

## Context

The Story-to-Implementation Pipeline requires a shared understanding of "what exists" at any point in time. Without this:

1. **Story interpretation drifts** — Each story is interpreted in isolation
2. **Conflicts go undetected** — New stories may contradict earlier decisions
3. **Implementation has no reference** — Coding agents don't know what's already built

### What System State Must Capture

| Concern | Question It Answers | Example |
|---------|---------------------|---------|
| **Entities** | What data structures exist? | Note entity with title, content, created_at |
| **Stories** | What features are we building? | S-001: Create Note |
| **Tasks** | What work items exist? | T-001: Define Note model |
| **Decisions** | What choices were made? | D-001: Use SQLite for simplicity |
| **Stack** | What technology are we using? | Python + React |

---

## Decision

Implement a **single JSON state file** that contains all system state. This file is:
- Human-readable (formatted JSON)
- Machine-parseable
- Saved after each state change
- Loaded on startup

---

## State Schema

### File Location

```
session/
└── state.json          # Single state file
```

### Complete Schema

```json
{
  "schema_version": "1.0",
  "project": {
    "name": "Simple Notes App",
    "description": "A simple notes app where users can create, organize, and search their notes",
    "created_at": "2025-01-02T10:00:00Z"
  },

  "stack": {
    "platform": "web_application",
    "backend": {
      "language": "python",
      "framework": "fastapi",
      "database": "sqlite",
      "orm": "sqlalchemy"
    },
    "frontend": {
      "language": "typescript",
      "framework": "react",
      "bundler": "vite"
    }
  },

  "entities": [
    {
      "id": "E-001",
      "name": "User",
      "status": "implemented",
      "attributes": [
        {"name": "id", "type": "UUID", "primary_key": true},
        {"name": "email", "type": "String", "unique": true},
        {"name": "name", "type": "String"},
        {"name": "created_at", "type": "DateTime"}
      ],
      "relationships": [
        {"type": "has_many", "target": "E-002", "foreign_key": "user_id"}
      ],
      "source_story": "S-001",
      "file_path": "backend/src/models/user.py"
    },
    {
      "id": "E-002",
      "name": "Note",
      "status": "implemented",
      "attributes": [
        {"name": "id", "type": "UUID", "primary_key": true},
        {"name": "title", "type": "String"},
        {"name": "content", "type": "Text"},
        {"name": "user_id", "type": "UUID", "foreign_key": "E-001"},
        {"name": "created_at", "type": "DateTime"},
        {"name": "updated_at", "type": "DateTime"}
      ],
      "relationships": [
        {"type": "belongs_to", "target": "E-001"}
      ],
      "source_story": "S-001",
      "file_path": "backend/src/models/note.py"
    }
  ],

  "stories": [
    {
      "id": "S-001",
      "title": "Create Note",
      "priority": "P0",
      "status": "completed",
      "user_story": "As a user, I want to create a new note so that I can capture my thoughts",
      "acceptance_criteria": [
        "Given I am logged in, when I click New Note, then a blank note editor opens",
        "Given I have entered content, when I click Save, then the note is persisted"
      ],
      "depends_on": ["E-001", "E-002"],
      "ambiguities": [
        {
          "question": "Max note length?",
          "classification": "auto-resolvable",
          "default": "10000 characters",
          "resolved": true
        }
      ],
      "tasks": ["T-001", "T-002", "T-003"]
    },
    {
      "id": "S-002",
      "title": "List Notes",
      "priority": "P0",
      "status": "pending",
      "user_story": "As a user, I want to see all my notes so that I can find what I need",
      "acceptance_criteria": [
        "Given I am logged in, when I view the notes page, then I see a list of my notes",
        "Notes are sorted by last updated, newest first"
      ],
      "depends_on": ["E-001", "E-002"],
      "ambiguities": [],
      "tasks": []
    }
  ],

  "tasks": [
    {
      "id": "T-001",
      "story_id": "S-001",
      "title": "Define Note model",
      "status": "completed",
      "description": "Create SQLAlchemy model for Note entity",
      "file_path": "backend/src/models/note.py"
    },
    {
      "id": "T-002",
      "story_id": "S-001",
      "title": "Create note API endpoint",
      "status": "completed",
      "description": "POST /api/notes endpoint",
      "file_path": "backend/src/api/notes.py"
    },
    {
      "id": "T-003",
      "story_id": "S-001",
      "title": "Write tests for note creation",
      "status": "completed",
      "description": "Unit and integration tests",
      "file_path": "backend/tests/test_notes.py"
    }
  ],

  "decisions": [
    {
      "id": "D-001",
      "title": "Use SQLite for database",
      "rationale": "Simple, no setup required, sufficient for MVP",
      "made_at": "2025-01-02T10:00:00Z",
      "affects": ["E-001", "E-002"]
    }
  ],

  "current": {
    "story": "S-002",
    "chunk": "story-interpretation"
  }
}
```

---

## Operations

### Loading State

```python
import json
from pathlib import Path

def load_state(state_path: Path = Path("session/state.json")) -> dict:
    """Load system state from JSON file."""
    if not state_path.exists():
        return create_initial_state()

    with open(state_path) as f:
        return json.load(f)
```

### Saving State

```python
def save_state(state: dict, state_path: Path = Path("session/state.json")) -> None:
    """Save system state to JSON file."""
    state_path.parent.mkdir(parents=True, exist_ok=True)

    with open(state_path, 'w') as f:
        json.dump(state, f, indent=2)
```

### Initialization from MVP Spec

```python
def initialize_state(mvp_spec: dict, stack: dict) -> dict:
    """Create initial state from MVP specification and stack choice."""

    state = {
        "schema_version": "1.0",
        "project": {
            "name": mvp_spec["name"],
            "description": mvp_spec["description"],
            "created_at": datetime.utcnow().isoformat()
        },
        "stack": stack,
        "entities": [],
        "stories": [],
        "tasks": [],
        "decisions": [],
        "current": {
            "story": None,
            "chunk": "initialization"
        }
    }

    # Import entities from MVP spec domain model
    for entity in mvp_spec.get("domain_model", {}).get("entities", []):
        state["entities"].append({
            "id": entity["id"],
            "name": entity["name"],
            "status": "planned",
            "attributes": entity["attributes"],
            "relationships": entity.get("relationships", []),
            "source_story": None,
            "file_path": None
        })

    # Import stories from MVP spec
    for story in mvp_spec.get("stories", []):
        state["stories"].append({
            "id": story["id"],
            "title": story["title"],
            "priority": story["priority"],
            "status": "pending",
            "user_story": story["user_story"],
            "acceptance_criteria": story["acceptance_criteria"],
            "depends_on": story.get("depends_on", []),
            "ambiguities": [],
            "tasks": []
        })

    return state
```

### Query Helpers

```python
class StateQueries:
    """Simple query helpers for state."""

    def __init__(self, state: dict):
        self.state = state

    def get_entity(self, entity_id: str) -> dict | None:
        for e in self.state["entities"]:
            if e["id"] == entity_id:
                return e
        return None

    def entity_exists(self, name: str) -> bool:
        return any(e["name"] == name for e in self.state["entities"])

    def get_story(self, story_id: str) -> dict | None:
        for s in self.state["stories"]:
            if s["id"] == story_id:
                return s
        return None

    def get_pending_stories(self) -> list[dict]:
        return [s for s in self.state["stories"] if s["status"] == "pending"]

    def get_story_tasks(self, story_id: str) -> list[dict]:
        return [t for t in self.state["tasks"] if t["story_id"] == story_id]
```

### Update Helpers

```python
class StateUpdater:
    """Simple update helpers for state."""

    def __init__(self, state: dict):
        self.state = state

    def add_entity(self, entity: dict) -> None:
        self.state["entities"].append(entity)

    def update_entity_status(self, entity_id: str, status: str, file_path: str = None) -> None:
        entity = StateQueries(self.state).get_entity(entity_id)
        if entity:
            entity["status"] = status
            if file_path:
                entity["file_path"] = file_path

    def add_story(self, story: dict) -> None:
        self.state["stories"].append(story)

    def update_story_status(self, story_id: str, status: str) -> None:
        story = StateQueries(self.state).get_story(story_id)
        if story:
            story["status"] = status

    def add_task(self, task: dict) -> None:
        self.state["tasks"].append(task)
        # Also update story's task list
        story = StateQueries(self.state).get_story(task["story_id"])
        if story and task["id"] not in story["tasks"]:
            story["tasks"].append(task["id"])

    def update_task_status(self, task_id: str, status: str) -> None:
        for task in self.state["tasks"]:
            if task["id"] == task_id:
                task["status"] = status
                break

    def add_decision(self, decision: dict) -> None:
        self.state["decisions"].append(decision)

    def set_current(self, story_id: str, chunk: str) -> None:
        self.state["current"]["story"] = story_id
        self.state["current"]["chunk"] = chunk
```

---

## Example: Notes App Initial State

After MVP spec processing and stack selection:

```json
{
  "schema_version": "1.0",
  "project": {
    "name": "Simple Notes App",
    "description": "A simple notes app where users can create, organize, and search their notes",
    "created_at": "2025-01-02T10:00:00Z"
  },
  "stack": {
    "platform": "web_application",
    "backend": {"language": "python", "framework": "fastapi", "database": "sqlite"},
    "frontend": {"language": "typescript", "framework": "react"}
  },
  "entities": [
    {"id": "E-001", "name": "User", "status": "planned", "attributes": [...], "relationships": [...]},
    {"id": "E-002", "name": "Note", "status": "planned", "attributes": [...], "relationships": [...]}
  ],
  "stories": [
    {"id": "S-001", "title": "Create Note", "priority": "P0", "status": "pending", ...},
    {"id": "S-002", "title": "List Notes", "priority": "P0", "status": "pending", ...},
    {"id": "S-003", "title": "Search Notes", "priority": "P0", "status": "pending", ...},
    {"id": "S-004", "title": "Delete Note", "priority": "P0", "status": "pending", ...}
  ],
  "tasks": [],
  "decisions": [],
  "current": {"story": null, "chunk": "ready"}
}
```

---

## Consequences

### Positive

1. **Simple**: One file, easy to understand and debug
2. **Human Readable**: Formatted JSON is inspectable
3. **No Dependencies**: Just file I/O, no database
4. **Fast**: In-memory operations, occasional disk writes
5. **Portable**: Copy the file to move/backup state

### Negative

1. **No History**: Can't see what changed over time (acceptable for POC)
2. **No Rollback**: Can't undo changes (user re-runs if needed)
3. **File Size**: Could grow large (unlikely for POC scope)

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| File corruption | Low | High | JSON is robust; user can restore from git |
| State grows too large | Low | Low | POC has limited stories |

---

## Resolved Questions

1. ~~Snapshot Granularity~~ → **No snapshots for POC**
2. ~~Concurrent Updates~~ → **Sequential processing only for POC**
3. ~~Cross-Story Dependencies~~ → **Process stories sequentially for POC**

---

## Next Steps

Upon approval:

1. Implement `SystemState` class with load/save/query/update
2. Implement initialization from MVP spec
3. Proceed to ADR-001d (Story Interpretation Engine)

---

## Related Documents

- [ADR-001: Story-to-Implementation Pipeline](./ADR-001-story-to-implementation-pipeline.md) (parent)
- [ADR-001a: MVP Spec Enhancement](./ADR-001a-mvp-spec-enhancement.md) (input format)
- [ADR-001d: Story Interpretation Engine](./ADR-001d-story-interpretation-engine.md) (consumer)
