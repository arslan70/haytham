# Dogfooding: Haytham Specs Itself

Haytham validates startup ideas and generates implementation specs. Haytham *is* a startup idea. The plan is to run Haytham on itself to generate stories for the next version.

**Status: Deferred** until Evolution (M2) is operational. See rationale below.

## Why Deferred

Genesis produces greenfield specifications for *new* systems. Running it on Haytham today would generate stories for building the system from scratch, not for improving what already exists. The system has no awareness of the current codebase, so architecture decisions and stories would be largely inapplicable.

Meaningful dogfooding requires Evolution's codebase-aware story generation: "existing system + change request = targeted changes." Once that capability exists, Haytham can analyze its own codebase, generate targeted improvement stories, and the recursive improvement loop becomes real.

## What's Ready

The scaffolding is in place for when Evolution lands:

- `haytham-idea-statement.md` - draft idea statement describing Haytham as a startup idea
- Directory structure for session outputs
- [Proposal 001](../proposals/001-docs-review-and-dogfooding-plan.md) documents the full execution plan

## Planned Structure

```
docs/dogfood/
  haytham-idea-statement.md          # The input fed to Haytham
  session-v1/
    phase-1-validation/              # Raw validation output
    phase-2-specification/           # Raw MVP scope + capabilities
    phase-3-design/                  # Raw build/buy + architecture
    phase-4-stories/                 # Raw stories
    annotations.md                   # Team commentary on outputs
```
