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

# Setup — configure .env with AWS creds + model IDs
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

### Four-Phase Workflow (ADR-016)

- **WHY** (Idea Validation): idea_analysis → market_context → risk_assessment → [pivot_strategy] → validation_summary → GATE 1
- **WHAT** (MVP Spec): mvp_scope → capability_model → GATE 2
- **HOW** (Technical Design): build_buy_analysis → architecture_decisions → GATE 3
- **STORIES** (Implementation): story_generation → story_validation → dependency_ordering

**Key transitions:**

```
risk_level(HIGH) → pivot_strategy → validation_summary
risk_level(MEDIUM|LOW) → validation_summary
validation_complete(GO) + gate_approved → mvp_scope
validation_complete(PIVOT) + gate_approved → idea_analysis (with pivot context)
validation_complete(NO-GO) + gate_approved → END
```

### Key Components

- **Burr Workflow** (`haytham/workflow/burr_workflow.py`): State machine with conditional branching. `when(risk_level="HIGH")` for pivot strategy.
- **StageRegistry** (`haytham/workflow/stage_registry.py`): Single source of truth for stage metadata. O(1) lookups by slug or action name.
- **StageExecutor** (`haytham/workflow/stage_executor.py`): Template Method Pattern. Stage configs in `haytham/workflow/stages/configs.py`.
- **Agent Factory** (`haytham/agents/factory/agent_factory.py`): Creates agents with Strands SDK. Config-driven via `AGENT_CONFIGS` in `config.py`.
- **SessionManager** (`haytham/session/session_manager.py`): State, checkpoints, stage outputs. Saves to `session/{stage-slug}/`.

**Key files:**
- `haytham/workflow/burr_workflow.py` — Workflow definition, transitions, conditional branching
- `haytham/workflow/burr_actions.py` — Burr action wrappers that call the stage executor
- `haytham/workflow/stage_registry.py` — Stage metadata (slugs, phases, ordering), `WorkflowType` enum
- `haytham/workflow/stage_executor.py` — `StageExecutor` class
- `haytham/workflow/stages/configs.py` — `STAGE_CONFIGS` dict (assembled from domain modules)
- `haytham/workflow/entry_conditions.py` — Entry validators, `_VALIDATORS` dict
- `haytham/agents/factory/agent_factory.py` — Agent creation via `create_agent_by_name()`
- `haytham/session/session_manager.py` — Session state, checkpoints, stage outputs

### Adding a New Agent

1. Create `haytham/agents/worker_{name}/worker_{name}_prompt.txt`
2. Add config entry in `AGENT_CONFIGS` in `config.py` (including `structured_output_model_path` if needed)
3. The generic `create_agent_by_name()` handles creation automatically from the config

**Key files:** `haytham/agents/factory/agent_factory.py`, `haytham/agents/hooks.py`, `haytham/config.py`

### Adding a New Stage

1. `StageMetadata` in `stage_registry.py`
2. `StageExecutionConfig` in `haytham/workflow/stages/configs.py`
3. Burr action in `burr_actions.py` + transition in `burr_workflow.py`
4. Entry validator in `entry_conditions.py` — register in `_VALIDATORS` dict and update `get_next_available_workflow()` order

**Key files:** `haytham/workflow/stage_registry.py`, `haytham/workflow/stages/configs.py`, `haytham/workflow/burr_actions.py`, `haytham/workflow/burr_workflow.py`, `haytham/workflow/entry_conditions.py`

### Adding a New Workflow Type

1. Add `WorkflowType` enum value in `stage_registry.py`
2. Add entry validator and register in `_VALIDATORS`
3. Add stages following the "Adding a New Stage" checklist above
4. Update `SessionManager` workflow aliases in ONE place (extract to constant if not yet done)

**Key files:** `haytham/workflow/stage_registry.py`, `haytham/workflow/entry_conditions.py`, `haytham/session/session_manager.py`

### Package Boundaries

- `haytham/workflow/` imports from `haytham/agents/` — not the reverse
- `haytham/session/` is imported by both `workflow/` and `agents/` — keep it dependency-free
- `haytham/agents/output_utils.py` is the shared extraction layer — individual `worker_*/` modules import from here, not from each other
- `haytham/phases/` is **deprecated** — it re-exports from `haytham/workflow/stage_registry`. Import from `workflow/` directly


## Documentation Editing Standards
- Write in plain, human-friendly language. Avoid jargon and verbose AI-sounding prose.
- Never use em dashes (—). Use commas, periods, or parentheses instead.
- Prefer diagrams (mermaid) over long explanatory paragraphs when showing architecture or flows.
- When editing docs, keep it concise. If the user asks for simplification, go further than you think necessary.

## Code Hygiene Rules

### DRY: Centralize Shared Logic

Before defining a constant, helper, or pattern in a new file, **search the codebase** for existing definitions. Duplicate definitions rot fast.

- **Shared constants**: Define once, import everywhere. Never recompute paths like `SESSION_DIR` per-file. Use `SessionManager` for session paths.
- **Shared initialization**: `sys.path.insert()` and `load_dotenv()` should each live in ONE init module, not be copy-pasted into every view.
- **Shared data structures**: If a dict (like workflow aliases) or list (like stage ordering) appears in more than one place, extract it to a single source of truth — typically the relevant registry or config module.
- **Shared formatting**: If two search providers, validators, or formatters have near-identical code, extract the common logic into a shared function/protocol.

**Check**: Before adding code, grep for similar patterns. If it exists elsewhere, import it.

### Single Responsibility: Split by Responsibility, Not by Size

Line counts and method counts are symptoms, not diagnoses. A 800-line file with one cohesive responsibility is healthier than five 160-line files with tangled dependencies. Before splitting, apply four tests:

1. **Debuggability**: When this breaks, does the module name in the traceback tell you what went wrong? If "session_manager.py" could mean 5 different things, split. If it clearly means "session state," it's fine.
2. **Reusability**: Can the extracted piece be used independently by other modules? If the extraction only makes sense in the context of the parent class (e.g., methods that all operate on `self.session_dir`), don't split.
3. **Responsibility boundaries**: Does the class/file mix genuinely different concerns (e.g., HTTP handling + business logic + formatting)? Split at the seam. But "reads files" and "writes files" in the same domain are not different responsibilities.
4. **Testability**: Can you test this piece in isolation without mocking half the system? If pure logic is trapped inside a class that requires infrastructure setup, extract it into standalone functions. (Example: `formatting.py` was extracted from `SessionManager` because formatting logic is pure and testable without a session directory.)

**When to split:**
- A class delegates to an internal collaborator via 5+ pure-forwarding wrappers (expose the collaborator instead).
- Private methods with zero callers (dead code, just delete).
- A function handles multiple execution paths via if/elif chains for different "modes" (extract each mode or use a strategy pattern).
- Two genuinely independent concerns share a file only because they were written at the same time.

**When NOT to split:**
- Methods all operate on the same state (`self.session_dir`, `self.config`) and serve the same domain.
- The extracted module would have zero reuse outside its parent.
- The split creates more import wiring than it removes complexity.

### Open/Closed: Extend via Configuration, Not Modification

When adding a new workflow, agent, stage, or search provider:

- Register it in a config dict or registry — don't add another `if name == "..."` block.
- If a function has a growing chain of `if/elif` for type dispatch, refactor to a dispatch dict or strategy pattern.
- Structured output models for agents should be declared in `AGENT_CONFIGS` metadata, not hardcoded in conditional blocks inside `create_agent_by_name()`.

### Error Handling Standards

- **Never use bare `except Exception:`** that silently swallows errors. Always catch specific exceptions (`json.JSONDecodeError`, `FileNotFoundError`, `KeyError`, etc.).
- **If a try/except pattern repeats 3+ times**, extract it into a helper (e.g., a `safe_json_load(path)` utility).
- **Search providers** should raise/handle a common exception type, not provider-specific exceptions that leak through the abstraction.

### Deprecation Policy

- When deprecating code, **delete it** rather than leaving dead implementations behind commented or marked `# Deprecated`.
- If backward compatibility requires keeping code temporarily, add a `warnings.warn()` call with a removal target date/version and create a backlog item for removal.
- Never register deprecated implementations (validators, enum values, etc.) alongside active ones — it creates confusion about which to use.

### Import Conventions

- **Module-level imports only**. No `import json` or `import re` inside function bodies unless avoiding a genuine circular dependency (document the reason in a comment).
- **Compile regex patterns at module level** if they're used in functions that may be called repeatedly.
- **Lazy imports for optional dependencies** (telemetry, tracing) should use a module-level pattern with `TYPE_CHECKING`, not re-import on every function call.

### Interface Consistency

- Functions/methods that serve the same role (e.g., `validate()` on entry validators) must have **identical signatures**. Never use runtime introspection (`__code__.co_varnames`) to determine how to call a method — that signals a broken interface.
- Parallel abstractions (e.g., search result types from different providers) should share a common protocol or base class.

## Key Patterns

- **Strands SDK**: Agents use `strands.Agent` with prompts from `worker_*_prompt.txt`
- **AWS Bedrock**: LLM calls via `create_bedrock_model()` with configurable timeouts
- **Parallel Execution**: Stage 2 runs market_intelligence and competitor_analysis concurrently
- **Structured Output**: `startup_validator` uses `structured_output_model=ValidationOutput`
- **Session Persistence**: Checkpoints saved as markdown in `session/{stage-slug}/`

**Key files:** `haytham/agents/factory/agent_factory.py`, `haytham/agents/output_utils.py`, `haytham/agents/hooks.py`, `haytham/config.py`

### CRITICAL: Strands SDK Structured Output

When accessing structured output from Strands agents, use `result.structured_output`, NOT `result.output`:

```python
# CORRECT - Strands SDK uses structured_output attribute
if hasattr(result, "structured_output") and result.structured_output is not None:
    if isinstance(result.structured_output, MyPydanticModel):
        return result.structured_output

# WRONG - This attribute doesn't exist in Strands
if hasattr(result, "output"):  # DON'T DO THIS
    ...
```

Reference implementation: `haytham/agents/output_utils.py:extract_text_from_result()`

### PITFALL: Agent Registration

```python
# WRONG — growing if/elif chain in create_agent_by_name()
def create_agent_by_name(name):
    if name == "new_agent":
        return Agent(structured_output=MyModel)  # DON'T ADD HERE

# CORRECT — declare in AGENT_CONFIGS, create_agent_by_name() handles the rest
AGENT_CONFIGS["new_agent"] = AgentConfig(
    structured_output_model_path="haytham.models:MyModel",
    ...
)
```

**Key file:** `haytham/agents/factory/agent_factory.py`

### PITFALL: Entry Validator Registration

```python
# WRONG — adding elif in get_next_available_workflow()
elif workflow_type == "new_type":
    return validate_new_type(session)

# CORRECT — register in _VALIDATORS dict
_VALIDATORS["new_type"] = validate_new_type
```

**Key file:** `haytham/workflow/entry_conditions.py`

### PITFALL: Agents Re-deriving Known Values

If the system has already extracted a value (e.g., `risk_level` from the Burr state), pass it explicitly to downstream agents as a structured input. Never embed it in prose and hope the agent extracts it correctly. Agents should receive facts, not re-derive them.

```python
# WRONG — burying a known value in prose for the LLM to re-extract
scorer_query = f"...Risk Assessment output:\n{risk_assessment_text}..."
# Agent must grep for "Overall Risk Level: HIGH" in thousands of chars
# and pass it to set_risk_and_evidence(risk_level="HIGH", ...)
# If the LLM extracts "MEDIUM" instead, the verdict is silently wrong.

# CORRECT — pass known values explicitly, fail if missing
risk_level = state.get("risk_level")
if not risk_level:
    raise ValueError("risk_level is required")
init_scorecard(risk_level=risk_level)  # pre-set before agent runs
# Agent tools read the pre-set value; agent cannot override it
```

**The principle**: Treat agent inputs like function arguments. If a value is already in the system state, it flows as typed data, not prose. If a required value is missing, fail loudly instead of letting the agent invent it. Structured output defines the output contract; apply the same discipline to inputs.

**Key file:** `haytham/agents/tools/recommendation.py` (`init_scorecard`), `haytham/workflow/stages/idea_validation.py`

### PITFALL: Imports Inside Function Bodies

```python
# WRONG — re-imports on every call, hides dependencies
def process_output(result):
    import json
    import re
    pattern = re.compile(r"```json(.*?)```", re.DOTALL)

# CORRECT — module-level imports and compiled patterns
import json
import re

_JSON_BLOCK_PATTERN = re.compile(r"```json(.*?)```", re.DOTALL)

def process_output(result):
    match = _JSON_BLOCK_PATTERN.search(result)
```

Exception: circular dependency avoidance (document the reason in a comment).

### Logging & Privacy

- **Debug/operational logging**: Use `logger.debug/info/warning/error()` via `logging.getLogger("haytham")`. Log operational metadata only — stage names, durations, token counts, file paths.
- **User-facing output**: Stage outputs saved as markdown in `session/{stage-slug}/`. Rendered in Streamlit UI.
- **Never log**: User's startup idea text, full LLM prompts/responses, API keys, or session state content in debug logs.

### Scoring & Validation Pipeline

The `validation-summary` stage runs scorer → narrator → merge sequentially. See [docs/architecture/scoring-pipeline.md](docs/architecture/scoring-pipeline.md) for the full verdict logic, dimension scoring, and post-validator details.

**Key files**: `recommendation.py`, `validation_summary_models.py`, `idea_validation.py`, `worker_validation_scorer_prompt.txt`, `validators/`

## Environment Variables

Required: `AWS_REGION` or `AWS_PROFILE`, `BEDROCK_REASONING_MODEL_ID`, `BEDROCK_HEAVY_MODEL_ID`, `BEDROCK_LIGHT_MODEL_ID`

Optional: `LOG_LEVEL`, `OTEL_SDK_DISABLED` (default: true), `OTEL_EXPORTER_OTLP_ENDPOINT` (default: localhost:4317), `DEFAULT_MAX_TOKENS` (default: 5000), `WEB_SEARCH_SESSION_LIMIT` (default: 20), `BRAVE_API_KEY` or `TAVILY_API_KEY`

## Backlog.md MCP (For Generated Systems Only)

**IMPORTANT:** The Backlog.md MCP tools are NOT for tracking Haytham development tasks. They are part of the system that Haytham generates — used by generated applications to manage their own task backlogs.

- **DO NOT** use `mcp__backlog__*` tools to track ADR implementations, bug fixes, or feature work on Haytham itself
- **DO** use these tools when working on the story generation or project management features that Haytham outputs for generated applications

For tracking Haytham development work, use the built-in Claude Code task tools (TaskCreate, TaskUpdate, TaskList) or work directly without formal task tracking.
