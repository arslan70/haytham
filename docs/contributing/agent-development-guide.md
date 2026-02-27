# Agent Development Guide

## Overview of Haytham Agent Architecture

Haytham uses a configuration-driven architecture for defining and constructing agents.

Agents are not hardcoded classes or registered using conditionals. Instead, all agents are defined in a single registry (`AGENT_CONFIGS`) located in `haytham/config.py`. This registry acts as the single source of truth for agent configuration.

Each agent is defined using an `AgentConfig` object, which specifies:

- The agent's name
- The prompt file to load
- Token limits
- Tool profile
- Model tier
- Optional structured output model
- Optional custom system prompt

When the system needs to create an agent, it calls:

`create_agent_by_name(agent_name)`

This factory method:

1. Looks up the agent in `AGENT_CONFIGS`
2. Resolves structured output models dynamically (if configured)
3. Applies any runtime overrides
4. Delegates construction to `_create_agent_from_config`

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

## Adding a New Agent

Because Haytham uses a configuration-driven architecture, adding a new agent does not require modifying factory logic. Instead, you define the agent declaratively and allow the system to construct it automatically.

Adding a new agent involves three steps:

### 1. Create the Prompt Directory

Create a new directory under:

`haytham/agents/`

Following the naming convention:

`worker_{agent_name}/`

Inside that directory, add a prompt file:

`worker_{agent_name}_prompt.txt`

Example:

haytham/agents/worker_concept_summarizer/
    worker_concept_summarizer_prompt.txt

The `prompt_key` defined in `AgentConfig` must match the worker directory name.

---

### 2. Register the Agent in AGENT_CONFIGS

Open:

`haytham/config.py`

Add a new entry to the `AGENT_CONFIGS` dictionary:

```python
"concept_summarizer": AgentConfig(
    name="concept_summarizer_agent",
    prompt_key="worker_concept_summarizer",
    max_tokens=TOKENS_DEFAULT,
)
```
This is the only required registration step.

`AGENT_CONFIGS` acts as the single source of truth for agent definitions.  
Once registered here, the factory can construct the agent automatically.

Optional configuration fields include:

- `tool_profile` — if the agent requires tools
- `model_tier` — to select the appropriate model tier
- `structured_output_model_path` — if the agent returns structured JSON
- `custom_system_prompt` — to override the prompt file entirely

---

### 3. (Optional) Register in STAGE_CONFIGS

If the agent should run as part of a workflow stage, register it in:

`haytham/workflow/stages/configs.py`

This determines when and how the agent participates in workflow orchestration.

If the agent is used programmatically outside a workflow stage, this step may not be required.

---

### No Changes to the Factory

You should never modify `agent_factory.py` to support a new agent.

The `create_agent_by_name()` factory method dynamically constructs agents using `AGENT_CONFIGS`, ensuring the system remains open for extension and closed for modification.

## Section 3: Structured Output (If Required)

If the agent must return structured JSON instead of plain text, define a Pydantic model.

Create a new file:

`haytham/schemas/concept_summary.py`

```python
from pydantic import BaseModel

class ConceptSummary(BaseModel):
    title: str
    summary: str
    key_points: list[str]
```

Then update your `AGENT_CONFIGS` entry:

```python
"concept_summarizer": AgentConfig(
    name="concept_summarizer_agent",
    prompt_key="worker_concept_summarizer",
    max_tokens=TOKENS_DEFAULT,
    structured_output_model_path="haytham.schemas.concept_summary.ConceptSummary",
)
```

When `structured_output_model_path` is provided, the factory automatically enables structured output parsing.

If your agent only returns text, you can skip this section.

## Testing an Agent

Agents should be tested without making real LLM calls.

Existing tests in the repository use mocked LLM responses. Follow the same pattern to ensure tests are fast and deterministic.

When writing a test for a new agent:

1. Mock the LLM client.
2. Provide a controlled response.
3. Verify that:
   - The agent loads correctly.
   - The prompt is applied.
   - Structured output (if enabled) is parsed correctly.
   - The output extraction behaves as expected.

Example test structure:

```python
def test_concept_summarizer():
    # Arrange
    # Mock LLM response

    # Act
    # Call agent

    # Assert
    # Verify expected output format
```

Refer to existing worker agent tests for the correct mocking pattern.

## How Agents Fit Into the Burr Workflow

Haytham agents do not run in isolation. They are executed as part of the Burr orchestration workflow.

The high-level lifecycle is:

1. A workflow stage is triggered.
2. The stage configuration (`STAGE_CONFIGS`) determines which agent should run.
3. The workflow calls `create_agent_by_name()`.
4. The factory builds the agent using `AGENT_CONFIGS`.
5. The agent executes with its prompt, tools, and model configuration.
6. The output is processed and passed to the next stage.

This separation ensures:
- Agents remain modular.
- Workflow logic remains independent.
- New agents can be added without modifying orchestration code.

## Tool Calling with Strands SDK

Some agents use tools to interact with external systems.

Tool access is controlled through the `tool_profile` field in `AgentConfig`.

When tools are enabled:

- The agent receives a predefined tool set.
- Tool parameters follow scalar input patterns.
- Tool outputs may be accumulated and passed back into the agent reasoning loop.

This tool integration is handled automatically by the factory and does not require custom wiring when adding a new agent.

Tool configuration should always be defined in `AGENT_CONFIGS`, not inside the factory.

## Testing Strategy and LLM-as-Judge (ADR-018)

For advanced validation workflows, Haytham supports evaluation using the LLM-as-Judge pattern described in ADR-018.

When writing tests:

- Avoid real model calls in unit tests.
- Use mocked LLM responses.
- Validate structured output schemas when applicable.
- Ensure agent behavior aligns with expected output format.

This approach guarantees deterministic and fast test execution while preserving production behavior.

## Architectural References

This guide follows the patterns defined in:

`docs/contributing/architecture-patterns.md`

That document describes:
- Core system design principles
- Agent registration patterns
- Workflow orchestration structure
- Extensibility guidelines

New contributors should review it alongside this guide for deeper architectural understanding.
