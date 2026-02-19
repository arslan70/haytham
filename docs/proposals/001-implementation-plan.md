# Proposal 001: Implementation Plan

Tracks all action items from [001-docs-review-and-dogfooding-plan.md](./001-docs-review-and-dogfooding-plan.md).

**Status key:** `TODO` | `IN PROGRESS` | `DONE` | `DEFERRED`

---

## Part A: Claude Can Do (Documentation Improvements)

| # | Item | Source | Status |
|---|------|--------|--------|
| A1 | Reorganize ADR index by topic with "Start Here" note | Issue 5 | DONE |
| A2 | Add system-level mermaid architecture diagram to `docs/architecture/overview.md` | Issue 6 | DONE |
| A3 | Expand CONTRIBUTING.md with first-contribution walkthrough, testing guide, and "good first issue" guidance | Issue 3 | DONE |
| A4 | Reframe `docs/roadmap.md` for community readers (intro, contribution-friendliness labels, dogfooding mention) | Issue 4 | DONE |
| A5 | Extract architecture patterns and code hygiene from CLAUDE.md into `docs/contributing/architecture-patterns.md`, link back from CLAUDE.md and CONTRIBUTING.md | Issue 2 | DONE |
| A6 | Create `docs/dogfood/` directory structure and README | Part 2 | DONE |
| A7 | Draft Haytham idea statement (`docs/dogfood/haytham-idea-statement.md`) for review | Part 2, Phase 0 | DONE |
| A8 | Add "Dogfooding: Haytham Specs Itself" section to README (placeholder until session outputs exist) | Part 2 | DONE |

## Part B: User Must Do

| # | Item | Source | Status |
|---|------|--------|--------|
| B1 | Capture or provide Streamlit UI screenshots (gate approval screen, pipeline view, stage output) for README/how-it-works | Issue 1 | DONE |
| B2 | Provide or run a session to populate `docs/example-session/` with real outputs | Issue 1 | DONE |
| B3 | Consider recording a ~2 min demo video or animated GIF | Issue 1 | TODO |
| B4 | Review and approve A5 (CLAUDE.md split) since it modifies the project's core instructions | Issue 2 | DONE |
| B5 | Review and refine A7 (Haytham idea statement) before dogfood run | Part 2, Phase 0 | DEFERRED |
| B6 | Run Haytham on its own idea statement through all four phases (dogfood session v1) | Part 2, Phase 1 | DEFERRED |
| B7 | Write annotations for each phase output (what it got right, wrong, surprised) | Part 2, Phase 2 | DEFERRED |
| B8 | Create GitHub Issues from generated stories with `dogfood-v1` and `good-first-issue` labels | Part 2, Phase 3 | DEFERRED |

---

## Deferral: Dogfooding (B5-B8)

**Decision:** Deferred until Evolution (M2) has codebase-aware story generation.

**Rationale:** Genesis produces specifications for *new* systems. Running it on Haytham would generate stories for building Haytham from scratch, not for improving the existing codebase. The system has no awareness of what already exists, so generated architecture decisions and stories would be largely inapplicable. The real value of dogfooding (the recursive improvement loop) requires Evolution's "existing system + change request = targeted changes" capability.

**What's preserved:** The scaffolding (A6-A8) remains in place. `docs/dogfood/`, the idea statement draft, and the README section cost nothing to keep and will be ready when Evolution lands.

**Revisit when:** Evolution (M2) can accept an existing codebase as context and generate targeted change stories rather than greenfield specifications.

---

## Dependency Notes

- **A1-A4** are independent of each other and can be done in any order
- **A5** (CLAUDE.md split) needs your review (B4) before merging
- **B1-B3** (screenshots/demo) are independent and can happen anytime
- **B5-B8** (dogfood run) deferred until Evolution (M2)
