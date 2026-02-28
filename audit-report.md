# Audit Report

**Date:** 2026-02-28
**Branch:** `main` (post-merge of PR #39)
**Scope:** Documentation quality, security, code hygiene, open-source readiness

---

## Critical

### CRIT-01: Broken link to `concept-paper.md` in ADR-003 and ADR-004
- `docs/adr/ADR-004-multi-phase-workflow-architecture.md:26,1010`
- `docs/adr/ADR-003-system-state-evolution.md:340`
- Links to `../concept-paper.md` which does not exist. File was deleted or renamed.

### CRIT-02: Broken links to `architecture.md` and `phased-workflow.md` in ADR-001
- `docs/adr/ADR-001-story-to-implementation-pipeline.md:297,299`
- Links to `../architecture.md` and `../phased-workflow.md`, neither exists.

### CRIT-03: Broken link to `CONSOLIDATION_PLAN.md` in ADR-018
- `docs/adr/ADR-018-llm-as-judge-agent-testing.md:329`
- Links to `../CONSOLIDATION_PLAN.md` which does not exist.

### CRIT-04: Wrong relative path for ADR-027 link in technology.md
- `docs/technology.md:124`
- `../adr/ADR-027-replace-vectordb-with-json-store.md` resolves outside `docs/` since `technology.md` is already in `docs/`. Should be `adr/ADR-027-replace-vectordb-with-json-store.md`.

### CRIT-05: CHANGELOG.md is missing
- No `CHANGELOG.md` or `CHANGELOG` exists at the repository root.
- A versioned project (v0.1.0, AGPL-licensed) should document changes for downstream users.

---

## Warning

### WARN-01: LLM response logged at DEBUG level (idea_validator.py)
- `frontend_streamlit/lib/idea_validator.py:156`
- `logger.debug(f"Gatekeeper response: {response_text[:500]}...")` logs LLM response content. Violates CLAUDE.md: "Never log LLM prompts/responses."

### WARN-02: Full LLM response logged on parse failure (idea_validator.py)
- `frontend_streamlit/lib/idea_validator.py:255`
- `logger.debug(f"Response text: {response_text}")` logs entire LLM response.

### WARN-03: LLM response logged at WARNING level (feedback_router.py)
- `haytham/feedback/feedback_router.py:248`
- `logger.warning(f"Failed to parse router response: {e}. Response: {response_text[:200]}")` logs at WARNING level (typically enabled in production).

### WARN-04: Agent input/output logged to disk unredacted (logging_utils.py)
- `haytham/agents/utils/logging_utils.py:293,322`
- `log_agent_call()` and `log_agent_response()` write full input/response data to log files. Should redact to length-only, consistent with `log_llm_input`/`log_llm_output`.

### WARN-05: `Backlog.md` auto-linked to `https://backlog.md/` domain
- `docs/architecture/overview.md:114`
- Should link to the Backlog.md product/repo or be unlinked text.

### WARN-06: Broken link to `phase-0-findings.md` in spec export design
- `docs/plans/2026-02-27-spec-export-design.md:4`
- References `./phase-0-findings.md` which does not exist.

### WARN-07: Proposal 001 still says "21 specialist agents"
- `docs/proposals/001-docs-review-and-dogfooding-plan.md:125`
- Should be 19. Already flagged by audit remediation plan but not fixed.

### WARN-08: STORIES phase agents missing from how-it-works.md table
- `docs/how-it-works.md:140-165`
- The agents table covers Discovery, WHY, WHAT, HOW but omits STORIES phase agents.

### WARN-09: Key Patterns section near-verbatim in CLAUDE.md and architecture-patterns.md
- `CLAUDE.md:211-218` and `docs/contributing/architecture-patterns.md:73-81`
- Creates maintenance drift risk. Should summarize in CLAUDE.md and link.

### WARN-10: Em dash in audit remediation plan
- `docs/plans/2026-02-27-audit-remediation-plan.md:743`
- Style guide prohibits em dashes.

### WARN-11: No GitHub Issue Templates
- `.github/ISSUE_TEMPLATE/` directory does not exist. Contributors get a blank text box.

### WARN-12: No Pull Request Template
- `.github/PULL_REQUEST_TEMPLATE.md` does not exist.

### WARN-13: Deprecated `phase_logger.py` still present (457 lines)
- `haytham/agents/utils/phase_logger.py`
- Marked `DEPRECATED` on line 4. No production code imports it. Per CLAUDE.md: "Delete deprecated code."

### WARN-14: `re.compile()` inside function body (story_swarm.py)
- `haytham/agents/worker_story_generator/story_swarm.py:374`
- Regex compiled on every function call. Per CLAUDE.md: "Compile regex at module level."

### WARN-15: Two `except Exception` handlers missing annotation
- `haytham/agents/utils/langfuse_tracer.py:547,578`
- Both in `trace_phase()` and `trace_agent()` context managers. Should have `# Intentional catch-all:` comment per project convention.

---

## Suggestion

### SUG-01: No length limit on user idea input in Streamlit UI
- `frontend_streamlit/views/new_project.py:84`, `frontend_streamlit/views/execution.py:164`
- `st.text_area` accepts arbitrary-length input. Add `max_chars` for defense in depth.

### SUG-02: Session manager `rmtree` calls lack path traversal checks
- `haytham/session/session_manager.py:159,232`
- Currently safe (slugs from StageRegistry), but adding `.resolve().is_relative_to()` guards against future refactors. `project_manager.py` already has this pattern.

### SUG-03: Add CI status badge to README.md
- README has Python and License badges but no CI badge.

### SUG-04: 8 function-body imports lack circular-dependency comments
- `haytham/state/supersede.py:110,211,261`, `haytham/state/coverage.py:145`, `haytham/backlog/cli.py:216`, `haytham/project/project_state.py:312`, `haytham/project/mvp_spec_validator.py:189`, `haytham/feedback/cascade_engine.py:178`
- Stdlib/same-package imports with no documented reason for being inside function bodies.

### SUG-05: 3 module-level `logger.setLevel()` calls
- `haytham/agents/utils/logging_utils.py:13`, `haytham/agents/utils/prompt_loader.py:13`, `haytham/agents/utils/phase_logger.py:31`
- Logging config should be centralized, not set per-module.

### SUG-06: Jargon not expanded in CLAUDE.md
- "JTBD" (line 215), "OTEL" (lines 229-232), "SOM" (line 295) used without expansion.

### SUG-07: `$5--$20` en dash in getting-started.md
- `docs/getting-started.md:144`
- Replace with `$5-$20` for plain-text consistency.

### SUG-08: Consider upper-bound version constraints in pyproject.toml
- All dependencies use `>=` with no upper bounds. Consider `>=X,<Y` for major versions or maintain a lockfile for CI/production.

### SUG-09: HTML-escape LLM-generated strings before `unsafe_allow_html=True`
- 50+ occurrences of `unsafe_allow_html=True` across `frontend_streamlit/`. Most embed static HTML, but LLM-generated content could contain injected HTML.

### SUG-10: Test coverage gaps for core modules
- 14 core modules have no direct test file, including: `agent_factory.py`, `output_utils.py`, `agent_runner.py`, `burr_workflow.py`, `context_builder.py`, `stage_registry.py`, `idea_validation.py`, `mvp_specification.py`, `story_pipeline.py`, `technical_design.py`, `feedback_agent.py`, `revision_executor.py`, `formatting.py`, `config.py`.

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 5 |
| Warning | 15 |
| Suggestion | 10 |
| **Total** | **30** |

**No CI-breaking issues.** Ruff check, ruff format, and all 979 unit tests pass. No hardcoded secrets, no unsafe imports, no exploitable vulnerabilities.

The critical findings are all broken internal links in ADR documents (files renamed/deleted during project evolution) plus a missing CHANGELOG.md. The warning-level findings cluster around logging policy violations (LLM responses written to logs), stale documentation, and deprecated code that should be deleted.
