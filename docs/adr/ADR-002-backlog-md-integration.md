# ADR-002: Backlog.md Integration for Task Management

## Status
**Superseded** - 2026-01-26

This ADR has been superseded by direct integration in the story generation stage.
See `haytham/workflow/stage_executor.py::_create_backlog_drafts_from_stories()`.

## Original Context

The Story-to-Implementation Pipeline (ADR-001 series) generates tasks that are stored in `project.yaml` under the `pipeline.tasks` field. While functional, this approach has limitations:

1. **Human Readability**: YAML nested structures are difficult for humans to scan and edit
2. **Collaboration**: No built-in visualization or tracking beyond the YAML file
3. **AI Agent Integration**: Coding agents like Claude Code need a clear, standardized format
4. **Workflow Visibility**: Difficult to see task status, dependencies, and progress at a glance

We chose **Backlog.md** because:

- **Markdown-native**: Tasks are individual `.md` files, human-readable and Git-friendly
- **AI-ready**: Built-in support for Claude Code, Gemini CLI, and other coding agents
- **CLI-first**: Full CLI for programmatic access without external APIs
- **Self-contained**: 100% offline, no external services required
- **Visualization**: Terminal Kanban board and web interface included

## Current Implementation (2026-01-26)

The original design proposed two agents (`TaskManagerAgent`, `TaskExecutorAgent`) but this was overly complex. The current implementation uses direct integration:

### Architecture

```
Story Generator Agent
        ↓
StoryGenerationOutput (structured)
        ↓
_create_backlog_drafts_from_stories()
        ↓
backlog/drafts/*.md
```

### Key Components

**BacklogCLI** (`haytham/backlog/cli.py`): Python wrapper for `backlog` CLI commands
- `create_draft()`, `promote_draft()`
- `update_status()`, `add_notes()`
- `list_tasks()`, `list_drafts()`

**_create_backlog_drafts_from_stories()** (`haytham/workflow/stage_executor.py`):
- Called automatically after story generation
- Creates one draft per story with full technical specification
- Labels by layer (layer-0, layer-1, etc.) and capability
- Sets priority based on layer (Layer 0-1 = high, others = medium)

### Workflow

1. **Story Generation Stage** → Generates `StoryGenerationOutput` (structured)
2. **Automatic Draft Creation** → Creates drafts in `backlog/drafts/`
3. **Human Review** → `backlog board` or `backlog browser`
4. **Draft Promotion** → `backlog draft promote <id>`
5. **Implementation** → Claude Code or manual development

## Removed Components

The following were removed as part of simplification:

- `haytham/backlog/task_manager.py` - TaskManagerAgent (used old PipelineState model)
- `haytham/backlog/task_executor_agent.py` - TaskExecutorAgent (unused)
- `tests/task_manager_tests.py` - Tests for removed code

## Prerequisites

```bash
# Install Backlog.md
npm i -g backlog.md
# or
brew install backlog-md
```

## References

- [Backlog.md GitHub](https://github.com/MrLesk/Backlog.md)
- [Story Generator Agent](../../haytham/agents/worker_story_generator/)
