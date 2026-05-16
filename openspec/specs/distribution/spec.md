# Distribution

## Purpose

This domain covers how Haytham reaches its users: the Claude Code plugin marketplace, the source-of-truth GitHub repository, and the version-management discipline that lets Claude Code propagate updates correctly. There is no separate release pipeline beyond `git push` and a version bump.

### Requirement: Plugin Distribution via Marketplace [CAP-F-012]

The system SHALL ship a `.claude-plugin/marketplace.json` that validates against the Claude Code marketplace schema, SHALL ship a `.claude-plugin/plugin.json` with name, description, author, repository, and license, SHALL bump the version only inside `plugins[0].version` in marketplace.json (not in plugin.json), SHALL keep the repository field pointing at a publicly accessible GitHub URL, and SHALL install cleanly via `/plugin marketplace add` followed by `/plugin install` on a fresh Claude Code session.

#### Scenario: Marketplace manifest validates against the schema

- **Given** the repository contains `.claude-plugin/marketplace.json` with a `$schema` field
- **When** the file is loaded by Claude Code's plugin loader
- **Then** the loader parses the manifest without errors and registers exactly one plugin entry named "haytham" with a populated `version` field

#### Scenario: Plugin manifest has required metadata

- **Given** the repository contains `.claude-plugin/plugin.json`
- **When** the file is read
- **Then** the JSON object contains `name`, `description`, `author`, `repository`, and `license` fields, and the `name` matches the marketplace.json plugin name

#### Scenario: Version lives only in marketplace.json

- **Given** a release is being prepared
- **When** the version is bumped
- **Then** the change updates only `plugins[0].version` in `.claude-plugin/marketplace.json` and not any `version` field in `.claude-plugin/plugin.json`

#### Scenario: Repository URL is publicly resolvable

- **Given** marketplace.json declares `repository` as a GitHub URL
- **When** an installer follows that URL
- **Then** the URL resolves to a publicly accessible GitHub repository and the plugin source can be cloned without authentication

#### Scenario: Two-command install on a clean session

- **Given** a Claude Code session with no haytham plugin installed
- **When** the user runs `/plugin marketplace add arslan70/haytham` followed by `/plugin install haytham@haytham`
- **Then** the plugin is installed without prompting for API keys or environment variables and `/haytham` becomes available as a slash command
