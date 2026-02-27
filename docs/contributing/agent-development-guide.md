# Agent Development Guide

## 1. Overview of Haytham Agent Architecture

Haytham uses a configuration-driven architecture for defining and constructing agents.

Agents are not hardcoded classes or registered using conditionals. Instead, all agents are defined in a single registry (`AGENT_CONFIGS`) located in `haytham/config.py`. This registry acts as the single source of truth for agent configuration.

Each agent is defined using an `AgentConfig` object, which specifies:

- Agent name
- Prompt file to load
- Token limits
- Tool profile
- Model tier
- Optional structured output model
- Optional custom system prompt

When the system needs to create an agent, it calls:

```python
create_agent_by_name(agent_name)
```

This factory method:

- Looks up the agent in `AGENT_CONFIGS`
- Resolves structured output models dynamically (if configured)
- Applies runtime overrides
- Delegates construction to `_create_agent_from_config`

Because of this design:

- No `if/elif` blocks are required for new agents
- Adding a new agent does not require modifying factory logic
- The system follows the Open-Closed Principle (OCP)

The high-level flow is:

Workflow Stage  
→ `create_agent_by_name()`  
→ `AGENT_CONFIGS` lookup  
→ `_create_agent_from_config()`  
→ Fully constructed Agent

---

## 2. Adding a New Agent

Adding a new agent does not require modifying factory logic. It is done entirely through configuration.

### Step 1: Create the Prompt Directory

Create a new directory under:

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

### Step 2: Register the Agent in AGENT_CONFIGS

Open:

```
haytham/config.py
```

Add an entry to `AGENT_CONFIGS`:

```python
"concept_summarizer": AgentConfig(
    name="concept_summarizer_agent",
    prompt_key="worker_concept_summarizer",
    max_tokens=TOKENS_DEFAULT,
)
```

This is the only required registration step.

`AGENT_CONFIGS` is the single source of truth for all agents.

Optional configuration fields include:

- `tool_profile` — if tools are required
- `model_tier` — to select model tier
- `structured_output_model_path` — if structured JSON output is needed
- `custom_system_prompt` — to override the prompt file

---

### Step 3: (Optional) Register in STAGE_CONFIGS

If the agent should run as part of a workflow stage, register it in:

```
haytham/workflow/stages/configs.py
```

This determines when and how the agent participates in workflow orchestration.

If the agent is used programmatically outside workflow stages, this step may not be required.

---

### No Changes to the Factory

You should never modify `agent_factory.py` to support a new agent.

The `create_agent_by_name()` method dynamically constructs agents using `AGENT_CONFIGS`, ensuring the system remains open for extension and closed for modification.

---

## 3. Structured Output (If Required)

If the agent must return structured JSON, define a Pydantic model.

Example:

```python
from pydantic import BaseModel

class ConceptSummary(BaseModel):
    title: str
    summary: str
    key_points: list[str]
```

Then update the agent configuration:

```python
"concept_summarizer": AgentConfig(
    name="concept_summarizer_agent",
    prompt_key="worker_concept_summarizer",
    max_tokens=TOKENS_DEFAULT,
    structured_output_model_path="haytham.schemas.concept_summary.ConceptSummary",
)
```

When `structured_output_model_path` is provided, the factory automatically resolves and enables structured output parsing.

If the agent only returns text, this section can be skipped.

---

## 4. Testing an Agent

Agents should be tested without making real LLM calls.

Existing tests in the repository use mocked LLM responses.

When writing tests for a new agent:

- Mock the LLM client
- Provide a controlled response
- Verify agent loads correctly
- Verify prompt is applied
- Verify structured output (if enabled)
- Verify output extraction behaves correctly

Example test structure:

```python
def test_concept_summarizer():
    # Arrange
    # Mock LLM response

    # Act
    # Call agent

    # Assert
    # Verify expected output
```

Refer to existing worker agent tests for the correct mocking pattern.

---

## 5. How Agents Fit Into the Burr Workflow

Haytham agents run inside the Burr orchestration workflow.

High-level lifecycle:

1. A workflow stage is triggered.
2. `STAGE_CONFIGS` determines which agent runs.
3. The workflow calls `create_agent_by_name()`.
4. The factory builds the agent using `AGENT_CONFIGS`.
5. The agent executes with its prompt, tools, and model configuration.
6. The output is processed and passed to the next stage.

This separation ensures:

- Agents remain modular
- Workflow logic remains independent
- New agents can be added without modifying orchestration code

---

## 6. Tool Calling

Some agents use tools.

Tool access is controlled via the `tool_profile` field in `AgentConfig`.

When tools are enabled:

- The agent receives a predefined tool set
- Tool parameters follow scalar input patterns
- Tool outputs may be accumulated into the reasoning loop

Tool configuration must be defined in `AGENT_CONFIGS`, not in the factory.

---

## 7. Testing Strategy (ADR-018)

Haytham supports evaluation using the LLM-as-Judge pattern described in ADR-018.

When writing tests:

- Avoid real model calls in unit tests
- Use mocked responses
- Validate structured output schemas
- Ensure behavior matches expected format

This guarantees deterministic and fast tests.

---

## 8. Architectural References

This guide follows patterns defined in:

```
docs/contributing/architecture-patterns.md
```

That document describes:

- Core system design principles
- Agent registration patterns
- Workflow orchestration structure
- Extensibility guidelines

New contributors should review it alongside this guide.
