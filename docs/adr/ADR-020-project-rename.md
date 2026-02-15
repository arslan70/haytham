# ADR-020: Project Rename (kickstarter → haytham)

## Status
**Accepted** — 2025-01-28 (proposed), 2026-02 (implemented as haytham)

**Milestone**: Consolidation (Pre-Evolution)

## Context

### The Problem

The codebase used "kickstarter" as the package name, but the product needed a unique identity for open-source release. This created confusion:

- Import statements: `from kickstarter.workflow import ...`
- Directory structure: `kickstarter/agents/...`
- Documentation mixed "Kickstarter" and "Helix"
- Session paths: `session/` (neutral, but config referenced kickstarter)

### Why Rename

1. **Before Evolution milestone** — Major changes are easier before adding new features
2. **Open-source readiness** — Need a unique, non-trademarked project name
3. **Brand identity** — "Haytham" (after Ibn al-Haytham, pioneer of the scientific method) reflects the project's empirical, evidence-driven approach

### Original vs Actual

This ADR originally proposed renaming to `helix`. The actual implementation renamed to `haytham` to avoid potential naming conflicts and better reflect the project's scientific methodology roots.

---

## Decision

### Rename `kickstarter/` → `haytham/`

The Python package was renamed from `kickstarter` to `haytham`.

### Scope

| Component | Before | After |
|-----------|--------|-------|
| Package directory | `kickstarter/` | `haytham/` |
| Import statements | `from kickstarter.* import` | `from haytham.* import` |
| pyproject.toml | `name = "kickstarter"` | `name = "haytham"` |
| Service name | `kickstarter-ai` | `haytham-ai` |
| Container name | `kickstarter-jaeger` | `haytham-jaeger` |

### What Stayed the Same

| Component | Reason |
|-----------|--------|
| `frontend_streamlit/` | Already uses "Haytham" branding, works fine |
| `session/` directory | Neutral name, no change needed |
| `backlog/` directory | Neutral name, no change needed |
| Git repository name | Separate decision |

---

## Implementation

Single atomic commit:

1. `git mv kickstarter haytham` — preserves git history
2. Bulk `sed` across all `.py` files for import replacement
3. Manual updates to `pyproject.toml`, `Makefile`, `.env.example`, `.gitignore`, `docker-compose.yml`, `LICENSE`
4. Documentation updates across `CLAUDE.md`, `README.md`, and ADR files

---

## Consequences

### Positive

1. **Unique identity** — No trademark conflicts for open-source release
2. **Professional appearance** — Consistent naming throughout codebase
3. **Scientific alignment** — Named after the father of the scientific method

### Negative

1. **One-time disruption** — All developers need to pull changes
2. **Documentation churn** — All docs needed review

### Neutral

1. **Git history preserved** — `git mv` maintains full history
2. **No functional changes** — Pure rename, no behavior change
