# Context Management

This module provides context loading and management for the phased workflow architecture.

## Overview

The `ContextLoader` class handles:
- **Selective Context Loading**: Loads only required agent outputs based on phase requirements
- **Automatic Preferences Loading**: Loads user preferences from preferences.json (authoritative) or project.yaml (fallback)
- **Context Summarization**: Automatically summarizes large contexts (>20K tokens) to prevent overflow
- **Context Caching**: Caches loaded context to avoid re-reading files
- **Temporal Guardrail**: Prevents phases < 7 from loading Phase 6 validation artifacts

## Context Requirements Matrix

Each phase has specific context requirements:

```python
CONTEXT_REQUIREMENTS = {
    1: [],  # No previous context
    2: ["concept_expansion"],
    3: ["concept_expansion", "market_intelligence", "competitor_analysis"],
    4: ["niche_identification", "decision_agent"],  # + auto-loaded preferences
    5: ["product_strategy", "decision_agent", "market_intelligence"],  # + auto-loaded preferences
    6: ["business_planning", "product_strategy", "decision_agent"],
    7: ["all"],  # Load ALL previous agents + auto-loaded preferences
}
```

## Usage

### Basic Context Loading

```python
from haytham.context import ContextLoader

# Initialize loader
loader = ContextLoader(
    base_dir="projects",
    summarization_threshold=20000,  # Trigger summarization at 20K tokens
    target_summary_tokens=10000     # Target 10K tokens after summarization
)

# Load context for a phase
context = loader.load_context(
    project_id="abc-123",
    session_id="xyz-789",
    phase_num=4,
    execution_mode="mvp"
)

# Access loaded data
agent_outputs = context["agent_outputs"]  # Dict of agent_name -> output
preferences = context["preferences"]      # User preferences (if applicable)
missing = context["_missing_agents"]      # List of missing required agents
tokens = context["_context_size_tokens"]  # Estimated token count
summarized = context["_summarized"]       # Whether summarization was applied
```

### Disable Summarization

For phases that need full detail (like Phase 7):

```python
context = loader.load_context(
    project_id="abc-123",
    session_id="xyz-789",
    phase_num=7,
    execution_mode="full",
    disable_summarization=True  # Disable automatic summarization
)
```

### Validate Context Availability

Check if required context is available before executing a phase:

```python
is_valid, missing_agents = loader.validate_phase_context(
    project_id="abc-123",
    session_id="xyz-789",
    phase_num=4,
    execution_mode="mvp"
)

if not is_valid:
    print(f"Missing required agents: {missing_agents}")
```

### Clear Cache

Clear the context cache between sessions to prevent memory leaks:

```python
loader.clear_cache()
```

### Temporal Guardrail

The temporal guardrail prevents phases < 7 from accessing Phase 6 validation artifacts:

```python
# This will raise ValueError if phase < 7 tries to access validation artifacts
loader.enforce_temporal_guardrail(
    phase_num=4,
    requested_files=["validation_report.json"]  # Will raise error
)
```

## Automatic Preferences Loading

User preferences are automatically loaded for phases 4, 5, and 7:

1. **Authoritative Source**: `preferences.json` in Phase 3 directory
2. **Fallback Source**: `user_preferences` section in `project.yaml`

Preferences include:
- `target_niche`
- `business_model`
- `pricing_strategy`
- `go_to_market_approach`
- `risk_tolerance`
- `target_region`

## Context Summarization

When context exceeds the summarization threshold (default: 20K tokens):

1. **Extractive Summarization**: Uses `ContextSummarizer` to extract key information
2. **Priority Sections**: Preserves summaries, conclusions, key findings, and metrics
3. **Target Size**: Reduces to target token count (default: 10K tokens)
4. **Metadata Preservation**: Keeps numerical metrics and quantitative data

## Execution Modes

### MVP Mode
- Phases: 1, 2, 3, 6 (simplified), 7
- Skips phases 4 and 5
- Uses `unified_validator` for Phase 6

### Full Mode
- Phases: 1, 2, 3, 4, 5, 6, 7
- Includes all agents
- Uses three-phase validation (6A, 6B, 6C)

## Error Handling

The ContextLoader handles various error conditions:

- **Missing Session Directory**: Raises `FileNotFoundError`
- **Invalid Phase Number**: Raises `ValueError`
- **Invalid Execution Mode**: Raises `ValueError`
- **Missing Agent Outputs**: Logs warnings and includes in `_missing_agents` list
- **Failed File Reads**: Logs errors and marks agents as missing
- **Temporal Violations**: Raises `ValueError` with clear message

## Logging

The ContextLoader provides comprehensive logging:

```python
# Info level: Context loading summary
INFO: Loading context for phase 4 (project=abc-123, session=xyz-789, mode=mvp)
INFO: Context loaded for phase 4: 3 agents, 15000 tokens, summarized=False, missing=0

# Debug level: Detailed operations
DEBUG: Loaded output for niche_identification: 5000 chars
DEBUG: Loaded preferences from preferences.json (authoritative)

# Warning level: Issues
WARNING: Missing required context for phase 4: decision_agent
WARNING: Failed to load preferences.json: File not found
```

## Integration with Phase Executors

Phase executors use the ContextLoader to prepare context before agent execution:

```python
# In PhaseExecutor
context = self.context_loader.load_context(
    project_id=project_id,
    session_id=session_id,
    phase_num=phase_num,
    execution_mode=execution_mode,
    disable_summarization=(phase_num == 7)  # Disable for Phase 7
)

# Pass to agent
agent_context = {
    "previous_outputs": context["agent_outputs"],
    "user_preferences": context["preferences"],
    "missing_agents": context["_missing_agents"]
}
```

## Requirements Coverage

This implementation satisfies:

- **Requirement 22.1-22.10**: Context Loading from Checkpoints
- **Requirement 23.1-23.8**: Universal Context Management and Optimization
- **Requirement 25.6**: Automatic preferences loading
- **Requirement 25.7**: Temporal guardrail enforcement
- **Requirement 14.6**: Preferences precedence (preferences.json > project.yaml)
