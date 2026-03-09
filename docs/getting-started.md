# Getting Started

## Prerequisites

- [Claude Code](https://claude.ai/code) installed and authenticated.

## Install

```
/plugin marketplace add arslan70/haytham
/plugin install haytham@haytham
```

That's it. No Python, no API keys, no environment variables. Your existing Claude Code subscription handles all LLM calls.

## First Run

Run the full 4-phase workflow:

```
/haytham "a gym community leaderboard with anonymous handles"
```

Or run individual phases:

| Command | Phase | What it does |
|---------|-------|-------------|
| `/haytham:validate` | WHY | Market research, competitor analysis, GO/NO-GO/PIVOT verdict |
| `/haytham:specify` | WHAT | MVP scope, capability model, system traits |
| `/haytham:design` | HOW | Build-vs-buy analysis, architecture decisions |
| `/haytham:plan` | SPECS | OpenSpec with SHALL requirements and Gherkin scenarios |

## What to Expect

Each phase runs specialist agents, writes structured output to `.haytham/session/`, and presents a gate decision for your review. Nothing proceeds without your approval.

```
.haytham/
  project.yaml                     # Your startup idea
  session/
    phase-1-why/                   # Validation findings and verdict
    phase-2-what/                  # MVP scope and capabilities
    phase-3-how/                   # Architecture decisions
    phase-4-specs/                 # Implementation-ready OpenSpec
```

A full 4-phase run takes approximately 15-20 minutes.

## Local Development

To modify agents or commands, clone the repo and work locally:

```bash
git clone https://github.com/arslan70/haytham.git
cd haytham
```

### Modifying Agents

Agent prompts are markdown files in `agents/`. Edit any file, then reload the plugin to pick up changes. Each agent file contains a system prompt with frontmatter for model selection and tool permissions.

### Adding a New Agent

1. Create `agents/your-agent.md` with appropriate frontmatter and system prompt
2. Reference it from the relevant command in `commands/`

### Adding a New Command

1. Create `commands/your-command.md`
2. The command becomes available as `/haytham:your-command`

### Testing Changes

Run the plugin against a test idea:

```
/haytham "a recipe sharing app for home cooks with dietary restrictions"
```

Check the output files in `.haytham/session/` to verify agent behavior.
