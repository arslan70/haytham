# Contributing to Haytham

Thanks for your interest in contributing! This guide covers everything from your first PR to advanced agent testing.

---

## Your First Contribution

Not sure where to start? Here are three paths, ordered by increasing complexity:

### Path 1: Improve a Prompt (no code, no API keys)

Every agent has a plain-text prompt file in `haytham/agents/worker_*/`. Read one, run the pipeline mentally, and suggest improvements. Prompt changes are high-impact because they directly affect output quality.

1. Pick an agent prompt: `haytham/agents/worker_market_intelligence/worker_market_intelligence_prompt.txt`
2. Read the corresponding [How It Works](docs/how-it-works.md) section to understand what the agent should produce
3. Edit the prompt, commit, and open a PR explaining what you changed and why

### Path 2: Add or Improve Tests (no API keys)

The test suite runs entirely without LLM calls. Tests use synthetic fixtures and mocked agents.

1. Look at `tests/conftest.py` for the synthetic data patterns
2. Pick a test file and read what it covers
3. Add a test case for an edge case or untested path
4. Run: `uv run pytest tests/ -v -m "not integration" -x`

### Path 3: Work from the Dogfood Backlog

Haytham generates its own implementation stories by running the pipeline on itself. These stories come with capability references, architecture decisions, and acceptance criteria, so you can jump straight into implementation.

Browse the backlog: [dogfood issues](https://github.com/arslan70/haytham/labels/dogfood-v1) | [docs/dogfood/](docs/dogfood/)

---

## Development Setup

```bash
# Clone the repository
git clone https://github.com/arslan70/haytham.git
cd haytham

# Install dependencies (including dev tools)
uv sync --dev

# Copy the environment template
cp .env.example .env
```

### Running Without AWS Credentials

You don't need an AWS account to develop on Haytham. See [Getting Started](docs/getting-started.md#provider-setup) for Anthropic, OpenAI, and Ollama setup instructions.

### Running the App

```bash
make run
# Open http://localhost:8501
```

---

## How to Test Without LLM Calls

Most development doesn't require API keys or LLM calls. Here's how the testing layers work:

### Unit Tests (no API keys, fast)

```bash
uv run pytest tests/ -v -m "not integration" -x
```

These tests use synthetic fixtures defined in `tests/conftest.py` (MVP scopes, capability models, build/buy outputs). They test the pipeline logic, output parsing, validation rules, and state management without calling any LLM.

### Agent Quality Tests (requires API keys, slower)

```bash
make test-agents-quick    # Smoke test: one agent, one idea
make test-agents          # Full suite: all agents x 2 test ideas
make test-agents-verbose  # Full suite with judge reasoning output
```

These use the LLM-as-Judge pattern ([ADR-018](docs/adr/ADR-018-llm-as-judge-agent-testing.md)): a judge LLM evaluates agent output against quality criteria. Useful for validating prompt changes.

### Recording Fixtures from Real Runs

If you've run the pipeline and want to capture outputs for testing:

```bash
make record-fixtures IDEA_ID=T1
```

This saves real agent outputs to `tests/fixtures/upstream_outputs/` so other tests can replay them without API calls.

---

## Areas Where Help Is Wanted

| Area | Difficulty | What's needed |
|------|-----------|---------------|
| Agent prompts | Beginner | Review and improve agent prompts for clarity and output quality |
| Test coverage | Beginner | Add edge-case tests for validation logic, stage configs, or output parsing |
| Documentation | Beginner | Fix unclear explanations, add examples, improve getting-started flow |
| Export formats | Intermediate | Implement OpenSpec or Spec Kit exporters ([Roadmap Item 5](docs/roadmap.md#5-spec-driven-export-openspec--spec-kit)) |
| Stitch integration | Intermediate | Connect Google Stitch MCP endpoint ([Roadmap Item 4](docs/roadmap.md#4-google-stitch-integration)) |
| Dogfood stories | Mixed | Implement stories from Haytham's self-generated backlog |

---

## Code Quality

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting. Pre-commit hooks are available:

```bash
uv run pre-commit install
```

### Before Every Commit

```bash
uv run ruff check haytham/ --fix
uv run ruff format haytham/
uv run pytest tests/ -v -m "not integration" -x
```

Or combined: `uv run ruff check haytham/ --fix && uv run ruff format haytham/ && uv run pytest tests/ -v -m "not integration" -x`

---

## Code Conventions

Architecture patterns, code hygiene rules, and checklists for adding agents, stages, and workflow types are documented in [Architecture Patterns](docs/contributing/architecture-patterns.md). The same content is available in [CLAUDE.md](CLAUDE.md) (optimized for AI coding assistants).

Key conventions:
- **DRY**: Search for existing helpers before writing new ones
- **Config-driven extension**: Add new agents/stages via config dicts, not if/elif chains
- **Module-level imports**: No imports inside function bodies (unless breaking circular deps)
- **Specific exceptions**: Never bare `except Exception:`

---

## Submitting Changes

1. **Branch from `main`** with a descriptive name (e.g., `feat/add-export-stage`, `fix/pivot-strategy-gate`)
2. **Keep PRs focused** on one feature or fix
3. **Write tests** for new functionality
4. **Lint before pushing** (see "Before Every Commit" above)
5. **CI must pass** before merging

### Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add export stage for PDF reports
fix: correct pivot strategy gate condition
docs: update quickstart for Ollama provider
refactor: extract common validation logic
test: add tests for stage executor edge cases
```

---

## Adding a New Agent (End-to-End)

1. Create `haytham/agents/worker_{name}/worker_{name}_prompt.txt`
2. Add a config entry in `AGENT_CONFIGS` in `haytham/config.py` (including `structured_output_model_path` if the agent returns structured data)
3. The generic `create_agent_by_name()` handles creation automatically from the config
4. Add a `StageExecutionConfig` in `haytham/workflow/stages/configs.py` if this agent powers a new stage
5. Write a unit test in `tests/` using synthetic fixtures
6. Run `make test-agents-quick` to verify the agent produces quality output

Key files: `haytham/agents/factory/agent_factory.py`, `haytham/config.py`, `haytham/workflow/stages/configs.py`

---

## Reporting Bugs

Open a [GitHub Issue](https://github.com/arslan70/haytham/issues) with:

1. **Haytham version**: `git rev-parse --short HEAD`
2. **Python version**: `python --version`
3. **OS**: macOS / Linux / WSL
4. **LLM provider**: Bedrock / Anthropic / OpenAI / Ollama
5. **What did you do?** Exact steps or startup idea used
6. **What did you expect?**
7. **What actually happened?** Full error message or unexpected output
8. **Which stage did it fail at?** e.g., `market-context`, `validation-summary`, `story-generation`

For security vulnerabilities, see [SECURITY.md](SECURITY.md). Do not open a public issue.

---

## Getting Help

- [GitHub Issues](https://github.com/arslan70/haytham/issues) for bug reports and feature requests
- [GitHub Discussions](https://github.com/arslan70/haytham/discussions) for questions and general discussion
- [Troubleshooting Guide](docs/troubleshooting.md) for common issues and debugging tools
