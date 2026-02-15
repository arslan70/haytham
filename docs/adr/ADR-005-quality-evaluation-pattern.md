# ADR-005: Quality Evaluation Pattern

## Status
**Accepted** — 2026-01-14

## Context

Workflow stages produce outputs (capabilities, decisions, entities, stories) that may have quality issues. These issues are valuable signals for improving the system—prompts, agents, and architecture—but should not block users from proceeding.

## Decision

All workflow stages follow the **Manual Quality Evaluation Pattern**:

```
Stage Execution ──► Output Saved ──► [Evaluate Button] ──► AI Judge ──► improvement_signals.md
                                          │
                                          ▼
                                    Human Reviews
                                    Plans Improvements
```

### Principles

1. **Non-Blocking**: Workflows always complete. Quality evaluation never prevents progress.

2. **Manual Trigger**: Users decide when to evaluate via an optional button after stage completion.

3. **Human Review**: AI Judge outputs are for human consumption. The system does not auto-remediate.

4. **Improvement Signals**: Quality issues are captured in `project/improvement_signals.md` as inputs for system improvement, not as blockers.

5. **System-Level Fixes**: Issues inform changes to prompts, agents, and architecture—not patches to individual outputs.

### Improvement Signals File

All evaluations append to `session/project/improvement_signals.md`:

```markdown
## Run: {timestamp}

**Stage:** {stage_name}
**Score:** {score}/100

### Issues Found
- [{severity}] {issue}
  - *Suggestion:* {suggestion}
```

### AI Judge Output Schema

Each stage's AI Judge outputs:

```json
{
  "overall_score": 0-100,
  "verdict": "PASS|FAIL",
  "shortcomings": [
    {
      "issue": "Description",
      "severity": "high|medium|low",
      "suggestion": "How to improve the system"
    }
  ],
  "prompt_improvements": ["Specific prompt changes"],
  "summary": "Overall assessment"
}
```

## Consequences

**Benefits:**
- Simple, predictable workflow behavior
- User control over evaluation timing
- Quality signals accumulate for pattern analysis
- No workflow interruptions

**Trade-offs:**
- Requires manual effort to trigger and review
- Issues not caught unless user evaluates

## Implementations

- [ADR-006: Story Generation Quality Evaluation](./ADR-006-story-generation-quality-evaluation.md)
