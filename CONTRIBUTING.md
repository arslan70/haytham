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

You don't need an AWS account to develop on Haytham. See [Getting Started](docs/getting-started.md#provider-setup) for Anthropic, OpenAI, and Ollama setup instructions.

## Running the App

```bash
make run
# Open http://localhost:8501
```

## Code Quality

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting. Pre-commit hooks are available:

```bash
uv run pre-commit install
```

See [CLAUDE.md](CLAUDE.md#before-every-commit-required) for the full lint/test/format workflow required before every commit.

## Code Conventions

See [CLAUDE.md](CLAUDE.md) for architecture patterns, code hygiene rules, and checklists for adding agents/stages.

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

See the [Troubleshooting Guide](docs/troubleshooting.md) for common issues and debugging tools.

---

## Getting Help

- [GitHub Issues](https://github.com/arslan70/haytham/issues) — bug reports and feature requests
- [GitHub Discussions](https://github.com/arslan70/haytham/discussions) — questions and general discussion
