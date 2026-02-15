# ADR-011: Story Effort Estimation

## Status
**Proposed** — 2026-01-19

## Context

### Current State

Generated stories include rich metadata but no effort estimates:

```json
{
  "title": "Authentication Foundation",
  "description": "Implement user authentication system with JWT tokens...",
  "acceptance_criteria": ["Given a user with valid credentials...", ...],
  "priority": "high",
  "order": 3
  // No estimate field
}
```

### The Problem

**Solo founders cannot plan timelines or budgets.** Without effort estimates:

| Planning Need | Current Gap |
|---------------|-------------|
| "How long will this MVP take?" | No data to answer |
| "How much will a contractor cost?" | Cannot scope work |
| "What can I build in 2 weeks?" | No basis for prioritization |
| "Which stories are quick wins?" | All stories look equal |

### Dogfood Evidence

The generated stories for Haytham included 27 tasks. A founder looking at this list has no way to know:
- Is "Authentication Foundation" a 2-hour task or a 2-day task?
- Can I ship Layer 1 (bootstrap) in a weekend?
- Should I outsource the "Data Anonymization Service" or build it myself?

### Industry Context

| Estimation Method | Pros | Cons |
|-------------------|------|------|
| Story Points | Relative, team-calibrated | Meaningless without team history |
| T-Shirt Sizes | Simple, quick | Too coarse for planning |
| Hour Ranges | Concrete, budgetable | False precision, varies by skill |
| Complexity Score | Objective factors | Doesn't translate to time |

**For solo founders, T-shirt sizes with hour ranges provide the best balance** — simple enough to understand, concrete enough for contractor quotes.

---

## Decision

### Add AI-Generated Effort Estimates to Stories

We will enhance the story generation stage to produce effort estimates using a structured analysis of complexity factors.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     EFFORT ESTIMATION ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Story Generation                                                           │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐  │
│  │ Generated       │────▶│ Effort           │────▶│ Estimated           │  │
│  │ Story           │     │ Estimator Agent  │     │ Story               │  │
│  └─────────────────┘     └──────────────────┘     └─────────────────────┘  │
│                                   │                                         │
│                                   ▼                                         │
│                          ┌──────────────────┐                               │
│                          │ Complexity       │                               │
│                          │ Analysis         │                               │
│                          ├──────────────────┤                               │
│                          │ • Scope breadth  │                               │
│                          │ • Technical depth│                               │
│                          │ • Dependencies   │                               │
│                          │ • Uncertainty    │                               │
│                          │ • Integration    │                               │
│                          └──────────────────┘                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Estimation Model

#### T-Shirt Sizes with Hour Ranges

| Size | Label | Solo Dev Hours | Contractor Hours | Typical Examples |
|------|-------|----------------|------------------|------------------|
| **XS** | Trivial | 1-2h | 1-2h | Config change, add field, fix typo |
| **S** | Small | 2-4h | 2-4h | Single endpoint, simple component |
| **M** | Medium | 4-8h | 4-8h | Feature with tests, CRUD operations |
| **L** | Large | 1-2 days | 8-16h | Multi-file feature, integration |
| **XL** | Extra Large | 2-4 days | 16-32h | Complex system, new subsystem |

#### Complexity Factors

The estimator analyzes five dimensions:

```python
@dataclass
class ComplexityAnalysis:
    """Structured complexity assessment for effort estimation."""

    # 1. Scope Breadth (1-5)
    # How many distinct pieces need to be built?
    scope_breadth: int
    scope_rationale: str

    # 2. Technical Depth (1-5)
    # How complex is the implementation logic?
    technical_depth: int
    depth_rationale: str

    # 3. Dependency Count (1-5)
    # How many other stories must be complete first?
    dependency_weight: int
    dependency_rationale: str

    # 4. Uncertainty (1-5)
    # How clear are the requirements? Any unknowns?
    uncertainty: int
    uncertainty_rationale: str

    # 5. Integration Surface (1-5)
    # How many external systems/APIs involved?
    integration_surface: int
    integration_rationale: str

    @property
    def total_score(self) -> int:
        """Sum of all factors (5-25 range)."""
        return (
            self.scope_breadth +
            self.technical_depth +
            self.dependency_weight +
            self.uncertainty +
            self.integration_surface
        )

    @property
    def tshirt_size(self) -> str:
        """Map total score to T-shirt size."""
        if self.total_score <= 7:
            return "XS"
        elif self.total_score <= 11:
            return "S"
        elif self.total_score <= 15:
            return "M"
        elif self.total_score <= 19:
            return "L"
        else:
            return "XL"
```

#### Score-to-Size Mapping

```
Score Range    T-Shirt    Reasoning
───────────────────────────────────────────────────────────
5-7            XS         Minimal across all dimensions
8-11           S          Low complexity, clear requirements
12-15          M          Moderate complexity, some integration
16-19          L          High complexity or uncertainty
20-25          XL         Complex across multiple dimensions
```

---

### Enhanced Story Schema

```json
{
  "title": "Authentication Foundation",
  "description": "Implement user authentication system with JWT tokens...",
  "acceptance_criteria": [...],
  "priority": "high",
  "order": 3,
  "labels": ["type:bootstrap", "layer:1"],
  "dependencies": ["Database Setup and Configuration"],

  "estimate": {
    "size": "M",
    "hours_range": {
      "min": 4,
      "max": 8
    },
    "confidence": "medium",
    "complexity": {
      "scope_breadth": 3,
      "technical_depth": 3,
      "dependency_weight": 2,
      "uncertainty": 2,
      "integration_surface": 2,
      "total": 12
    },
    "rationale": "Standard JWT implementation with bcrypt. Clear patterns but multiple components (login, token validation, middleware)."
  }
}
```

---

### Estimation Agent

#### System Prompt

```markdown
You are a senior software architect estimating implementation effort for user stories.

For each story, analyze these five complexity factors on a 1-5 scale:

1. **Scope Breadth** (1-5)
   - 1: Single function or config change
   - 3: Multiple related functions, one file
   - 5: Multiple files, multiple concerns

2. **Technical Depth** (1-5)
   - 1: Straightforward CRUD, no algorithms
   - 3: Moderate logic, standard patterns
   - 5: Complex algorithms, performance-critical

3. **Dependency Weight** (1-5)
   - 1: No dependencies, can start immediately
   - 3: 1-2 dependencies, clear interfaces
   - 5: Many dependencies, complex coordination

4. **Uncertainty** (1-5)
   - 1: Crystal clear requirements, done this before
   - 3: Some ambiguity, may need clarification
   - 5: Significant unknowns, research required

5. **Integration Surface** (1-5)
   - 1: No external integrations
   - 3: 1-2 APIs or services
   - 5: Multiple external systems, complex protocols

Output your analysis as structured JSON with rationale for each score.
```

#### Example Analysis

**Input Story:**
```
Title: Data Anonymization Service
Description: Implement privacy-first data handling with encryption and anonymization at input stage
Acceptance Criteria:
- All sensitive fields anonymized before storage
- Encryption at rest and in transit
- GDPR-compliant deletion
```

**Agent Output:**
```json
{
  "scope_breadth": 4,
  "scope_rationale": "Multiple components: anonymization logic, encryption layer, deletion handlers, audit logging",

  "technical_depth": 4,
  "depth_rationale": "Requires cryptographic implementation, PII detection, secure deletion patterns",

  "dependency_weight": 2,
  "dependency_rationale": "Depends on auth foundation, but interface is clear",

  "uncertainty": 3,
  "uncertainty_rationale": "GDPR requirements may need legal review; PII detection scope unclear",

  "integration_surface": 2,
  "integration_rationale": "Integrates with database layer only, no external services",

  "total": 15,
  "size": "M",
  "hours_range": {"min": 4, "max": 8},
  "confidence": "medium",
  "rationale": "Well-scoped privacy feature with clear patterns but multiple security-sensitive components requiring careful implementation."
}
```

---

### Aggregate Estimates

#### Project Summary View

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  📊 EFFORT SUMMARY                                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Total Stories: 27                                                          │
│                                                                             │
│  By Size:                          Estimated Total:                         │
│  ┌────────────────────────┐        ┌──────────────────────────────────┐    │
│  │ XS  ██░░░░░░░░  3      │        │ Best Case:   45 hours (6 days)   │    │
│  │ S   ████░░░░░░  6      │        │ Expected:    72 hours (9 days)   │    │
│  │ M   ██████████  12     │        │ Worst Case:  110 hours (14 days) │    │
│  │ L   ████░░░░░░  5      │        └──────────────────────────────────┘    │
│  │ XL  █░░░░░░░░░  1      │                                                │
│  └────────────────────────┘        At $100/hr contractor rate:             │
│                                    $4,500 - $11,000                         │
│  By Layer:                                                                  │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │ Layer 1: Bootstrap       ████░░░░░░░░░░░░  12-20h (3 stories)     │    │
│  │ Layer 2: Entities        ██████░░░░░░░░░░  18-30h (6 stories)     │    │
│  │ Layer 3: Infrastructure  ████░░░░░░░░░░░░  10-18h (3 stories)     │    │
│  │ Layer 4: Features        ████████████████  40-70h (15 stories)    │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Implementation

#### Directory Structure

```
haytham/
├── agents/
│   └── worker_effort_estimator/
│       ├── __init__.py
│       └── effort_estimator_prompt.txt
├── workflow/
│   └── estimation/
│       ├── __init__.py
│       ├── models.py           # ComplexityAnalysis, EstimatedStory
│       ├── estimator.py        # Estimation logic
│       └── aggregator.py       # Project-level summaries
```

#### Integration Points

**Option A: Post-Generation Enhancement**

Run estimation as a separate pass after story generation:

```python
# In story generation workflow
stories = generate_stories(capabilities)
estimated_stories = estimate_effort(stories)  # New step
save_stories(estimated_stories)
```

**Pros:** Non-blocking, can retry estimation independently
**Cons:** Extra API calls, longer total time

**Option B: Inline Generation**

Include estimation in the story generation prompt:

```python
# Single prompt generates story + estimate
story_with_estimate = generate_story_with_estimate(capability)
```

**Pros:** Single pass, faster
**Cons:** Larger prompt, harder to tune independently

**Recommendation:** Start with Option A for flexibility, optimize to Option B if latency is an issue.

---

### Confidence Levels

Not all estimates are equal. We track confidence:

| Confidence | Criteria | Display |
|------------|----------|---------|
| **High** | Clear requirements, standard patterns, similar stories estimated consistently | Solid bar |
| **Medium** | Some ambiguity, moderate complexity, reasonable confidence | Hatched bar |
| **Low** | Significant unknowns, novel tech, high uncertainty score | Dotted bar |

```
Authentication Foundation     [████████████] M  4-8h   (High)
Data Anonymization Service    [████░░░░░░░░] M  4-8h   (Medium)
AI Agent Orchestration        [░░░░░░░░░░░░] XL 16-32h (Low)
```

---

### Export Integration

Estimates flow into ADR-010 exports:

#### Linear CSV
```csv
Title,Description,Priority,Labels,Estimate
"Authentication Foundation","Implement JWT auth...","High","bootstrap,layer-1","M (4-8h)"
```

#### Markdown
```markdown
### STORY-003: Authentication Foundation
**Priority:** High | **Estimate:** M (4-8h) | **Confidence:** High

...
```

#### Aggregate Export
```markdown
## Project Effort Summary

| Metric | Value |
|--------|-------|
| Total Stories | 27 |
| Estimated Hours | 45-110h |
| Expected Duration | 9 working days |
| Contractor Budget | $4,500-$11,000 |
```

---

### Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| Estimation accuracy | Within 50% of actual | Post-project survey (long-term) |
| User trust | >70% find estimates "useful" | In-app feedback |
| Export usage | >50% of exports include estimates | Feature flag tracking |
| Estimation time | <30s per story batch | Performance monitoring |

---

### Rollout Plan

#### Phase 1: Core Estimation (Week 1)
1. Implement `ComplexityAnalysis` model
2. Create effort estimator agent with prompt
3. Add estimation to story generation workflow
4. Display estimates in stories view

#### Phase 2: Aggregation (Week 2)
1. Build project summary calculations
2. Add summary panel to UI
3. Include estimates in exports (ADR-010)

#### Phase 3: Calibration (Week 3+)
1. Collect actual vs. estimated data
2. Tune scoring thresholds
3. Add confidence indicators
4. Build feedback loop for improving estimates

---

## Consequences

### Positive

1. **Actionable planning** — Founders can scope work and set timelines
2. **Budget visibility** — Contractor costs become estimable
3. **Prioritization data** — Quick wins vs. big efforts become visible
4. **Export value** — Estimates make exports more useful

### Negative

1. **False precision risk** — Users may over-trust estimates
2. **Calibration needed** — Initial estimates may be off
3. **Extra latency** — Additional API calls for estimation

### Risks

1. **Estimate anchoring** — Users take estimates as commitments
   - **Mitigation:** Always show ranges, display confidence levels, include disclaimers

2. **Context blindness** — AI doesn't know user's skill level
   - **Mitigation:** Document that estimates assume "mid-level developer"; add skill multiplier option later

---

## Alternatives Considered

### Alternative A: Story Points Only

Use abstract story points (1, 2, 3, 5, 8, 13) without hour mapping.

**Rejected because:**
- Meaningless without team velocity history
- Solo founders need concrete time/cost estimates
- Points require calibration sessions we can't facilitate

### Alternative B: User-Provided Estimates

Let users estimate their own stories after generation.

**Rejected because:**
- Adds friction to the workflow
- Users often lack estimation experience
- Defeats the purpose of AI-assisted planning

### Alternative C: Historical Data Only

Build estimates from a database of similar completed stories.

**Rejected because:**
- Requires large dataset we don't have yet
- Cold start problem for new story types
- Can supplement AI estimates later, not replace

---

## References

- [ADR-010: Stories Export](./ADR-010-stories-export.md)
- [ADR-009: Workflow Separation](./ADR-009-workflow-separation.md)
- [Mountain Goat Software: Story Points](https://www.mountaingoatsoftware.com/blog/what-are-story-points)
