# Agent Development Guide

This guide expands upon the "Adding a New Agent" section in `CLAUDE.md` and should be kept consistent with it. If architectural changes are made, update both documents together.

---

## 1. Overview of Haytham Agent Architecture

Haytham uses a configuration-driven architecture for defining and constructing agents.

Agents are not hardcoded classes and are not registered using conditionals. Instead, all agents are defined in a single registry (`AGENT_CONFIGS`) located in `haytham/config.py`. This registry acts as the single source of truth for agent configuration.

Each agent is defined using an `AgentConfig` object, which defines:

- `name`
- `prompt_key`
- `max_tokens`
- `timeout_config`
- `tool_profile`
- `model_tier`
- `streaming`
- `use_file_ops_model`
- `structured_output_model`
- `structured_output_model_path`
- `custom_system_prompt`

Agents must be created using:

```python
create_agent_by_name(agent_name)
```

The factory:

- Looks up the agent in `AGENT_CONFIGS`
- Resolves structured output models dynamically (if configured)
- Applies runtime overrides
- Delegates construction to `_create_agent_from_config`
- Attaches required hooks and tracing attributes
- Ensures correct model tier routing

### High-level flow

```
Workflow Stage
→ create_agent_by_name()
→ AGENT_CONFIGS lookup
→ _create_agent_from_config()
→ Fully constructed Agent
```

This design follows the Open-Closed Principle (OCP): new agents can be added without modifying factory logic.

---

### Model Tier Guidance

Select the appropriate `model_tier` based on task complexity:

- **LIGHT** — Extraction, summarization, simple transformations
- **HEAVY** — Structured output generation, synthesis, complex reasoning
- **REASONING** — Cross-referencing, validation workflows, multi-step logic

Choosing the correct tier ensures appropriate capability and cost efficiency.

---

## 2. Factory Usage Requirement

All agents must be instantiated via:

```python
create_agent_by_name(agent_name)
```

Direct instantiation of the `Agent` class is prohibited.

Bypassing the factory can result in:

- Missing hooks
- Broken tracing (`agent.name` not set)
- Incorrect model routing
- Inconsistent structured output handling
- Reduced observability

All new agents must be registered in `AGENT_CONFIGS`. The factory must remain generic and should not be modified to support individual agents.

---

## 3. Adding a New Agent

Adding a new agent is done entirely through configuration.

### Step 1: Create the Prompt Directory

Create a directory under:

```
haytham/agents/
```

Follow the naming convention:

```
worker_{agent_name}/
```

Inside that directory, create:

```
worker_{agent_name}_prompt.txt
```

Example:

```
haytham/agents/worker_concept_summarizer/
    worker_concept_summarizer_prompt.txt
```

The `prompt_key` in `AgentConfig` must match the worker directory name.

---

### Step 2: Register in `AGENT_CONFIGS`

Open:

```
haytham/config.py
```

Add:

```python
"concept_summarizer": AgentConfig(
    name="concept_summarizer_agent",
    prompt_key="worker_concept_summarizer",
    max_tokens=TOKENS_DEFAULT,
)
```

Optional fields:

- `tool_profile`
- `model_tier`
- `structured_output_model_path`
- `custom_system_prompt`

No changes to the factory are required.

---

### Step 3 (Optional): Register in `STAGE_CONFIGS`

If the agent participates in a workflow stage, register it in:

```
haytham/workflow/stages/configs.py
```

This determines when and how the agent executes within workflow orchestration.

---

## 4. Structured Output (Optional)

If the agent must return structured JSON, define a Pydantic model:

```python
from pydantic import BaseModel

class ConceptSummary(BaseModel):
    title: str
    summary: str
    key_points: list[str]
```

Then configure:

```python
"concept_summarizer": AgentConfig(
    name="concept_summarizer_agent",
    prompt_key="worker_concept_summarizer",
    max_tokens=TOKENS_DEFAULT,
    structured_output_model_path="haytham.schemas.concept_summary.ConceptSummary",
)
```

When `structured_output_model_path` is provided, the factory dynamically resolves and enables structured output parsing.

---

## 5. Testing Agents

Agents must be tested without making real LLM calls.

### Unit Testing (Mocked LLM)

When writing tests:

- Mock the LLM client
- Provide controlled responses
- Verify agent loads correctly
- Verify prompt usage
- Verify structured output (if enabled)
- Verify output extraction

Example:

```python
def test_concept_summarizer():
    # Arrange: mock LLM response
    # Act: call agent
    # Assert: verify expected output
```

Refer to existing worker agent tests for correct mocking patterns.

---

### LLM-as-Judge Evaluation (ADR-018)

Agent quality is validated using the LLM-as-Judge framework (ADR-018).

Run:

```
make test-agents
```

Quick mode:

```
make test-agents-quick
```

To record fixtures:

```
make record-fixtures
```

All new agents should integrate with this evaluation framework where applicable.

---

### Output Extraction

Agent responses must be processed using:

```python
extract_text_from_result()
```

(from `haytham/agents/output_utils.py`)

This ensures standardized text extraction across all agents.

---

## 6. Tool Calling

Agents may define tools via `tool_profile` in `AgentConfig`.

Tool implementation rules:

- Tools must never raise exceptions. Return structured error responses instead.
- Tool parameters must be strongly typed.
- Provide comprehensive docstrings (the LLM reads both types and docstrings).
- Tool outputs should be deterministic and structured.
- Tool configuration must be defined in `AGENT_CONFIGS`, not in the factory.

---

## 7. Workflow Integration

Agents execute within the Burr orchestration workflow:

- A workflow stage is triggered.
- `STAGE_CONFIGS` determines which agent runs.
- The workflow calls `create_agent_by_name()`.
- The factory builds the agent from `AGENT_CONFIGS`.
- The agent executes with configured prompt, tools, and model tier.
- Output is processed and passed to the next stage.

This separation keeps agents modular and workflow logic independent.

---

## 8. Architectural References

This guide follows architectural patterns defined in:

```
docs/contributing/architecture-patterns.md
```

That document describes:

- Core system design principles
- Agent registration patterns
- Workflow orchestration structure
- Extensibility guidelines

New contributors should review it alongside this guide.
