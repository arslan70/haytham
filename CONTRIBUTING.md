# Contributing to Haytham

Thanks for your interest in contributing! This guide will help you get set up and start contributing.

## First-Time Contributors

New to the project? Welcome! Here's how to get started:

- **Documentation improvements** — fix typos, clarify explanations, add examples
- **Test contributions** — add test cases, improve coverage for existing agents or stages
- **Small bug fixes** — issues labeled `good-first-issue`

> See [CLAUDE.md](CLAUDE.md) for detailed architecture patterns. It's the primary reference for how the codebase is structured.

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

## Running Without AWS Credentials

You don't need an AWS account to develop on Haytham. Pick one of these options:

### Anthropic API

```bash
# In .env:
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

### Ollama (Free, Local)

```bash
# Install Ollama: https://ollama.com/download
ollama pull llama3.1:70b

# In .env:
LLM_PROVIDER=ollama
```

See [`.env.example`](.env.example) for all provider options.

## Running the App

```bash
make run
# Or: streamlit run frontend_streamlit/Haytham.py

# Open http://localhost:8501
```

## Running Tests

```bash
# Unit tests (recommended during development)
uv run pytest tests/ -v -m "not integration"

# All tests
uv run pytest tests/ -v

# Run a specific test
uv run pytest tests/ -k "test_stage_registry" -v
```

## Code Quality

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
# Check for lint issues
uv run ruff check haytham/

# Auto-fix lint issues
uv run ruff check haytham/ --fix

# Format code
uv run ruff format haytham/
```

Pre-commit hooks are available to run these checks automatically:

```bash
uv run pre-commit install
```

## Code Conventions

- See [CLAUDE.md](CLAUDE.md) for detailed architecture patterns and code hygiene rules.
- Use the Strands SDK for agent creation. Access structured output via `result.structured_output`, not `result.output`.
- New agents: add prompt file + config entry + factory function (see "Adding a New Agent" in CLAUDE.md).
- New stages: add metadata + execution config + Burr action + entry validator + UI entry (see "Adding a New Stage" in CLAUDE.md).

## Submitting Changes

1. **Branch from `main`** — use a descriptive branch name (e.g., `feat/add-export-stage`, `fix/pivot-strategy-gate`)
2. **Keep PRs focused** — one feature or fix per PR
3. **Write tests** — new functionality should have corresponding tests
4. **Lint before pushing** — `uv run ruff check haytham/ && uv run ruff format --check haytham/`
5. **CI must pass** — all checks must be green before merging

### Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add export stage for PDF reports
fix: correct pivot strategy gate condition
docs: update quickstart for Ollama provider
refactor: extract common validation logic
test: add tests for stage executor edge cases
```

## Reporting Bugs

Open a [GitHub Issue](https://github.com/arslan70/haytham/issues) with the following information:

### Required Information

1. **Haytham version** — `git rev-parse --short HEAD`
2. **Python version** — `python --version`
3. **OS** — macOS / Linux / WSL
4. **LLM provider** — Bedrock / Anthropic / OpenAI / Ollama

### What to Include

1. **What did you do?** — Exact steps or startup idea used
2. **What did you expect to happen?**
3. **What actually happened?** — Full error message or unexpected output
4. **Can you reproduce it?** — Every time, or intermittent?
5. **Which stage did it fail at?** — e.g., `market-context`, `validation-summary`, `story-generation`

For security vulnerabilities, see [SECURITY.md](SECURITY.md) — do not open a public issue.

---

## Troubleshooting

### `uv sync` fails with resolver errors

```bash
# Clear the cache and retry
uv cache clean && uv sync
```

### `ModuleNotFoundError: No module named 'haytham'`

Streamlit views must call `setup_paths()` before importing `haytham.*` modules:

```python
from lib.session_utils import setup_paths
setup_paths()  # Must be first — adds project root to sys.path

from haytham.workflow import ...  # Now safe
```

### Tests pass locally but fail in CI

Ensure you're skipping integration tests (they require live LLM credentials):

```bash
uv run pytest tests/ -v -m "not integration"
```

### `StreamlitAPIException` or session state errors

Clear the session and restart:

```bash
make reset
make run
```

### Ruff reports lint issues

The codebase should be lint-clean. If you see issues, run the full fix and format cycle:

```bash
uv run ruff check haytham/ --fix && uv run ruff format haytham/
```

---

## Getting Help

- [GitHub Issues](https://github.com/arslan70/haytham/issues) — bug reports and feature requests
- [GitHub Discussions](https://github.com/arslan70/haytham/discussions) — questions and general discussion
