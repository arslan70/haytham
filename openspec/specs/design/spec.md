# Design

## Purpose

This domain covers Phase 3 (HOW). After specification, the architect agent produces a build-vs-buy analysis and a set of architecture decisions. Each decision cites the capabilities it serves and the alternatives that were considered. Web search is allowed in this phase so recommendations can be grounded in current product realities; web judgement remains qualitative while traceability and coverage are deterministic.

### Requirement: Architecture Decisions and Build/Buy Analysis [CAP-F-003]

The system SHALL produce a build-vs-buy analysis with one recommendation per infrastructure category, SHALL produce architecture decisions where every decision cites the capabilities it serves, SHALL list alternatives considered with concrete pros and cons, and SHALL cover every functional and non-functional capability with at least one architecture decision.

#### Scenario: Architect reads upstream artifacts by path

- **Given** Phase 2 output exists under `.haytham/session/phase-2-what/`
- **When** the architect agent runs
- **Then** the agent reads `capabilities.json`, `system-traits.json`, and `mvp-scope.md` by path and does not re-derive their contents

#### Scenario: Build/buy analysis recommends per category

- **Given** the system-traits.json declares the system needs database, hosting, auth, payments, and email
- **When** the architect produces `build-buy.json`
- **Then** the `recommended_stack[]` includes one entry per infrastructure category with a BUY, BUILD, or PLATFORM recommendation and a rationale paragraph that names the specific capability constraint that drove the choice

#### Scenario: Every architecture decision cites served capabilities

- **Given** the architect produces N architecture decisions
- **When** the decisions are written to `architecture-decisions.json`
- **Then** every decision has a non-empty `serves_capabilities[]` array referencing valid CAP-F-* or CAP-NF-* IDs from the capability model

#### Scenario: Coverage check lists capabilities and decisions

- **Given** architecture-decisions.json has been written
- **When** the file is read
- **Then** the `coverage_check` object lists every covered functional and non-functional capability, and any uncovered capability is named with the reason it has no dedicated decision

#### Scenario: Alternatives considered are concrete

- **Given** an architecture decision recommends a specific stack choice
- **When** the alternatives_considered are recorded
- **Then** each alternative names a concrete option (not a generic category) and gives concrete pros and cons, not hand-waving prose
