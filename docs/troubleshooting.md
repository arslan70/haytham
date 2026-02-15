# Troubleshooting

## Common Issues

**"Module not found" errors** — Make sure you ran `uv sync` with the correct `--extra` flag for your provider. See [Getting Started](getting-started.md#installation).

**Ollama connection refused** — Ensure Ollama is running (`ollama serve`) and the model is pulled (`ollama list`).

**AWS credential errors** — Verify your AWS credentials are configured (`aws sts get-caller-identity`). Check that your IAM role has Bedrock model access in the configured region.

**Incomplete or low-quality outputs** — Try a more capable model. The REASONING tier has the most impact on output quality. See [Three-Tier Model Configuration](getting-started.md#three-tier-model-configuration).

**Stage seems stuck** — Some stages (especially validation scoring) involve long LLM reasoning chains. Check the console logs for activity. If truly stuck, increase `DEFAULT_MAX_TOKENS` in `.env`.

**Token limit errors** — If a stage fails with a Bedrock throttling or token limit error, either increase `DEFAULT_MAX_TOKENS` or switch to a model with a larger context window.

## Logs

Haytham logs to the console (stdout) by default. No file logging is configured out of the box.

### Log Level

Set `LOG_LEVEL` in `.env` to control verbosity:

```bash
LOG_LEVEL=DEBUG    # Everything — LLM calls, tool invocations, state transitions
LOG_LEVEL=INFO     # Default — stage starts/completions, key decisions
LOG_LEVEL=WARNING  # Problems only
LOG_LEVEL=ERROR    # Failures only
```

### Log Format

```
2026-02-13 14:30:01 | INFO     | haytham.workflow.stage_executor | Running stage: idea-analysis
```

Fields: `timestamp | level | logger name | message`

### Saving Logs to a File

Redirect output when starting the app:

```bash
make run 2>&1 | tee haytham.log
```

### Noisy Third-Party Logs

At `INFO` and above, `urllib3`, `botocore`, and `boto3` are automatically suppressed to `WARNING`. Set `LOG_LEVEL=DEBUG` to see them.

## Tracing with Jaeger

Haytham includes OpenTelemetry tracing for visualizing the full execution pipeline — workflow, stages, agents, LLM calls, and tool invocations. **Disabled by default.**

### Quick Start

1. Start Jaeger (requires Docker):

   ```bash
   make jaeger-up
   ```

2. Enable tracing in `.env`:

   ```bash
   OTEL_SDK_DISABLED=false
   ```

3. Run a workflow:

   ```bash
   make run
   ```

4. Open the Jaeger UI:

   ```bash
   make jaeger-ui
   # Or visit http://localhost:16686
   ```

5. Search for service **`haytham-ai`** to see traces.

### What You See in Jaeger

Traces have a nested span hierarchy:

```
workflow (root)
└── stage: idea-analysis
    └── agent: idea_analysis_agent
        ├── llm call (prompt + completion)
        └── tool: http_request
└── stage: market-context
    ├── agent: market_intelligence_agent
    │   └── llm call
    └── agent: competitor_analysis_agent
        └── llm call
```

Each span includes:
- **Duration** — how long the operation took
- **Attributes** — stage slug, agent name, model ID, token counts
- **Errors** — flagged with `error=true`, including whether it was a token limit error

### Tracing Configuration

All configuration is via environment variables in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `OTEL_SDK_DISABLED` | `true` | Master switch — set to `false` to enable |
| `OTEL_TRACES_EXPORTER` | `otlp` | Exporter: `otlp`, `console`, or `none` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | OTLP collector endpoint |
| `OTEL_SERVICE_NAME` | `haytham-ai` | Service name in traces |
| `OTEL_TRACES_SAMPLER` | `always_on` | Sampling strategy (`always_on` or `traceidratio`) |
| `OTEL_TRACES_SAMPLER_ARG` | `1.0` | Sample rate when using `traceidratio` (0.0–1.0) |

### Console Tracing (No Docker)

If you don't have Docker, you can print traces to the console instead of Jaeger:

```bash
OTEL_SDK_DISABLED=false
OTEL_TRACES_EXPORTER=console
```

This prints span data to stdout alongside regular logs.

### Stopping Jaeger

```bash
make jaeger-down
```

## Burr Tracking UI

[Burr](https://github.com/dagworks-inc/burr) provides a visual UI for workflow state machine execution — which stages ran, what state was passed between them, and where branching occurred.

```bash
burr
# Open http://localhost:7241
```

This is independent of OpenTelemetry. Burr tracking is always active when running workflows and shows:
- State machine transitions
- Stage inputs and outputs
- Conditional branches (e.g., pivot strategy triggered by HIGH risk)

## Langfuse (LLM Monitoring)

[Langfuse](https://langfuse.com/) provides LLM-specific observability: token usage, cost tracking, and user feedback scoring. This is an optional cloud integration.

### Setup

```bash
ENABLE_LANGFUSE=true
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com   # or self-hosted URL
```

### What Langfuse Tracks

- **Token usage** per LLM call (input/output tokens)
- **Cost** per call and per workflow (based on model pricing)
- **Trace hierarchy** mirroring the OpenTelemetry structure
- **User feedback** scores and comments from the Streamlit UI
- **Errors** with agent and phase context

Langfuse can run alongside Jaeger — they serve different purposes (infrastructure tracing vs. LLM analytics).

## Structured Output Errors

Agents that use Pydantic structured output can fail if the LLM returns malformed JSON or missing fields.

**"ValidationError: N validation errors for ModelName"** — The LLM returned JSON that doesn't match the Pydantic model. Common causes:
- Model too small (LIGHT tier used where HEAVY is needed) — check `AGENT_CONFIGS` in `haytham/config.py`
- Prompt doesn't clearly specify the expected schema — check the agent's prompt file
- Token limit hit mid-response — increase `DEFAULT_MAX_TOKENS`

**"structured_output is None"** — The agent completed but didn't produce structured output. Check that:
1. The agent's config has `structured_output_model` set in `AGENT_CONFIGS`
2. The extraction code uses `result.structured_output`, not `result.output` (Strands SDK convention)
3. The model supports structured output (some Ollama models may not)

**Debugging structured output:** Set `LOG_LEVEL=DEBUG` to see the raw LLM response before Pydantic parsing.

## Web Search Failures

**"Search rate limit reached"** — The session-wide search limit (`WEB_SEARCH_SESSION_LIMIT`, default 20) has been exceeded. This is a cost protection measure. To increase it, set `WEB_SEARCH_SESSION_LIMIT=50` in `.env`.

**"No search results"** — The DuckDuckGo provider may be rate-limited. Add a Brave or Tavily API key for more reliable results:

```bash
BRAVE_API_KEY=BSA...    # Brave Search
TAVILY_API_KEY=tvly-... # Tavily
```

Providers are tried in order: DuckDuckGo → Brave → Tavily. If one fails, the next is tried automatically.

## Debugging Specific Problems

### "Which stage is slow?"

Enable Jaeger tracing, run a workflow, then sort spans by duration. Stage spans are named `stage:{slug}` (e.g., `stage:idea-analysis`). Agent spans within a stage show individual agent timing.

### "Why did validation return NO-GO?"

Check the `session/validation-summary/` directory for the scorer output. The scorer JSON includes dimension scores, knockouts, counter-signals, and the verdict chain. See [Scoring Pipeline](architecture/scoring-pipeline.md) for the full logic.

### "An agent is producing bad output"

1. Set `LOG_LEVEL=DEBUG` to see the full prompt and response
2. Check the agent's prompt file: `haytham/agents/worker_{name}/worker_{name}_prompt.txt`
3. Use the agent quality tests: `make test-agents-verbose` to run LLM-as-Judge evaluation with reasoning

### "I want to re-run from a specific stage"

```bash
make clear-from STAGE=market-context   # Clears this stage and everything after it
make run                                # Re-runs from that point
```

### "I want to inspect stage outputs"

```bash
make view-stage STAGE=idea-analysis    # View a specific stage's output
make stages-list                        # List all stages and their status
```
