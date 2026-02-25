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
