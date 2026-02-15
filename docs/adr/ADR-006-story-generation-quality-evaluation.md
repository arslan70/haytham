# ADR-006: Story Generation Quality Evaluation

## Status
**Accepted** — 2026-01-14

## Context

Story generation (Workflow 2, Stage 3) produces implementation stories from capabilities, decisions, and entities. Quality issues observed include:

- Missing bootstrap layer (project init, database setup, authentication)
- Empty dependencies on stories that should have them
- Incomplete entity or capability coverage

This ADR applies [ADR-005: Quality Evaluation Pattern](./ADR-005-quality-evaluation-pattern.md) to story generation.

## Decision

### Evaluation Trigger

After story generation completes, an **"Evaluate Stories"** button appears. When clicked, the AI Judge evaluates the generated stories.

### Evaluation Criteria

| Criterion | What It Checks |
|-----------|----------------|
| Layer Completeness | Bootstrap stories exist (project init, DB setup, auth) |
| Entity Coverage | Every ENT-* has a model creation story |
| Capability Coverage | Every CAP-* has at least one implementing story |
| Dependency Validity | Stories in layers 2-4 have non-empty dependencies |
| Acceptance Criteria Quality | Criteria are specific and implementable |
| Implementation Order | Stories can be executed in sequence without blockers |

### Output

Results written to `project/improvement_signals.md` per ADR-005 pattern:

```markdown
## Run: 2026-01-14T10:30:00

**Stage:** story_generation
**Score:** 65/100

### High Severity Issues
- [critical_gap] Missing Layer 1 bootstrap stories
  - *Suggestion:* Add explicit Layer 1 template to prompt

### Medium Severity Issues
- [ai_judge_shortcoming] 0/25 stories have dependencies defined
  - *Suggestion:* Enforce dependency requirements with examples in prompt
```

## Consequences

Quality issues in story generation are captured for review. Users can analyze patterns across runs and improve the story generation prompt, agent configuration, or workflow design based on accumulated signals.

## References

- [ADR-005: Quality Evaluation Pattern](./ADR-005-quality-evaluation-pattern.md)
- [ADR-004: Multi-Phase Workflow Architecture](./ADR-004-multi-phase-workflow-architecture.md)
