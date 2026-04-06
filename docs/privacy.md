# Privacy Policy

*Last updated: April 6, 2026*

## Overview

Haytham is a Claude Code plugin that runs entirely within your local Claude Code session. It does not operate a backend service, does not collect telemetry, and does not transmit your data to any servers controlled by the Haytham project.

## What Haytham processes

When you run a Haytham command (e.g., `/haytham "your idea"`), the plugin:

- Reads and writes files in your local `.haytham/` session directory
- Sends prompts to Claude via Claude Code's built-in agent infrastructure
- For market and competitor research (Phase 1 and Phase 3), uses Claude Code's `WebSearch` and `WebFetch` tools to query public web data

All of this happens through Claude Code. Haytham itself does not make network requests or maintain any external connections.

## Data storage

All session data (validation reports, MVP scopes, architecture decisions, generated specs) is stored locally in the `.haytham/` directory within your project. No data is sent to Haytham's maintainers or any third-party service.

## Data collection

Haytham collects **no** user data. Specifically:

- No analytics or usage tracking
- No crash reporting
- No cookies or identifiers
- No account creation required
- No data shared with third parties

## Third-party services

Haytham delegates all LLM inference and web search to Claude Code. Your interactions with Claude are governed by [Anthropic's privacy policy](https://www.anthropic.com/privacy) and [terms of service](https://www.anthropic.com/terms). Haytham has no access to your Anthropic account or API keys.

## Your control

- You can delete all session data at any time by removing the `.haytham/` directory
- You can uninstall the plugin at any time via Claude Code
- No data persists outside your local machine

## Changes to this policy

If this policy changes, the updated version will be published in this repository with a revised date. Since Haytham has no way to contact users, checking the repo is the only way to see updates.

## Contact

For questions about this policy, open an issue at [github.com/arslan70/haytham](https://github.com/arslan70/haytham/issues).
