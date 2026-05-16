# Planning

## Purpose

This domain covers Phase 4 (SPECS) and Phase 5 (build setup). The spec-generator emits an OpenSpec directory tree that a coding agent can use to build the system from zero. The build command scaffolds a fresh project directory and delegates implementation to a separate Claude Code session, preserving the Control-Plane invariant: Haytham declares what to build; downstream sessions execute.

### Requirement: OpenSpec Generation [CAP-F-004]

The system SHALL produce an OpenSpec directory whose structure passes `scripts/validate_openspec.py`, SHALL write a `config.yaml` with name, description, appetite, traits, and generated_at, SHALL write a `project.md` containing Tech Stack, Architecture Decisions, Project Structure, Data Schemas, and Component Map sections, SHALL ensure every capability ID appears in at least one spec file with no capability duplicated across domain specs, and SHALL produce SHALL statements with bare infinitive verbs and Scenario blocks complete with Given, When, and Then.

#### Scenario: OpenSpec passes the validator

- **Given** Phase 3 output exists under `.haytham/session/phase-3-how/`
- **When** the spec-generator agent runs and `scripts/validate_openspec.py` is invoked against the output directory
- **Then** the validator exits with status zero and prints no warnings

#### Scenario: Every capability is covered by at least one spec

- **Given** capabilities.json lists 12 functional and 5 non-functional capabilities
- **When** the validator runs the coverage check against the produced specs
- **Then** the validator finds every CAP-F-* and CAP-NF-* identifier in at least one spec.md file

#### Scenario: No capability appears in multiple domain specs

- **Given** the spec-generator writes capability requirements across multiple domain spec files
- **When** the validator runs the duplicate-capability check
- **Then** no CAP-F-* identifier appears in more than one domain spec.md

#### Scenario: SHALL statements use bare infinitive verbs

- **Given** a spec file contains a Requirement section starting with "The system SHALL"
- **When** the validator scans for SHALL grammar
- **Then** the verb immediately after SHALL is a bare infinitive (e.g., `provide`, `validate`, `produce`) and not a third-person form (e.g., `provides`, `validates`, `produces`)

#### Scenario: Every Scenario block is Gherkin-complete

- **Given** a spec.md contains a Scenario block
- **When** the validator scans the block
- **Then** the block contains all three of `**Given**`, `**When**`, and `**Then**` markers

### Requirement: Build Setup [CAP-F-005]

The system SHALL accept a target project directory, SHALL refuse to overwrite a non-empty directory without explicit confirmation, SHALL copy the OpenSpec tree from Phase 4 output into the target, and SHALL produce founder-facing instructions to continue implementation in a separate Claude Code session.

#### Scenario: Build setup creates a fresh project

- **Given** Phase 4 output exists and the founder runs `/haytham:build ../my-new-product`
- **When** the target directory does not yet exist
- **Then** the command creates the directory, copies the OpenSpec tree into it, initializes git, and prints clear instructions for opening the new project in a fresh Claude Code session

#### Scenario: Build setup refuses to overwrite existing work

- **Given** the target directory exists and contains files
- **When** `/haytham:build` is invoked against it
- **Then** the command refuses to write and surfaces a clear error explaining why, requiring the founder to choose a different target or confirm overwrite explicitly

#### Scenario: Implementation is delegated, not in-session

- **Given** build setup has completed
- **When** the founder reads the instructions printed by the command
- **Then** the instructions tell the founder to open the new directory in a separate Claude Code session and do not invoke any implementation agent inside the current plugin session
