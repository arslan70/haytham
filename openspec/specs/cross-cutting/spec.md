# Cross-Cutting

## Purpose

This domain covers requirements that span multiple phases of the pipeline: the full-pipeline orchestrator, the four pipeline-output reviews, the UX review, and the non-functional invariants that govern how every phase operates (anchor preservation, deterministic-vs-qualitative boundary, zero setup, archetype genericity, phase gating).

### Requirement: Full-Pipeline Orchestration [CAP-F-006]

The system SHALL run Phases 1 through 4 in order without skipping phases, SHALL pause at every phase boundary for human approval in normal mode, SHALL auto-approve every gate in BATCH_MODE and skip interactive review steps, SHALL read each upstream artifact as a file rather than passing state in memory, and SHALL offer a resume option from the failed phase on phase failure rather than restart from the beginning.

#### Scenario: Pipeline runs phases in order

- **Given** the founder runs `/haytham "an idea"`
- **When** the orchestrator dispatches phases
- **Then** Phase 1 completes before Phase 2 starts, Phase 2 before Phase 3, and Phase 3 before Phase 4, with no phase skipped or reordered

#### Scenario: Approval gate pauses between phases

- **Given** Phase 1 has completed in normal mode
- **When** the orchestrator reaches the Phase 1 to Phase 2 boundary
- **Then** the orchestrator surfaces the Phase 1 output digest and waits for founder approval before invoking any Phase 2 agent

#### Scenario: BATCH_MODE skips gates

- **Given** the founder runs `/haytham "an idea" --batch`
- **When** the orchestrator reaches any phase boundary
- **Then** the orchestrator auto-approves the gate, does not prompt for review, and proceeds directly to the next phase

#### Scenario: Resume from a failed phase

- **Given** Phase 2 has failed mid-run and `.haytham/session/phase-2-what/` is partially populated
- **When** the founder runs `/haytham:validate --from 2` (or the equivalent resume command)
- **Then** the orchestrator restarts at Phase 2 reading the existing Phase 1 output and does not re-run Phase 1

### Requirement: Pipeline Output Reviews [CAP-F-010]

The system SHALL provide four review commands (review-depth, review-fidelity, review-consistency, review-actionability) that read pipeline outputs from `.haytham/session/`, SHALL emit a markdown report with PASS, PARTIAL, or FAIL per dimension with specific evidence citations, SHALL not modify pipeline output, and SHALL run independently of the pipeline phase they evaluate so they can be re-run after correction.

#### Scenario: Review-depth evaluates Phase 1 quality

- **Given** Phase 1 output exists under `.haytham/session/phase-1-why/`
- **When** the founder runs `/haytham:review-depth`
- **Then** the command emits a report scoring analysis depth and evidence quality per dimension and cites specific file lines or sections as evidence for each score

#### Scenario: Reviews are read-only

- **Given** any review command is running
- **When** the review attempts to read pipeline output
- **Then** the command's `allowed-tools` frontmatter contains only Read and Glob, and the command writes no files into `.haytham/session/`

#### Scenario: Reviews are re-runnable

- **Given** a review has completed and surfaced a FAIL on one dimension
- **When** the founder fixes the underlying agent prompt and the pipeline re-runs that phase
- **Then** the review can be re-invoked on the new output and produces a fresh report without needing pipeline state to be reset

### Requirement: UX Review of Pipeline Run [CAP-F-011]

The system SHALL accept a path to a transcript file, SHALL read the current Agent UX Standards from CLAUDE.md at runtime, SHALL produce a row-per-standard report with PASS, PARTIAL, or FAIL plus a transcript quote or line reference, and SHALL surface concrete improvement suggestions actionable as prompt changes.

#### Scenario: UX review reads CLAUDE.md at runtime

- **Given** the founder runs `/haytham:ux-review path/to/transcript.txt`
- **When** the command loads its rules
- **Then** the command reads CLAUDE.md from the current repository and does not embed UX standards in its own prompt body

#### Scenario: Each standard gets a verdict and an evidence pointer

- **Given** the review has read CLAUDE.md and the transcript
- **When** the report is emitted
- **Then** each row of the report names one UX standard, assigns PASS, PARTIAL, or FAIL, and quotes or line-references the specific transcript span that justified the verdict

### Requirement: Concept Anchor Drift Prevention [CAP-NF-001]

The system SHALL pass the concept anchor extracted in Phase 1 unchanged to every downstream phase, SHALL forbid agents from re-deriving values already present in upstream artifacts, and SHALL preserve every anchor invariant verbatim from `.haytham/session/phase-1-why/concept-anchor.json` to `phase-4-specs/openspec/context/concept-anchor.json`.

#### Scenario: Anchor invariants survive every phase

- **Given** Phase 1 has produced concept-anchor.json with N invariants
- **When** Phase 4 has produced its OpenSpec output
- **Then** every invariant from Phase 1 appears verbatim in `phase-4-specs/openspec/context/concept-anchor.json`, with no reworded or removed entries

#### Scenario: Downstream agents read the anchor by path

- **Given** any Phase 2, 3, or 4 agent runs
- **When** the agent needs concept-anchor values
- **Then** the agent reads `concept-anchor.json` by file path and does not extract values from validation-report.md prose

### Requirement: Deterministic Rules in Hooks, Qualitative Judgement in LLM [CAP-NF-002]

The system SHALL enforce non-negotiable rules (phase prerequisites, output schemas, SHALL grammar, Gherkin completeness, capability coverage, no duplicate capabilities) via hook scripts that exit non-zero on violation, and SHALL not place these rules inside LLM prompt text where compliance is variable.

#### Scenario: Phase prereq violation blocks the agent call

- **Given** the user runs `/haytham:specify` with no Phase 1 output present
- **When** the Agent tool is about to be invoked
- **Then** `check_phase_prereqs.sh` fires from the PreToolUse hook, exits non-zero, and Claude Code refuses to dispatch the agent

#### Scenario: Schema violation surfaces from PostToolUse

- **Given** an agent writes a malformed JSON file (e.g., capabilities.json with missing required fields)
- **When** the Write tool finishes
- **Then** `validate_schema.py` fires from the PostToolUse hook and surfaces the violation in the session log

#### Scenario: OpenSpec validator catches grammar and coverage gaps

- **Given** Phase 4 has emitted an OpenSpec directory
- **When** `validate_openspec.py` is invoked against that directory
- **Then** the script enforces all of: required config keys present, project.md sections present, no duplicate capabilities across domain specs, SHALL verbs are bare infinitives, every Scenario contains Given/When/Then, and every capability appears in at least one spec

### Requirement: Zero-Setup Distribution [CAP-NF-003]

The system SHALL run end-to-end on a fresh Claude Code session without requiring the user to set API keys, define environment variables, install Python packages beyond what the OS ships, or create accounts beyond their existing Claude Code subscription.

#### Scenario: Fresh install runs a full validation

- **Given** a fresh Claude Code session on a machine with the plugin newly installed and no haytham-specific environment configured
- **When** the user runs `/haytham "an idea"`
- **Then** the pipeline runs to completion without prompting for an API key, an environment variable, or an external account credential

#### Scenario: Hook scripts use standard interpreters

- **Given** the repository ships hook scripts in `scripts/`
- **When** the scripts are inspected
- **Then** every script uses an interpreter present by default on macOS, Linux, and WSL (Bash, Python 3), and no script requires `pip install` of a non-standard library

### Requirement: Genericity Across Input Archetypes [CAP-NF-004]

The system SHALL produce coherent output for every valid startup-idea archetype (web app, CLI tool, API service, marketplace, embedded system), SHALL keep every prompt and every hook rule free of archetype-specific prescriptions, and SHALL pass a cross-archetype test before any change to a prompt or hook is merged.

#### Scenario: Prompt review rejects prescription

- **Given** a prompt change adds language naming a specific technology (e.g., "Use Supabase") or a fixed count (e.g., "list five capabilities")
- **When** the change is reviewed
- **Then** the reviewer rejects the change because it violates archetype genericity, and the author rewrites the rule to enforce a principle (traceability, consistency) rather than a prescription

#### Scenario: Cross-archetype validation

- **Given** the plugin has run on at least one marketplace product (GiftKaro), one web app (TinyTales), and one developer tool (Haytham itself)
- **When** any prompt or hook is modified
- **Then** the change is validated against representative inputs from at least two archetypes before release

### Requirement: Phase Prerequisite Gating [CAP-NF-005]

The system SHALL refuse to dispatch any phase agent if the upstream phase output is missing, SHALL enforce this check via the `check_phase_prereqs.sh` PreToolUse hook on the Agent tool, and SHALL produce a clear founder-facing error message naming the missing prerequisite.

#### Scenario: Missing prereq blocks dispatch with a useful message

- **Given** no Phase 2 output exists and the founder runs `/haytham:design`
- **When** the orchestrator tries to invoke the architect agent
- **Then** the PreToolUse hook fires, the dispatch is blocked, and the user sees an error message that names the missing file path (e.g., `.haytham/session/phase-2-what/capabilities.json`) so they can either run the prerequisite phase or correct the working directory
