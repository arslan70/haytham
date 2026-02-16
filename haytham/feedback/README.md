# User Feedback Loop

This module provides interactive user feedback collection for the phased workflow execution.

Updated for single-session architecture - uses SessionManager instead of CheckpointManager.

## Overview

The User Feedback Loop enables users to review phase results and provide feedback after each phase completes. This supports the session-based architecture where users can:

- **Approve & Continue**: Proceed to the next phase
- **Request Changes**: Retry the phase with modifications
- **Skip Phase**: Skip the phase and continue without its outputs

## Components

### UserFeedbackLoop

Main class for managing user feedback collection and processing.

**Key Methods:**

- `present_phase_results()`: Display phase results with action buttons
- `get_change_request()`: Collect change request details from user

### FeedbackAction

Enum defining possible user actions:
- `APPROVE`: User approved the phase
- `REQUEST_CHANGES`: User wants to retry with modifications
- `SKIP`: User wants to skip the phase

### ChangeRequest

Dataclass representing a user's change request:
- `change_type`: Type of change ("modify_prompt", "provide_guidance", "retry_with_same")
- `modified_prompt`: New prompt (if change_type is "modify_prompt")
- `additional_guidance`: Additional guidance (if change_type is "provide_guidance")
- `timestamp`: When the request was created

## Usage

### Basic Usage

```python
from haytham.feedback import UserFeedbackLoop, FeedbackAction
from haytham.session import SessionManager

# Initialize
session_manager = SessionManager()
feedback_loop = UserFeedbackLoop(session_manager=session_manager)

# Present phase results
action = await feedback_loop.present_phase_results(
    phase_num=1,
    phase_name="Concept Expansion",
    agent_outputs={"concept_expansion": "...output..."},
    duration=120.5,
    tokens_used=15000,
    cost=0.0375
)

# Handle user action
if action == FeedbackAction.APPROVE:
    # Continue to next phase
    pass
elif action == FeedbackAction.REQUEST_CHANGES:
    # Get change request details
    change_request = await feedback_loop.get_change_request(
        phase_num=1,
        phase_name="Concept Expansion",
        retry_count=0
    )
    
    # Apply changes and retry phase
    if change_request.change_type == "modify_prompt":
        new_query = change_request.modified_prompt
    elif change_request.change_type == "provide_guidance":
        new_query = default_query + "\n\n" + change_request.additional_guidance
    else:  # retry_with_same
        new_query = default_query
        
elif action == FeedbackAction.SKIP:
    # Skip to next phase
    pass
```

### Integration with Burr Workflow

```python
from haytham.agents.factory import create_agent_by_name
from haytham.feedback import UserFeedbackLoop

# In workflow execute_phase method
async def execute_phase(self, phase_num: int):
    # Execute phase
    results = await self.executor.execute(phase_num)
    
    # Present results and get feedback
    action = await self.feedback_loop.present_phase_results(
        phase_num=phase_num,
        phase_name=self.phase_config.name,
        agent_outputs=results.agent_outputs,
        duration=results.duration,
        tokens_used=results.tokens_used,
        cost=results.cost
    )
    
    # Handle feedback
    if action == FeedbackAction.REQUEST_CHANGES:
        change_request = await self.feedback_loop.get_change_request(
            phase_num=phase_num,
            phase_name=self.phase_config.name,
            retry_count=results.retry_count
        )
        
        # Retry phase with changes
        return await self.retry_phase(phase_num, change_request)
    
    elif action == FeedbackAction.SKIP:
        # Mark phase as skipped
        self.checkpoint_manager.save_checkpoint(
            project_id=self.project_id,
            session_id=self.session_id,
            phase_num=phase_num,
            status="skipped",
            agents=[]
        )
        
    return results
```

## File Persistence

All feedback is saved to `user_feedback.md` files in phase directories:

```
session/
└── phase_1_concept/
    └── user_feedback.md
```

### user_feedback.md Format

```markdown
# User Feedback: Concept Expansion

## Review Status
- Reviewed: true
- Approved: true
- Timestamp: 2024-01-15T10:05:00Z

## User Comments
User approved phase results

## Requested Changes
- No changes requested

## Action Taken
- Action: approved
- Retry Count: 0
```

## Error Handling

### Non-Interactive Mode

If running in non-interactive mode (e.g., CLI or tests):
- Automatically approves all phases
- Logs warning message
- Continues execution

### Timeout

If user doesn't respond within timeout (default 5 minutes):
- Automatically approves phase
- Logs warning message
- Continues execution

### No Response

If user closes dialog without selecting action:
- Defaults to approve
- Logs warning message
- Continues execution

## Requirements

- **SessionManager**: For saving feedback to files
- **Python 3.11+**: For async/await support

## Testing

See `tests/test_user_feedback_loop.py` for unit tests.

## Change Request Handler

The `ChangeRequestHandler` processes user change requests and implements retry logic with exponential backoff.

### ChangeRequestHandler

Handles processing of user change requests for phase execution.

**Key Methods:**

- `handle_change_request()`: Process change request and return modified query
- `should_allow_retry()`: Check if retry should be allowed based on retry count
- `get_retry_delay()`: Get the delay for the given retry count

### RetryConfig

Configuration for retry behavior with exponential backoff.

**Attributes:**

- `max_retries`: Maximum number of retry attempts (default: 3)
- `base_delay`: Base delay in seconds for exponential backoff (default: 1.0)
- `max_delay`: Maximum delay in seconds (default: 60.0)
- `exponential_base`: Base for exponential calculation (default: 2.0)

### Usage Example

```python
from haytham.feedback import ChangeRequestHandler, RetryConfig, ChangeRequest
from haytham.session import SessionManager

# Initialize with custom retry config
session_manager = SessionManager()
retry_config = RetryConfig(
    max_retries=5,
    base_delay=2.0,
    max_delay=120.0,
    exponential_base=2.0
)

handler = ChangeRequestHandler(
    session_manager=session_manager,
    retry_config=retry_config
)

# Process change request
change_request = ChangeRequest(
    change_type="provide_guidance",
    additional_guidance="Focus on B2B market"
)

modified_query, should_retry = handler.handle_change_request(
    phase_num=2,
    phase_name="Market Research",
    change_request=change_request,
    default_query="Conduct market research",
    retry_count=0
)

if should_retry:
    # Retry phase with modified query
    print(f"Retrying with: {modified_query}")
else:
    # Max retries exceeded
    print("Cannot retry - max retries exceeded")
```

### Exponential Backoff

The handler implements exponential backoff for retries:

```python
# With default config (base_delay=1.0, exponential_base=2.0):
# retry_count=0: 1.0s delay
# retry_count=1: 2.0s delay
# retry_count=2: 4.0s delay
# retry_count=3: 8.0s delay
# retry_count=4: 16.0s delay
# retry_count=5: 32.0s delay
# retry_count=6: 60.0s delay (capped at max_delay)
```

### Change Request Types

1. **modify_prompt**: Replace entire query with modified prompt
2. **provide_guidance**: Append additional guidance to default query
3. **retry_with_same**: Use default query without modifications

### Max Retries Handling

When max retries is exceeded:
- Returns `should_retry=False`
- Saves "max_retries_exceeded" feedback
- Prevents infinite retry loops

## Related Components

- **SessionManager**: Saves feedback to user_feedback.md files
- **Burr Workflow Engine**: Orchestrates phased execution with feedback loops
- **PhaseExecutor**: Executes individual phases
- **ChangeRequestHandler**: Processes change requests with exponential backoff
