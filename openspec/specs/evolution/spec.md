# Evolution

## Purpose

This domain covers `/haytham:evolve`, the change-application loop that maintains the reasoning graph alongside code changes. Three variant proposers run in parallel with different framings, an orchestrator synthesizes a recommendation with explicit tradeoffs, the founder confirms, and the chosen variant executes both code and graph updates in a single commit. This is the loop that makes Genesis output durable across the product's lifetime.

### Requirement: Graph-Maintaining Change Application [CAP-F-007]

The system SHALL refuse to run without a change description and an `openspec/` directory in the current path, SHALL launch three variant proposers in parallel with distinct framings (minimal graph touch, clean refactor, pragmatic middle), SHALL detect and surface invariant or scope conflicts before synthesis, SHALL commit to a recommended variant with one specific reason and a cited file, SHALL require user confirmation before execution, SHALL execute code and graph updates in a single commit naming the variant, and SHALL stop and surface discrepancies rather than silently deviate when a proposal step proves wrong.

#### Scenario: Evolve refuses without preconditions

- **Given** the current directory contains no `openspec/` subdirectory or the user passed no change description
- **When** the founder runs `/haytham:evolve` or `/haytham:evolve ""`
- **Then** the command refuses with a clear message and does not launch any agent

#### Scenario: Three variants run in parallel

- **Given** preconditions are satisfied and the founder runs `/haytham:evolve "add a category-first home page"`
- **When** the orchestrator dispatches variant proposers
- **Then** three Agent tool calls are issued in a single message with the same file list and change description but distinct framings, and all three return before the orchestrator proceeds

#### Scenario: Read-only proposers do not mutate state

- **Given** the three variant proposers are running
- **When** any proposer attempts to write code, write graph files, or commit
- **Then** the proposal returns without any side effect and the orchestrator's eventual execution step is the only writer in the run

#### Scenario: Invariant conflict halts synthesis

- **Given** any variant returns `INVARIANT_CONFLICT:` or `SCOPE_CONFLICT:` followed by the conflicting text
- **When** the orchestrator receives the three responses
- **Then** the orchestrator surfaces the conflict verbatim, does not synthesize a recommendation, and asks the founder how to resolve

#### Scenario: Orchestrator commits to a recommendation

- **Given** all three variants return non-conflicting proposals
- **When** the orchestrator synthesizes
- **Then** the comparison table lists files touched, graph delta, tradeoff, and confidence per variant, and the recommendation paragraph names the chosen variant, gives one specific reason citing a file from the graph (mvp-scope.md, capabilities.json, or a spec path), and says in one sentence each what the rejected variants gave up

#### Scenario: Execution commits code and graph together

- **Given** the founder confirms a variant
- **When** the chosen variant executes
- **Then** the final commit contains both the code changes and any updates to capabilities.json, architecture-decisions.json, mvp-scope.md, concept-anchor.json, or specs/*/spec.md, and the commit message names the variant (e.g., "evolve: <change> [variant B]")

#### Scenario: Discrepancies stop execution

- **Given** the chosen variant's proposal names a file path that does not exist
- **When** the executor tries to modify that file
- **Then** the executor stops, surfaces the discrepancy, and does not silently improvise an alternative file path

#### Scenario: Self-check filters by confidence

- **Given** execution has completed
- **When** the self-check pass runs
- **Then** only concerns with confidence at or above 80 are surfaced explicitly, and lower-confidence concerns are collapsed into one trailing line indicating the suppressed count
