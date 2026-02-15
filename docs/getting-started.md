# Getting Started

## Prerequisites

- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** — Python package manager
- **An LLM provider** — Anthropic API key, AWS credentials, OpenAI API key, or Ollama installed locally

## Installation

```bash
git clone https://github.com/arslan70/haytham.git
cd haytham
```

Install dependencies for your chosen provider:

```bash
# Anthropic (recommended)
uv sync --extra anthropic

# OpenAI
uv sync --extra openai

# Ollama (free, local)
uv sync --extra ollama

# AWS Bedrock
uv sync

# All providers
uv sync --extra providers
```

## Provider Setup

Copy the environment template and configure your provider:

```bash
cp .env.example .env
```

### Anthropic (Recommended)

Best balance of quality and ease of setup.

```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Model configuration (defaults shown):
ANTHROPIC_REASONING_MODEL_ID=claude-sonnet-4-20250514
ANTHROPIC_HEAVY_MODEL_ID=claude-sonnet-4-20250514
ANTHROPIC_LIGHT_MODEL_ID=claude-3-5-haiku-20241022
```

### Ollama (Free, Local)

No API key needed. Runs entirely on your machine.

```bash
# Install Ollama: https://ollama.com/download
ollama pull llama3.1:70b
```

```bash
LLM_PROVIDER=ollama

# Model configuration (defaults shown):
OLLAMA_REASONING_MODEL_ID=llama3.1:70b
OLLAMA_HEAVY_MODEL_ID=llama3.1:70b
OLLAMA_LIGHT_MODEL_ID=llama3.1:8b
```

Note: Quality depends heavily on model size. The 70b parameter model is recommended for meaningful results but requires significant hardware (40+ GB GPU memory). If you don't have a high-end GPU, try the `8b` model — results will be less consistent, but it runs on most machines. Smaller models may produce incomplete or inconsistent outputs.

### OpenAI

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...

# Model configuration (defaults shown):
OPENAI_REASONING_MODEL_ID=gpt-4o
OPENAI_HEAVY_MODEL_ID=gpt-4o
OPENAI_LIGHT_MODEL_ID=gpt-4o-mini
```

### AWS Bedrock

Requires AWS credentials configured via environment variables or AWS CLI profile.

```bash
LLM_PROVIDER=bedrock
AWS_REGION=us-east-1

# Model configuration (defaults shown):
BEDROCK_REASONING_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0
BEDROCK_HEAVY_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0
BEDROCK_LIGHT_MODEL_ID=us.anthropic.claude-3-5-haiku-20241022-v1:0
```

## Three-Tier Model Configuration

Haytham uses three model tiers to balance cost and quality:

| Tier | Purpose | Used For |
|------|---------|----------|
| **REASONING** | Complex analysis requiring deep reasoning | Validation scoring, risk assessment |
| **HEAVY** | Substantial generation tasks | Market analysis, architecture decisions, story generation |
| **LIGHT** | Fast, simple tasks | Idea polishing, formatting, classification |

You can assign different models to each tier. For example, use a more capable model for REASONING and a cheaper model for LIGHT tasks.

## Running Haytham

```bash
make run
# Or: streamlit run frontend_streamlit/Haytham.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

## Your First Run

1. **Enter an idea** — describe a startup idea in plain language. Be specific about the problem, target users, and what makes it different. The more detail you provide, the better the analysis.

2. **Discovery** — Haytham checks whether your idea is clear enough to analyze. If gaps exist (missing problem statement, unclear target user, vague value proposition), it asks targeted questions. If the idea is clear, this step is automatic.

3. **Phase 1: Should this be built?** — Specialist agents analyze the market, competitors, and risks. You receive a GO / NO-GO / PIVOT verdict with evidence. Review the findings and approve to proceed.

4. **Phase 2: What exactly should we build?** — Agents define MVP scope and extract capabilities. Review the scope boundaries and capability model, then approve.

5. **Phase 3: How should we build it?** — Build-vs-buy analysis per capability and architecture decisions. Review the technical choices and approve.

6. **Phase 4: What are the tasks?** — Ordered user stories with acceptance criteria and full traceability. These are ready to hand to a developer or coding agent.

Each phase takes a few minutes. The full pipeline completes in approximately 20 minutes.

**Cost note:** A full 4-phase run sends requests to 21 agents with web search. With commercial API providers (Anthropic, OpenAI), expect roughly $5–$20 in API credits per run depending on model choices and idea complexity. Use Ollama for free local inference, or assign cheaper models to the LIGHT tier to reduce costs.

## Optional: Observability

Haytham includes [OpenTelemetry](https://opentelemetry.io/) tracing for debugging. **Disabled by default** — no data is collected unless you opt in.

```bash
# Start Jaeger (requires Docker)
make jaeger-up

# In .env:
OTEL_SDK_DISABLED=false

# View traces at http://localhost:16686
```

## Optional: Burr Tracking UI

[Burr](https://github.com/dagworks-inc/burr) provides a tracking UI to visualize workflow state and transitions:

```bash
burr
# Open http://localhost:7241
```

## Platform Support

| Platform | Status |
|----------|--------|
| macOS | Tested |
| Linux | Expected to work |
| Windows | Untested |

## Troubleshooting

**"Module not found" errors** — Make sure you ran `uv sync` with the correct `--extra` flag for your provider.

**Ollama connection refused** — Ensure Ollama is running (`ollama serve`) and the model is pulled (`ollama list`).

**AWS credential errors** — Verify your AWS credentials are configured (`aws sts get-caller-identity`). Check that your IAM role has Bedrock model access in the configured region.

**Incomplete or low-quality outputs** — Try a more capable model. The REASONING tier has the most impact on output quality.

For logs, tracing, and more debugging tools, see the full **[Troubleshooting Guide](troubleshooting.md)**.
