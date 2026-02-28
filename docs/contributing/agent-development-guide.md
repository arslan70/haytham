Agent Development Guide

This guide expands upon the “Adding a New Agent” section in CLAUDE.md.
If architectural changes are introduced, both documents should be updated together.

1. Overview of Haytham Agent Architecture

Haytham uses a configuration-driven architecture for defining and constructing agents.

Agents are not hardcoded classes or registered using conditionals. Instead, all agents are defined in a centralized registry (AGENT_CONFIGS) located in haytham/config.py. This registry is the single source of truth for agent configuration.

Each agent is defined using an AgentConfig object, which includes:

name

prompt_key

max_tokens

timeout_config

tool_profile

model_tier

streaming

use_file_ops_model

structured_output_model

structured_output_model_path

custom_system_prompt

When the system needs to construct an agent, it calls:

create_agent_by_name(agent_name)

The factory method:

Looks up configuration in AGENT_CONFIGS

Resolves structured_output_model_path dynamically (if provided)

Applies runtime overrides

Delegates construction to _create_agent_from_config

This design follows the Open-Closed Principle (OCP):
new agents can be added without modifying factory logic.

Model Tier Guidance

Select the appropriate model_tier based on task complexity:

LIGHT — Extraction, summarization, simple transformations

HEAVY — Structured output generation, synthesis, complex reasoning

REASONING — Cross-referencing, validation workflows, multi-step logic

Choosing the correct tier ensures appropriate capability and cost efficiency.

Agent Construction Flow

Workflow Stage
→ create_agent_by_name()
→ AGENT_CONFIGS lookup
→ _create_agent_from_config()
→ Fully constructed Agent

Important: Do Not Instantiate Agents Directly

Agents must always be created using create_agent_by_name().

Directly calling Agent(...) bypasses critical system behavior:

OpenTelemetry tracing (missing agent.name)

Required hook registration (hooks=[HaythamAgentHooks()])

Model tier routing

Runtime overrides

Structured output resolution

Observability instrumentation

The factory automatically attaches HaythamAgentHooks() and ensures proper tracing attributes are set.

Bypassing the factory will result in missing hooks, broken observability, and inconsistent behavior.

2. Adding a New Agent

New agents are added entirely through configuration.
No changes to the factory are required.

Step 1: Create the Prompt Directory

Create a directory under:

haytham/agents/

Follow the naming convention:

worker_{agent_name}/

Inside that directory, create:

worker_{agent_name}_prompt.txt

Example:

haytham/agents/worker_concept_summarizer/
    worker_concept_summarizer_prompt.txt

The prompt_key in AgentConfig must match the worker directory name.

Step 2: Register in AGENT_CONFIGS

Open:

haytham/config.py

Add a new entry:

"concept_summarizer": AgentConfig(
    name="concept_summarizer_agent",
    prompt_key="worker_concept_summarizer",
    max_tokens=TOKENS_DEFAULT,
)

Optional fields include:

tool_profile

model_tier

structured_output_model_path

custom_system_prompt

Step 3: (Optional) Register in STAGE_CONFIGS

If the agent participates in a workflow stage, register it in:

haytham/workflow/stages/configs.py

This determines when and how the agent executes within orchestration.

If the agent is used programmatically outside workflow stages, this step is not required.

3. Structured Output (Optional)

If the agent must return structured JSON, define a Pydantic model:

from pydantic import BaseModel

class ConceptSummary(BaseModel):
    title: str
    summary: str
    key_points: list[str]

Update configuration:

"concept_summarizer": AgentConfig(
    name="concept_summarizer_agent",
    prompt_key="worker_concept_summarizer",
    max_tokens=TOKENS_DEFAULT,
    structured_output_model_path="haytham.schemas.concept_summary:ConceptSummary",
)

When structured_output_model_path is provided, the factory dynamically resolves the class and enables structured output parsing.

4. Testing Agents

Agents must be tested without making real LLM calls.

Unit Testing (Mocked LLM)

When writing tests:

Mock the LLM client

Provide a controlled response

Verify prompt loading

Verify structured output (if enabled)

Verify output extraction behavior

Example structure:

def test_concept_summarizer():
    # Arrange: mock LLM response

    # Act: call agent

    # Assert: verify expected output

Refer to existing worker agent tests for correct mocking patterns.

LLM-as-Judge Evaluation (ADR-018)

Agent quality is validated using the LLM-as-Judge evaluation framework (ADR-018).

Run evaluations with:

make test-agents

For faster execution:

make test-agents-quick

If new fixtures are required:

make record-fixtures

All new agents should integrate with this evaluation system where applicable.

Output Extraction

Agent responses must be processed using:

extract_text_from_result()
(from haytham/agents/output_utils.py).

This ensures consistent text extraction across all agents and avoids manual parsing.

5. Tool Calling

Tool access is controlled via the tool_profile field in AgentConfig.

When defining tools:

Use the @tool decorator

Tools must never raise exceptions — return structured error responses instead

Use strongly typed parameters

Provide clear, comprehensive docstrings (the LLM reads them)

Ensure outputs are deterministic and structured

Tool configuration must be defined in AGENT_CONFIGS, not in the factory.

6. How Agents Fit Into the Workflow

Agents execute inside the Burr orchestration workflow.

Lifecycle:

A workflow stage is triggered

STAGE_CONFIGS determines which agent runs

The workflow calls create_agent_by_name()

The factory constructs the agent

The agent executes with its prompt, tools, and model configuration

The output is processed and passed to the next stage

This separation ensures modularity, extensibility, and clean orchestration boundaries.

7. Architectural References

This guide aligns with:

docs/contributing/architecture-patterns.md

Contributors should review that document alongside this guide for deeper architectural context.
