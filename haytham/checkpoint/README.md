# Checkpoint Manager

The Checkpoint Manager provides checkpoint persistence, session management, and recovery for the phased workflow architecture.

## Overview

The CheckpointManager handles:
- Session creation and manifest management
- Phase checkpoint saving and loading
- Agent output persistence
- User feedback storage
- Session resume and recovery
- Schema validation

## Directory Structure

```
projects/{project_id}/sessions/{session_id}/
├── session_manifest.md          # Session metadata and phase status
├── phase_1_concept/
│   ├── checkpoint.md            # Phase metadata
│   ├── concept_expansion.md     # Agent output
│   └── user_feedback.md         # User review
├── phase_2_market_research/
│   ├── checkpoint.md
│   ├── market_intelligence.md
│   ├── competitor_analysis.md
│   └── user_feedback.md
└── ...
```

## Usage

### Basic Usage

```python
from haytham.checkpoint.checkpoint_manager import CheckpointManager

# Initialize manager
checkpoint_manager = CheckpointManager(base_dir="projects")

# Create session
session_dir = checkpoint_manager.create_session(
    project_id="project-123",
    session_id="session-456",
    user_id="user-789",
    execution_mode="mvp"
)

# Save checkpoint
checkpoint_manager.save_checkpoint(
    project_id="project-123",
    session_id="session-456",
    phase_num=1,
    status="completed",
    agents=[
        {
            "agent_name": "concept_expansion",
            "status": "completed",
            "output_file": "concept_expansion.md",
            "tokens": 15000,
            "cost": 0.0375,
            "duration": 120.5
        }
    ],
    started="2024-11-24T10:00:00Z",
    completed="2024-11-24T10:02:00Z",
    duration=120.5,
    execution_mode="single"
)

# Save agent output
checkpoint_manager.save_agent_output(
    project_id="project-123",
    session_id="session-456",
    phase_num=1,
    agent_name="concept_expansion",
    output_content="Agent analysis and recommendations...",
    status="completed",
    duration=120.5,
    model="anthropic.claude-3-sonnet-20240229-v1:0",
    input_tokens=12000,
    output_tokens=3000,
    tools_used=["file_write"]
)

# Save user feedback
checkpoint_manager.save_user_feedback(
    project_id="project-123",
    session_id="session-456",
    phase_num=1,
    reviewed=True,
    approved=True,
    comments="Looks great!",
    action="approved"
)
```

### Session Resume

```python
# Load session state
session_state = checkpoint_manager.load_session(
    project_id="project-123",
    session_id="session-456"
)

print(f"Current phase: {session_state['current_phase']}")
print(f"Completed phases: {session_state['completed_phases']}")
print(f"Status: {session_state['status']}")

# Get phase outputs
outputs = checkpoint_manager.get_phase_outputs(
    project_id="project-123",
    session_id="session-456",
    phase_nums=[1, 2]  # Or None for all completed phases
)

# Access agent outputs
concept_output = outputs[1]["concept_expansion"]
market_output = outputs[2]["market_intelligence"]
```

### Checkpoint Validation

```python
# Validate checkpoint
is_valid, errors = checkpoint_manager.validate_checkpoint(
    project_id="project-123",
    session_id="session-456",
    phase_num=1
)

if not is_valid:
    print(f"Validation errors: {errors}")
```

## File Formats

### session_manifest.md

Tracks overall session state and phase status:

```markdown
# Session Manifest

## Metadata
- Session ID: {session_id}
- Project ID: {project_id}
- User ID: {user_id}
- Workflow Type: idea_validation
- Execution Mode: mvp
- Created: {ISO 8601 timestamp}
- Last Updated: {ISO 8601 timestamp}
- Status: in_progress

## Phase Status

| Phase | Name | Status | Started | Completed | Duration |
|-------|------|--------|---------|-----------|----------|
| 1 | Concept Expansion | completed | ... | ... | 120s |
| 2 | Market Research | in_progress | ... | - | - |
...
```

### checkpoint.md

Tracks individual phase execution state:

```markdown
# Phase Checkpoint: {Phase Name}

## Metadata
- Phase Number: {1-7}
- Phase Name: {name}
- Status: completed
- Started: {ISO 8601 timestamp}
- Completed: {ISO 8601 timestamp}
- Duration: {seconds}

## Agents in Phase
- {agent_name}: {status}

## Metrics
- Total Tokens: {count}
- Input Tokens: {count}
- Output Tokens: {count}
- Cost: ${amount}
...
```

### agent_name.md

Stores agent analysis and recommendations:

```markdown
# Agent Output: {Agent Name}

## Metadata
- Agent: {agent_name}
- Phase: {phase_number} - {phase_name}
- Executed: {ISO 8601 timestamp}
- Duration: {seconds}
- Status: completed

## Execution Details
- Model: {model_id}
- Input Tokens: {count}
- Output Tokens: {count}
- Tools Used: [{tool_list}]

## Output

{agent's actual output content}
```

### user_feedback.md

Stores user review and feedback:

```markdown
# User Feedback: {Phase Name}

## Review Status
- Reviewed: true
- Approved: true
- Timestamp: {ISO 8601 timestamp}

## User Comments
{user's feedback text}

## Requested Changes
- Change 1: {description}

## Action Taken
- Action: approved
- Retry Count: 0
```

## Execution Modes

### MVP Mode

Creates phase directories for: 1, 2, 3, 6, 7

### Full Mode

Creates phase directories for: 1, 2, 3, 4, 5, 6, 7

## Phase Names

| Phase | Name |
|-------|------|
| 1 | Concept Expansion |
| 2 | Market Research |
| 3 | Niche Selection |
| 4 | Product Strategy |
| 5 | Business Planning |
| 6 | Validation |
| 7 | Final Synthesis |

## Error Handling

The CheckpointManager includes comprehensive error handling:

- **ValueError**: Invalid phase number, status, or execution mode
- **FileNotFoundError**: Session or phase directory not found
- **Validation errors**: Missing required sections or fields

## Integration with ProjectManager

The CheckpointManager works seamlessly with ProjectManager:

```python
from haytham.project.project_manager import ProjectManager
from haytham.checkpoint.checkpoint_manager import CheckpointManager

# Initialize both managers
project_manager = ProjectManager(base_dir="projects")
checkpoint_manager = CheckpointManager(base_dir="projects")

# Create project
project = project_manager.create_project(
    user_id="user-123",
    startup_idea="My startup idea",
    execution_mode="mvp"
)

# Start session
session = project_manager.start_session(project["project_id"])

# Create checkpoint structure
checkpoint_manager.create_session(
    project_id=project["project_id"],
    session_id=session["session_id"],
    user_id="user-123",
    execution_mode="mvp"
)

# Execute phases and save checkpoints...
```

## Testing

Run tests with:

```bash
pytest tests/test_checkpoint_manager.py -v
```

## Example

See `examples/checkpoint_manager_example.py` for a complete working example.
