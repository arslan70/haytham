---
date: 2026-03-01
authors:
  - haytham
categories:
  - Multi-Agent Systems
  - Architecture
tags:
  - openspec
  - coding-agents
  - specs
description: "Go from a raw startup idea to a validated OpenSpec in 20 minutes. No hand-writing specs."
---

# From Startup Idea to Agent-Ready Spec in 20 Minutes

You describe a startup idea. Twenty minutes later, you have a validated OpenSpec directory tree, complete with SHALL requirements, Gherkin acceptance criteria, and architecture decisions. No hand-writing specs. No prompt engineering. Point Claude Code (or Cursor, or Copilot) at it and start building.

That's the workflow Haytham delivers. This post is about why it matters and what the output actually looks like.

<!-- more -->

## The spec gap

Coding agents have gotten remarkably good at implementing things. The bottleneck has shifted. The hard part is no longer "can an agent write this code?" It's "does the agent know *what* to build?"

OpenSpec and Spec Kit solve the format problem. They give agents a structured directory of requirements, scenarios, and architectural context that's easy to parse and reason about. But someone still has to write the contents of those files. And that's where most projects fall apart.

Writing a good spec is genuinely difficult. You need to research the market to know if the idea is viable. You need to scope the MVP so you're not building everything at once. You need to make architecture decisions that fit the constraints. You need to decompose features into SHALL requirements with Gherkin scenarios so an agent can implement them domain by domain without ambiguity. Most people skip all of this and hand vague requirements to a coding agent. The results are predictable: generic implementations that miss the constraints that made the idea distinctive.

## What Haytham does

Haytham is an open-source multi-agent system with 19 specialist agents organized into four phases. Each phase does a specific job, and each has a human approval gate before the next phase starts.

**WHY** (Should this be built?): Agents research the market with live web search, analyze competitors, and synthesize findings into a GO/PIVOT/NO-GO recommendation with evidence. **WHAT** (What exactly?): Agents scope the MVP, extract a capability model with functional and non-functional requirements, and classify system traits like auth model, deployment target, and data layer. **HOW** (How should we build it?): Build-vs-buy analysis per capability, then architecture decisions covering tech stack, integration patterns, and infrastructure. **SPECS** (What are the specs?): OpenSpec with SHALL requirements and Gherkin scenarios, grouped by domain from infrastructure through data models, API contracts, and user-facing features.

The human gates are not a formality. After the WHY phase, you see the market research and validation verdict. If the recommendation is PIVOT, you can adjust the idea and re-run. If it's NO-GO, you've saved yourself from building something nobody wants. These gates exist because the agents are doing real research, not just reformatting your input, and you should review the findings before committing further.

The SPECS phase produces OpenSpec directly. The spec-generator agent reads all upstream artifacts and writes the OpenSpec directory tree: config.yaml for project metadata, project.md for architecture context, and domain-grouped spec files with SHALL statements and Gherkin scenarios. Every capability becomes a requirement. Every architecture decision is documented with rationale.

## What the output looks like

Here's the OpenSpec directory tree from a gym leaderboard app:

```
openspec/
├── config.yaml
├── project.md
└── specs/
    ├── user-authentication/
    │   └── spec.md
    ├── leaderboard-management/
    │   └── spec.md
    └── cross-cutting/
        └── spec.md
```

Inside `specs/user-authentication/spec.md`, you get requirements like this:

```markdown
### Requirement: Secure Authentication

The system SHALL provide secure user authentication with
email/password login and session management.

#### Scenario: Successful login

- **Given** a registered user with valid credentials
- **When** the user submits their email and password
- **Then** the system authenticates the user and creates a session
```

That's a real SHALL statement generated from the capability model, with a Gherkin scenario generated from the capability model. A coding agent can parse this directly: the requirement tells it what to build, the scenario tells it how to verify it works.

## How to try it

Haytham is now a Claude Code plugin. Install it and run:

```
/plugin marketplace add arslan70/haytham
/plugin install haytham@haytham
/haytham "your startup idea here"
```

After the SPECS phase completes, the OpenSpec directory is ready at `.haytham/session/phase-4-specs/openspec/`. Point your coding agent at the directory.

## What's next

The next step is Phase 5: Coding Agent Integration, where a traced requirement from the OpenSpec feeds directly into Claude Code for automated implementation, with validation against the Gherkin scenarios. **Update (March 2026):** Haytham is now a [Claude Code plugin](../posts/2026-03-03-build-where-developers-already-are.md), which makes the handoff seamless.
