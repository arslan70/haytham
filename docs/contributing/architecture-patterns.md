# Architecture Patterns & Code Hygiene

This document contains the detailed architecture patterns, code hygiene rules, and common pitfalls for contributing to Haytham. These same rules are summarized in [CLAUDE.md](../../CLAUDE.md) for AI coding assistants.

---

## Code Hygiene Rules

### DRY: Centralize Shared Logic

Before defining a constant, helper, or pattern in a new file, **search the codebase** for existing definitions. Duplicate definitions rot fast.

- **Shared constants**: Define once, import everywhere. Never recompute paths like `SESSION_DIR` per-file. Use `SessionManager` for session paths.
- **Shared initialization**: `sys.path.insert()` and `load_dotenv()` should each live in ONE init module, not be copy-pasted into every view.
- **Shared data structures**: If a dict (like workflow aliases) or list (like stage ordering) appears in more than one place, extract it to a single source of truth, typically the relevant registry or config module.
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

- Register it in a config dict or registry. Don't add another `if name == "..."` block.
- If a function has a growing chain of `if/elif` for type dispatch, refactor to a dispatch dict or strategy pattern.
- Structured output models for agents should be declared in `AGENT_CONFIGS` metadata, not hardcoded in conditional blocks inside `create_agent_by_name()`.

### Error Handling Standards

- **Never use bare `except Exception:`** that silently swallows errors. Always catch specific exceptions (`json.JSONDecodeError`, `FileNotFoundError`, `KeyError`, etc.).
- **If a try/except pattern repeats 3+ times**, extract it into a helper (e.g., a `safe_json_load(path)` utility).
- **Search providers** should raise/handle a common exception type, not provider-specific exceptions that leak through the abstraction.

### Deprecation Policy

- When deprecating code, **delete it** rather than leaving dead implementations behind commented or marked `# Deprecated`.
- If backward compatibility requires keeping code temporarily, add a `warnings.warn()` call with a removal target date/version and create a backlog item for removal.
- Never register deprecated implementations (validators, enum values, etc.) alongside active ones.

### Import Conventions

- **Module-level imports only**. No `import json` or `import re` inside function bodies unless avoiding a genuine circular dependency (document the reason in a comment).
- **Compile regex patterns at module level** if they're used in functions that may be called repeatedly.
- **Lazy imports for optional dependencies** (telemetry, tracing) should use a module-level pattern with `TYPE_CHECKING`, not re-import on every function call.

### Interface Consistency

- Functions/methods that serve the same role (e.g., `validate()` on entry validators) must have **identical signatures**. Never use runtime introspection (`__code__.co_varnames`) to determine how to call a method.
- Parallel abstractions (e.g., search result types from different providers) should share a common protocol or base class.

---

## Key Patterns

- **Strands SDK**: Agents use `strands.Agent` with prompts from `worker_*_prompt.txt`
- **AWS Bedrock**: LLM calls via `create_bedrock_model()` with configurable timeouts
- **Parallel Execution**: Phase 1 runs market_intelligence and competitor_analysis concurrently
- **Structured Output**: Agents like `startup_validator` use `structured_output_model=ValidationOutput`
- **Session Persistence**: Checkpoints saved as markdown in `session/{stage-slug}/`

Key files: `haytham/agents/factory/agent_factory.py`, `haytham/agents/output_utils.py`, `haytham/agents/hooks.py`, `haytham/config.py`

---

## Common Pitfalls

### Strands SDK Structured Output

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

### Agent Registration

```python
# WRONG - growing if/elif chain in create_agent_by_name()
def create_agent_by_name(name):
    if name == "new_agent":
        return Agent(structured_output=MyModel)  # DON'T ADD HERE

# CORRECT - declare in AGENT_CONFIGS, create_agent_by_name() handles the rest
AGENT_CONFIGS["new_agent"] = AgentConfig(
    structured_output_model_path="haytham.models:MyModel",
    ...
)
```

Key file: `haytham/agents/factory/agent_factory.py`

### Entry Validator Registration

```python
# WRONG - adding elif in get_next_available_workflow()
elif workflow_type == "new_type":
    return validate_new_type(session)

# CORRECT - register in _VALIDATORS dict
_VALIDATORS["new_type"] = validate_new_type
```

Key file: `haytham/workflow/entry_conditions.py`

### Agents Re-deriving Known Values

If the system has already extracted a value (e.g., `risk_level` from the Burr state), pass it explicitly to downstream agents as a structured input. Never embed it in prose and hope the agent extracts it correctly. Agents should receive facts, not re-derive them.

```python
# WRONG - burying a known value in prose for the LLM to re-extract
scorer_query = f"...Risk Assessment output:\n{risk_assessment_text}..."
# Agent must grep for "Overall Risk Level: HIGH" in thousands of chars

# CORRECT - pass known values explicitly, fail if missing
risk_level = state.get("risk_level")
if not risk_level:
    raise ValueError("risk_level is required")
init_scorecard(risk_level=risk_level)  # pre-set before agent runs
```

**The principle**: Treat agent inputs like function arguments. If a value is already in the system state, it flows as typed data, not prose. If a required value is missing, fail loudly instead of letting the agent invent it.

Key file: `haytham/agents/tools/recommendation.py` (`init_scorecard`), `haytham/workflow/stages/idea_validation.py`

### Imports Inside Function Bodies

```python
# WRONG - re-imports on every call, hides dependencies
def process_output(result):
    import json
    import re
    pattern = re.compile(r"```json(.*?)```", re.DOTALL)

# CORRECT - module-level imports and compiled patterns
import json
import re

_JSON_BLOCK_PATTERN = re.compile(r"```json(.*?)```", re.DOTALL)

def process_output(result):
    match = _JSON_BLOCK_PATTERN.search(result)
```

Exception: circular dependency avoidance (document the reason in a comment).

### LLM Text Overriding Deterministic Rules

Never let LLM-generated text override deterministic safety rules. If the system needs a property enforced (e.g., HIGH risk always caps GO to PIVOT), make the rule unconditional. String-based quality gates (length checks, phrase blocklists) cannot reliably verify substance and will be bypassed. The LLM's job is qualitative judgment (scoring, evaluating evidence). The system's job is deterministic rules from those judgments. Keep this boundary sharp.

---

## Logging & Privacy

- **Debug/operational logging**: Use `logger.debug/info/warning/error()` via `logging.getLogger("haytham")`. Log operational metadata only: stage names, durations, token counts, file paths.
- **User-facing output**: Stage outputs saved as markdown in `session/{stage-slug}/`. Rendered in Streamlit UI.
- **Never log**: User's startup idea text, full LLM prompts/responses, API keys, or session state content in debug logs.

---

## Scoring & Validation Pipeline

The `validation-summary` stage runs scorer, narrator, then merge sequentially. See [scoring-pipeline.md](../architecture/scoring-pipeline.md) for the full verdict logic, dimension scoring, and post-validator details.

Key files: `recommendation.py`, `validation_summary_models.py`, `idea_validation.py`, `worker_validation_scorer_prompt.txt`, `validators/`
