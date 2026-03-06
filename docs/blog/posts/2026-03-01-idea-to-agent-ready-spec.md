---
date: 2026-03-01
authors:
  - haytham
categories:
  - Multi-Agent Systems
  - Architecture
tags:
  - openspec
  - spec-kit
  - coding-agents
  - exports
description: "Go from a raw startup idea to a validated OpenSpec or Spec Kit export in 20 minutes. No hand-writing specs."
---

# From Startup Idea to Agent-Ready Spec in 20 Minutes

You type a startup idea into a text box. Twenty minutes later, you download a zip file containing a validated OpenSpec or Spec Kit directory tree, complete with SHALL statements, Gherkin acceptance criteria, architecture decisions, and dependency-ordered stories. No hand-writing specs. No prompt engineering. You unzip it into a project folder, point Claude Code (or Cursor, or Copilot) at it, and start building.

That's the workflow we shipped this week with Haytham's new export layer. This post is about why it matters and what the output actually looks like.

<!-- more -->

## The spec gap

Coding agents have gotten remarkably good at implementing things. The bottleneck has shifted. The hard part is no longer "can an agent write this code?" It's "does the agent know *what* to build?"

OpenSpec and Spec Kit solve the format problem. They give agents a structured directory of requirements, scenarios, and architectural context that's easy to parse and reason about. But someone still has to write the contents of those files. And that's where most projects fall apart.

Writing a good spec is genuinely difficult. You need to research the market to know if the idea is viable. You need to scope the MVP so you're not building everything at once. You need to make architecture decisions that fit the constraints. You need to decompose features into stories with clear acceptance criteria, ordered by dependency so an agent can implement them sequentially without hitting blockers. Most people skip all of this and hand vague requirements to a coding agent. The results are predictable: generic implementations that miss the constraints that made the idea distinctive.

## What Haytham does

Haytham is an open-source multi-agent system with 19 specialist agents organized into four phases. Each phase does a specific job, and each has a human approval gate before the next phase starts.

**WHY** (Should this be built?): Agents research the market with live web search, analyze competitors, and synthesize findings into a GO/PIVOT/NO-GO recommendation with evidence. **WHAT** (What exactly?): Agents scope the MVP, extract a capability model with functional and non-functional requirements, and classify system traits like auth model, deployment target, and data layer. **HOW** (How should we build it?): Build-vs-buy analysis per capability, then architecture decisions covering tech stack, integration patterns, and infrastructure. **STORIES** (What are the tasks?): Dependency-ordered user stories with Gherkin acceptance criteria, layered from infrastructure setup through data models, API contracts, and user-facing features.

The human gates are not a formality. After the WHY phase, you see the market research and validation verdict. If the recommendation is PIVOT, you can adjust the idea and re-run. If it's NO-GO, you've saved yourself from building something nobody wants. These gates exist because the agents are doing real research, not just reformatting your input, and you should review the findings before committing further.

After the STORIES phase completes, a deterministic export pipeline (no LLM calls) transforms all of this structured data into either OpenSpec or Spec Kit format. The pipeline reads the execution contract JSON from the session directory and produces a zip file. Every capability becomes a SHALL statement. Every acceptance criterion becomes a Gherkin scenario. Every architecture decision lands in the right place.

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

That's a real SHALL statement generated from the capability model, with a Gherkin scenario pulled from the story acceptance criteria. A coding agent can parse this directly: the requirement tells it what to build, the scenario tells it how to verify it works.

The Spec Kit export goes further. It produces a `.specify/` directory with numbered feature folders, each containing `spec.md`, `plan.md`, `tasks.md`, and (where applicable) `data-model.md` and `contracts/api.md`. It also generates a `constitution.md` that maps system traits to architectural principles, like "Article 1: Interface Principle" declaring the frontend framework choice, or quality attributes derived from non-functional capabilities. The constitution gives a coding agent the project-wide constraints it needs before it touches any individual feature.

None of this is LLM prose. The export pipeline is pure Python string formatting over structured JSON. The LLMs did their work upstream (research, scoping, architecture). The export is a deterministic transformation of their validated output.

## How to try it

```bash
git clone https://github.com/arslan70/haytham.git
cd haytham
uv sync                    # or: uv sync --extra anthropic
cp .env.example .env       # configure your provider
make run                   # opens at localhost:8501
```

Haytham works with AWS Bedrock (tested), Anthropic, OpenAI, and Ollama (free, local). After the STORIES phase completes, use the export dropdown in the UI to download your spec as OpenSpec or Spec Kit. Unzip into your project root and point your coding agent at the directory. The [Getting Started guide](../../getting-started.md) covers provider setup and model configuration in detail.

## What's next

The export layer makes Haytham's output consumable by any coding agent, but you still have to manually download the zip, extract it, and point your agent at the files. The next step is Phase 5: Coding Agent Integration, where a traced story from the export feeds directly into Claude Code or a similar agent for automated implementation, with validation against the acceptance criteria. **Update (March 2026):** Haytham is now a [Claude Code plugin](../posts/2026-03-03-build-where-developers-already-are.md), which makes this handoff automatic.
