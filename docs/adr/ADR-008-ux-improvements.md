# ADR-008: User Experience Improvements

## Status
**Proposed** — 2026-01-15

## Context

Haytham MVP is feature-complete. The system successfully:
- Takes a startup idea through Discovery (7 stages)
- Translates it to technical artifacts in Architect workflow
- Generates implementation stories in Backlog.md

**Current Pain Points (from user feedback):**

1. **Missing Visibility**: Users cannot easily see what was generated without running external tools
   - VectorDB artifacts (capabilities, decisions, entities) require `./scripts/lancedb-viewer.sh`
   - Stories are in Backlog.md, not visible in the main UI
   - Users complete a workflow but don't see the actual output

2. **Unclear Journey Position**: No indication of where user is in the overall Haytham journey
   - Workflow 1 and 2 stages are mixed in the same view
   - No "You are here" indicator across Discovery → Architect → Implementation

3. **Action Overload**: Bottom of screen has 6 buttons without clear hierarchy
   - Primary vs secondary actions not distinguished
   - "Next Steps" lists parallel options as numbered sequence

4. **First-Time User Friction**: Optimizing for first-time users going through the flow
   - Need clear guidance on what to do next
   - Need immediate value visibility (show what was created)

## Decision

Implement UX improvements in three phases, prioritizing visibility.

---

## Phase 1: Artifact Visibility (High Priority)

### 1.1 Inline Artifact Preview

Replace the static "What Was Created" table with expandable artifact previews.

**Current:**
```
| Artifact     | Count | Description                    |
|--------------|-------|--------------------------------|
| Capabilities | 9     | Business requirements...       |
| Decisions    | 9     | Architecture decisions (DEC-*) |
| Entities     | 9     | Domain model entities (ENT-*)  |
| Stories      | —     | Draft tasks in Backlog.md      |
```

**Proposed:**
```
### What Was Created

▸ Capabilities (9) — Click to expand
  ├─ CAP-F-001: Challenge Management System
  ├─ CAP-F-002: Progress Tracking
  ├─ CAP-F-003: Leaderboard Engine
  └─ ... +6 more

▸ Decisions (9) — Click to expand
  ├─ DEC-001: FastAPI + PostgreSQL stack
  ├─ DEC-002: JWT authentication
  └─ ... +7 more

▸ Entities (9) — Click to expand
  ├─ ENT-001: Member (id, name, email, gym_id)
  ├─ ENT-002: Challenge (id, name, type, points)
  └─ ... +7 more

▸ Stories (21) — Click to expand
  ├─ Layer 1: Bootstrap (3 stories)
  ├─ Layer 2: Entity Models (7 stories)
  ├─ Layer 3: Infrastructure (4 stories)
  └─ Layer 4: Features (7 stories)
```

**Implementation:**
- Read artifacts from VectorDB directly in the UI
- Use Chainlit's collapsible elements or custom components
- Show ID + title + brief summary for each item

### 1.2 Remove External Tool Dependency

**Current:** Users must run `./scripts/lancedb-viewer.sh` to see artifacts

**Proposed:**
- Add "View Full Details" button that opens artifact viewer in browser
- OR embed artifact list directly in Chainlit message
- Eliminate the bash command from the UI entirely

### 1.3 Story Layer Summary

Show stories grouped by layer with counts, not just "Draft tasks in Backlog.md".

**Proposed:**
```
Stories Generated: 21 total
├─ Layer 1: Bootstrap (3) — Project init, DB, Auth
├─ Layer 2: Entities (7) — Database models
├─ Layer 3: Infrastructure (4) — API, Security, Integrations
└─ Layer 4: Features (7) — User-facing functionality

[View in Task Browser] [Download as Markdown]
```

---

## Phase 2: Journey Clarity (Medium Priority)

### 2.1 Workflow Phase Indicator

Add a persistent header showing overall progress.

**Proposed:**
```
┌─────────────────────────────────────────────────────┐
│  Discovery ───●─── Architect ───○─── Implementation │
│     ✓ Complete      ▶ In Progress    ○ Not Started  │
└─────────────────────────────────────────────────────┘
```

**Implementation:**
- Read from `.workflow_phase` file
- Show at top of every message or as sticky header
- Clear visual distinction between phases

### 2.2 Separate Workflow Progress

Don't mix Workflow 1 and Workflow 2 stages in the same list.

**Current:**
```
Previous Progress
  ✓ Stage 1: Idea Analysis
  ✓ Stage 2: Market Context
  ... (7 stages from Workflow 1)
```

**Proposed:**
```
Discovery Phase (Complete)
  ✓ All 7 stages complete — View summary

Architect Phase (Current)
  ✓ Architecture Decisions — 9 decisions
  ✓ Component Boundaries — 9 entities
  ✓ Story Generation — 21 stories
  ○ Story Evaluation — Not run yet
```

### 2.3 Clear "What's Next" Guidance

Replace numbered list with single prominent next action.

**Current:**
```
Next Steps:
1. Review draft tasks in the Task Browser
2. View Coverage Report
3. Retry Technical Translation
```

**Proposed:**
```
┌─────────────────────────────────────────┐
│ ▶ NEXT: Review your 21 implementation   │
│   stories in the Task Browser           │
│                                         │
│   [Open Task Browser]                   │
│                                         │
│   Other options: Coverage Report | Retry│
└─────────────────────────────────────────┘
```

---

## Phase 3: Action Simplification (Lower Priority)

### 3.1 Action Button Hierarchy

**Current:** 6 buttons in 2 rows, no hierarchy
```
[Retry Technical Translation] [Evaluate Stories] [View Coverage Report]
[View Change Impact] [Download Validation Report] [Download MVP Specification]
```

**Proposed:** Group by intent
```
Primary Actions:
  [View Stories] [View Coverage Report]

Downloads:
  [MVP Specification] [Validation Report]

Advanced:
  [Retry Workflow] [Evaluate Stories] [Change Impact]
```

### 3.2 Contextual Actions

Only show relevant actions based on state:
- If stories not generated → Don't show "Evaluate Stories"
- If evaluation already run → Show "Re-evaluate" with previous score
- If all artifacts complete → Highlight "Download" actions

### 3.3 Quick Actions in Artifact Preview

Add inline actions next to artifact groups:
```
▸ Stories (21)
  [View in Browser] [Download] [Evaluate Quality]
```

---

## Implementation Order

| Phase | Item | Effort | Impact |
|-------|------|--------|--------|
| 1 | Inline Artifact Preview | Medium | High |
| 1 | Remove bash script dependency | Low | High |
| 1 | Story Layer Summary | Low | Medium |
| 2 | Workflow Phase Indicator | Medium | High |
| 2 | Separate Workflow Progress | Medium | Medium |
| 2 | Clear "What's Next" | Low | Medium |
| 3 | Action Button Hierarchy | Low | Low |
| 3 | Contextual Actions | Medium | Low |
| 3 | Quick Actions in Preview | Low | Low |

**Recommended implementation sequence:**
1. Start with 1.1 (Inline Artifact Preview) — biggest visibility win
2. Then 2.1 (Workflow Phase Indicator) — clarity win
3. Then 1.2 (Remove bash dependency) — friction reduction

---

## Consequences

**Benefits:**
- First-time users immediately see value (what was generated)
- No external tools required to understand output
- Clear guidance on where to go next
- Reduced cognitive load from action button overload

**Trade-offs:**
- More complex UI rendering in Chainlit
- VectorDB reads in UI code (currently isolated to actions)
- May need custom Chainlit components

**Mitigations:**
- Use Chainlit's built-in expandable/collapsible elements where possible
- Cache artifact summaries in session state
- Lazy-load full artifact details on expand

---

## Open Questions

1. Should we build a dedicated web artifact viewer, or enhance Chainlit UI?
2. Do we want real-time updates as artifacts are created, or batch display at end?
3. Should the workflow indicator be a header, sidebar, or inline element?

## References

- [Chainlit Custom Elements](https://docs.chainlit.io/concepts/elements)
- [Progressive Disclosure (UX Pattern)](https://www.nngroup.com/articles/progressive-disclosure/)
