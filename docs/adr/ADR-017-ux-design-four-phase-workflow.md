# ADR-017: UX Design for Four-Phase Workflow

## Status
**Proposed**, 2026-01-24

**Milestone**: Genesis (M1), User experience for Phases 1-6

**Related**: [ADR-016: Four-Phase Workflow Architecture](./ADR-016-four-phase-workflow.md)

---

## Context

### The Problem

ADR-016 defines the backend architecture for the four-phase workflow, but the **user experience** needs dedicated design. Current issues:

1. **No phase awareness**: Users don't know which phase they're in or what comes next
2. **Unclear decision gates**: "Continue" buttons exist but lack context for the decision
3. **Missing progress visualization**: No sense of progress through Genesis
4. **Inconsistent navigation**: Views appear/disappear without clear structure
5. **No milestone framing**: Users don't understand they're building toward a working MVP

### Design Principles

Aligned with the [VISION.md](../../VISION.md), the UX must:

1. **Show the journey**: Users should always know where they are in Genesis
2. **Enable informed decisions**: Decision gates provide context, not just buttons
3. **Close the loop visually**: Progress toward "working MVP" should be tangible
4. **Stay lean**: Minimum UI that serves the workflow, no decorative complexity
5. **Build trust gradually**: As we move toward Evolution/Sentience, increase autonomy cues

---

## Decision

### User Journey Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      GENESIS: USER JOURNEY                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐                   │
│  │  START  │───▶│  IDEA   │───▶│ RUNNING │───▶│ REVIEW  │                   │
│  │         │    │  INPUT  │    │  PHASE  │    │ RESULTS │                   │
│  └─────────┘    └─────────┘    └─────────┘    └────┬────┘                   │
│                                                     │                        │
│                                          ┌─────────┴─────────┐              │
│                                          │   DECISION GATE   │              │
│                                          │                   │              │
│                                          │  [Continue]       │              │
│                                          │  [Download]       │              │
│                                          │  [Refine]         │              │
│                                          └─────────┬─────────┘              │
│                                                    │                        │
│                                          ┌─────────▼─────────┐              │
│                                          │    NEXT PHASE     │──────────┐   │
│                                          └───────────────────┘          │   │
│                                                                         │   │
│                                                              (repeat)   │   │
│                                          ┌──────────────────────────────┘   │
│                                          │                                  │
│                                          ▼                                  │
│                                    ┌───────────┐                            │
│                                    │  GENESIS  │                            │
│                                    │ COMPLETE  │                            │
│                                    │           │                            │
│                                    │ Working   │                            │
│                                    │   MVP     │                            │
│                                    └───────────┘                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## UX Components

### 1. Global Progress Indicator

**Purpose**: Always show where the user is in the Genesis journey.

**Location**: Top of every page, below the header.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GENESIS PROGRESS BAR                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                      │   │
│  │   WHY        WHAT        HOW       STORIES     BUILD     VALIDATE   │   │
│  │    ●──────────●──────────◐──────────○──────────○──────────○         │   │
│  │    ✓          ✓        (now)                                        │   │
│  │                                                                      │   │
│  │   Phase 3 of 6: Technical Design                                    │   │
│  │   "How should we build each capability?"                            │   │
│  │                                                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  Legend:  ● Complete   ◐ In Progress   ○ Not Started                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**States**:
- **Complete** (●): Phase locked, outputs available
- **In Progress** (◐): Currently working on this phase
- **Not Started** (○): Blocked by previous phase
- **Skipped** (-): Phase was skipped (e.g., pivot strategy not needed)

**Interaction**: Clicking a completed phase navigates to its results view.

---

### 2. Navigation Sidebar

**Purpose**: Provide structured access to all completed phases and current work.

**Structure**: Organized by phase with clear hierarchy.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         NAVIGATION SIDEBAR                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────┐                                       │
│  │                                  │                                       │
│  │  🏠 Dashboard                    │                                       │
│  │                                  │                                       │
│  │  ─────────────────────────────   │                                       │
│  │                                  │                                       │
│  │  PHASE 1: WHY ✓                  │  ← Collapsed, complete                │
│  │    └─ Idea Validation            │                                       │
│  │                                  │                                       │
│  │  PHASE 2: WHAT ✓                 │  ← Collapsed, complete                │
│  │    └─ MVP Specification          │                                       │
│  │                                  │                                       │
│  │  PHASE 3: HOW ◐                  │  ← Expanded, in progress              │
│  │    ├─ Build vs Buy               │                                       │
│  │    └─ Architecture        ●      │  ← Current page                       │
│  │                                  │                                       │
│  │  PHASE 4: STORIES 🔒             │  ← Locked (requires Phase 3)          │
│  │                                  │                                       │
│  │  PHASE 5: BUILD 🔒               │  ← Locked                             │
│  │                                  │                                       │
│  │  PHASE 6: VALIDATE 🔒            │  ← Locked                             │
│  │                                  │                                       │
│  │  ─────────────────────────────   │                                       │
│  │                                  │                                       │
│  │  ⚙️ Settings                     │                                       │
│  │  📥 Export All                   │                                       │
│  │                                  │                                       │
│  └──────────────────────────────────┘                                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Behaviors**:
- Completed phases: Collapsed by default, expandable
- Current phase: Expanded, shows sub-pages
- Locked phases: Grayed out with lock icon, tooltip explains requirement
- Clicking locked phase: Shows modal explaining what's needed

---

### 3. Decision Gates

**Purpose**: Pause between phases for user review and decision.

**When**: After completing the terminal stage of each phase.

**Design**: Full-width card at bottom of phase results page.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DECISION GATE CARD                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                      │   │
│  │  ╔════════════════════════════════════════════════════════════════╗  │   │
│  │  ║  ✅ PHASE 2 COMPLETE: MVP Specification                        ║  │   │
│  │  ╚════════════════════════════════════════════════════════════════╝  │   │
│  │                                                                      │   │
│  │  ## What You've Defined                                             │   │
│  │                                                                      │   │
│  │  • **The One Thing**: [core value proposition]                      │   │
│  │  • **6 Capabilities**: 4 functional, 2 non-functional               │   │
│  │  • **MVP Boundaries**: [in scope] / [out of scope]                  │   │
│  │                                                                      │   │
│  │  ─────────────────────────────────────────────────────────────────  │   │
│  │                                                                      │   │
│  │  ## Next: Phase 3 - HOW (Technical Design)                           │   │
│  │                                                                      │   │
│  │  You'll decide **how** to build each capability:                    │   │
│  │  • Build vs Buy analysis for each capability                        │   │
│  │  • Architecture decisions (DEC-*)                                   │   │
│  │  • Technology choices                                               │   │
│  │                                                                      │   │
│  │  **Estimated time**: 5-10 minutes                                   │   │
│  │                                                                      │   │
│  │  ─────────────────────────────────────────────────────────────────  │   │
│  │                                                                      │   │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐         │   │
│  │  │ 🚀 Continue to │  │ 📄 Download    │  │ ✏️ Refine     │         │   │
│  │  │   Phase 3      │  │   Spec         │  │   Capabilities │         │   │
│  │  └────────────────┘  └────────────────┘  └────────────────┘         │   │
│  │        (primary)          (secondary)        (secondary)            │   │
│  │                                                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Decision Gate Content by Phase**:

| After Phase | Summary Shows | Next Phase Preview | Actions |
|-------------|---------------|-------------------|---------|
| 1: WHY | Recommendation (GO/NO-GO/PIVOT), key risks | WHAT: Define MVP scope | Continue, Download Report, Try Different Idea |
| 2: WHAT | Capabilities count, boundaries | HOW: Technical decisions | Continue, Download Spec, Refine Capabilities |
| 3: HOW | Build/Buy breakdown, key decisions | STORIES: Implementation tasks | Continue, Download Architecture, Revise Decisions |
| 4: STORIES | Story count, effort estimate | BUILD: Start coding | Continue, Export Stories, Refine Stories |
| 5: BUILD | Implementation status | VALIDATE: Test capabilities | Continue, View Code |
| 6: VALIDATE | Pass/Fail per capability | GENESIS COMPLETE | Deploy, Export All |

---

### 4. Phase Context Header

**Purpose**: Every view shows context about its phase.

**Location**: Top of each view, below progress bar.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PHASE CONTEXT HEADER                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                      │   │
│  │  PHASE 3: HOW - Technical Design                                     │   │
│  │  ════════════════════════════════                                   │   │
│  │                                                                      │   │
│  │  Question: "How should we build each capability?"                   │   │
│  │  Role: Software Architect                                           │   │
│  │                                                                      │   │
│  │  ┌─────────────────┐  ┌─────────────────┐                           │   │
│  │  │ Build vs Buy    │  │ Architecture    │                           │   │
│  │  │      ✓          │  │   (current)     │                           │   │
│  │  └─────────────────┘  └─────────────────┘                           │   │
│  │                                                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 5. Dashboard (Home)

**Purpose**: Central hub showing project status and next action.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DASHBOARD                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                      │   │
│  │  # [Project Name]                                                   │   │
│  │                                                                      │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │              GENESIS PROGRESS: 50%                          │    │   │
│  │  │  ████████████████████░░░░░░░░░░░░░░░░░░░░                   │    │   │
│  │  │                                                             │    │   │
│  │  │  WHY ✓   WHAT ✓   HOW ◐   STORIES   BUILD   VALIDATE       │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  │                                                                      │   │
│  │  ─────────────────────────────────────────────────────────────────  │   │
│  │                                                                      │   │
│  │  ## Current Phase: HOW (Technical Design)                           │   │
│  │                                                                      │   │
│  │  You're deciding how to build each capability.                      │   │
│  │                                                                      │   │
│  │  **Next step**: Complete Architecture Decisions                     │   │
│  │                                                                      │   │
│  │  ┌─────────────────────┐                                            │   │
│  │  │ ▶️ Continue Phase 3  │                                            │   │
│  │  └─────────────────────┘                                            │   │
│  │                                                                      │   │
│  │  ─────────────────────────────────────────────────────────────────  │   │
│  │                                                                      │   │
│  │  ## Phase Summary                                                   │   │
│  │                                                                      │   │
│  │  │ Phase     │ Status    │ Key Output                │ Action     │ │   │
│  │  │───────────│───────────│───────────────────────────│────────────│ │   │
│  │  │ 1. WHY    │ ✓ Done    │ GO recommendation         │ [View]     │ │   │
│  │  │ 2. WHAT   │ ✓ Done    │ 6 capabilities defined    │ [View]     │ │   │
│  │  │ 3. HOW    │ ◐ Active  │ 4/6 build vs buy decided  │ [Continue] │ │   │
│  │  │ 4. STORIES│ 🔒 Locked │ -                         │ -          │ │   │
│  │  │ 5. BUILD  │ 🔒 Locked │ -                         │ -          │ │   │
│  │  │ 6. VALIDATE│🔒 Locked │ -                         │ -          │ │   │
│  │                                                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 6. Execution View (Running a Phase)

**Purpose**: Show real-time progress when agents are working.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EXECUTION VIEW                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                      │   │
│  │  PHASE 3: HOW - Running Technical Design                             │   │
│  │  ═══════════════════════════════════════                            │   │
│  │                                                                      │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │  Stage 1/2: Build vs Buy Analysis                           │    │   │
│  │  │  ████████████████████████████████░░░░░░░░  80%              │    │   │
│  │  │                                                             │    │   │
│  │  │  ⏳ Analyzing capability: CAP-F-004 (Payment Processing)    │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  │                                                                      │   │
│  │  ## Live Output                                                     │   │
│  │                                                                      │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │ ✓ CAP-F-001: User Authentication         → BUY (Auth0)     │    │   │
│  │  │ ✓ CAP-F-002: Data Storage                → BUILD           │    │   │
│  │  │ ✓ CAP-F-003: API Gateway                 → HYBRID          │    │   │
│  │  │ ⏳ CAP-F-004: Payment Processing         → Analyzing...    │    │   │
│  │  │ ○ CAP-NF-001: Performance                → Pending         │    │   │
│  │  │ ○ CAP-NF-002: Security                   → Pending         │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  │                                                                      │   │
│  │  ## Agent Activity                                                  │   │
│  │                                                                      │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │ 🤖 build_buy_advisor                                        │    │   │
│  │  │                                                             │    │   │
│  │  │ Evaluating payment processing options...                    │    │   │
│  │  │ - Stripe: High capability match, moderate integration      │    │   │
│  │  │ - Custom: Full control, significant build effort           │    │   │
│  │  │ - Analyzing cost-benefit tradeoffs...                      │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  │                                                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 7. Genesis Complete Celebration

**Purpose**: Mark the milestone achievement when MVP is validated.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      GENESIS COMPLETE                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                      │   │
│  │                        🎉 GENESIS COMPLETE 🎉                        │   │
│  │                                                                      │   │
│  │              Your MVP is built and validated!                       │   │
│  │                                                                      │   │
│  │  ═══════════════════════════════════════════════════════════════   │   │
│  │                                                                      │   │
│  │  ## Journey Summary                                                 │   │
│  │                                                                      │   │
│  │  │ Phase      │ Output                                    │        │   │
│  │  │────────────│───────────────────────────────────────────│        │   │
│  │  │ WHY        │ GO recommendation, 3 risks mitigated      │        │   │
│  │  │ WHAT       │ 6 capabilities defined                    │        │   │
│  │  │ HOW        │ 2 BUILD, 3 BUY, 1 HYBRID                  │        │   │
│  │  │ STORIES    │ 24 stories, 47 story points               │        │   │
│  │  │ BUILD      │ All stories implemented                   │        │   │
│  │  │ VALIDATE   │ 6/6 capabilities passing                  │        │   │
│  │                                                                      │   │
│  │  ═══════════════════════════════════════════════════════════════   │   │
│  │                                                                      │   │
│  │  ## What's Next?                                                    │   │
│  │                                                                      │   │
│  │  Your MVP is ready! You can now:                                    │   │
│  │                                                                      │   │
│  │  • **Deploy** your application                                      │   │
│  │  • **Evolve** it with new features (coming soon)                    │   │
│  │  • **Enable Sentience** for autonomous improvement (future)         │   │
│  │                                                                      │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │   │
│  │  │ 🚀 Deploy   │  │ 📦 Export   │  │ 🔄 Evolve   │                  │   │
│  │  │             │  │    All      │  │  (Soon)     │                  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                  │   │
│  │                                                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Page Mapping

| Phase | Stage | View File | Shows |
|-------|-------|-----------|-------|
| - | - | `dashboard.py` | Project overview, next action |
| 1: WHY | All | `discovery.py` | Validation results, GO/NO-GO |
| 2: WHAT | All | `mvp_spec.py` | MVP scope, capabilities |
| 3: HOW | build-buy | `build_buy.py` | BUILD/BUY/HYBRID per capability |
| 3: HOW | architecture | `architecture.py` | DEC-* decisions |
| 4: STORIES | All | `stories.py` | Story list with filters |
| 4: STORIES | roadmap | `roadmap.py` | Visual timeline |
| 5: BUILD | All | `implementation.py` | Code progress (future) |
| 6: VALIDATE | All | `validation.py` | Capability test results (future) |
| - | Execution | `execution.py` | Real-time agent progress |

---

## Navigation Rules

### Visibility Rules

```python
# Phase 1: WHY - Always visible after project created
if has_project():
    show("dashboard")
    show("discovery")  # WHY results

# Phase 2: WHAT - Visible after WHY locked
if is_locked("idea-validation"):
    show("mvp_spec")  # WHAT results

# Phase 3: HOW - Visible after WHAT locked
if is_locked("mvp-specification"):
    show("build_buy")      # HOW: Build vs Buy
    show("architecture")   # HOW: Architecture

# Phase 4: STORIES - Visible after HOW locked
if is_locked("technical-design"):
    show("stories")   # STORIES: Story list
    show("roadmap")   # STORIES: Visual roadmap

# Phase 5: BUILD - Visible after STORIES locked
if is_locked("story-generation"):
    show("implementation")  # BUILD: Code progress

# Phase 6: VALIDATE - Visible after BUILD locked
if is_locked("implementation"):
    show("validation")  # VALIDATE: Test results
```

### Locked State Behavior

When a user clicks a locked phase:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LOCKED PHASE MODAL                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                      │   │
│  │  🔒 Phase 4: STORIES is locked                                      │   │
│  │                                                                      │   │
│  │  To unlock this phase, you need to complete:                        │   │
│  │                                                                      │   │
│  │  ✓ Phase 1: WHY (Idea Validation)         - Complete                 │   │
│  │  ✓ Phase 2: WHAT (MVP Specification)      - Complete                 │   │
│  │  ◐ Phase 3: HOW (Technical Design)        - In Progress              │   │
│  │                                                                      │   │
│  │  **Missing**: Architecture Decisions                                │   │
│  │                                                                      │   │
│  │  ┌────────────────────────┐                                         │   │
│  │  │ Go to Phase 3: HOW     │                                         │   │
│  │  └────────────────────────┘                                         │   │
│  │                                                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Color System

| Element | Color | Meaning |
|---------|-------|---------|
| Phase complete | Green (#22c55e) | Done, outputs available |
| Phase in progress | Blue (#3b82f6) | Currently working |
| Phase locked | Gray (#9ca3af) | Not yet available |
| Decision gate | Purple (#8b5cf6) | Requires user decision |
| Error/blocked | Red (#ef4444) | Action needed |
| Genesis complete | Gold (#eab308) | Milestone achieved |

---

## Responsive Behavior

| Viewport | Navigation | Progress Bar |
|----------|------------|--------------|
| Desktop (>1024px) | Sidebar always visible | Full with labels |
| Tablet (768-1024px) | Collapsible sidebar | Compact with icons |
| Mobile (<768px) | Bottom nav | Minimal dots only |

---

## Implementation Plan

### Phase 1: Core Navigation (with ADR-016)

1. Add progress bar component
2. Restructure sidebar with phase groupings
3. Add phase context headers to existing views
4. Update navigation rules for 4 phases

### Phase 2: Decision Gates

1. Create decision gate component
2. Add to each phase terminal view
3. Implement "next phase preview" content

### Phase 3: Dashboard Enhancement

1. Redesign dashboard with Genesis progress
2. Add phase summary table
3. Add "next action" prominent CTA

### Phase 4: Execution View

1. Enhance execution view with stage progress
2. Add live output streaming
3. Add agent activity display

### Phase 5: Future Phases (with Phase 5-6 ADRs)

1. Create implementation.py view
2. Create validation.py view
3. Add Genesis complete celebration

---

## Files to Create/Modify

| File | Change |
|------|--------|
| `components/progress_bar.py` | NEW: Genesis progress bar component |
| `components/decision_gate.py` | NEW: Decision gate component |
| `components/phase_header.py` | NEW: Phase context header component |
| `components/locked_modal.py` | NEW: Locked phase explanation modal |
| `Haytham.py` | Update navigation structure |
| `views/dashboard.py` | Redesign with Genesis progress |
| `views/discovery.py` | Add decision gate |
| `views/mvp_spec.py` | Add decision gate |
| `views/build_buy.py` | Add phase context, update flow |
| `views/architecture.py` | NEW: Architecture view with decision gate |
| `views/stories.py` | Add phase context |
| `views/roadmap.py` | Add phase context |
| `views/execution.py` | Enhance with stage progress |
| `views/implementation.py` | NEW: Phase 5 view (future) |
| `views/validation.py` | NEW: Phase 6 view (future) |

---

## Consequences

### Positive

1. **Clear mental model**: Users understand they're building toward a working MVP
2. **Informed decisions**: Decision gates provide context, not just buttons
3. **Progress visibility**: Users can see how far they've come and what's left
4. **Reduced confusion**: Phase groupings clarify which views belong together
5. **Future-ready**: UI structure supports Evolution and Sentience milestones

### Negative

1. **More UI work**: Significant Streamlit component development
2. **Learning curve**: Users must understand the phase model
3. **Rigidity**: Users must follow the phase order (by design)

### Risks

1. **Over-complicated**: Too much UI structure for simple tasks
   - **Mitigation**: Keep individual views simple, complexity is in navigation

2. **Progress bar overhead**: Showing all 6 phases when only 4 implemented
   - **Mitigation**: Mark Phase 5-6 as "Coming Soon" until implemented

---

## References

- [VISION.md](../../VISION.md) - Complete roadmap
- [ADR-016: Four-Phase Workflow Architecture](./ADR-016-four-phase-workflow.md) - Backend architecture
- [ADR-008: UX Improvements](./ADR-008-ux-improvements.md) - Previous UX work
