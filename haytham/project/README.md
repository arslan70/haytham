# Project Management System

The Project Management System provides CRUD operations, session management, and version tracking for Haytham's phased workflow architecture.

## Overview

A **project** represents one startup idea with multiple **sessions** (iterations/refinements). Each session produces a versioned `requirements.md` output.

## Directory Structure

```
projects/{project_id}/
├── project.yaml                 # Project config and state
├── sessions/
│   └── {session_id}/           # Session-specific data
│       ├── session_manifest.md
│       └── phase_*/            # Phase directories
├── outputs/
│   ├── latest_requirements.md
│   ├── requirements_v1.md
│   └── requirements_v2.md
└── history/
    └── changelog.md
```

## Key Features

- **Multi-project support**: Users can have multiple projects
- **Version tracking**: Each session produces a numbered version
- **User preferences**: Persistent storage of strategic decisions
- **Session resume**: Can resume from any checkpoint
- **Project lifecycle**: Create, archive, delete projects

## Usage

```python
from haytham.project import ProjectManager

# Initialize
pm = ProjectManager(base_dir="projects")

# Create project
project = pm.create_project(
    user_id="user_123",
    startup_idea="Your startup idea here",
    project_name="My Project",
    execution_mode="mvp"  # or "full"
)

# Start session
session = pm.start_session(project["project_id"])

# Update preferences (Phase 3)
pm.update_user_preferences(
    project["project_id"],
    {
        "target_niche": "Solo founders",
        "business_model": "SaaS",
        "pricing_strategy": "usage-based"
    }
)

# Complete session
pm.complete_session(
    project_id=project["project_id"],
    session_id=session["session_id"],
    requirements_content="# Requirements...",
    metrics={"duration_seconds": 1200, "tokens": 50000, "cost": 0.75}
)

# List projects
projects = pm.list_user_projects("user_123")

# Get status
status = pm.get_project_status(project["project_id"])
```

## API Reference

### ProjectManager

#### `create_project(user_id, startup_idea, project_name=None, execution_mode="mvp")`
Create a new project for a startup idea.

**Returns**: Project metadata dict with `project_id`

#### `start_session(project_id, workflow_type="idea_validation")`
Start a new session within a project.

**Returns**: Session metadata dict with `session_id`

#### `complete_session(project_id, session_id, requirements_content, metrics=None)`
Complete a session and save the generated requirements.

**Returns**: Completion metadata with version number

#### `list_user_projects(user_id, status=None)`
List all projects for a user, optionally filtered by status.

**Returns**: List of project metadata dicts

#### `get_project_status(project_id)`
Get the current status of a project.

**Returns**: Project status dict

#### `update_user_preferences(project_id, preferences)`
Update user preferences for a project.

#### `get_user_preferences(project_id)`
Get user preferences for a project.

**Returns**: User preferences dict

#### `archive_project(project_id)`
Archive a project (mark as inactive).

#### `delete_project(project_id)`
Delete a project and all its data.

## Project Configuration (project.yaml)

```yaml
project_id: "uuid"
user_id: "user_123"
project_name: "My Project"
startup_idea: "The raw startup idea"
execution_mode: "mvp"  # or "full"
created_at: "2024-01-15T10:00:00Z"
updated_at: "2024-01-15T12:00:00Z"
status: "active"  # or "archived"
current_version: 2
sessions:
  - session_id: "uuid1"
    started_at: "2024-01-15T10:00:00Z"
    completed_at: "2024-01-15T11:00:00Z"
    status: "completed"
    version: 1
  - session_id: "uuid2"
    started_at: "2024-01-15T11:30:00Z"
    completed_at: "2024-01-15T12:00:00Z"
    status: "completed"
    version: 2
metrics:
  total_sessions: 2
  completed_sessions: 2
  total_duration_seconds: 3600
  total_tokens: 200000
  total_cost: 2.50
user_preferences:
  target_niche: "Solo founders"
  business_model: "SaaS"
  pricing_strategy: "usage-based"
  go_to_market_approach: "product-led"
  risk_tolerance: "medium"
  target_region: "North America"
```

## Testing

Run tests with:
```bash
pytest tests/test_project_manager.py -v
```

## Example

See `examples/project_manager_example.py` for a complete usage example.
