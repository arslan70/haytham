# Architecture Overview

This document describes the system architecture of Haytham. For the user-facing process walkthrough, see [How It Works](../how-it-works.md). For details on each technology and why it was chosen, see [Technology Stack](../technology.md).

---

## System Design

Haytham is a multi-phase workflow system where:

- **Specialist AI agents** perform analysis and generation at each stage
- **Humans approve** at phase boundaries (gates)
- **Shared state** provides continuity across the entire lifecycle

```
┌──────────────────────────────────────────────────────────────┐
│                       Streamlit UI                            │
└──────────────────────────┬───────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                   Burr Workflow Engine                        │
│       State machine · Conditional branching · Checkpoints    │
└──────────────────────────┬───────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  Phase 1   idea_analysis → market_context → risk_assessment  │
│            → [pivot_strategy] → validation_summary → GATE    │
│  Phase 2   mvp_scope → capability_model → system_traits      │
│            → GATE                                            │
│  Phase 3   build_buy_analysis → architecture_decisions       │
│            → GATE                                            │
│  Phase 4   story_generation → story_validation →             │
│            dependency_ordering                               │
└──────────────────────────┬───────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                    Shared State Layer                         │
│                                                              │
│   VectorDB (LanceDB)              Backlog.md (MCP)           │
│   • Capabilities (CAP-*)          • Stories                  │
│   • Decisions (DEC-*)    linked   • Dependencies             │
│   • Entities (ENT-*)    via tags  • Status                   │
└──────────────────────────────────────────────────────────────┘
```

## Core Components

### Burr Workflow Engine

[Burr](https://github.com/dagworks-inc/burr) ([docs](https://burr.dagworks.io/)) provides the state machine that orchestrates the four phases. Each stage is a Burr action with defined inputs and outputs.

Key behaviors:
- **Conditional branching** — `when(risk_level="HIGH")` triggers the pivot strategy stage
- **Checkpoint persistence** — state saved after each action, resume from any point
- **Tracking UI** — optional visualization of workflow state at `localhost:7241`

**Key file:** `haytham/workflow/burr_workflow.py`

### Stage Registry

Single source of truth for stage metadata. Every stage is registered with its slug, display name, phase, and ordering. O(1) lookups by slug or action name.

**Key file:** `haytham/workflow/stage_registry.py`

### Stage Executor

Template Method pattern for stage execution. Each stage is configured via a `StageExecutionConfig` entry in the `STAGE_CONFIGS` dict — no per-stage subclasses needed.

**Key file:** `haytham/workflow/stage_executor.py`

### Agent Factory

Creates agents using the [Strands Agents SDK](https://github.com/strands-agents/sdk-python) ([docs](https://strandsagents.com/)). Each agent is registered in the `AGENT_FACTORIES` dict with its configuration (prompt file, model tier, structured output model if needed).

Agents are created dynamically by name — adding a new agent means adding an entry to the config dict and a factory function.

**Key file:** `haytham/agents/factory/agent_factory.py`

### Session Manager

Manages session state, checkpoints, and stage outputs. Each stage writes its output to `session/{stage-slug}/`. Phase completion is tracked via lock files (e.g., `.idea-validation.locked`).

**Key file:** `haytham/session/session_manager.py`

### Workflow Runner

Synchronous wrapper that bridges the Burr async workflow with the Streamlit UI. New workflow types are configured via a `WorkflowConfig` dataclass.

**Key file:** `frontend_streamlit/lib/workflow_runner.py`

## Shared State Layer

Two complementary stores provide continuity across phases:

| Store | Contains | Lifecycle | Purpose |
|-------|----------|-----------|---------|
| **VectorDB ([LanceDB](https://lancedb.github.io/lancedb/))** | Capabilities (CAP-\*), Decisions (DEC-\*), Entities (ENT-\*) | Immutable definitions; new versions supersede old | Semantic queries; agent input |
| **[Backlog.md](https://backlog.md/) (MCP)** | Stories, tasks, status | Mutable work items | Implementation handoff; status tracking |

LanceDB is an embedded vector database — no server required. It stores capabilities, decisions, and entities with vector embeddings so agents can retrieve semantically relevant context from earlier stages. Backlog.md provides task management for the generated application via the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/), enabling coding agents to read and update stories during implementation.

### Immutability and Superseding

Capabilities and decisions are never modified. When requirements change, new versions are created with `supersedes:` links. This preserves the audit trail and makes changes explicit.

### Traceability Tags

Stories in Backlog.md link to the shared state via tags:

- `implements:CAP-F-001` — which capability this story delivers
- `uses:DEC-001` — which architecture decision it depends on
- `touches:ENT-001` — which domain entity it affects

This traceability is what enables the Evolution milestone — the system can understand what exists and generate targeted changes.

## Why Separate Phases?

| Factor | Benefit |
|--------|---------|
| **Role alignment** | Each phase maps to a recognizable role (Founder, Product Owner, Architect, Tech Lead) |
| **Focused state** | Each phase manages only the state it needs |
| **Failure isolation** | Problems are contained to one phase |
| **Independent evolution** | Improve one phase without affecting others |
| **Natural pacing** | Days between phases is normal — no pressure to run end-to-end in one session |

## Agent Architecture

Each agent follows a consistent pattern:

1. **Prompt file** — `haytham/agents/worker_{name}/worker_{name}_prompt.txt`
2. **Config entry** — registered in `AGENT_CONFIGS` with model tier and optional structured output model
3. **Factory function** — registered in `AGENT_FACTORIES` for dynamic creation

Agents use the Strands SDK. Structured output is accessed via `result.structured_output` (not `result.output`).

### Model Tiers

Agents are assigned to one of three model tiers:

| Tier | Purpose | Examples |
|------|---------|---------|
| **REASONING** | Deep analysis requiring chain-of-thought | Validation scoring, risk assessment |
| **HEAVY** | Substantial generation | Market analysis, architecture decisions, story generation |
| **LIGHT** | Fast classification and formatting | Idea polishing, input validation |

Each tier maps to a configurable model ID per provider, allowing cost/quality trade-offs.

### Structured Output Pipeline

Agents that need typed responses use [Pydantic](https://docs.pydantic.dev/) models for structured output. The pipeline:

1. **Define** a Pydantic model in the agent's directory (e.g., `validation_models.py`)
2. **Register** it in `AGENT_CONFIGS` as `structured_output_model` or `structured_output_model_path` (lazy import)
3. **Create** the agent via the factory — Strands passes the model to the LLM as a response schema
4. **Extract** the result via `result.structured_output` (canonical extraction in `haytham/agents/output_utils.py`)

The structured output is then serialized — `model_dump_json()` for Burr state persistence, `to_markdown()` for human-readable session output.

### The Control Plane Pattern

Haytham's architecture separates two concerns that are often conflated: **deciding what to build** (specification) and **executing the build** (implementation). The specification phases (1–4) are Haytham's core. The execution phase (5) dispatches traced work items to whatever agent is best suited to perform them.

This separation is what makes Haytham a control plane rather than a monolithic system. The executor can be:

- **A hosted coding agent** (Devin, Amazon Q Developer Agent, Google Jules, Claude Code) receiving a story with acceptance criteria, architecture constraints, and capability context
- **An MCP-native service** (Google Stitch) receiving capability specs and generating UI code
- **A cloud provider agent** (AWS Bedrock Agents, Google Vertex AI Agents) receiving infrastructure requirements
- **A human developer** receiving the same traced specification

The `AGENT_FACTORIES` registry, `StageExecutionConfig` pattern, and Burr's state machine all treat agents as interchangeable units of work. The workflow engine doesn't distinguish between an agent that reasons locally and one that delegates to an external service — they participate in the same state machine, traceability chains, and approval gates.

### Planned Example: Google Stitch

The planned [Google Stitch](https://stitch.withgoogle.com/) integration (see [ADR-021](../adr/ADR-021-design-ux-workflow-stage.md)) will demonstrate this pattern end-to-end: a `ux_designer` agent will use the Strands `mcp_client` tool to connect to Stitch's official MCP endpoint, discover its tools, and orchestrate UI generation — all within the same Burr state machine, `StageExecutionConfig`, and approval gates used by every other agent.

As more providers expose agent interfaces — whether through MCP, native SDKs, or other protocols — the same integration path applies. What varies is the executor; the specification-driven context, traceability, and governance remain constant.

See [Vision and Roadmap](../../VISION.md#the-control-plane-orchestrating-execution-agents) for the full rationale.

## Validation Pipeline

The validation summary stage (Phase 1 terminator) runs a three-step pipeline:

1. **Scorer** (REASONING tier) — Records knockouts, counter-signals, dimension scores, and computes a verdict. Evidence is validated through rubric phrase rejection, source tag validation, and dedup checks.
2. **Narrator** (HEAVY tier) — Receives scorer JSON and upstream context, generates prose sections (executive summary, Lean Canvas, findings, next steps).
3. **Merge** — Deterministic combination of scorer and narrator outputs. Fixes verdict if narrator hallucinated a different verdict than the scorer computed.

For full details, see [Scoring Pipeline](scoring-pipeline.md).

## Project Structure

Simplified view — showing key components. The full package includes additional modules for context management, exporters, feedback, and more.

```
haytham/
├── agents/                  # AI agents
│   ├── factory/              # Agent factory and orchestration
│   ├── output_utils.py      # Shared output extraction
│   └── worker_*/            # Specialist agents (prompt + config each)
├── workflow/                # Burr workflow engine
│   ├── burr_workflow.py     # Workflow definition and transitions
│   ├── stage_registry.py    # Centralized stage metadata
│   ├── stage_executor.py    # Generic stage execution (Template Method)
│   └── workflow_factories.py # Workflow creation helpers
├── session/                 # Session management and persistence
├── state/                   # State schema and coverage tracking
├── formatters/              # Output formatting
├── phases/                  # Stage configuration
└── telemetry/               # Optional OpenTelemetry integration

frontend_streamlit/          # Streamlit UI
├── Haytham.py               # Main dashboard
├── lib/                     # Workflow runner and utilities
├── views/                   # UI views (execution, feedback, gates)
├── components/              # Reusable UI components
└── assets/                  # Static assets

tests/                       # Test suite
```
