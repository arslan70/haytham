# Contributor Backlog Design

**Date:** 2026-02-19
**Status:** Approved

## Strategic Context

Genesis Phases 1-4 are complete. The Genesis loop (idea in, working validated MVP out) requires Phases 5-6: coding agent dispatch and capability validation. Report/output improvements are premature without execution feedback. The execution attempt IS the test.

**Target audience for community issues:** AI/agent developers interested in MCP, agent orchestration, and spec-driven workflows.

## Backlog Structure

Three tracks, one story: close the loop, make the output useful to the ecosystem, extend the control plane.

### Track 1: Close the Genesis Loop (Core Team, Sequential)

| # | Issue | Depends on |
|---|-------|-----------|
| #5 | Execution Contract Schema | - |
| #8 | Coding Agent Integration (Claude Code) | #5 |
| #11 | Capability Validation | #8 |

This is the critical path. Each step depends on the previous. When done, Genesis works end-to-end. Execution feedback from this track reveals the real output quality problems.

### Track 2: Make Output Useful to Ecosystem (Community, Parallel)

| # | Issue | Depends on |
|---|-------|-----------|
| #9 | OpenSpec Export | #5 (soft) |
| #10 | Spec Kit Export | #5 (soft), #9 |

Soft dependency on the execution contract schema. Can be designed in parallel, informing each other. These make Haytham's output consumable by any coding agent today, even before Phase 5 is built.

### Track 3: Extend the Control Plane (Community, Immediate)

| # | Issue | Depends on |
|---|-------|-----------|
| #6 | Google Stitch MCP Integration | - |

Proves the "service as agent" pattern with a real MCP-native external service. No dependencies, can start immediately.

### Track 4: Community Enablement (Immediate)

| # | Issue | Depends on |
|---|-------|-----------|
| #7 | Agent Development Guide + Template | - |

Lowers the barrier to all agent-related contributions. No dependencies.

## Sequencing Diagram

```
Track 4: #7 Agent Guide ─────────────────────── (start immediately)
Track 3: #6 Stitch Integration ──────────────── (start immediately)

Track 1: #5 Exec Contract ── #8 Coding Agent ── #11 Validation
                    │
Track 2:            ├── #9 OpenSpec Export
                    └── #10 Spec Kit Export
```

Items #6 and #7 can start immediately. Items #9 and #10 have soft dependencies on #5. Items #5, #8, #11 are sequential core-team work.

## Decisions Made

- **Hosted version:** Dropped. Infrastructure distraction, not interesting to AI/agent devs.
- **Report improvements:** Deferred until execution feedback reveals real gaps.
- **Output quality optimization:** Premature without closing the loop. "You can't know what's wrong with the output until you try to build from the stories."
- **Generic OSS issues (tests, docs):** Not included. Backlog is strategically directed, not a grab bag.

## Labels Created

| Label | Color | Purpose |
|-------|-------|---------|
| `core-team` | Red | Requires deep pipeline knowledge |
| `community-welcome` | Green | Good for external contributors |
| `track:genesis-loop` | Yellow | Closes the Genesis loop |
| `track:ecosystem` | Blue | Makes output useful to agent ecosystem |
| `track:control-plane` | Orange | Extends the control plane pattern |
| `track:enablement` | Light blue | Lowers barrier to contributing |
