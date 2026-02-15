# Technology Stack

Haytham is built on emerging open-source technologies chosen for their fit with multi-agent workflow orchestration. This page explains what each technology does, why it was chosen, and where to find its documentation.

## Stack at a Glance

```
┌─────────────────────────────────────────────────────────┐
│                  Streamlit (UI)                          │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│               Burr (Workflow Engine)                     │
│         State machine · Branching · Checkpoints         │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│            Strands Agents SDK (Agent Runtime)            │
│     Agents · Tools · Hooks · Swarms · Structured Output │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│              LLM Providers (Model Layer)                 │
│   AWS Bedrock · Anthropic · OpenAI · Ollama (local)     │
└─────────────────────────────────────────────────────────┘

Cross-cutting:
  Pydantic (data models) · OpenTelemetry (tracing) · Langfuse (LLM analytics)
```

---

## Core Technologies

### Strands Agents SDK

| | |
|---|---|
| **What** | Python framework for building AI agents with tools, structured output, and observability |
| **Docs** | [github.com/strands-agents/sdk-python](https://github.com/strands-agents/sdk-python) |
| **Version** | `>=1.25.0` (with `[otel]` extra for tracing) |

**Why Strands?** Strands provides a minimal, composable agent abstraction that stays out of the way. Unlike heavier frameworks, it doesn't impose opinionated chains or retrieval patterns. Agents are just prompt + tools + model, with first-class support for structured output via Pydantic models and built-in OpenTelemetry instrumentation.

**How Haytham uses it:**

- **Agent creation** — All agents are created through a centralized factory (`haytham/agents/factory/agent_factory.py`). Each agent is configured with a prompt file, model tier, tool profile, and optional structured output model.
- **Structured output** — Agents that need typed responses (validation scores, competitor analysis, story skeletons) declare a Pydantic model. Results are accessed via `result.structured_output` — **not** `result.output`.
- **Tools** — Custom tools decorated with `@tool` provide web search, recommendation scoring, build/buy evaluation, PDF generation, and more. Tool sets are grouped into profiles (e.g., `WEB_RESEARCH`, `RECOMMENDATION`).
- **Hooks** — `HaythamAgentHooks` intercepts agent lifecycle events (before/after invocation, tool calls) to record timing, cache metrics, and OpenTelemetry attributes.
- **Swarms** — Multi-agent handoff orchestration for MVP scope (3-agent swarm) and story generation. Agents pass context through shared working memory.
- **Trace attributes** — Every agent is created with `trace_attributes` (agent name, session ID, stage slug) that propagate to all child spans.

**Key files:** `haytham/agents/factory/agent_factory.py`, `haytham/agents/hooks.py`, `haytham/config.py`

### Burr

| | |
|---|---|
| **What** | Lightweight state machine framework for building applications as a series of actions with explicit state |
| **Docs** | [github.com/dagworks-inc/burr](https://github.com/dagworks-inc/burr) |
| **Version** | `>=0.40.2` (with `[start]` extra for tracking UI) |

**Why Burr?** Haytham needs conditional branching (e.g., pivot strategy only runs when risk is HIGH), checkpoint persistence (resume from any stage), and a tracking UI for debugging. Burr provides all three with minimal boilerplate. Unlike Airflow or Dagster, it's designed for application-level state machines rather than data pipeline DAGs.

**How Haytham uses it:**

- **Workflow definition** — The four-phase pipeline is defined as Burr actions with explicit transitions. Each stage reads from and writes to shared state.
- **Conditional branching** — `when(risk_level="HIGH")` routes to the pivot strategy stage. `default` transitions handle the normal path.
- **Lifecycle hooks** — `StageProgressHook` implements `PreRunStepHook` and `PostRunStepHook` to report stage progress to the Streamlit UI.
- **Tracking UI** — `LocalTrackingClient` records every state transition. Run `burr` to visualize at `http://localhost:7241`.
- **Checkpoint persistence** — State is saved after each action, enabling resume from any point.

**Key files:** `haytham/workflow/burr_workflow.py`, `haytham/workflow/burr_actions.py`

### Pydantic

| | |
|---|---|
| **What** | Data validation and serialization library using Python type annotations |
| **Docs** | [docs.pydantic.dev](https://docs.pydantic.dev/) |
| **Version** | `>=2.0.0` |

**Why Pydantic?** Structured output from LLMs needs validation — the model might return malformed JSON, missing fields, or wrong types. Pydantic models define the expected schema, validate it at parse time, and provide serialization to JSON and markdown. Strands SDK has native Pydantic integration for structured output.

**How Haytham uses it:**

- **Structured output models** — 53+ Pydantic models define agent output schemas. Examples: `ValidationOutput`, `CompetitorAnalysis`, `StorySkeletonOutput`, `BuildBuyDecision`, `SystemTraitsOutput`.
- **Field documentation** — Every field uses `Field(description="...")` which serves as both validation metadata and self-documentation.
- **Serialization** — Models implement `to_markdown()` for human-readable output and `model_dump_json()` for state persistence.
- **Agent factory wiring** — Models are declared in `AGENT_CONFIGS` as `structured_output_model` or `structured_output_model_path` (lazy import to avoid circular dependencies).

**Key files:** Model definitions in `haytham/agents/worker_*/` directories, extraction logic in `haytham/agents/output_utils.py`

### Streamlit

| | |
|---|---|
| **What** | Python framework for building interactive web applications |
| **Docs** | [docs.streamlit.io](https://docs.streamlit.io/) |
| **Version** | `>=1.52.2` |

**Why Streamlit?** Haytham's UI needs are interactive but not complex — forms for idea input, progress indicators for stages, expandable sections for outputs, and approval gates between phases. Streamlit provides all of this with pure Python, no frontend build step required.

**How Haytham uses it:**

- **Multi-page app** — Main dashboard (`Haytham.py`) with separate pages for each workflow phase.
- **Session state** — `st.session_state` tracks workflow progress, user approvals, and feedback across reruns.
- **Custom components** — Reusable UI blocks for feedback chat, decision gates, progress bars, and locked-workflow modals.
- **Workflow bridge** — `WorkflowRunner` wraps the async Burr engine for synchronous Streamlit execution with progress callbacks.

**Key files:** `streamlit_prototype/Haytham.py`, `streamlit_prototype/lib/session_utils.py`, `streamlit_prototype/lib/workflow_runner.py`

---

## LLM Providers

Haytham uses a provider abstraction with three model tiers (REASONING, HEAVY, LIGHT). Any provider can be used — switch by setting `LLM_PROVIDER` in `.env`.

| Provider | Package | How Models Are Created |
|---|---|---|
| **AWS Bedrock** | `boto3` + `strands.models.bedrock` | `BedrockModel` with custom timeout config (300s read, 60s connect) |
| **Anthropic** | `anthropic` (optional extra) | Direct API via Strands Anthropic model adapter |
| **OpenAI** | `openai` (optional extra) | Direct API via Strands OpenAI model adapter |
| **Ollama** | `ollama` (optional extra) | Local inference via Strands Ollama model adapter |

The provider factory lives in `haytham/agents/utils/model_provider.py`. It resolves the active provider and maps each tier to a model ID from environment variables or sensible defaults.

**Bedrock AgentCore** (`bedrock-agentcore>=1.0.0`) provides the runtime integration layer for AWS Bedrock agent features.

See [Getting Started](getting-started.md#provider-setup) for configuration.

---

## Observability

### OpenTelemetry

| | |
|---|---|
| **What** | Vendor-neutral standard for distributed tracing, metrics, and logs |
| **Docs** | [opentelemetry.io](https://opentelemetry.io/) |
| **Version** | Bundled via `strands-agents[otel]` |

**Why OpenTelemetry?** It's the industry standard for observability. Strands SDK auto-instruments agent/LLM/tool spans. Haytham adds workflow and stage spans on top, giving a complete picture from UI click to LLM response.

**How Haytham uses it:**

- **Manual instrumentation** — `workflow_span()` and `stage_span()` context managers create parent spans. Agent-level spans are auto-created by Strands.
- **Agent hooks** — Annotate spans with timing, stop reason, and Bedrock cache metrics.
- **Exporters** — OTLP (Jaeger), console, or none. Disabled by default (`OTEL_SDK_DISABLED=true`).
- **Graceful degradation** — If OTel is unavailable, a `_NoOpTracer` ensures no errors.

**Key files:** `haytham/telemetry/config.py`, `haytham/telemetry/spans.py`

### Langfuse

| | |
|---|---|
| **What** | LLM observability platform — token usage, cost tracking, user feedback |
| **Docs** | [langfuse.com/docs](https://langfuse.com/docs) |
| **Version** | `>=2.0.0` (optional extra) |

Langfuse is complementary to OpenTelemetry. While Jaeger shows infrastructure timing, Langfuse focuses on LLM-specific analytics: which models cost the most, how many tokens each agent consumes, and how users rate the outputs.

**Key file:** `haytham/agents/utils/langfuse_tracer.py`

### Jaeger

| | |
|---|---|
| **What** | Open-source distributed tracing backend with a web UI for trace visualization |
| **Docs** | [jaegertracing.io](https://www.jaegertracing.io/) |
| **Version** | Docker image `jaegertracing/all-in-one:1.54` |

Haytham ships a `docker-compose.yml` with a pre-configured Jaeger instance. See [Troubleshooting — Tracing with Jaeger](troubleshooting.md#tracing-with-jaeger) for setup.

---

## Supporting Technologies

### Web Search Providers

Agents that need real-time information (market intelligence, competitor analysis) use a multi-provider fallback chain:

1. **DuckDuckGo** (`ddgs>=6.1.0`) — Free, no API key, used by default
2. **Brave Search** — Requires `BRAVE_API_KEY`, higher quality results
3. **Tavily** — Requires `TAVILY_API_KEY`, alternative provider

If one provider fails or is rate-limited, the next is tried automatically. A session-wide rate limit (`WEB_SEARCH_SESSION_LIMIT`, default 20) prevents runaway costs.

**Key file:** `haytham/agents/utils/web_search.py`

### ReportLab (PDF Generation)

| | |
|---|---|
| **What** | Python library for generating PDF documents |
| **Docs** | [docs.reportlab.com](https://docs.reportlab.com/) |
| **Version** | `>=4.0.0` (optional extra) |

Used for generating styled PDF reports from workflow outputs. Reports are configured via a data-driven `ReportConfig` with typed section definitions (markdown, tables, scorecards, metrics).

**Key file:** `haytham/agents/tools/pdf_report.py`

### LanceDB (Vector Storage)

| | |
|---|---|
| **What** | Embedded vector database for semantic search |
| **Docs** | [lancedb.github.io/lancedb](https://lancedb.github.io/lancedb/) |
| **Version** | `>=0.26.1` (optional extra) |

Stores capabilities (CAP-\*), decisions (DEC-\*), and entities (ENT-\*) with vector embeddings for semantic retrieval. Agents query LanceDB to find relevant context from earlier stages.

---

## Version Pinning

Several of these technologies are rapidly evolving. The `pyproject.toml` pins minimum versions that are tested:

| Package | Minimum | Notes |
|---|---|---|
| `strands-agents` | `1.25.0` | Breaking changes between minor versions are possible |
| `burr` | `0.40.2` | Pre-1.0; API may change |
| `bedrock-agentcore` | `1.0.0` | Recently released |
| `pydantic` | `2.0.0` | Stable; v2 required (not v1) |
| `streamlit` | `1.52.2` | Stable |

When upgrading, test with `pytest tests/ -v -m "not integration"` before committing.
