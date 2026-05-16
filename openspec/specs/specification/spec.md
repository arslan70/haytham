# Specification

## Purpose

This domain covers Phase 2 (WHAT). After validation approval, the system converts the approved idea into a structured MVP scope, a capability model with traceability to scope items, and a system trait classification. This phase contains no web search and writes no architecture decisions; its job is to define what the system must do, not how.

### Requirement: MVP Specification and Capability Model [CAP-F-002]

The system SHALL read Phase 1 artifacts as files without re-extracting their values, SHALL produce an MVP scope document with a concept-anchor compliance check, SHALL produce a capability model where every functional and non-functional capability traces to a scope item, and SHALL classify the system's traits across interface, auth, deployment, data layer, realtime, communication, payments, and scheduling.

#### Scenario: Specification reads Phase 1 output by file path

- **Given** Phase 1 output exists under `.haytham/session/phase-1-why/`
- **When** the mvp-scoper and capability-modeler agents run
- **Then** both agents read `concept-anchor.json` and `validation-report.md` by path and do not re-extract values such as the GO/NO-GO verdict or anchor invariants from prose

#### Scenario: MVP scope covers every concept-anchor invariant

- **Given** the concept-anchor.json contains N invariants
- **When** the mvp-scoper produces `mvp-scope.md`
- **Then** the file contains a concept-anchor compliance table with one row per invariant and an IN SCOPE, OUT OF SCOPE, or DEFERRED status for each

#### Scenario: Capability model traces every functional capability to a scope item

- **Given** the mvp-scope.md lists M scope items under IN SCOPE
- **When** the capability-modeler writes `capabilities.json`
- **Then** every `functional[]` entry includes a `serves_scope_item` field referencing a scope item, and every IN SCOPE item is either covered or listed in `traceability.scope_items_not_covered` with a reason

#### Scenario: System traits classification is grounded in the anchor

- **Given** the concept anchor states `session_medium` as "Claude Code CLI session"
- **When** the capability-modeler classifies traits
- **Then** the `interface` trait reflects this constraint and the `explanations.interface` field cites the anchor or scope text that justified the classification

#### Scenario: Capability count respects the stated appetite

- **Given** the MVP scope states an appetite of "Small (1-2 weeks)"
- **When** the capability-modeler produces capabilities
- **Then** the number and granularity of capabilities are commensurate with the appetite and the agent does not invent capabilities the scope does not require
