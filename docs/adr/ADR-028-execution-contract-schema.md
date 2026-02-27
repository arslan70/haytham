# ADR-028: Execution Contract Schema

## Status
**Accepted** - 2026-02-27

## Context

### The Problem

Phase 4 story output is a mix of structured metadata (`StoryHybrid` Pydantic model) and freeform markdown content. The `implements` field mixes capability references (`CAP-F-*`, `CAP-NF-*`) with architecture decision references (`DEC-*`). Acceptance criteria live as unstructured text inside the `content` markdown field.

Downstream consumers (coding agent #6, OpenSpec #8, Spec Kit #9) each need to:
- Split capabilities from decisions for traceability validation
- Parse acceptance criteria into structured Gherkin for test generation
- Access system traits for infrastructure decisions
- Validate story dependencies

Without a contract, each consumer would re-implement this parsing independently.

### Constraints

**ADR-025 complexity ceiling:** Complex nested JSON is a known LLM failure mode. The `StoryHybrid` model was deliberately designed with freeform `content` to avoid constraining agent output ([ADR-022](ADR-022-story-generation-hybrid.md)). The contract must be built by deterministic code, not by asking the LLM for richer structured output.

## Decision

Add an `ExecutionContract` as a deterministic post-processing layer on top of existing story generation output. The LLM output (`StoryHybrid`) stays unchanged.

The contract is assembled by code that:
1. Loads stories from `stories.json` (already produced by story generation)
2. Splits the mixed `implements` field by prefix: `CAP-*` goes to `implements`, `DEC-*` goes to `uses`
3. Parses acceptance criteria from story `content` using string-based pattern matching (checkbox, fenced Gherkin, unfenced Gherkin formats)
4. Extracts system traits from the session's `system-traits` stage output
5. Writes a single `execution_contract.json` to the session directory

### Pipeline Integration

The contract is generated via the `additional_save` callback on the `dependency-ordering` stage, which already runs after all stories are ordered. A composed callback runs contract generation first, then the existing backlog draft creation.

### Schema Versioning

Starts at `1.0`. Major version increments on breaking changes (field removals, type changes). Minor version increments on additive changes (new optional fields).

## Alternatives Considered

| Alternative | Why Rejected |
|---|---|
| LLM-generated structured AC | ADR-025: complex nested JSON is an LLM failure mode |
| Modify StoryHybrid to split CAP/DEC | Breaks existing consumers of the model; the split is a presentation concern |
| Per-consumer parsing | Duplicates logic across 3+ consumers; inconsistency risk |
| New pipeline stage | Overkill for deterministic post-processing with no LLM calls |

## Consequences

**Positive:**
- Single machine-readable contract for all downstream consumers
- Traceability tags (CAP/DEC split) are validated structurally
- Acceptance criteria are parsed once, consistently
- JSON Schema available for external validation without importing Haytham code

**Negative:**
- Gherkin parser must handle whatever formats the detail agents produce (three known formats, fallback for unknown)
- Contract must be regenerated if story output changes (tied to `additional_save` callback)

## Key Files

| File | Role |
|---|---|
| `haytham/workflow/contracts/execution_contract.py` | Pydantic models |
| `haytham/workflow/contracts/gherkin_parser.py` | AC extraction from markdown |
| `haytham/workflow/contracts/assembler.py` | Contract assembly from stories + session |
| `haytham/workflow/stages/story_pipeline.py` | `save_execution_contract()` callback |
| `haytham/workflow/stages/configs.py` | Composed `additional_save` on dependency-ordering |
| `docs/architecture/execution-contract-schema.json` | Generated JSON Schema |
| `tests/test_execution_contract.py` | 38 unit tests |
