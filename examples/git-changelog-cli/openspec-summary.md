# OpenSpec Summary

Phase 4 produces an `openspec/` directory that a coding agent can use to build the system from zero. Here's what the spec generator produced for the git changelog CLI.

## Structure

```
openspec/
  config.yaml                          # Project metadata, appetite, system traits
  project.md                           # Tech stack, architecture decisions, dependencies
  specs/
    commit-parsing/spec.md             # Git log reading and commit range resolution
    commit-classification/spec.md      # LLM-powered commit categorization
    changelog-output/spec.md           # Markdown formatting and file output
    cli-interface/spec.md              # Argument parsing, defaults, configuration
    cross-cutting/spec.md              # Non-functional requirements
```

## Requirement Counts

| Domain | Functional Requirements | Scenarios |
|--------|------------------------|-----------|
| Commit Parsing | 2 (CAP-F-001, CAP-F-002) | 6 |
| Commit Classification | 2 (CAP-F-003, CAP-F-004) | 7 |
| Changelog Output | 2 (CAP-F-005, CAP-F-006) | 5 |
| CLI Interface | 2 (CAP-F-007, CAP-F-008) | 6 |
| Cross-Cutting | 2 (CAP-NF-001, CAP-NF-002) | 4 |
| **Total** | **10** | **28** |

## Example Spec Snippet

From `specs/commit-classification/spec.md`:

```markdown
# Commit Classification

## Purpose

Classify git commits into changelog-relevant categories using an LLM,
handling messy real-world commit messages that don't follow conventions.

### Requirement: Classify Commits by Type [CAP-F-003]

The system SHALL classify each commit into one of the following categories:
feature, fix, breaking, chore, docs.

#### Scenario: Clear feature commit

- **Given** a commit with message "Add dark mode toggle to settings page"
- **When** the system classifies the commit
- **Then** the commit is classified as "feature"

#### Scenario: Ambiguous commit message

- **Given** a commit with message "stuff" and a diff that modifies error handling in auth.py
- **When** the system classifies the commit
- **Then** the system uses the diff content to classify the commit as "fix"

#### Scenario: Breaking change detection

- **Given** a commit with message "rename config keys" and a diff that removes
  the `api_key` field from config.json and adds `api_token`
- **When** the system classifies the commit
- **Then** the commit is classified as "breaking"

#### Scenario: LLM API failure

- **Given** the LLM API returns an error or times out
- **When** the system attempts to classify a commit
- **Then** the commit is placed in an "unclassified" category and the user
  is warned that N commits could not be classified
```

## System Traits

```yaml
traits:
  interface: [terminal]
  auth: none
  deployment: [package_registry]
  data_layer: file_system
  realtime: false
  communication: none
  payments: none
  scheduling: none
```

These traits drove the architecture decisions: no web framework, no database, no auth. The project is a Node.js CLI published to npm, reading from git and writing to stdout or files.
