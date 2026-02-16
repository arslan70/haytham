# Stage Configuration System

The Stage Configuration System provides structured configuration for the validation workflow stages.

## Overview

The system defines:
- **StageConfig**: Configuration for each workflow stage
- **STAGES**: Validation phase configuration (6 stages)
- **Helper functions**: For retrieving and formatting configurations

> **Note**: Stage execution is now handled by the Burr workflow engine in `haytham/workflow/`. See [Workflow Engine Documentation](../../docs/architecture.md) for details.

## Quick Start

```python
from haytham.phases import (
    get_stage_by_slug,
    get_all_stage_slugs,
    get_stage_count,
    estimate_total_duration,
    format_query
)

# Get stage configuration
stage1 = get_stage_by_slug("idea-analysis")
print(f"Stage: {stage1.name}")
print(f"Execution Mode: {stage1.execution_mode}")
print(f"Agents: {stage1.agent_names}")

# Get all stage slugs
slugs = get_all_stage_slugs()
# ["idea-analysis", "market-context", "risk-assessment", "pivot-strategy", "validation-summary", "mvp-specification"]

# Estimate total workflow duration
duration = estimate_total_duration()  # ~900 seconds (15 min)
```

## Validation Stages (6 Stages)

| Stage | Slug | Execution Mode | Agents | Duration |
|-------|------|----------------|--------|----------|
| 1 | idea-analysis | single | concept_expansion | 2-3 min |
| 2 | market-context | parallel | market_intelligence, competitor_analysis | 3-4 min |
| 3 | risk-assessment | single | startup_validator | 2-3 min |
| 3b | pivot-strategy | single | report_synthesis (conditional) | 2-3 min |
| 4 | validation-summary | single | report_synthesis | 2-3 min |
| 5 | mvp-specification | single | mvp_specification | 3-4 min |

**Total Duration**: ~15-20 minutes

## StageConfig Structure

```python
@dataclass
class StageConfig:
    slug: str                         # kebab-case identifier
    name: str                         # Display name
    execution_mode: str               # "single" or "parallel"
    agent_names: list[str]            # List of agent names
    query_template: str               # Query template for agents
    required_context: list[str]       # Required previous stage outputs
    duration_estimate: int            # Estimated duration in seconds
    requires_preferences: bool        # Whether stage needs user preferences
```

## Workflow Engine Integration

Stage execution is handled by the Burr workflow engine:

```python
from haytham.workflow import create_validation_workflow, get_stage_registry

# Create workflow with Burr
app = create_validation_workflow(system_goal="Your startup idea")

# Use StageRegistry for metadata (preferred over StageConfig)
registry = get_stage_registry()
stage = registry.get_by_slug("idea-analysis")
```

### StageRegistry vs StageConfig

| Feature | StageConfig (phases/) | StageRegistry (workflow/) |
|---------|----------------------|---------------------------|
| Purpose | Legacy configuration | Burr workflow metadata |
| Includes | Query templates, duration | Display info, state keys |
| Used by | Context loading | Workflow engine, UI |

Both are maintained for compatibility, but `StageRegistry` is the primary source for workflow execution.

## Helper Functions

### `get_stage_by_slug(slug)`
```python
stage = get_stage_by_slug("idea-analysis")
```

### `get_stage_index(slug)`
```python
index = get_stage_index("market-context")  # Returns: 1
```

### `get_all_stage_slugs()`
```python
slugs = get_all_stage_slugs()
# Returns: ["idea-analysis", "market-context", ...]
```

### `get_stage_count()`
```python
count = get_stage_count()  # Returns: 6
```

### `estimate_total_duration()`
```python
duration = estimate_total_duration()  # Returns: ~900 seconds
```

### `format_query(slug, **kwargs)`
```python
query = format_query("idea-analysis", system_goal="A leaderboard for gyms")
```

## Context Requirements

Each stage loads specific context from previous stages:

```python
# Stage 1: No previous context
stage1.required_context = []

# Stage 2: Needs idea analysis
stage2.required_context = ["idea-analysis"]

# Stage 3: Needs idea analysis and market context
stage3.required_context = ["idea-analysis", "market-context"]

# Stage 4+: Needs all previous outputs
stage4.required_context = ["all"]
```

## Related Documentation

- [Architecture Overview](../../docs/architecture.md) - System architecture with Burr workflow
- [Workflow Engine](../../docs/phased-workflow.md) - Detailed workflow documentation
