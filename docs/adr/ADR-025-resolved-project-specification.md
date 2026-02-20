# ADR-025: Resolved Project Specification

## Status
**Proposed** -- 2026-02-20

## Context

### The Problem

Several key pipeline stages (capability model, architecture decisions, MVP scope) store their output as raw strings in Burr state with no Pydantic model. Other stages do have structured models, but no shared mechanism exists to cross-reference IDs across stages. Every downstream consumer must independently parse raw strings and resolve references like `CAP-F-003` or `DEC-AUTH-001` back to their full definitions.

Concrete example: the capability model agent outputs JSON with `CAP-F-001`, `CAP-F-002`, etc. This gets stored as a raw string in Burr state (no `output_model` on the stage config). Story generation reads it as a string and passes it into `_build_shared_context()`, which concatenates it with other raw strings into one prose block. The skeleton agent then greps through that prose to extract CAP-* IDs for its `implements` field. Later, any exporter or coding agent receiving `STORY-005: implements ["CAP-F-003"]` must re-parse the same raw string to resolve that ID back to its full definition.

### What's Structured Today vs. What Isn't

Stages that set `output_model` on their `StageExecutionConfig` store JSON in Burr state (markdown is rendered only for disk persistence in `session/{stage-slug}/`). Three stages already benefit from this:

| Stage Output | Has Pydantic Model | JSON in Burr State | Notes |
|-------------|-------------------|--------------------|-------|
| Build/Buy Analysis | `BuildBuyAnalysisOutput` | Yes (`output_model`) | Deserialized directly by downstream stages |
| System Traits | `SystemTraitsOutput` | Yes (`output_model`) | Deserialized directly by downstream stages |
| Validation Summary | `ValidationSummaryOutput` | Yes (`output_model`) | Partial: scorer + narrator merge produce the model |
| Concept Anchor | `ConceptAnchor` | Yes | Stored as `concept_anchor_str` in state |
| Capability Model | None | No | Agent prompt defines a JSON schema, but output is stored as a raw string with no Pydantic validation |
| Architecture Decisions | None | No | Markdown only, `DEC-*` headers |
| MVP Scope | None | No | Markdown only |

The gap is in the three unstructured stages. Capability model, architecture decisions, and MVP scope lack Pydantic models and enter Burr state as raw strings. Every downstream consumer that needs to reference a `CAP-*` or `DEC-*` ID must independently parse these strings.

### Who Needs Resolved References

Four current or planned consumers must resolve capability/decision IDs to full definitions:

1. **Story generation** (today): The skeleton agent receives raw prose via `_build_shared_context()` and must extract CAP-*/DEC-* IDs to populate `implements`. Gets them from unstructured text, which is why `implements` currently mixes `CAP-F-*`, `CAP-NF-*`, and `DEC-*` in one flat list with no semantic distinction.

2. **Story validation** (today): Checks "does every CAP-* have at least one implementing story?" Must parse capability IDs from the raw `capability_model` string in Burr state. This accounts for ~100 lines of brittle parsing in `story_pipeline.py` that would shrink to ~10 with structured input.

3. **Coding agent** (roadmap Item 2): Cannot implement `STORY-005: implements CAP-F-003` without the full capability spec, acceptance criteria, and relevant architecture decisions.

4. **Spec-driven export** (roadmap Items 4, 5): OpenSpec maps capabilities to `specs/`, decisions to `design.md`. Spec Kit maps them to specifications and `constitution.md`. Both need resolved definitions, not just IDs.

Without a shared resolution layer, each consumer independently parses the same raw strings. Parse once, use everywhere.

### The Export Pipeline Is Already Broken

The existing `ExportableStory` model in `haytham/exporters/transformer.py` was built for the old story format (from the deprecated `haytham/phases/` module). It expects `labels`, `dependencies` (title-based), `description`, `acceptance_criteria` as separate dict keys. `StoryHybrid` has none of these. The transformer silently degrades: priority defaults to "medium", acceptance criteria returns `[]`, description returns `""`.

The `LAYER_NAMES` dict in `exporters/models.py` maps layers 1-4, while the actual pipeline produces layers 0-5. The transformer looks for `generated_stories.json`, a filename from the old format; the current pipeline writes `stories.json`.

The roadmap (Item 5, line 132 of `docs/roadmap.md`) explicitly states: "the story-only `ExportableStory` is insufficient for spec-driven formats."

### Relationship to ADR-022 Part 6 (Structured Output Envelope)

ADR-022 Part 6 proposes wrapping all agent outputs in a `StageOutput` envelope with `tldr`, `anchor_compliance`, `claims`, and `content` fields. That envelope is about metadata for validation. This ADR is about resolving cross-stage references into a coherent project specification. They are complementary: the envelope wraps individual stage outputs; the resolved spec assembles them.

## Decision

### Two-part approach: structure upstream outputs, then assemble

This ADR has two parts that work together:

1. **Structure the source.** Add `output_model` to the three unstructured stages (capability model, architecture decisions, MVP scope) so they store validated JSON in Burr state, not raw strings.

2. **Assemble the spec.** A deterministic (no LLM) assembly step deserializes structured outputs from Burr state, cross-references IDs, and produces two models: a `ProjectContext` for story generation input, and a `ResolvedProjectSpec` (context + stories) for coding agents and exporters.

Part 1 is a prerequisite for Part 2. By fixing the data at the source, the assembly step becomes trivial deserialization rather than fragile regex parsing. Every downstream consumer benefits immediately, not just the ones that go through the assembler.

### Part 1: Upstream Structured Output Models

Three new Pydantic models, one per unstructured stage. Each is set as `output_model` on the stage's `StageExecutionConfig`, following the same pattern as `BuildBuyAnalysisOutput` and `SystemTraitsOutput`.

```python
class CapabilityModelOutput(BaseModel):
    """Structured output for the capability-model stage.

    The capability model agent already outputs JSON matching this schema
    (defined in its prompt). This model validates and captures that output
    in Burr state instead of storing it as a raw string.

    NOTE: The agent prompt also produces summary, traceability, and metadata
    sections. These are captured here to avoid Pydantic validation errors,
    even though downstream consumers primarily use the capabilities field.
    """
    summary: CapabilitySummary | None = None
    capabilities: CapabilitiesContainer
    traceability: CapabilityTraceability | None = None
    metadata: CapabilityMetadata | None = None


class CapabilitySummary(BaseModel):
    system_name: str
    system_purpose: str
    primary_user_segment: str
    input_method: str | None = None
    mvp_scope_respected: bool = True


class CapabilitiesContainer(BaseModel):
    functional: list[FunctionalCapability]
    non_functional: list[NonFunctionalCapability]


class FunctionalCapability(BaseModel):
    id: str  # CAP-F-001
    name: str
    description: str
    acceptance_criteria: list[str]
    user_flow: str | None = None
    serves_scope_item: str | None = None
    rationale: str | None = None


class NonFunctionalCapability(BaseModel):
    id: str  # CAP-NF-001
    name: str
    description: str
    category: str | None = None
    requirement: str | None = None
    measurement: str | None = None
    rationale: str | None = None


class CapabilityTraceability(BaseModel):
    scope_items_covered: list[str] = []
    scope_items_not_covered: list[str] = []
    flows_covered: list[str] = []


class CapabilityMetadata(BaseModel):
    functional_count: int = 0
    non_functional_count: int = 0


class ArchitectureDecisionsOutput(BaseModel):
    """Structured output for the architecture-decisions stage.

    The architecture decisions agent already outputs JSON (via
    ARCHITECTURE_DECISIONS_PROMPT in actions.py). run_architecture_decisions()
    already parses it with extract_json_from_response(). This model
    captures that JSON in Burr state instead of converting it to markdown.
    """
    decisions: list[ArchitectureDecision]
    coverage_check: ArchitectureCoverageCheck | None = None
    summary: str | None = None


class ArchitectureDecision(BaseModel):
    id: str  # DEC-AUTH-001, DEC-DB-001
    name: str
    description: str
    rationale: str
    serves_capabilities: list[str]  # CAP-* IDs
    implements_recommendation: str | None = None  # Which Build/Buy rec this implements
    alternatives_considered: list[str] = []


class ArchitectureCoverageCheck(BaseModel):
    functional_capabilities_covered: list[str] = []
    non_functional_capabilities_covered: list[str] = []
    uncovered_capabilities: list[str] = []


class MvpScopeOutput(BaseModel):
    """Structured output for the mvp-scope stage.

    MVP scope is produced by a swarm (run_mvp_scope_swarm). See the
    "MVP Scope Swarm Aggregation Strategy" section below for how
    structured output is extracted from the 3-agent swarm.
    """
    summary: str  # TL;DR or first section
    in_scope: list[str]
    out_of_scope: list[str]
    success_criteria: list[str] = []
```

Each model follows the existing convention: JSON is stored in Burr state for programmatic access, and the `StageExecutor` renders markdown for disk persistence in `session/{stage-slug}/`.

**Agent prompt changes:** The capability model agent already outputs JSON matching this schema (the prompt defines the schema, no prompt change needed). The architecture decisions agent already outputs JSON (parsed by `extract_json_from_response()` in `run_architecture_decisions()`), but the result is converted to markdown before storage. The change is to keep the JSON in Burr state instead. The MVP scope swarm requires a new aggregation strategy (see below).

### JSON Complexity Assessment

Complex nested JSON is a known failure mode for LLMs. Before implementation, each model's complexity was assessed against `BuildBuyAnalysisOutput`, the most complex structured output that already works in production (3 levels of nesting, 6 sub-models, an enum, list-of-objects fields).

| Model | Nesting Depth | Field Types | Complexity vs Baseline |
|-------|--------------|-------------|----------------------|
| `MvpScopeOutput` | 1 (root > flat string lists) | `str`, `list[str]` only | Well below baseline |
| `ArchitectureDecisionsOutput` | 2 (root > decisions > object) | `str`, `list[str]`, optional `str` | Below baseline |
| `CapabilityModelOutput` | 3 (root > capabilities > functional > object) | `str`, `list[str]`, optional sub-models | Comparable to baseline |

All three models are at or below the complexity of what already works. The primary risk is not JSON complexity but **schema mismatch**: when the Pydantic model expects a field the agent doesn't produce (or vice versa), validation hard-fails at runtime. This is strictly better than silent degradation (fail-fast), but must be caught in testing.

**Sample outputs for each model are provided in Appendix A.**

### MVP Scope Swarm Aggregation Strategy

The MVP scope stage is produced by a 3-agent Swarm (`mvp_scope_core` > `mvp_scope_boundaries` > `mvp_scope_flows`). Today, their outputs are concatenated as raw text (`"\n\n".join(outputs)` in `run_mvp_scope_swarm()`). Unlike the other two stages, there is no single agent to attach a `structured_output_model` to.

Three options were considered:

**Option A: Synthesizer agent.** Add a 4th agent that receives the combined prose and produces `MvpScopeOutput` JSON. Clean separation but adds LLM latency and cost for what is essentially extraction.

**Option B: Per-agent structured sections.** Each swarm agent produces its own structured section (core produces `summary`, boundaries produces `in_scope`/`out_of_scope`, flows produces `success_criteria`). A deterministic merge step assembles `MvpScopeOutput` from the parts. No extra LLM call, but requires prompt changes to all 3 agents and careful handoff design.

**Option C: Post-swarm deterministic extraction.** Keep the swarm producing prose. After the swarm completes, use a lightweight extraction step (regex or `extract_json_from_text()`) to parse the combined output into `MvpScopeOutput`. Accepts that one parser exists, but it is centralized (one parser, not N consumers).

**Chosen: Option B** (per-agent structured sections with deterministic merge). This aligns with the ADR's principle of "structure at the source" without adding agent cost. Each swarm agent already has a well-defined responsibility (core, boundaries, flows) that maps cleanly to `MvpScopeOutput` fields. The merge step is a pure function that validates completeness.

Implementation: each agent's prompt is updated to output a small JSON block alongside its prose (or as its sole output). `run_mvp_scope_swarm()` extracts the structured section from each agent's result and merges them into `MvpScopeOutput`. The prose is still concatenated for session persistence rendering.

### Part 2: Assembled Project Context and Resolved Spec

After the HOW phase completes, before story generation begins, a deterministic assembly step deserializes structured outputs from Burr state and produces a `ProjectContext`. This is not a new pipeline stage with its own agent. It is programmatic deserialization and cross-referencing.

In code terms: each phase is a separate workflow (`WorkflowType`), and transitions between phases are governed by entry validators (`_VALIDATORS` in `entry_conditions.py`). The assembly step runs inside `run_story_generation()` in `story_pipeline.py`, after the `StoryGenerationEntryValidator` passes but before `run_story_swarm()` is called.

```
Phase 1 (WHY)  ->  Phase 2 (WHAT)  ->  Phase 3 (HOW)
                                            |
                                   StoryGenerationEntryValidator passes
                                            |
                                   run_story_generation() begins
                                            |
                                   [Assembly] -- assemble_project_context(state)
                                            |
                                   ProjectContext
                                            |
                                   run_story_swarm(context) -- Phase 4 (STORIES)
                                            |
                                   [Attach stories] -- build_resolved_spec(context, stories)
                                            |
                                   ResolvedProjectSpec
                                            |
                                   Exporters / coding agent
```

### Model Definitions

Two models with a clear lifecycle boundary: `ProjectContext` is the input to story generation, `ResolvedProjectSpec` is the output consumed by coding agents and exporters.

```python
class ProjectContext(BaseModel):
    """Assembled context from phases 1-3, consumed by story generation.

    Produced deterministically from Burr state. All fields are resolved
    from structured output models (no string parsing). Passed into
    run_story_swarm() as the single input, replacing 5 raw strings.
    """

    # Identity
    system_goal: str
    concept_anchor: ConceptAnchor | None

    # From Phase 1 (WHY)
    validation_verdict: str  # GO | PIVOT | NO-GO
    risk_level: str  # HIGH | MEDIUM | LOW

    # From Phase 2 (WHAT) -- deserialized from MvpScopeOutput, CapabilityModelOutput
    mvp_scope: MvpScopeOutput
    capabilities: CapabilityModelOutput

    # From Phase 3 (HOW) -- deserialized from existing output_models + new one
    architecture_decisions: ArchitectureDecisionsOutput
    build_buy_analysis: BuildBuyAnalysisOutput
    system_traits: SystemTraitsOutput


class ResolvedProjectSpec(BaseModel):
    """Full project specification with stories, for coding agents and exporters.

    Built by attaching story generation output to an existing ProjectContext.
    Every field is populated. No Optional/None lifecycle ambiguity.
    """

    # All fields from ProjectContext (flattened or nested, see implementation)
    context: ProjectContext

    # From Phase 4 (STORIES) -- always populated
    stories: list[StoryHybrid]

    def resolve_capability(self, cap_id: str) -> FunctionalCapability | NonFunctionalCapability | None:
        """Look up a capability by ID (e.g., CAP-F-003)."""
        for cap in self.context.capabilities.capabilities.functional:
            if cap.id == cap_id:
                return cap
        for cap in self.context.capabilities.capabilities.non_functional:
            if cap.id == cap_id:
                return cap
        return None

    def resolve_decision(self, dec_id: str) -> ArchitectureDecision | None:
        """Look up a decision by ID (e.g., DEC-AUTH-001)."""
        for dec in self.context.architecture_decisions.decisions:
            if dec.id == dec_id:
                return dec
        return None
```

The split addresses a concrete problem: with a single model, `stories: list[StoryHybrid] | None = None` means every consumer must runtime-check whether stories are populated. Story generation never uses stories (it produces them). Coding agents always need stories (they consume them). Two models make the contract explicit at the type level.

### How Story Generation Consumes It

`run_story_swarm()` currently receives five raw strings. With `ProjectContext`:

- The skeleton agent receives structured capability and decision lists, not prose to grep through. This enables clean separation of `implements` (capabilities) from `uses` (decisions).
- Detail agents receive system traits directly, allowing them to adapt sections to the actual tech stack rather than inferring it from prose context.
- `_build_shared_context()` renders the `ProjectContext` to the prompt format the agents expect, but the source data is structured, not string-concatenated.

### How Exporters and Coding Agents Consume It

After story generation completes, `build_resolved_spec(context, stories)` produces a `ResolvedProjectSpec`. Any consumer receives the full spec and can:

- Resolve `STORY-005.implements = ["CAP-F-003"]` to the full `FunctionalCapability` by ID lookup
- Map capabilities to OpenSpec `specs/` or Spec Kit specifications
- Map decisions to `design.md` or technical approach docs
- Pass system traits as structured data to a coding agent
- Generate correct dependency chains using story `depends_on` IDs

No consumer needs to parse raw Burr state strings. No consumer needs to check whether stories are populated.

### What This Does NOT Include

- **No new LLM agent.** The assembly step is deterministic Python: deserialize JSON from Burr state, build Pydantic models.
- **No changes to session persistence.** Markdown files in `session/{stage-slug}/` remain unchanged. The `StageExecutor` already handles rendering structured output to markdown for disk persistence.
- **No structured output for detail agents.** Story content remains a freeform markdown blob in `StoryHybrid.content`. Per ADR-022's finding, forcing structured output on detail agents risks quality regression. The resolved spec structures the metadata envelope, not the creative content.
- **No entity references (ENT-*) yet.** The current pipeline does not generate entities. The schema can accommodate `touches: list[str]` on stories when entities are introduced, but this ADR does not add entity generation.

### Re-assembly Strategy

The project context and resolved spec are **re-assembled from Burr state each time a consumer needs it**, not cached. `assemble_project_context(state)` is a pure function: same Burr state in, same context out. This means:

- Story generation calls `assemble_project_context(state)` at the start of `run_story_generation()`.
- Exporters call `build_resolved_spec(assemble_project_context(state), stories)` independently when they run.
- The assembly cost is low (JSON deserialization only, no parsing or LLM calls), so re-assembly is acceptable.
- No new persistence format is introduced. If caching becomes necessary (e.g., for performance), the context can be serialized to Burr state as JSON, but this is not required initially.

### Backward Compatibility

After Part 1 lands, all six upstream stages will have `output_model` set, so the assembly step only deserializes JSON from Burr state.

For sessions completed before Part 1 (where capability model, architecture decisions, and MVP scope are raw strings), the assembly function includes a fallback path: if `json.loads()` fails, it wraps the raw string in a minimal model (e.g., `MvpScopeOutput(summary=raw_string, in_scope=[], out_of_scope=[])`). This is a transitional measure. These sessions will have reduced data quality in the resolved spec (no individual capability lookups, no decision cross-references), but story generation and validation will still function.

**Removal deadline:** The fallback path is removed in the PR immediately following Part 2 completion. It must not persist beyond one release cycle. A `# TODO(ADR-025): Remove fallback path` comment marks the code for removal. If sessions from before Part 1 still need to run, they should be re-run through the updated pipeline rather than kept alive through fallback code.

### Interaction with `required_context`

The `StageMetadata.required_context` mechanism and `context_builder.build_context_summary()` are used by the standard agent execution path (`run_agent` in `StageExecutor`). Story generation already bypasses this: `run_story_generation()` is a programmatic executor that reads directly from Burr state. The project context formalizes this bypass, replacing ad-hoc `state.get()` calls with a structured assembly step. No changes to `required_context` or the standard agent path are needed.

## Alternatives Considered

### A1: Each exporter resolves references independently

No intermediate schema. Each exporter reads Burr state directly.

**Rejected because:** With 3+ planned consumers (coding agent, OpenSpec, Spec Kit) plus story validation, the reference resolution logic would be duplicated 4+ times. Each implementation parses the same raw strings with the same failure modes. A bug fix in parsing must be applied everywhere.

### A2: Post-process after story generation only

Build the resolved spec as an export-time transformation, not upstream of stories.

**Rejected because:** Story generation is itself a consumer of the resolved data. Today `_build_shared_context()` concatenates raw strings and the skeleton agent re-parses them. Placing the resolution upstream means story generation benefits from structured input too, improving traceability (`implements` vs `uses` separation) and enabling system traits to flow into detail agents.

### A3: Build parsers for unstructured upstream outputs instead of structuring them

Work with the current agent output formats. Build regex parsers for capability model JSON, architecture decisions markdown, and MVP scope markdown. The assembly step handles format variations with fallback behavior (ID-only resolution when parsing fails).

**Rejected because:** This builds workarounds at the boundary instead of fixing the source. The architecture decisions parser (regex extraction of `## DEC-AUTH-001: ...` sections) is fragile and acknowledged as "the riskiest part." It produces code known to be temporary, since structured output on these stages is the eventual fix anyway. The Constitution's "Close the Loop" principle argues against building infrastructure you plan to replace. Structuring the upstream outputs is a smaller per-step effort and immediately benefits all downstream consumers (story validation, story generation, exporters, coding agents), not just the ones that go through the assembler.

### A4: Single model with Optional stories field

Use one `ResolvedProjectSpec` with `stories: list[StoryHybrid] | None = None` that serves both story generation (pre-stories) and coding agents (post-stories).

**Rejected because:** This creates a lifecycle ambiguity. Story generation never uses stories (it produces them). Coding agents always need stories (they consume them). A single model with an Optional field forces every consumer to runtime-check whether stories are populated, and the type system cannot distinguish between the two lifecycle phases. Two models (`ProjectContext` and `ResolvedProjectSpec`) make the contract explicit: story generation receives `ProjectContext`, coding agents receive `ResolvedProjectSpec` where `stories` is always populated.

### A5: Add structured fields to StoryHybrid (fully structured stories)

Replace the `content: str` blob with structured fields for acceptance criteria, files to create, verification commands, etc.

**Rejected because:** ADR-022 analysis found that structured output constrains agent flexibility for creative specification content. Each layer's detail agent produces different sections (Layer 0: data models; Layer 4: page structure; Layer 5: subscription channels). A flat model forces either a union type with 6 variants or empty optional fields on most stories. The hybrid model (`StoryHybrid`) was a deliberate design choice, not a compromise.

## Implementation Touchpoints

### Part 1: Upstream Structured Output

| Component | Change | Risk |
|-----------|--------|------|
| New: `haytham/agents/worker_capability_model/capability_model_models.py` | `CapabilityModelOutput` and related models. Model must include `summary`, `traceability`, `metadata` sections the agent already produces, not just `capabilities` | Near-zero. Agent already outputs matching JSON. Config one-liner |
| New: `haytham/agents/worker_architecture/architecture_models.py` | `ArchitectureDecisionsOutput` and related models. Model must include `implements_recommendation`, `coverage_check`, `summary` fields the agent already produces | Low. Agent already outputs JSON via `extract_json_from_response()`. Change is to keep JSON in state instead of converting to markdown |
| New: `haytham/agents/worker_mvp_scope/mvp_scope_models.py` | `MvpScopeOutput` model | Low. New model file |
| `haytham/workflow/stages/configs.py` | Add `output_model` to `capability-model`, `architecture-decisions`, `mvp-scope` stage configs | Low. Three one-line additions |
| Capability model prompt | No change needed (already outputs JSON matching schema) | Near-zero |
| Architecture decisions executor | `run_architecture_decisions()` stops converting JSON to markdown, stores JSON directly. No agent prompt change needed | Low. Logic removal, not addition |
| MVP scope swarm | Update 3 swarm agent prompts to produce per-agent structured sections. Update `run_mvp_scope_swarm()` merge logic. See "MVP Scope Swarm Aggregation Strategy" | Medium-High. Prompt changes to 3 agents + merge redesign. Test with reasoning model first |

### Part 2: Assembly and Resolved Spec

| Component | Change | Risk |
|-----------|--------|------|
| New: `haytham/workflow/resolved_spec.py` | `ProjectContext`, `ResolvedProjectSpec`, `assemble_project_context(state)`, `build_resolved_spec(context, stories)` | Low. New file, pure functions, no existing code modified |
| `haytham/workflow/stages/story_pipeline.py` | `run_story_generation()` calls `assemble_project_context()` and passes `ProjectContext` to `run_story_swarm()` | Medium. Changes the story generation input path |
| `haytham/agents/worker_story_generator/story_swarm.py` | `run_story_swarm()` accepts `ProjectContext` instead of 5 raw strings. `_build_shared_context()` renders from structured data | Medium. Signature change, but behavior should be equivalent |
| `haytham/exporters/transformer.py` | Replace broken `ExportableStory` mapping with `ResolvedProjectSpec`-based transformation | Low. Current transformer is already broken for `StoryHybrid` format |
| `haytham/exporters/models.py` | `ExportableStory` fields updated or replaced. Consider `ExportableProject` that wraps the full spec | Low. Current model is unused/broken |

### Sequencing

Steps are ordered by risk, not alphabetically. Each step is validated before the next begins. Do not parallelize 1a/1b/1c: ship the lowest-risk change first and prove the pattern.

```
Part 1 — Structure upstream outputs (risk-ordered, validate each before proceeding)

  1a. capability-model [NEAR-ZERO RISK]
      - Define CapabilityModelOutput (model matches what agent already produces)
      - Add output_model to capability-model config (one-line change)
      - No prompt change needed
      - Validate: run gym leaderboard session, confirm Pydantic accepts agent output

  1b. architecture-decisions [LOW RISK]
      - Define ArchitectureDecisionsOutput
      - Change run_architecture_decisions() to keep JSON in state instead of
        converting to markdown (agent already outputs JSON, parsed by
        extract_json_from_response())
      - Validate: run gym leaderboard session, confirm model captures all fields

  1c. mvp-scope [MEDIUM-HIGH RISK]
      - Define MvpScopeOutput
      - Update 3 swarm agent prompts for per-agent structured sections (Option B)
      - Update run_mvp_scope_swarm() to merge structured sections
      - Validate: run gym leaderboard session with BEDROCK_REASONING_MODEL_ID first.
        If reasoning model produces clean structured output, heavy model will too.
        If reasoning model struggles, simplify the per-agent schema before proceeding.

  1d. Pre-validate all three models against real gym leaderboard outputs
      Gate: Part 2 does not begin until all three models pass validation
      against at least 2 different idea inputs (e.g., T1 gym leaderboard + one other)

Part 2 — Assembly and wiring (changes pipeline input paths)
  2a. Define ProjectContext, ResolvedProjectSpec, assembly functions
  2b. Wire into story generation (replace 5 raw strings with ProjectContext)
  2c. Update story validation to use ProjectContext (eliminate ~100 lines of parsing)
  2d. Update exporters to consume ResolvedProjectSpec
  2e. Validate end-to-end with gym leaderboard session
```

Steps 2a-2b are the critical path. Step 2c is a cleanup that can happen in the same PR or separately. Step 2d can proceed in parallel with 2b-2c once the models exist.

## Consequences

**Positive:**
- All six upstream stages now have `output_model`, making the pipeline uniformly structured
- Story generation receives structured input, enabling clean `implements`/`uses` separation
- System traits flow into story generation for the first time
- Story validation parsing (~100 lines) collapses to structured deserialization (~10 lines)
- All downstream consumers (exporters, coding agent) get resolved references without re-parsing
- Export pipeline fixed (currently broken for `StoryHybrid` format)
- Foundation for roadmap Items 2, 4, 5
- Type-safe lifecycle: `ProjectContext` (no stories) vs `ResolvedProjectSpec` (always has stories)

**Negative:**
- MVP scope swarm aggregation is the highest-risk change: 3 agent prompts need updating and merge logic needs redesign. Must be validated with reasoning model before heavy model. See "MVP Scope Swarm Aggregation Strategy"
- Schema mismatches between Pydantic models and actual agent output will cause hard validation failures at runtime. This is better than silent degradation (fail-fast), but requires pre-validation against real gym leaderboard outputs before wiring into the pipeline
- Story generation signature changes from 5 strings to 1 structured object. Existing tests need updating
- Backward compatibility for pre-Part-1 sessions requires a fallback path (removal deadline: one release cycle after Part 2)

**Neutral:**
- Does not change session persistence format (markdown files in `session/{stage-slug}/` are unchanged)
- Does not require ADR-022 Part 6 as a prerequisite (the structured output envelope is complementary)
- Detail agent story content remains freeform markdown (`StoryHybrid.content`)

## References

- [Issue #5: Define execution contract schema](https://github.com/arslan70/haytham/issues/5)
- [ADR-022: Concept Fidelity and Pipeline Integrity](ADR-022-concept-fidelity-pipeline-integrity.md), Part 6 (Structured Output Envelope)
- [ADR-016: Four-Phase Workflow](ADR-016-four-phase-workflow.md)
- [Roadmap Items 1-5](../roadmap.md)
- `haytham/agents/worker_story_generator/story_generation_models.py` (StoryHybrid, hybrid model rationale)
- `haytham/agents/worker_build_buy_advisor/build_buy_models.py` (BuildBuyAnalysisOutput, pattern to follow)
- `haytham/agents/worker_system_traits/system_traits_models.py` (SystemTraitsOutput, pattern to follow)
- `haytham/exporters/transformer.py` (broken ExportableStory mapping)
- `haytham/workflow/stages/configs.py` (stage configs, `output_model` usage)
- `haytham/phases/workflow_2/actions.py` (ARCHITECTURE_DECISIONS_PROMPT, existing JSON output format)

## Appendix A: Sample JSON Outputs

These samples show the exact JSON complexity each agent must produce. They are based on the Gym Leaderboard test idea and reflect the actual prompt schemas. Use these to validate that the Pydantic models match agent output before wiring into the pipeline.

### A1: CapabilityModelOutput (Nesting depth: 3, matches existing agent output)

```json
{
  "summary": {
    "system_name": "GymBoard",
    "system_purpose": "Community fitness leaderboard for workout accountability",
    "primary_user_segment": "People who track workouts and want social accountability",
    "input_method": "Manual workout entry",
    "mvp_scope_respected": true
  },
  "capabilities": {
    "functional": [
      {
        "id": "CAP-F-001",
        "name": "Workout Logging",
        "description": "Users can log completed exercises with sets and reps",
        "serves_scope_item": "Manual workout logging with exercise + sets + reps",
        "user_flow": "Flow 1",
        "acceptance_criteria": [
          "User can select exercise from list",
          "User can enter sets and reps for each set",
          "Workout is saved and visible in history"
        ],
        "rationale": "Core input mechanism for the gamification loop"
      },
      {
        "id": "CAP-F-002",
        "name": "Leaderboard Viewing",
        "description": "Users can view ranked leaderboard by workout volume",
        "serves_scope_item": "Weekly leaderboard ranked by total volume",
        "user_flow": "Flow 2",
        "acceptance_criteria": [
          "Leaderboard shows top users by weekly volume",
          "User can see their own rank",
          "Leaderboard resets weekly"
        ],
        "rationale": "Core output that drives competitive engagement loop"
      }
    ],
    "non_functional": [
      {
        "id": "CAP-NF-001",
        "name": "Leaderboard Freshness",
        "description": "Leaderboard updates within 30 seconds of new workout entry",
        "category": "performance",
        "requirement": "Leaderboard reflects new data within 30s",
        "measurement": "Time from workout save to leaderboard update",
        "rationale": "Real-time feel drives competitive engagement"
      }
    ]
  },
  "traceability": {
    "scope_items_covered": [
      "Manual workout logging with exercise + sets + reps",
      "Weekly leaderboard ranked by total volume"
    ],
    "scope_items_not_covered": [],
    "flows_covered": ["Flow 1", "Flow 2"]
  },
  "metadata": {
    "functional_count": 2,
    "non_functional_count": 1
  }
}
```

### A2: ArchitectureDecisionsOutput (Nesting depth: 2, agent already outputs this format)

```json
{
  "decisions": [
    {
      "id": "DEC-AUTH-001",
      "name": "Supabase Email/Password Auth",
      "description": "Use Supabase Auth with email/password signup and anonymous handle generation at registration",
      "rationale": "Supabase Auth is already recommended in build/buy. Email/password is simplest for MVP. Anonymous handles avoid PII collection.",
      "serves_capabilities": ["CAP-F-001", "CAP-NF-001"],
      "implements_recommendation": "Supabase Auth",
      "alternatives_considered": [
        "Auth0 - more features but additional vendor and cost",
        "Custom JWT - more control but significant build effort for MVP"
      ]
    },
    {
      "id": "DEC-DB-001",
      "name": "Supabase PostgreSQL Schema",
      "description": "Three core tables: users, workouts, leaderboard_cache with row-level security policies",
      "rationale": "Supabase Postgres gives us RLS for multi-tenant security with zero backend code. Leaderboard cache avoids expensive aggregation queries.",
      "serves_capabilities": ["CAP-F-001", "CAP-F-002", "CAP-NF-001"],
      "implements_recommendation": "Supabase Database",
      "alternatives_considered": [
        "Firebase Firestore - good real-time but weaker relational queries for leaderboard aggregation",
        "PlanetScale - MySQL-based, less ecosystem fit with Supabase Auth"
      ]
    },
    {
      "id": "DEC-REALTIME-001",
      "name": "Supabase Realtime for Leaderboard Updates",
      "description": "Subscribe to leaderboard_cache table changes via Supabase Realtime channels",
      "rationale": "Meets CAP-NF-001 30-second freshness requirement without polling. Supabase Realtime is included in the free tier.",
      "serves_capabilities": ["CAP-F-002", "CAP-NF-001"],
      "implements_recommendation": "Supabase Realtime",
      "alternatives_considered": [
        "Client-side polling every 30s - simpler but wastes bandwidth",
        "Server-sent events - requires custom backend"
      ]
    }
  ],
  "coverage_check": {
    "functional_capabilities_covered": ["CAP-F-001", "CAP-F-002"],
    "non_functional_capabilities_covered": ["CAP-NF-001"],
    "uncovered_capabilities": []
  },
  "summary": "Supabase-first approach leveraging auth, database, and real-time from one vendor to minimize integration effort"
}
```

### A3: MvpScopeOutput (Nesting depth: 1, simplest of the three)

```json
{
  "summary": "A community fitness leaderboard that lets gym-goers log workouts and compete weekly on total volume lifted",
  "in_scope": [
    "Manual workout logging with exercise selection, sets, and reps",
    "Weekly leaderboard ranked by total volume (sets x reps x weight)",
    "Anonymous handles (no real names required)",
    "Basic workout history view"
  ],
  "out_of_scope": [
    "Social features (following, messaging, comments)",
    "Exercise form tracking or video recording",
    "Nutrition or diet tracking",
    "Trainer or coach management features",
    "Custom exercise creation",
    "Mobile native app (web-only for MVP)"
  ],
  "success_criteria": [
    "User can log a workout in under 60 seconds",
    "Leaderboard updates within 30 seconds of new entry",
    "Works on mobile browser without app install"
  ]
}
```

**Key observation:** `MvpScopeOutput` is by far the simplest JSON (flat string lists, nesting depth 1). The risk for this stage is not JSON complexity but the swarm aggregation strategy (3 agents must coordinate to produce it). See "MVP Scope Swarm Aggregation Strategy."
