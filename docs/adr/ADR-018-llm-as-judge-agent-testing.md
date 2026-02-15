# ADR-018: LLM-as-Judge Agent Testing

## Status
**Proposed** — 2026-01-28

**Milestone**: Consolidation (Pre-Evolution)

## Context

### The Problem

Agent prompts are the **biggest factor of regression** in Haytham. When prompts change:
1. Output quality may degrade in subtle ways
2. Output structure may break downstream stages
3. The effect is non-deterministic — same input produces different outputs

Current testing infrastructure has gaps:
- `tests/test_stage_config.py` — Tests stage metadata (23 tests passing)
- `tests/test_session_manager.py` — Tests session persistence
- **No tests for agent output quality**

### Why Traditional Testing Fails

**Snapshot testing doesn't work** for agents because:
- Agent outputs are non-deterministic (LLM temperature, phrasing variance)
- Two semantically identical outputs differ textually
- Snapshot comparisons produce false negatives constantly

**Unit tests with mocked LLMs** don't work because:
- Mocked responses are static — they don't exercise the prompt
- Real regressions happen when prompts interact poorly with real LLMs
- Mock-based tests give false confidence

### The Solution: LLM-as-Judge

Use an LLM to evaluate agent outputs against defined criteria:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LLM-AS-JUDGE EVALUATION                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Test Input              Agent Under Test           LLM Judge              │
│   (fixed idea)     ──►    (real execution)    ──►    (evaluation)          │
│                                                                              │
│   "A gym leaderboard      concept_expansion         "Does the output:       │
│    with anonymous         (with real LLM)            - Include problem?     │
│    handles"                    │                     - Define target user?  │
│                                │                     - Have clear UVP?"     │
│                                ▼                            │               │
│                           Agent Output                      ▼               │
│                           (markdown)              PASS/FAIL + reasoning     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Prior Art

1. **Strands SDK**: Has built-in LLM judge support via `strands.evaluate`
2. **ADR-005**: Defines quality evaluation pattern (used in story validation)
3. **ADR-006**: Story generation quality evaluation (specific implementation)

This ADR extends the quality evaluation pattern to all agents as a developer testing tool.

---

## Decision

### Implement LLM-as-Judge for All Agents

Create a `make test-agents` command that:
1. Runs each agent with a fixed test input
2. Evaluates outputs using an LLM judge
3. Reports PASS/FAIL with reasoning for each agent

### Key Design Decisions

**1. Separate from CI**
- This is a **developer tool**, not a CI gate
- Run manually before releases or after prompt changes
- LLM calls are expensive and slow — not suitable for every commit

**2. Test ALL agents (13 total)**

| Agent | Stage | Key Criteria |
|-------|-------|--------------|
| concept_expansion | idea-analysis | Problem, users, UVP defined |
| market_intelligence | market-context | Market data, trends, size |
| competitor_analysis | market-context | Competitors identified, gaps found |
| startup_validator | risk-assessment | Risks categorized, validation criteria |
| pivot_strategy | pivot-strategy | Alternative directions if HIGH risk |
| validation_summary | validation-summary | GO/NO-GO/PIVOT recommendation |
| mvp_scope | mvp-scope | The One Thing, boundaries clear |
| capability_model | capability-model | CAP-F-* and CAP-NF-* IDs, traceability |
| build_buy_advisor | build-buy-analysis | BUILD/BUY per capability with rationale |
| build_buy_analyzer | build-buy-analysis | Framework/service recommendations |
| story_generator | story-generation | Stories with implements:CAP-* labels |
| (story_validator) | story-validation | Validates story consistency |
| (dependency_orderer) | dependency-ordering | Correct dependency graph |

**3. Judge Evaluation: Binary PASS/FAIL**
- Not numeric scores (hard to set thresholds)
- Judge provides **reasoning** for failures
- Reasoning helps developers understand what broke

**4. Fixed Test Inputs**
- Use `tests/fixtures/test_ideas.json` (already exists)
- Each idea represents a category (Web App, CLI, API, Marketplace, Mobile)
- Run agents against all ideas to catch category-specific regressions

---

## Implementation Plan

### Phase 1: Prototype (This ADR)

Validate the approach with a minimal implementation:

**1. Create evaluation framework**
```
haytham/
└── testing/
    ├── __init__.py
    ├── judge.py           # LLM judge wrapper
    ├── criteria.py        # Per-agent evaluation criteria
    └── runner.py          # Test orchestration
```

**2. Define criteria for 3 pilot agents**
- `concept_expansion` (Phase 1)
- `capability_model` (Phase 2)
- `story_generator` (Phase 4)

**3. Create `make test-agents` command**
```makefile
test-agents:
    python -m haytham.testing.runner --agents concept_expansion,capability_model,story_generator
```

**4. Run against 2 test ideas**
- T1: Web App ("gym leaderboard")
- T2: CLI Tool ("markdown to PDF converter")

**5. Evaluate results**
- Does the judge catch real quality issues?
- Are false positives/negatives manageable?
- Is the cost/time acceptable?

### Phase 2: Full Implementation (Future)

If prototype succeeds:
1. Add criteria for all 13 agents
2. Run against all 5 test ideas
3. Add to pre-release checklist
4. Document criteria maintenance process

---

## Evaluation Criteria Structure

Each agent has defined criteria the judge evaluates:

```python
# haytham/testing/criteria.py

AGENT_CRITERIA = {
    "concept_expansion": {
        "name": "Concept Expansion Agent",
        "criteria": [
            "Output includes a clear problem statement",
            "Target user persona is defined with demographics",
            "Unique value proposition differentiates from competitors",
            "Use cases are concrete and actionable",
            "Output is structured with clear sections",
        ],
        "fail_threshold": 2,  # Fail if 2+ criteria not met
    },

    "capability_model": {
        "name": "Capability Model Agent",
        "criteria": [
            "All capabilities have CAP-F-* or CAP-NF-* IDs",
            "Each capability traces to an IN SCOPE item",
            "Functional and non-functional capabilities are separated",
            "No duplicate capabilities with different IDs",
            "Capabilities are atomic (not composite)",
        ],
        "fail_threshold": 1,  # Stricter — structure must be correct
    },

    "story_generator": {
        "name": "Story Generator Agent",
        "criteria": [
            "Each story has a unique STORY-* ID",
            "Each story has implements:CAP-* label(s)",
            "Stories follow 'As a <user>, I can <action>' format",
            "Acceptance criteria are testable",
            "Dependencies reference valid STORY-* IDs",
        ],
        "fail_threshold": 1,
    },
}
```

---

## Judge Prompt Template

```
You are evaluating the output of an AI agent in a startup validation system.

AGENT: {agent_name}
INPUT: {test_input}
OUTPUT:
```
{agent_output}
```

Evaluate the output against these criteria:
{criteria_list}

For each criterion, determine if it is MET or NOT MET.
Provide brief reasoning for each.

Then give a final verdict: PASS or FAIL
A test FAILS if {fail_threshold} or more criteria are NOT MET.

Respond in this exact format:
## Criteria Evaluation
1. [criterion]: MET/NOT MET - [brief reason]
2. [criterion]: MET/NOT MET - [brief reason]
...

## Verdict
**{PASS/FAIL}**

## Reasoning
[Brief summary of why the test passed or failed]
```

---

## Cost and Time Estimates

**Per agent test run:**
- Agent execution: ~$0.05-0.10 (depends on output length)
- Judge evaluation: ~$0.02-0.05 (short evaluation)
- Time: ~30-60 seconds per agent

**Full test suite (13 agents × 5 ideas):**
- Cost: ~$5-10 per run
- Time: ~30-45 minutes

**Prototype (3 agents × 2 ideas):**
- Cost: ~$0.50-1.00 per run
- Time: ~5-10 minutes

---

## Success Criteria for Prototype

The prototype is successful if:

1. **Catches real regressions**: When a prompt change breaks output quality, the judge fails the test
2. **Low false positive rate**: < 20% of failures are false positives
3. **Actionable feedback**: Failure reasoning helps identify the problem
4. **Acceptable cost**: < $1 per prototype run
5. **Reasonable time**: < 10 minutes for prototype run

---

## Files to Create

| File | Purpose |
|------|---------|
| `haytham/testing/__init__.py` | Module entry |
| `haytham/testing/judge.py` | LLM judge wrapper using Strands |
| `haytham/testing/criteria.py` | Per-agent evaluation criteria |
| `haytham/testing/runner.py` | Test orchestration CLI |
| `tests/fixtures/test_ideas.json` | Already exists — verify contents |
| `Makefile` | Add `test-agents` target |

---

## Consequences

### Positive

1. **Catches prompt regressions** before they reach users
2. **Speeds up development** — confidence to iterate on prompts
3. **Documents expected behavior** via explicit criteria
4. **Leverages Strands** — uses existing LLM infrastructure
5. **Binary verdict** — clear pass/fail, no ambiguous scores

### Negative

1. **Cost per run** — $5-10 not trivial for frequent testing
2. **Time per run** — 30-45 minutes too slow for TDD
3. **Judge quality** — LLM judge may have blind spots
4. **Maintenance burden** — criteria must evolve with prompts

### Risks

1. **False positives frustrate developers**
   - Mitigation: Tune criteria based on prototype learnings

2. **False negatives miss real bugs**
   - Mitigation: Review failures manually, expand criteria

3. **Judge model changes affect results**
   - Mitigation: Pin judge model version, document baseline

---

## Next Steps

1. **Approve this ADR** — Confirm prototype scope
2. **Implement prototype** — 3 agents, 2 test ideas
3. **Evaluate results** — Does it catch real issues?
4. **Decide on full rollout** — If prototype succeeds

---

## References

- [ADR-005: Quality Evaluation Pattern](./ADR-005-quality-evaluation-pattern.md)
- [ADR-006: Story Generation Quality Evaluation](./ADR-006-story-generation-quality-evaluation.md)
- [Strands Evaluate Documentation](https://strandsai.github.io/sdk-python/user-guide/evaluation/)
- [CONSOLIDATION_PLAN.md](../CONSOLIDATION_PLAN.md) — Phase 4.2: Stage-Level Tests
