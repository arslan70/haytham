# CLAUDE.md

## Constitution

Haytham transforms startup ideas into self-improving autonomous systems via three milestones:

1. **GENESIS** (COMPLETE): Idea → working MVP. Validated with Gym Leaderboard.
2. **EVOLUTION** (CURRENT FOCUS): Existing MVP + change request → updated, validated system. Add features, fix bugs, refactor with capability traceability.
3. **SENTIENCE** (VISION): Running MVP with telemetry → continuous autonomous improvement.

### Guiding Principles

1. **Stay Focused**: Only work on features that advance the current milestone
2. **Stay Lean**: Minimum viable implementation. No gold-plating. No premature optimization
3. **Challenge Distractions**: If it doesn't advance the roadmap, push back. Defer polish, config options, UI enhancements, and premature abstractions
4. **Close the Loop**: Partial solutions have no value. Complete the feedback loop
5. **Trace Everything**: Every story traces to a capability. Every capability traces to a user need

Before starting work, ask: Does this advance the current milestone? Is it the minimum viable implementation? Can it be deferred? If so, challenge the request. See [VISION.md](./VISION.md).

### Meta-System Design

**Haytham is a factory that produces applications.** It must handle ANY valid startup idea (web app, CLI tool, API service, marketplace), not just specific examples. This means:

- **Generic prompts**: Enforce principles (traceability, consistency), not prescriptions (use Supabase, limit to 5 items). If a rule wouldn't apply to a CLI AND a web app AND an API, it's too specific.
- **Test across input classes**: Web app, CLI tool, API service, marketplace. A fix that works for one but breaks another is not a fix.
- **Read signals, don't hardcode**: Determine context from input rather than prescribing counts, services, or tech choices.
- **Enforce consistency, not content**: "Every capability must trace to an IN SCOPE item" (good) vs "Output should have 5 capabilities" (bad).
- **Self-checking agents**: Validate output against input constraints. Include SELF-CHECK sections in prompts.

**Review test**: "Would this work for a CLI tool? An IoT system? A marketplace?" If no, find the generalization.

### System Integrity Traits

When evaluating or making changes, consider these traits critical to the system's integrity:

- **Missing logical stages**: Are there gaps in the workflow where a necessary analysis or transformation step is absent?
- **Stage handoff quality**: Is information passed cleanly between stages, or is context lost/mangled at boundaries?
- **Information schema fit**: Is the schema between stages too tight (blocking valid inputs) or too loose (allowing garbage through)?
- **Prompt quality**: Are agent prompts clear, well-scoped, and producing consistent results?
- **Agent role burden**: Is any single agent overloaded with too many responsibilities? Split when a prompt tries to do too much.
- **Agent tooling gaps**: Do agents have the tools they need to do their job, or are they forced to hallucinate what a tool should provide?

---

## Project Overview

Haytham is a stage-based multi-agent system that validates startup ideas and generates MVP specifications. Uses a Burr-powered workflow engine to orchestrate specialist agents through four phases.

## Commands

```bash
# Run
make run                                      # Streamlit UI
burr                                          # Burr tracking UI (optional)
make jaeger-up                                # Jaeger traces at localhost:16686

# Development
uv sync                                       # Install dependencies
ruff check haytham/ && ruff format haytham/
pytest tests/ -v                              # All tests
pytest tests/ -k "test_stage" -v              # Pattern match
pytest tests/ -m "not integration" -v         # Skip integration

# Stage iteration
make clear-from STAGE=market-context          # Re-run from stage
make stages-list                              # List all stages
make view-stage STAGE=idea-analysis           # View stage output
make reset                                    # Clear session

# Agent quality testing (ADR-018) - LLM-as-Judge evaluation
make test-agents                              # All pilots x 2 ideas
make test-agents-quick                        # Smoke test
make test-agents-verbose                      # With judge reasoning
make record-fixtures IDEA_ID=T1               # Record upstream fixtures

# Setup: configure .env with AWS creds + model IDs
```

## Before Every Commit (REQUIRED)

**CI will fail if you skip these steps:**

```bash
uv run ruff check haytham/ --fix   # Fix lint issues
uv run ruff format haytham/        # Format code
uv run pytest tests/ -v -m "not integration" -x  # Run unit tests (stop on first failure)
```

Or combined: `uv run ruff check haytham/ --fix && uv run ruff format haytham/ && uv run pytest tests/ -v -m "not integration" -x`

**Common failures from skipping this:**
- Ruff formatting differences → run `uv run ruff format haytham/`
- Unused imports or variables → run `uv run ruff check haytham/ --fix`
- Test regressions → run `uv run pytest tests/ -v -m "not integration"` and fix

## Before Every PR (REQUIRED)

Always run the `/audit` skill before creating a pull request. Do not proceed with PR creation until the audit passes.

---

## Architecture

### Four-Phase Workflow (ADR-016, simplified by ADR-026)

- **WHY** (Idea Validation): idea_analysis → market_context → report_synthesis → GATE 1
- **WHAT** (MVP Spec): mvp_scope → capability_model → GATE 2
- **HOW** (Technical Design): build_buy_analysis → architecture_decisions → GATE 3
- **STORIES** (Implementation): story_generation → story_validation → dependency_ordering

**Key transitions:**

```
market_context → report_synthesis (linear, no conditional branching)
recommendation(GO) + gate_approved → mvp_scope
recommendation(PIVOT) + gate_approved → idea_analysis (with pivot context)
recommendation(NO-GO) + gate_approved → END
```

### Key Components

- **Burr Workflow** (`haytham/workflow/burr_workflow.py`): State machine with linear transitions per workflow.
- **StageRegistry** (`haytham/workflow/stage_registry.py`): Single source of truth for stage metadata. O(1) lookups by slug or action name.
- **StageExecutor** (`haytham/workflow/stage_executor.py`): Template Method Pattern. Stage configs in `haytham/workflow/stages/configs.py`.
- **Agent Factory** (`haytham/agents/factory/agent_factory.py`): Creates agents with Strands SDK. Config-driven via `AGENT_CONFIGS` in `config.py`.
- **SessionManager** (`haytham/session/session_manager.py`): State, checkpoints, stage outputs. Saves to `session/{stage-slug}/`.

**Key files:**
- `haytham/workflow/burr_workflow.py` - Workflow definition and transitions
- `haytham/workflow/burr_actions.py` - Burr action wrappers that call the stage executor
- `haytham/workflow/stage_registry.py` - Stage metadata (slugs, phases, ordering), `WorkflowType` enum
- `haytham/workflow/stage_executor.py` - `StageExecutor` class
- `haytham/workflow/stages/configs.py` - `STAGE_CONFIGS` dict (assembled from domain modules)
- `haytham/workflow/entry_conditions.py` - Entry validators, `_VALIDATORS` dict
- `haytham/agents/factory/agent_factory.py` - Agent creation via `create_agent_by_name()`
- `haytham/session/session_manager.py` - Session state, checkpoints, stage outputs

### Adding a New Agent

1. Create `haytham/agents/worker_{name}/worker_{name}_prompt.txt`
2. Add config entry in `AGENT_CONFIGS` in `config.py` (including `structured_output_model_path` if needed)
3. The generic `create_agent_by_name()` handles creation automatically from the config

**Key files:** `haytham/agents/factory/agent_factory.py`, `haytham/agents/hooks.py`, `haytham/config.py`

### Adding a New Stage

1. `StageMetadata` in `stage_registry.py`
2. `StageExecutionConfig` in `haytham/workflow/stages/configs.py`
3. Burr action in `burr_actions.py` + transition in `burr_workflow.py`
4. Entry validator in `entry_conditions.py`. Register in `_VALIDATORS` dict and update `get_next_available_workflow()` order

**Key files:** `haytham/workflow/stage_registry.py`, `haytham/workflow/stages/configs.py`, `haytham/workflow/burr_actions.py`, `haytham/workflow/burr_workflow.py`, `haytham/workflow/entry_conditions.py`

### Adding a New Workflow Type

1. Add `WorkflowType` enum value in `stage_registry.py`
2. Add entry validator and register in `_VALIDATORS`
3. Add stages following the "Adding a New Stage" checklist above
4. Update `SessionManager` workflow aliases in ONE place (extract to constant if not yet done)

**Key files:** `haytham/workflow/stage_registry.py`, `haytham/workflow/entry_conditions.py`, `haytham/session/session_manager.py`

### Package Boundaries

- `haytham/workflow/` imports from `haytham/agents/`, not the reverse
- `haytham/session/` is imported by both `workflow/` and `agents/`. Keep it dependency-free
- `haytham/agents/output_utils.py` is the shared extraction layer. Individual `worker_*/` modules import from here, not from each other
- `haytham/workflow/architecture_diff.py` contains `ArchitectureDiff` and diff computation for Workflow 2


## Documentation Editing Standards
- Write in plain, human-friendly language. Avoid jargon and verbose AI-sounding prose.
- Never use em dashes. Use commas, periods, or parentheses instead.
- Prefer diagrams (mermaid) over long explanatory paragraphs when showing architecture or flows.
- When editing docs, keep it concise. If the user asks for simplification, go further than you think necessary.

## Code Hygiene Rules (Summary)

Full details with examples and rationale: [docs/contributing/architecture-patterns.md](docs/contributing/architecture-patterns.md)

- **DRY**: Search for existing helpers before writing new ones. Define constants once, import everywhere.
- **Single Responsibility**: Split by responsibility, not by size. Apply the four tests: debuggability, reusability, responsibility boundaries, testability.
- **Open/Closed**: Register new agents/stages/validators in config dicts, not if/elif chains.
- **Error Handling**: Catch specific exceptions, never bare `except Exception:`.
- **Deprecation**: Delete deprecated code. Don't leave it commented or marked `# Deprecated`.
- **Imports**: Module-level only. Compile regex at module level. No imports inside function bodies.
- **Interface Consistency**: Same-role methods must have identical signatures.
- **Logging**: Use `logging.getLogger("haytham")`. Never log user idea text, LLM prompts/responses, or API keys.

## Key Patterns

- **Strands SDK**: Agents use `strands.Agent` with prompts from `worker_*_prompt.txt`
- **AWS Bedrock**: LLM calls via `create_bedrock_model()` with configurable timeouts
- **Sequential Execution**: Phase 1 runs market_intelligence then competitor_analysis (JTBD handoff)
- **Structured Output**: `report_synthesis` uses `structured_output_model=ValidationReport`
- **Session Persistence**: Checkpoints saved as markdown in `session/{stage-slug}/`

**Key files:** `haytham/agents/factory/agent_factory.py`, `haytham/agents/output_utils.py`, `haytham/agents/hooks.py`, `haytham/config.py`

### Strands SDK Best Practices

**Agent creation:** Always use `create_agent_by_name()` from the factory. It ensures hooks, name, trace_attributes, and model tiering are applied consistently. Never create `Agent()` directly unless the agent has genuinely unique requirements (custom tools, conversation history) that the factory can't support.

**Structured output:** When `structured_output_model` is configured on an agent, `result.structured_output` is always a validated Pydantic model on success. Don't add defensive `isinstance`/`hasattr` fallback chains. Use `extract_text_from_result()` from `output_utils.py` for all extraction.

**Tools:** Tools decorated with `@tool` must never raise exceptions. Return error strings/dicts so the model can reason about failures. Use typed parameters and comprehensive docstrings (the model reads both for tool calling).

**Hooks:** Every agent on an active execution path must have `hooks=[HaythamAgentHooks()]`. This provides timing, cache metrics, and OTEL span annotation. The factory injects this automatically.

**Agent naming:** Always pass `name=` when creating `Agent()` directly. Without it, OTEL spans and logs show "unknown". The factory handles this via `AgentConfig.name`.

**Model tiering:** Use `ModelTier.HEAVY` for synthesis/structured output, `LIGHT` for extraction/summarization, `REASONING` for cross-referencing. Don't call `create_model()` with no arguments (defaults to LIGHT tier without config routing).

### DSPy for Prompt Testing and Pipeline Validation

Use [DSPy](https://dspy.ai/) (`dspy` optional dependency, install with `uv sync --extra dspy-poc`) to empirically test prompt and pipeline changes before committing to them.

**When to use DSPy:**
- Before adding a new agent or splitting an existing one: test whether a single agent with full context produces better output
- Before major prompt rewrites: compare old vs new output across test ideas
- When debating architectural approaches: generate outputs from both and compare with the quality checklist
- When optimizing prompts systematically: use MIPROv2 or GEPA optimizers to find better instructions

**How to use it:**
1. Define a `dspy.Signature` with typed input/output fields. The class docstring becomes the system prompt.
2. Load upstream fixtures from `tests/dspy_poc/fixtures/{idea_id}/`
3. Run with `dspy.Predict(YourSignature)` and compare output against baselines
4. Use `uv run --extra dspy-poc python -m tests.dspy_poc.synthesize T1` for the existing report synthesis PoC

**Key constraint:** DSPy uses LiteLLM for Bedrock. Bedrock's Converse API does not support DSPy's `instructions` parameter. Put all instructions in the Signature docstring instead.

**Key files:** `tests/dspy_poc/signatures.py`, `tests/dspy_poc/synthesize.py`, `tests/fixtures/test_ideas.json`

### CRITICAL: Strands SDK Structured Output

Use `result.structured_output`, NOT `result.output`. Reference: `haytham/agents/output_utils.py:extract_text_from_result()`

### PITFALL: Agent Registration

Declare in `AGENT_CONFIGS`, not in if/elif inside `create_agent_by_name()`. Key file: `haytham/agents/factory/agent_factory.py`

### PITFALL: Entry Validator Registration

Register in `_VALIDATORS` dict, not elif in `get_next_available_workflow()`. Key file: `haytham/workflow/entry_conditions.py`

### PITFALL: Agents Re-deriving Known Values

Pass known values (e.g., `recommendation`) explicitly as structured inputs. Never embed them in prose for re-extraction. Treat agent inputs like function arguments. Key file: `haytham/workflow/stages/idea_validation.py`

### PITFALL: Imports Inside Function Bodies

Module-level imports and compiled patterns only. Exception: circular dependency avoidance (document reason in comment).

### PITFALL: LLM Text Overriding Deterministic Rules

Never let LLM-generated text override deterministic safety rules. If the system needs a property enforced, make the rule unconditional. String-based quality gates (length checks, phrase blocklists) cannot reliably verify substance and will be bypassed. The LLM's job is qualitative judgment (scoring, evaluating evidence). The system's job is deterministic rules from those judgments. Keep this boundary sharp.

### PITFALL: Splitting LLM Reasoning Across Multiple Agents

Do not split a task that requires holistic reasoning across multiple agents connected by deterministic glue. When an LLM needs to cross-reference findings (e.g., risk findings should inform next steps, market gaps should inform pivot rationale), it does this naturally when it has full context in a single call. Splitting the same reasoning across a scorer agent, narrator agent, merge function, and post-validators fragments the context, creates information loss at boundaries, and requires validators to patch inconsistencies that wouldn't exist if one agent had the full picture.

**The test**: If you're adding a validator to catch inconsistencies between two agents' outputs, ask whether a single agent with both agents' context would produce the inconsistency in the first place. If not, you have an architecture problem, not a validation problem.

**Evidence**: A single LLM call with upstream context scored 8 PASS / 4 PARTIAL / 0 FAIL on report quality criteria, versus 1 PASS / 3 PARTIAL / 8 FAIL from a 4-agent + 6-validator pipeline processing the same inputs. See [ADR-026](docs/adr/ADR-026-simplified-validation-pipeline.md).

**When multi-agent IS justified**: When agents need different tools (e.g., web search vs. analysis), different model tiers, or operate on genuinely independent tasks. Gathering information (web research, competitor analysis) is a valid reason to split. Synthesizing information is not.

### PITFALL: Bypassing the Agent Factory

Do not create `Agent()` directly in stage modules or worker files. Direct instantiation skips hooks (no observability), name assignment (broken OTEL), trace_attributes (no distributed tracing), and model tier routing (wrong model). Use `create_agent_by_name()` for all standard agents. If an agent needs custom tools or conversation history, still add `hooks=[HaythamAgentHooks()]` and `name=`.

### Report Synthesis Pipeline (ADR-026)

The old validation-summary pipeline (4 agents + 6 validators) was replaced with a single `report_synthesis` agent per [ADR-026](docs/adr/ADR-026-simplified-validation-pipeline.md). Two lightweight post-validators remain: `validate_som_arithmetic` and `validate_regulated_domain_safety`.

**Key files**: `haytham/workflow/stages/idea_validation.py`, `haytham/agents/worker_report_synthesis/`, `haytham/workflow/validators/report_guardrails.py`

## Environment Variables

Required: `AWS_REGION` or `AWS_PROFILE`, `BEDROCK_REASONING_MODEL_ID`, `BEDROCK_HEAVY_MODEL_ID`, `BEDROCK_LIGHT_MODEL_ID`

Optional: `LOG_LEVEL`, `OTEL_SDK_DISABLED` (default: true), `OTEL_EXPORTER_OTLP_ENDPOINT` (default: localhost:4317), `DEFAULT_MAX_TOKENS` (default: 5000), `WEB_SEARCH_SESSION_LIMIT` (default: 30), `BRAVE_API_KEY` or `TAVILY_API_KEY`

## Backlog.md MCP (For Generated Systems Only)

**IMPORTANT:** The Backlog.md MCP tools are NOT for tracking Haytham development tasks. They are part of the system that Haytham generates, used by generated applications to manage their own task backlogs.

- **DO NOT** use `mcp__backlog__*` tools to track ADR implementations, bug fixes, or feature work on Haytham itself
- **DO** use these tools when working on the story generation or project management features that Haytham outputs for generated applications

For tracking Haytham development work, use the built-in Claude Code task tools (TaskCreate, TaskUpdate, TaskList) or work directly without formal task tracking.
