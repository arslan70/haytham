# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) for Haytham. Each ADR captures a significant design decision — the context, the decision, the rationale, and the implications.

## Index

### Core Architecture

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-004](ADR-004-multi-phase-workflow-architecture.md) | Multi-Phase Workflow Architecture | Accepted |
| [ADR-016](ADR-016-four-phase-workflow.md) | Four-Phase Workflow (replaces three-phase) | Accepted |
| [ADR-003](ADR-003-system-state-evolution.md) | System State Evolution (VectorDB design) | Accepted |
| [ADR-009](ADR-009-workflow-separation.md) | Workflow Separation | Superseded by ADR-016 |

### Agents and Quality

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-018](ADR-018-llm-as-judge-agent-testing.md) | LLM-as-Judge Agent Testing | Accepted |
| [ADR-022](ADR-022-concept-fidelity-pipeline-integrity.md) | Concept Fidelity and Pipeline Integrity | Accepted |
| [ADR-023](ADR-023-scorer-dimension-reduction.md) | Scorer Dimension Reduction | Accepted |
| [ADR-005](ADR-005-quality-evaluation-pattern.md) | Quality Evaluation Pattern | Accepted |
| [ADR-006](ADR-006-story-generation-quality-evaluation.md) | Story Generation Quality Evaluation | Accepted |
| ADR-007 | *(number reserved — not used)* | — |
| [ADR-019](ADR-019-system-trait-detection.md) | System Trait Detection | Accepted |

### Features

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-002](ADR-002-backlog-md-integration.md) | Backlog.md Integration | Accepted |
| [ADR-013](ADR-013-build-vs-buy-recommendations.md) | Build vs Buy Recommendations | Accepted |
| [ADR-014](ADR-014-web-search-fallback-chain.md) | Web Search Fallback Chain | Accepted |
| [ADR-010](ADR-010-stories-export.md) | Stories Export | Accepted |
| [ADR-011](ADR-011-story-effort-estimation.md) | Story Effort Estimation | Accepted |
| [ADR-012](ADR-012-visual-roadmap.md) | Visual Roadmap | Accepted |
| [ADR-015](ADR-015-google-stitch-mcp-integration.md) | Google Stitch MCP Integration | Deferred |

### UX

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-008](ADR-008-ux-improvements.md) | UX Improvements | Accepted |
| [ADR-017](ADR-017-ux-design-four-phase-workflow.md) | UX Design for Four-Phase Workflow | Accepted |
| [ADR-021](ADR-021-design-ux-workflow-stage.md) | Design UX Workflow Stage | Accepted |

### Infrastructure

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-020](ADR-020-project-rename.md) | Project Rename (kickstarter to haytham) | Completed |

### Genesis Foundation (Early ADRs)

These ADRs document the initial design exploration for the story-to-implementation pipeline:

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-001](ADR-001-story-to-implementation-pipeline.md) | Story-to-Implementation Pipeline | Foundational |
| [ADR-001a](ADR-001a-mvp-spec-enhancement.md) | MVP Spec Enhancement | Foundational |
| [ADR-001b](ADR-001b-platform-stack-proposal.md) | Platform Stack Proposal | Foundational |
| [ADR-001c](ADR-001c-system-state-model.md) | System State Model | Foundational |
| [ADR-001d](ADR-001d-story-interpretation-engine.md) | Story Interpretation Engine | Foundational |
| [ADR-001e](ADR-001e-system-design-evolution.md) | System Design Evolution | Foundational |
| [ADR-001f](ADR-001f-task-generation-refinement.md) | Task Generation Refinement | Foundational |
| [ADR-001g](ADR-001g-implementation-execution.md) | Implementation Execution | Foundational |
| [ADR-001h](ADR-001h-orchestration-feedback-loops.md) | Orchestration Feedback Loops | Foundational |

## Status Definitions

| Status | Meaning |
|--------|---------|
| **Accepted** | Decision is active and implemented |
| **Superseded** | Replaced by a newer ADR (linked) |
| **Deferred** | Decision postponed to a future milestone |
| **Foundational** | Early-stage exploration that informed later decisions |
| **Completed** | One-time action that has been executed |
