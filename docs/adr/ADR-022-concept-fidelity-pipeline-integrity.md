# ADR-022: Concept Fidelity & Pipeline Integrity

## Status
**Proposed**, 2026-02-01
**Revised**, 2026-02-02 (critical review: enforcement mechanism, alternatives reassessment, measurement strategy)
**Revised**, 2026-02-03 (incorporated empirical findings from "Towards a Science of Scaling Agent Systems")
**Revised**, 2026-02-04 (added swarm-based verification architecture, empirical drift validation with anchor)
**Revised**, 2026-02-05 (added confidence scoring and ambiguity clarification for anchor invariants)

## Context

### The Problem

A full stage-by-stage QA review of the Genesis pipeline (using a real input, a psychologist's "Power of 8" wish-exchange app) revealed that the system suffers from **progressive concept degradation**. The original idea enters Stage 1 with distinctive, specific features and exits Stage 10 as a generic product bearing little resemblance to the founder's vision.

This is not a single-agent failure. It is a **systemic pipeline problem** where individually reasonable stages compound small losses into total concept drift.

### What the QA Review Found

**Input idea.** A psychologist wants an app for his existing patients where eight people gather in online sessions: one receiver with a specific need (health, finance, happiness) and seven givers who send good wishes. Based on "The Power of 8" book.

**Key features of the idea.** Closed community (existing patients only), 1:7 receiver/giver structure, live online sessions, psychologist as orchestrator, specific spiritual/psychological practice.

**What the pipeline produced.** A generic async encouragement board with open registration, no sessions, no group structure, no psychologist role, no 1:7 mechanic, plus 20 stories across 4 different frontend frameworks.

### Observed Systemic Issues

The QA review identified issues across all 10 stages. These collapse into **six systemic failure modes**:

---

#### S1: Progressive Concept Genericization

Each stage strips away one distinctive feature and replaces it with a generic startup equivalent:

| Stage | What Was Lost | What Replaced It |
|-------|--------------|-----------------|
| 1 (Idea Analysis) | Spiritual wish-exchange practice | "Interconnected recovery networks" |
| 1 (Idea Analysis) | "For his existing patients" (closed community) | Generic user segments |
| 4 (Validation Summary) | Single psychologist | "Therapists seeking client engagement tools" (B2B SaaS) |
| 5 (MVP Scope) | 1:7 session structure | Post-and-respond message board |
| 5 (MVP Scope) | Live online sessions | Async text exchange |
| 5 (MVP Scope) | Psychologist as orchestrator | No admin role |
| 7 (System Traits) | Real-time group sessions | `realtime: false` |

**Root cause.** Agents are trained on startup patterns and default to the most common template (SaaS platform, open registration, async CRUD) when the input doesn't match familiar patterns. There is no mechanism to flag when an agent's output has dropped a distinctive feature from the original idea.

---

#### S2: Fabrication & Hallucination Without Grounding Enforcement

Three types of fabrication were observed:

1. **Invented statistics presented as validated.** "68% of therapists report insufficient tools" tagged `[validated]` with no source (Stage 2). "Increase resilience by 40%" (Stage 1). Market sizes that change between stages ($12B → $4.3B).

2. **Invented claims attributed to the founder.** Risk assessment (Stage 3) fabricated claims the founder never made ("minimal technical complexity," "subscription revenue model," "will scale beyond patient base") then assessed those phantom claims.

3. **Completely wrong competitor analysis.** Stage 2 returned gift registry platforms (Giftster, Elfster) because the agent confused "good wishes" with "wishlists." The mandatory bias check endorsed this result.

**Root cause.** Agents can generate any text with no post-hoc grounding validation. Self-check sections in prompts are instructions to the LLM, not programmatic verification. The `[validated]` tag system is cosmetic; nothing actually validates.

---

#### S3: Inter-Stage Contradiction Without Detection

Stages 7, 8, and 9 directly contradicted each other on real-time requirements:

| Stage | Position on Real-Time |
|-------|--------------------|
| 7 (System Traits) | `realtime: false` - "MVP focuses on manual entry and viewing wishes later" |
| 8 (Build/Buy) | Lists "Real-time updates" as a database requirement, recommends Supabase for "real-time subscriptions" |
| 9 (Architecture) | Creates DEC-REALTIME-001 for real-time subscriptions |

None of the three stages flagged the contradiction. Each made a locally reasonable decision in isolation.

**Root cause.** Each stage validates only against its immediate inputs, never against sibling or downstream stages. There is no mechanism for a downstream stage to formally challenge or override an upstream decision.

---

#### S4: Context Handoff Information Loss

The context building mechanism (`_build_context_summary()`) extracts only the first line (max 200 characters) from each prior stage's output. Custom context builders truncate at 2,000 characters.

This means:
- **The 1:7 structure** (mentioned in the body of Stage 1's output, not the first line) was lost before Stage 2 even ran.
- **"For his existing patients"** (a clause in the middle of the idea analysis) was truncated away.
- By Stage 5, the MVP scope agent received a 200-character summary of a nuanced idea analysis, losing all distinctive details

**Root cause.** Token limit management through aggressive truncation. The system prioritizes fitting within context windows over preserving critical information. There is no concept of "must-not-lose" data points that should survive truncation.

---

#### S5: Self-Check Mechanisms That Don't Work

Multiple agents include self-check sections in their prompts:
- Competitor analysis has a "Bias Check" that endorsed gift registries as correct competitors.
- Capability model checks `mvp_scope_respected: true`, which was technically true, but the scope had already lost the core concept.
- Risk assessment counts its own claims but miscounted (stated 2/3/3/1, actual was 3/3/3/0).

**Root cause.** Self-checks are prompt instructions, not programmatic validations. An LLM asked "did you do this correctly?" will almost always say yes, especially when the error is a systemic drift it can't detect (like concept fidelity loss across stages it hasn't seen).

---

#### S6: Appetite-to-Output Mismatch

MVP Scope declared a "Small" appetite (1-2 weeks). Story generation produced 20 stories referencing 4 different frontend frameworks (Vite, Next.js, Vue, Astro), a 6-8 week project.

**Root cause.** The story generation agent has no appetite constraint. The appetite is a field in the MVP scope output but is not programmatically enforced as a bound on story count or complexity. The story skeleton prompt suggests "15-25 stories" regardless of appetite.

---

### Codebase Reality: Output Format Constraints

A critical factor in evaluating solutions is the current output format. Most agents produce **freeform markdown**. Even stages that use structured output (Pydantic models like `ValidationSummaryOutput`, `BuildBuyAnalysisOutput`) have their output converted to markdown by `_extract_agent_output()` before entering the Burr pipeline state. All stage outputs are stored as markdown files in `session/{stage-slug}/`.

This means:
- **"Programmatic validators" that compare structured fields don't have structured fields to compare.** Detecting whether Stage 8's prose contradicts Stage 7's `realtime: false` requires parsing natural language, not comparing dict keys.
- **The mechanical/semantic split assumed by earlier analysis doesn't hold.** S3 (inter-stage contradiction) was classified as "mechanical," but comparing two markdown paragraphs for semantic contradiction is an LLM task, not a regex task.
- **Self-reported structured metadata (e.g., `[validated]` tags) already failed.** Any enforcement mechanism that relies on agents correctly self-reporting compliance in freeform text is a variant of S5.


This reality directly shapes the decision: enforcement mechanisms must either (a) change agent outputs to structured formats that programmatic validators can inspect, or (b) accept that validation of freeform markdown requires LLM judgment.

---

### Empirical Grounding: Multi-Agent Scaling Research

Recent research on scaling agent systems provides empirical validation for several problems identified in the QA review. Kim et al. (2025), "Towards a Science of Scaling Agent Systems" (arXiv:2512.08296), studied five multi-agent architectures across four benchmarks and quantified the failure modes we observe qualitatively.

#### Relevant Findings

| ADR-022 Problem | Research Finding | Implication |
|----------------|------------------|-------------|
| **S1: Concept Genericization** | "Agents operate on progressively divergent world states with only **34% overlap after 10 interactions**" | Confirms information diverges across agent handoffs. The anchor pattern's immutability directly counters this divergence. |
| **S3: Inter-Stage Contradiction** | Contradiction correlates with failure: "**2.3% contradictory tokens in successes vs. 8.1% in failures**" (detected via BERTScore < 0.3 semantic similarity threshold) | Contradiction detection is a valid quality signal. The paper's BERTScore threshold can inform Part 2's consistency validation. |
| **S4: Context Handoff Loss** | "Global context must be compressed into inter-agent messages" creating "**intrinsic information fragmentation**" | The paper names our exact problem. The anchor pattern bypasses compression by providing fixed-size, non-truncatable context. |
| **S5: Self-Check Failure** | "**Independent agents amplify errors 17.2× vs. 4.4× for centralized systems**" with orchestrator verification | Self-checks fail because there's no external verification. Centralized verification (analogous to our phase-boundary verifiers) reduces error amplification by 4×. |

#### Error Amplification Quantified

The research provides a critical number: **error amplification drops from 17.2× to 4.4× when centralized verification is introduced**. This validates the phase-boundary verifier pattern. An orchestrator (the verifier) checking agent outputs before propagation achieves a **22.7% average error reduction** (95% CI: [20.1%, 25.3%]).

For Haytham's sequential pipeline, this suggests phase-boundary verifiers should reduce the compounding effect where Stage N errors propagate to Stages N+1 through N+10.

#### Context Saturation Threshold

The research finds **message density exhibits logarithmic saturation** with performance plateauing at c* = 0.39 messages per turn. Beyond this threshold, additional context yields diminishing returns. This supports the anchor pattern's design: a small (~500 token), high-signal artifact is more effective than flooding agents with full upstream outputs. The anchor's fixed size is consistent with staying below the saturation threshold.

#### Applicability Caveat

The paper primarily studies **parallel multi-agent architectures** (multiple agents solving the same problem simultaneously), while Haytham uses a **sequential pipeline** (agents solving different problems in series). The "baseline paradox" finding (that multi-agent coordination yields negative returns when single-agent performance exceeds ~45%) applies to redundant parallelization, not sequential specialization. However, the error amplification, context fragmentation, and contradiction correlation findings transfer directly to sequential pipelines.

---

### Empirical Validation: Anchor Without Enforcement (2026-02-04)

After implementing the concept anchor extraction (Part 1a-1b), a validation run on the "Power of 8" idea confirmed that **anchor presence alone does not prevent drift**. The anchor was correctly extracted with all invariants:

```yaml
invariants:
  - property: patient_base
    value: existing patients only
    source: "an app for his existing patients"
  - property: group_structure
    value: 1 receiver with 7 givers
    source: "eight people gather: one receiver...and seven givers"
  - property: timing_constraint
    value: within 24 hours of therapy topics
  - property: evidence_basis
    value: validated wishing framework from 'The Power of 8'
```

Despite the anchor being passed to all stages, the following drift occurred:

| Invariant | Where Drift Started | What Happened |
|-----------|---------------------|---------------|
| `patient_base` | MVP Scope to Architecture | "Auth" listed generically, became open email/password registration |
| `group_structure` | MVP Scope | "Organizing users into groups" explicitly marked OUT OF SCOPE |
| `timing_constraint` | MVP Scope | Dropped entirely, no IN SCOPE item for therapy topic connection |
| `orchestrator_role` | MVP Scope | Only receiver/giver roles defined, no therapist admin |

**Key finding.** The MVP Scope stage is the primary genericization point. It made "reasonable" simplifications for a "Small appetite" MVP, but each simplification violated an anchor invariant. The stages after MVP Scope (Capability Model, Architecture, Stories) propagated and cemented the drift.

**Conclusion.** This validates that Part 1d (Phase-Boundary Verifiers) is essential, not optional. The anchor provides the *criteria* for verification, but without an independent verifier checking MVP Scope output against those criteria, drift proceeds unchecked. The WHAT-phase verifier (Gate 2) would have caught all four violations before they propagated.

---

## Decision

### Part 1: Anchor Pattern - Drift Prevention for Multi-Agent Pipelines

**Problem addressed.** S1 (Concept Genericization), S4 (Context Handoff Loss)

#### The General Problem

Any multi-agent system where Agent N's output becomes Agent N+1's input suffers from **semantic drift**, the LLM equivalent of the telephone game. Each agent:

1. Receives a compressed/summarized version of prior context
2. Interprets it through its own prompt's framing (which biases toward common patterns in training data)
3. Produces output that subtly shifts the meaning toward the generic case
4. Passes that shifted output downstream

After 5-10 hops, the final output can describe something fundamentally different from the original input. This is not a bug in any single agent; each agent's output is locally reasonable. The drift is emergent and cumulative.

#### The Anchor Pattern

The solution is to extract a **small, structured, immutable artifact** from the original input that bypasses the agent chain entirely. This artifact (the **anchor**) is passed to every agent unchanged, as a constraint they must honor.

The anchor has three properties that make it effective:

1. **Small and fixed-size.** Extracted once, never grows. Typically 200-500 tokens regardless of pipeline complexity. Can be included in every agent's context without contributing to token pressure.
2. **Immutable.** No downstream agent modifies the anchor. Agents can *respond* to it (e.g., "We deliberately excluded invariant X because...") but they cannot rewrite it. This breaks the telephone game: the anchor is a direct channel from the original input to every stage.
3. **Extractable by a focused LLM call.** A short, dedicated agent (or structured output call) extracts the anchor from raw input. Its only job is distillation, not expansion or interpretation. Because it doesn't reframe, it's less prone to the genericization that plagues downstream agents.

#### Anchor Schema (Domain-Agnostic)

Any anchor captures three things:

```yaml
anchor:
  # What the user said, distilled to core constraints
  intent:
    goal: "string, one sentence, the user's actual ask"
    explicit_constraints:
      - "string, things the user explicitly stated or implied"
    non_goals:
      - "string, things the user did NOT ask for (inferred from constraints)"

  # Properties that must be true in every downstream agent's output
  invariants:
    - property: "string, name of the invariant"
      value: "string, the required value or condition"
      source: "string, exact quote or paraphrase from the original input"
      confidence: "float (0-1), extraction confidence. < 0.7 means ambiguous"
      ambiguity: "string | null, if confidence < 0.7, what's unclear and why"
      clarification_options: "list[string] | null, if ambiguous, 2-3 concrete choices for the user"

  # What makes this input different from the generic/default case
  identity:
    - feature: "string, the distinctive element"
      why_distinctive: "string, why an LLM is likely to genericize this"
```

The three sections serve different enforcement purposes:

- **Intent** prevents scope expansion. Agents that introduce things listed under `non_goals` are drifting.
- **Invariants** prevent constraint loss. Agents whose output contradicts an invariant must explicitly justify the override.
- **Identity** prevents genericization. Agents that replace a distinctive feature with a common pattern must flag it.

#### Enforcement: Phase-Boundary Verifiers (Not Prompt Self-Checks)

The anchor alone doesn't prevent drift; agents can ignore it. The original design proposed an "enforcement contract" injected into every agent's prompt, asking each agent to self-verify against the anchor before finalizing output. **This approach is rejected** because it suffers from the same failure mode diagnosed in S5: an LLM asked "did you honor these constraints?" will almost always say yes, especially when the violation is subtle genericization rather than overt contradiction.

Instead, enforcement is handled by **phase-boundary verifier agents**, independent LLM calls at each of the 4 decision gates that check the cumulative phase output against the anchor. This is categorically different from self-checking: a separate agent with a narrow mandate reviews the producing agent's work.

```
Phase stages → outputs → Phase-Boundary Verifier → PASS → decision gate
                                                  → WARNINGS → surfaced at gate for user review
                                                  → FAIL → re-run with specific correction feedback
```

Each verifier receives:
- The concept anchor (~500 tokens, fixed)
- The phase's stage outputs (1-3 stages, manageable context)
- A focused rubric for that phase

This avoids the problems identified with per-stage verifiers (A4):
- **Cost:** 4 additional LLM calls (one per phase), not 11 (one per stage)
- **Context pressure:** Phase-scoped, not pipeline-scoped, never exceeds practical limits
- **Focus:** Each verifier checks one phase's concerns, avoiding the "jack of all trades" problem
- **Natural integration:** Decision gates already exist at phase boundaries; verifiers run immediately before them

**Phase-specific verifier rubrics:**

| Phase | Gate | Verifier Focus |
|-------|------|---------------|
| WHY (Idea Validation) | Gate 1 | Concept preservation: Does the validation summary still describe the original idea? Are fabricated claims attributed to the founder? |
| WHAT (MVP Spec) | Gate 2 | Scope fidelity: Does the MVP scope preserve distinctive features? Are anchor invariants reflected in capabilities? |
| HOW (Technical Design) | Gate 3 | Trait consistency: Do architecture decisions align with system traits? Are there contradictions between build/buy and architecture? |
| STORIES (Implementation) | Gate 4 | Appetite compliance: Story count within bounds? Framework coherence? Stories trace to capabilities? |

The anchor content is still included verbatim in every agent's context. Agents *should* honor it, and the structured anchor makes this easier than honoring vague instructions. But compliance is *verified* by an independent reviewer, not self-reported.

#### Cross-Domain Examples

The schema applies unchanged across domains:

**Code refactoring pipeline:**
```yaml
anchor:
  intent:
    goal: "Extract authentication logic into a shared middleware"
    explicit_constraints:
      - "Must remain backwards-compatible with existing API routes"
      - "No new dependencies"
    non_goals:
      - "Rewriting the auth system"
      - "Adding new auth methods"
  invariants:
    - property: "api_contract"
      value: "All existing endpoints return identical responses"
      source: "backwards-compatible"
  identity:
    - feature: "Extract, don't rewrite. Move existing code, don't improve it"
      why_distinctive: "LLMs default to 'improving' code they touch"
```

**Research synthesis pipeline:**
```yaml
anchor:
  intent:
    goal: "Summarize clinical trial evidence for Drug X in pediatric populations"
    explicit_constraints:
      - "Pediatric only, no adult studies"
      - "Phase 2 and Phase 3 trials only"
    non_goals:
      - "Treatment recommendations"
      - "Comparison with other drugs"
  invariants:
    - property: "population"
      value: "pediatric (age < 18)"
      source: "pediatric populations"
  identity:
    - feature: "Evidence summary, not recommendation. Present findings without editorial"
      why_distinctive: "LLMs default to providing recommendations when presenting medical data"
```

---

#### Haytham Instantiation: Concept Anchor

In Haytham, the anchor pattern is instantiated as the **Concept Anchor**, extracted after Stage 1 (Idea Analysis) from the original idea + concept expansion output.

##### 1a. Add Anchor Extraction Step After Stage 1

A dedicated extraction agent (or structured output call) produces the anchor from the raw input:

```yaml
anchor:
  intent:
    goal: "App for existing patients to exchange good wishes in group sessions"
    explicit_constraints:
      - "For his existing patients only (closed community)"
      - "Based on 'The Power of 8' book methodology"
      - "Online sessions (synchronous, not async)"
    non_goals:
      - "Open platform for general public"
      - "Scaling beyond current patient base"
      - "B2B SaaS for multiple therapists"

  invariants:
    - property: "group_structure"
      value: "1 receiver + 7 givers per session"
      source: "eight people gather: one receiver...and seven givers"
      confidence: 0.95
    - property: "community_model"
      value: "closed, invite-only"
      source: "for his existing patients"
      confidence: 0.95
    - property: "orchestrator_role"
      value: "psychologist creates and manages sessions"
      source: "a psychologist wants to develop an app"
      confidence: 0.9
    - property: "interaction_model"
      value: "synchronous (realtime: true)"
      source: "eight people gather in online sessions"
      confidence: 0.6
      ambiguity: "'online sessions' could mean video calls OR async web forms"
      clarification_options:
        - "Synchronous video/audio calls - all 8 people present at once"
        - "Asynchronous participation - people contribute at their own pace"
    - property: "session_medium"
      value: "video/audio call"
      source: "people gather online"
      confidence: 0.5
      ambiguity: "'gather online' typically means video but could be text chat"
      clarification_options:
        - "Video/audio call (like Zoom)"
        - "Text-based chat room"
        - "Hybrid - video with text chat"

  identity:
    - feature: "Wish-exchange is a spiritual/psychological practice, not a messaging feature"
      why_distinctive: "LLMs default to 'messaging platform' patterns"
    - feature: "Synchronous group gathering, not async post-and-reply"
      why_distinctive: "LLMs default to async CRUD as the simpler architecture"
```

The extraction agent's prompt is deliberately narrow: "Read the original input. Extract what's distinctive. Do not expand, interpret, or add."

**Confidence scoring.** Each invariant includes a `confidence` score (0.0-1.0) reflecting how clearly the property is stated in the original input. The extraction agent applies this scale:

| Confidence | Meaning | Required Action |
|-----------|---------|----------------|
| 0.9-1.0 | Explicitly stated, no ambiguity | None |
| 0.7-0.9 | Strongly implied, minor interpretation | None |
| 0.5-0.7 | Ambiguous | MUST include `ambiguity` explanation and `clarification_options` |
| < 0.5 | Very uncertain | MUST include, flagged heavily |

For example, "for his existing patients only" yields `access_model` at confidence 0.95 (explicit). But "online sessions where people gather" yields `interaction_model` at ~0.6, since "gather" could mean synchronous video calls or async web forms. The extractor provides 2-3 concrete clarification options for the user to resolve.

**Required invariants.** The extraction prompt mandates three invariants when detectable: `access_model` (who can use this), `interaction_model` (synchronous vs async), and `session_medium` (video/text/in-person). These were identified as the properties most frequently lost to genericization in the QA review.

**Anchor extraction quality risk.** The `non_goals` and `identity.why_distinctive` fields require inference, not pure distillation. A bad anchor is worse than no anchor because it constrains the entire pipeline with wrong invariants. Mitigations:
1. User confirmation and ambiguity clarification at Decision Gate 1 (see 1c)
2. Anchor quality rubric in the LLM-as-Judge framework (see Part 7). The same test suite that evaluates agents should evaluate the anchor extractor
3. The extraction prompt should be tested across input classes per CLAUDE.md's meta-system design principles (web app, CLI tool, API service, marketplace)

##### 1b. Pass Anchor to Every Downstream Stage

Add `concept_anchor` to the Burr state. The `_build_context()` method includes it verbatim in every agent's context. The anchor is never truncated. At ~300-500 tokens, it fits within any agent's context window alongside other inputs.

##### 1c. User Confirmation and Ambiguity Clarification at Decision Gate 1

The anchor is surfaced to the user at the first decision gate (after Phase 1: WHY). The review UI has two modes depending on whether ambiguous invariants exist:

**When all invariants are high-confidence (>= 0.7):** The UI displays the anchor in review mode with green styling. The user can inspect and correct misextracted constraints before they propagate.

**When ambiguous invariants exist (confidence < 0.7):** The UI enters clarification mode:
1. An amber "Clarification Needed" banner alerts the user that some constraints are ambiguous
2. High-confidence invariants display normally (green, with source quotes)
3. Low-confidence invariants display with amber/warning styling, a confidence badge (e.g., "60% confident"), and the `ambiguity` explanation
4. Each ambiguous invariant presents its `clarification_options` as radio buttons for the user to choose from
5. The user clicks "Confirm Clarifications" to resolve all ambiguities at once
6. Clarified invariants are updated: `value` is set to the user's selection, `confidence` is set to 1.0, `ambiguity` and `clarification_options` are cleared, and `user_clarified` is set to `true`
7. The anchor is re-saved and the anchor context string is regenerated

The gate cannot proceed until all ambiguities are resolved. This ensures that ambiguous constraints (the ones most likely to cause downstream drift) are resolved by the user rather than guessed by the pipeline.

This mitigates the risk of a poorly extracted anchor causing downstream harm. The anchor is small enough for a human to review in seconds, and the clarification flow specifically targets the invariants where extraction confidence is low.

##### 1d. Phase-Boundary Verifiers

Four verifier agents, one at each decision gate. Each receives the concept anchor and the phase's cumulative output. Each has a focused rubric (see table above). Verifier output is structured:

```python
class PhaseVerification(BaseModel):
    phase: str
    passed: bool
    invariants_honored: list[str]
    invariants_violated: list[InvariantViolation]
    identity_preserved: list[str]
    identity_genericized: list[GenericizationFlag]
    warnings: list[str]

class InvariantViolation(BaseModel):
    invariant: str
    violation: str
    severity: Literal["blocking", "warning"]

class GenericizationFlag(BaseModel):
    original_feature: str
    generic_replacement: str
    stage: str
```

Warnings are surfaced at the decision gate. Blocking violations trigger re-run with specific correction feedback by default, but users can override any violation (warning or blocking) at the gate with acknowledgment. Overrides are logged in session state for traceability: the system informs, the user decides.

##### 1e. Swarm-Based Verification (Enhancement)

A single verifier agent checking invariants AND genericization AND fabrication AND consistency is a "jack of all trades," mediocre at each task. The Strands SDK supports **swarm patterns** where specialized agents hand off to each other. This can improve verification thoroughness at critical phases.

**Swarm architecture for verification:**

```
Phase Outputs ──┬──► InvariantChecker ────────┐
                │                             │
                ├──► GenericizationDetector ──┼──► Coordinator ──► PhaseVerification
                │                             │
                └──► ConsistencyValidator ────┘
```

Each specialist agent has a narrow focus:
- **InvariantChecker**: Verifies each anchor invariant is honored, hands off to GenericizationDetector if it sees pattern replacement
- **GenericizationDetector**: Identifies distinctive features replaced with generic patterns
- **ConsistencyValidator**: Checks for contradictions between stages within the phase
- **Coordinator**: Synthesizes findings into final `PhaseVerification` with proper severity levels

**Swarm implementation sketch:**

```python
from strands import Agent, Swarm

invariant_checker = Agent(
    name="invariant_checker",
    system_prompt=INVARIANT_CHECKER_PROMPT,
    tools=[transfer_to_genericization, transfer_to_coordinator]
)

genericization_detector = Agent(
    name="genericization_detector",
    system_prompt=GENERICIZATION_DETECTOR_PROMPT,
    tools=[transfer_to_invariant_checker, transfer_to_coordinator]
)

coordinator = Agent(
    name="coordinator",
    system_prompt=COORDINATOR_PROMPT,
    structured_output_model=PhaseVerification
)

verification_swarm = Swarm(
    agents=[invariant_checker, genericization_detector, coordinator],
    initial_agent="invariant_checker"
)
```

**Trade-offs:**

| Aspect | Single Agent | Swarm |
|--------|--------------|-------|
| LLM calls | 1 per phase | 3-5 per phase |
| Cost | ~$0.05/phase | ~$0.15-0.25/phase |
| Thoroughness | Medium | High |
| Latency | Fast | Slower (serial handoffs) |
| Implementation | Simple | More complex |

**Recommended hybrid strategy:**

Use swarm verification for phases where drift is most damaging, single agent elsewhere:

| Phase | Strategy | Rationale |
|-------|----------|-----------|
| WHY | Single | Simpler checks, lower drift risk |
| **WHAT** | **Swarm** | Primary genericization point - worth extra cost |
| HOW | Single | Mostly consistency checks |
| **STORIES** | **Swarm** | Complex traceability + invariant preservation |

This concentrates verification investment where empirical data shows drift is worst (MVP Scope, Stories) while keeping costs proportional for other phases.

#### Implementation touchpoints:
- `stage_registry.py`: Add `concept_anchor` as a state key available to all stages
- `stage_executor.py` → `_build_context()`: Always include concept_anchor verbatim in context dict
- New: `haytham/workflow/stages/concept_anchor.py`. Extraction logic after Stage 1
- New: `haytham/workflow/anchor_schema.py`. Domain-agnostic anchor schema definition (reusable outside Haytham). Includes `Invariant` model with `confidence`, `ambiguity`, and `clarification_options` fields
- New: `haytham/workflow/verifiers/` package with phase-specific verifier prompts and `PhaseVerification` schema
- `haytham/agents/worker_anchor_extractor/worker_anchor_extractor_prompt.txt`: Confidence scoring instructions, required invariant types, ambiguity detection examples
- `frontend_streamlit/components/anchor_review.py`: Anchor review with dual-mode UI: standard review for high-confidence anchors, clarification flow with radio buttons for ambiguous invariants
- `frontend_streamlit/components/decision_gate.py`: Surface anchor for user review and editing at Gate 1; surface verifier warnings/violations at each gate with override capability

---

### Part 2: Cross-Stage Consistency Validation

**Problem addressed.** S3 (Inter-Stage Contradiction), S5 (Self-Check Failure)

**Prerequisite.** Part 6 (Structured Output Envelope). Without structured output, most "programmatic" validators degenerate into LLM-based text parsing, which is what the phase-boundary verifiers (Part 1d) already do. Part 2 should be implemented *after* Part 6 provides structured fields to validate against.

#### 2a. Programmatic Post-Processors for Structured Fields

Once agents produce structured output envelopes (Part 6), validators can perform genuine programmatic checks:

- **Trait consistency:** If the `system_traits` stage output includes `realtime: false` in its structured envelope, a post-processor on Stage 8 can check the structured `constraints_referenced` field, not grep through prose for the word "real-time" (which would false-positive on "real-time is not needed").
- **Statistic consistency:** If Stage 4's structured `claims` list includes a market size, compare it against Stage 2's `claims` list. Flag mismatches as warnings.

Add a `post_validators` field to `StageExecutionConfig`:

```python
@dataclass
class StageExecutionConfig:
    # ... existing fields ...
    post_validators: list[Callable[[StageOutput, State], list[str]]] | None = None
```

Validators return a list of warnings. If warnings exist, they are:
1. Logged
2. Surfaced to the user at the decision gate
3. Optionally fed back to the agent for self-correction

**Scope limitation.** Programmatic validators are restricted to checks that can be performed reliably on structured data: field comparison, count verification, enum consistency. Semantic checks (e.g., "does this architecture decision contradict the system traits?") remain the domain of phase-boundary verifiers (Part 1d).

#### 2c. Embedding-Based Contradiction Detection

Research on multi-agent scaling (Kim et al., 2025) demonstrates that semantic contradiction between agent outputs can be detected using embedding similarity. Their approach:

1. Compute BERTScore (or similar embedding-based similarity) between stage outputs that should be consistent
2. Flag pairs with **similarity < 0.3** as contradictory (this threshold correlated with failure in their experiments)
3. Surface contradictions as warnings for phase-boundary verifiers to arbitrate

This technique is **LLM-adjacent** (uses embeddings, not full LLM inference) and can detect contradictions that structured field comparison misses. For example, Stage 7's prose "Real-time is unnecessary for this MVP" and Stage 8's prose "We recommend Supabase for its real-time subscriptions" would register as semantically opposed even without structured fields.

```python
def detect_contradiction(stage_a_output: str, stage_b_output: str) -> bool:
    """Flag semantic contradiction using embedding similarity."""
    score = bert_score(stage_a_output, stage_b_output)
    return score < 0.3  # Paper's empirically-derived threshold

# Apply to stage pairs that should be consistent:
# - system_traits vs. build_buy_analysis
# - build_buy_analysis vs. architecture_decisions
# - capability_model vs. story_generation
```

**Limitation.** BERTScore detects semantic opposition but not logical contradiction. "We need real-time" and "We don't need real-time" are semantically similar (both discuss real-time) but logically contradictory. The 0.3 threshold catches overt opposition; subtle contradictions still require phase-boundary verifier judgment.

#### 2b. Trait Propagation Enforcement

When `system_traits` produces structured output, extract key constraints into a `constraints` dict in Burr state that downstream post-processors check against:

```python
constraints = {
    "realtime": False,  # from system_traits structured output
    "community_model": "closed",  # from concept_anchor
    "auth_model": "invite_only",  # derived from closed community
}
```

#### Implementation touchpoints:
- `stage_executor.py`: Add post-validator execution after agent output, before state update
- New: `haytham/workflow/validators/` package with:
  - `consistency.py`: cross-stage field comparison (operates on structured `StageOutput`)
  - `trait_propagation.py`: system trait enforcement on downstream stages
  - `contradiction.py`: BERTScore-based semantic contradiction detection (Part 2c)
- Depends on Part 6 for structured output fields to validate against
- Part 2c can be implemented independently on freeform markdown (doesn't require Part 6)

---

### Part 3: Grounding Enforcement

**Problem addressed.** S2 (Fabrication/Hallucination)

#### 3a. Structured Claims in Agent Output

Require agents that cite statistics to include claims in the structured output envelope (Part 6):

```python
class Claim(BaseModel):
    statement: str
    source: Literal["web_search", "estimate", "unsourced"]
    evidence: str | None  # URL or reasoning
```

A post-processor can then:
- Flag `UNSOURCED` claims
- Verify `web_search` claims actually came from the tool's output (by comparing against the tool call log)
- Downgrade `ESTIMATE` claims from appearing as facts

**Prerequisite.** The Strands SDK must expose tool call history programmatically for source verification. If tool call logs are not accessible, source verification degrades to self-reported tags, which is the same `[validated]` pattern that already failed. This dependency must be confirmed before committing to implementation.

#### 3b. Competitor Validation Against Input Concept

The competitor analysis agent's bias check failed because it was a self-assessment. Replace it with a check at the Phase 1 boundary verifier (Part 1d):

The WHY-phase verifier receives the concept anchor's `intent` and `identity` sections alongside the competitor analysis output. Its rubric includes: "Do the identified competitors operate in the same problem domain as the idea? If competitors are about [different domain] while the idea is about [anchor domain], flag as FAIL."

This is a semantic check, exactly where LLM verifiers add value that programmatic checks cannot. The original proposal to use keyword matching ("at least 50% of identified competitors share keywords related to the core concept") would produce unreliable results on natural language.

#### Implementation touchpoints:
- Part 6's `StageOutput.claims` field: Structured claim format
- New: `haytham/workflow/validators/grounding.py`. Claim verification against tool call logs (contingent on Strands SDK access)
- Phase 1 verifier rubric: Competitor domain relevance check
- `stage_executor.py`: Access agent tool call logs for verification (if available)

---

### Part 4: Appetite-Bound Story Generation

**Problem addressed.** S6 (Appetite Mismatch)

#### 4a. Story Count Limits by Appetite

Enforce appetite as a hard constraint on story generation:

| Appetite | Max Stories | Max Layers |
|----------|-----------|-----------|
| Small (1-2 weeks) | 8 | 3-4 |
| Medium (3-4 weeks) | 15 | 5 |
| Large (5-6 weeks) | 25 | 6 |

Add these limits to the story skeleton prompt and enforce them in the post-processor. Story count is a genuinely mechanical check: count `## Story` headers in the output. This is one of the few validators that works reliably on freeform markdown without structured output.

#### 4b. Framework Coherence Validation

After story generation, a post-processor scans all stories for framework references. If more than one frontend framework is detected for the same component (e.g., two frameworks for the main app), the stories are rejected with an error listing the conflict. Multi-framework architectures where each framework serves a distinct purpose (e.g., Astro marketing site + React app) should not be rejected. The validator checks for conflicts within a component, not across components.

#### Implementation touchpoints:
- `worker_story_generator/story_skeleton_prompt.txt`: Add appetite-based limits
- New: `haytham/workflow/validators/story_coherence.py`. Framework conflict detection, story count enforcement

---

### Part 5: Context Handoff Improvement

**Problem addressed.** S4 (Information Loss)

#### 5a. Replace First-Line Truncation with Structured Summaries

Instead of truncating to the first 200 characters, require each agent to output a `## TL;DR` section (max 300 words) at the top of its output. The context builder uses these structured summaries rather than blind truncation.

**Enforcement caveat.** Requiring agents to produce a `## TL;DR` section is a prompt instruction. Agents may omit it or produce poor summaries. With Part 6 (Structured Output Envelope), the TL;DR becomes a required field (`StageOutput.tldr`) that the framework validates for presence. Without Part 6, the context builder should fall back to the existing truncation if no `## TL;DR` header is found.

#### 5b. Anchor as Non-Truncatable Context

The anchor (Part 1) is always included in full. It is small (< 500 tokens) by design and carries the information that truncation currently destroys. This is a core property of the anchor pattern: because the anchor is fixed-size and immutable, it never contributes to the context growth problem that truncation is trying to solve.

#### 5c. Enable Context Retrieval Tools

The codebase already has a context retrieval tool system (`context_retrieval.py`) that allows agents to selectively fetch full upstream outputs. Enable this for stages that need deep context (MVP Scope, Story Generation) rather than relying on truncated summaries.

#### Token budget impact

The anchor adds ~500 tokens per agent context. TL;DR summaries from prior stages add ~400 tokens each. By Stage 10: anchor (500) + TL;DRs from 9 prior stages (3,600) = ~4,100 tokens of fixed context overhead. This is manageable within the current `DEFAULT_MAX_TOKENS=5000` output budget, but should be monitored. If context tools (5c) are enabled, agents can selectively fetch full outputs, reducing the need for all TL;DRs to be present simultaneously.

#### Implementation touchpoints:
- `burr_actions.py` → `_build_context_summary()`: Use TL;DR sections instead of first-line truncation, with fallback to existing behavior
- All `worker_*_prompt.txt` files: Add `## TL;DR` output requirement
- `stage_executor.py`: Enable `use_context_tools=True` for MVP Scope and Story Generation stages

---

### Part 6: Structured Output Envelope

**Problem addressed.** Prerequisite for Parts 2, 3, and 5a. Makes programmatic validation viable

#### The Problem with Validating Freeform Markdown

The pipeline currently stores all stage outputs as markdown strings. The programmatic validators described in Parts 2 and 3 were designed assuming structured data to compare. On freeform markdown:

- "Statistic consistency" requires extracting numbers from prose, unreliable with regex, requires LLM otherwise
- "Trait consistency" requires understanding whether a sentence endorses or rejects a trait, semantic, not mechanical
- "Claim sourcing" requires distinguishing cited facts from editorial, structural parsing of natural language
- "TL;DR presence" (Part 5a) is a prompt instruction with no programmatic guarantee

Without structured output, most "programmatic validators" degenerate into either (a) brittle regex patterns or (b) additional LLM calls, defeating the purpose of choosing programmatic over LLM-based verification.

#### Structured Output Envelope

Require all agents to produce output through a structured envelope that wraps their freeform content:

```python
class StageOutput(BaseModel):
    """Structured envelope for all stage outputs."""
    tldr: str  # Max 300 words, replaces first-line truncation
    anchor_compliance: AnchorComplianceReport
    claims: list[Claim]  # Only for stages that cite statistics
    content: str  # The actual markdown output (freeform)

class AnchorComplianceReport(BaseModel):
    invariants_preserved: list[str]  # Invariant property names honored
    invariants_overridden: list[InvariantOverride]
    identity_features_preserved: list[str]
    identity_features_genericized: list[str]  # Must be empty or justified

class InvariantOverride(BaseModel):
    invariant: str  # Which invariant
    reason: str  # Why it was overridden
    user_impact: str  # What the user should know

class Claim(BaseModel):
    statement: str
    source: Literal["web_search", "estimate", "unsourced"]
    evidence: str | None
```

**What this enables:**
- Part 2 validators compare `StageOutput` fields across stages: genuine programmatic checks
- Part 3 iterates `claims` and verifies against tool logs: structured, not parsed
- Part 5a's TL;DR is a required field, not a prompt instruction, guaranteed present
- `anchor_compliance` is self-reported (agents can lie), but structured self-reporting is *checkable*. A programmatic validator can flag when `invariants_overridden` is empty but the `content` mentions changing a core feature. The phase-boundary verifier (Part 1d) then arbitrates

**What this does NOT solve:**
- Agents can still fill structured fields incorrectly (the "self-check" problem)
- The `content` field remains freeform markdown; the envelope doesn't eliminate prose, it wraps it
- Phase-boundary verifiers remain necessary for semantic validation

**Implementation path.** The Strands SDK already supports `structured_output_model` (Pydantic). The `_extract_agent_output()` function already handles Pydantic models. Migration is incremental: stages can adopt `StageOutput` one at a time while `_extract_agent_output()` falls back to raw string handling for unmigrated stages.

#### Implementation touchpoints:
- New: `haytham/workflow/stage_output.py`. `StageOutput`, `AnchorComplianceReport`, `Claim` schemas
- `agent_factory.py`: Set `structured_output_model=StageOutput` for each agent's `AgentConfig`
- `burr_actions.py` → `_extract_agent_output()`: Handle `StageOutput` envelope, extract `tldr` for context building
- `stage_executor.py`: Store both the full `StageOutput` (for validators) and the `content` field (for session markdown files)
- All `worker_*_prompt.txt` files: Update output format instructions to match `StageOutput` schema

---

### Part 7: Measurement Strategy

**Problem addressed.** No mechanism to verify that Parts 1-6 actually work

#### The Gap

The QA review that motivated this ADR was a manual, one-time evaluation. After implementing fixes, the same question arises: did concept drift decrease? Is the anchor being respected? Are validators catching real issues or producing false positives? Without measurement, there is no feedback loop and no regression detection.

#### Integration with ADR-018 LLM-as-Judge Framework

ADR-018 established LLM-as-Judge for agent quality testing. Extend it with concept fidelity dimensions:

##### 7a. Concept Fidelity Rubric

Add a rubric dimension to the judge framework that evaluates end-to-end concept preservation:

| Score | Criteria |
|-------|----------|
| 5 | All anchor invariants preserved. All identity features recognizable in final output. No silent genericization. |
| 4 | All invariants preserved. Minor genericization of non-critical identity features, flagged by verifier. |
| 3 | One invariant violated with justification (Invariant Override). Identity features partially preserved. |
| 2 | One or more invariants silently violated. Core identity features genericized without flagging. |
| 1 | Final output describes a fundamentally different product than the input idea. |

Run this rubric against the "Power of 8" idea and at least 2 other test ideas (per CLAUDE.md: test across input classes: web app, CLI tool, API service).

##### 7b. Anchor Quality Rubric

Evaluate the anchor extractor independently:

| Score | Criteria |
|-------|----------|
| 5 | All explicit constraints captured. Invariants match verifiable statements in input. Non-goals are reasonable inferences. Identity features are genuinely distinctive. |
| 4 | Constraints captured. One non-goal is debatable but not harmful. |
| 3 | One explicit constraint missed. Or one invariant over-inferred (not clearly in input). |
| 2 | Multiple constraints missed. Or non-goals that contradict user intent. |
| 1 | Anchor describes a different idea than the input. |

##### 7c. Validator Calibration Metrics

Track per-validator:
- **True positive rate:** Warnings that correspond to real issues (confirmed by judge or human)
- **False positive rate:** Warnings that are incorrect or overly strict
- **Miss rate:** Issues found by the judge that no validator caught

Start validators in warning-only mode. Graduate to blocking after calibration shows acceptable false positive rates (< 20% target).

##### 7d. Error Propagation Metric

Research on multi-agent scaling (Kim et al., 2025) quantified error amplification: **17.2× for independent agents vs. 4.4× for centralized verification**. Adapt this metric to measure whether phase-boundary verifiers reduce error propagation in Haytham:

**Measurement approach.**
1. Introduce a known error at Stage N (e.g., incorrect market size, wrong competitor domain, fabricated claim)
2. Track whether the error appears in Stages N+1, N+2, ... N+k
3. Compare propagation rates with and without phase-boundary verifiers enabled

**Target.** Phase-boundary verifiers should reduce error propagation by at least 50% (from ~17× to ~8× or lower), consistent with the research finding that centralized verification achieves 22.7% average error reduction.

**Implementation.** Add a "chaos testing" mode to the test harness that injects controlled errors and measures propagation. This validates that verifiers catch errors before they compound.

##### 7e. State Divergence Metric

The research found "only 34% overlap after 10 interactions" in agent world states. For Haytham, measure semantic overlap between:
- The original idea (input)
- Stage 1 output (concept expansion)
- Stage 5 output (MVP scope)
- Stage 10 output (stories)

Use embedding similarity (cosine distance) to quantify how much the pipeline's understanding of the idea diverges from the original. The anchor pattern should maintain higher overlap than the pre-anchor baseline.

**Target.** With the anchor pattern, Stage 10's semantic similarity to the original idea should exceed 60% (vs. the research baseline of 34% without anchoring).

#### Implementation touchpoints:
- Extend ADR-018's rubric definitions with concept fidelity and anchor quality dimensions
- Add "Power of 8" as a permanent regression test idea alongside existing test fixtures
- Add at least 2 structurally different test ideas (CLI tool, API service) to test anchor generality
- `make test-agents` output: Include concept fidelity scores alongside existing quality scores
- New: `haytham/testing/error_propagation.py`. Chaos testing harness for error injection and propagation measurement (Part 7d)
- New: `haytham/testing/state_divergence.py`. Embedding-based semantic overlap measurement (Part 7e)

---

## Priority & Sequencing

| Priority | Part | Effort | Impact | Dependencies |
|----------|------|--------|--------|-------------|
| **P0** | Part 1a-1d: Anchor Pattern + Phase-Boundary Verifiers | Medium | Addresses root cause of concept drift with independent enforcement. Single highest-impact change | None |
| **P0** | Part 5: Context Handoff | Small | Low-effort fix that compounds with the Concept Anchor | None (enhanced by Part 6) |
| **P0** | Part 7: Measurement Strategy | Small | Without measurement, no way to verify Parts 1-6 work. Must ship alongside Part 1 | Part 1, ADR-018 |
| **P1** | Part 1e: Swarm-Based Verification | Medium | Improves verification accuracy at WHAT/STORIES phases where drift is worst | Part 1a-1d, Strands SDK swarm support |
| **P1** | Part 6: Structured Output Envelope | Medium | Prerequisite for programmatic validators. Incremental migration | None |
| **P1** | Part 4: Appetite-Bound Stories | Small | Simple post-processor, works on freeform markdown. Prevents the most visible output problem | None |
| **P2** | Part 2: Cross-Stage Validation | Medium | Programmatic validators for structured fields | Part 6 |
| **P2** | Part 3: Grounding Enforcement | Large | Most complex, requires tool call log access and structured claims | Part 6, Strands SDK investigation |

**Key sequencing insight.** Parts 2 and 3 depend on Part 6 (structured output) to function as designed. Implementing them before Part 6 would require either brittle regex parsing or additional LLM calls, both of which undermine the rationale for choosing programmatic validators over verifier agents. The phase-boundary verifiers (Part 1d) provide semantic coverage in the interim.

---

## Consequences

### Positive
- The pipeline's most critical failure (producing the wrong product) is addressed at the root cause (anchor pattern) with independent enforcement (phase-boundary verifiers), not prompt self-checks
- **Empirically grounded.** The phase-boundary verifier pattern is supported by research showing centralized verification reduces error amplification from 17.2× to 4.4× (Kim et al., 2025). The anchor pattern's fixed-size design aligns with the finding that context effectiveness saturates at c* = 0.39 messages/turn
- The anchor pattern is domain-agnostic and reusable in any multi-agent pipeline, not just Haytham. The schema (intent/invariants/identity) and enforcement contract can be extracted as an independent library
- Phase-boundary verifiers integrate naturally with existing decision gates, requiring no new UX concepts
- Structured output envelopes (Part 6) make the pipeline programmatically inspectable, enabling a class of validators that are impossible on freeform markdown
- Measurement strategy (Part 7) creates a regression test for concept fidelity. The QA review becomes repeatable, not one-time
- Appetite enforcement prevents the most jarring output problem (20 stories for a 2-week MVP)
- Context handoff improvements preserve information without exceeding token limits

### Negative
- Anchor extraction adds one LLM call; phase-boundary verifiers add 4 more (one per phase). Total pipeline overhead: 5 additional LLM calls (or 9-13 with swarm verification at WHAT and STORIES phases)
- Structured output migration (Part 6) requires updating all agent prompts and may constrain agent output flexibility. Agents producing structured envelopes may be less exploratory than those producing freeform prose
- Phase-boundary verifiers add latency at each decision gate (but gates already pause for user input, so the verifier runs during wait time)
- Swarm-based verification (Part 1e) increases cost ~3x for WHAT and STORIES phases. Justified by those being the primary drift points, but adds ~$0.40-0.50 per full pipeline run
- Framework coherence checking may need nuance for legitimate multi-framework architectures. The validator checks per-component conflicts, not cross-component usage
- Token overhead of anchor + TL;DRs is ~4,100 tokens by Stage 10, manageable but non-trivial

### Risks
- **Anchor quality is the single point of failure.** A poorly extracted anchor constrains the entire pipeline with wrong invariants. Mitigated by: confidence scoring that flags uncertain extractions, user clarification of ambiguous invariants at Gate 1, anchor quality rubric (Part 7), testing across input classes
- **The `non_goals` section is inferred, not stated.** If the extraction agent infers a non-goal that the user actually wants, it becomes an invisible constraint. User confirmation of the anchor is critical. Confidence scoring partially addresses this for invariants (low-confidence invariants are explicitly surfaced) but does not yet cover `non_goals` or `identity` sections
- **Phase-boundary verifiers are still LLM-based.** They can be confidently wrong. But they are categorically better than self-checks: separate context, dedicated prompt, narrow mandate, structured output. The "hallucination verifying hallucination" risk is reduced (not eliminated) by giving the verifier the anchor as a concrete rubric rather than asking "did you do this right?"
- **Structured output may degrade content quality.** Agents forced to produce JSON envelopes may allocate fewer tokens to the actual content. Monitor content quality scores (ADR-018) during Part 6 migration
- **Over-constraining agents** may reduce their ability to add genuine value (e.g., identifying a better approach than the founder's original vision). The `InvariantOverride` mechanism is designed to allow this explicitly, requiring justification rather than prohibition
- **Validator calibration** requires iteration. Start in warning-only mode (Part 7c) and graduate to blocking after false positive rates are acceptable

---

## Alternatives Considered

### A1: Fine-tune agents on diverse input types
**Rejected.** Fine-tuning is expensive, hard to maintain, and doesn't address the systemic issue (pipeline structure), only the symptom (individual agent quality). A well-prompted general model with proper constraints outperforms a fine-tuned model in a broken pipeline.

### A2: Single mega-agent instead of pipeline
**Rejected.** A single agent generating everything from idea to stories would hit context limits and lose the structured traceability that makes the pipeline valuable. The pipeline architecture is correct; the information flow within it is the problem.

### A3: Human-in-the-loop at every stage
**Rejected for default flow.** Decision gates already exist at phase boundaries. Adding human review at every stage would make the system unusable. The concept anchor + phase-boundary verifiers approach automates what humans would catch, reserving human judgment for phase-level decisions.

### A4: Inline Verifier Agents

**Partially adopted, as phase-boundary verifiers (Part 1d), not per-stage verifiers.**

This alternative places an LLM-based verifier after each stage (or phase) to evaluate the producing agent's output before it enters the pipeline state. Two variants were considered:

#### Variant A: Single Master Verifier

One verifier agent runs after every stage. It receives the original idea, the concept anchor, all prior stage outputs, and the current stage's output. Its prompt covers all check types: concept fidelity, fabrication, contradiction detection, and schema compliance.

```
Stage Agent → output → Master Verifier → PASS → state update
                                        → FAIL → re-run agent with correction feedback
```

**Pros:**
- Single prompt to maintain, one place to improve verification quality
- Cross-stage view: can detect cross-stage contradictions that stage-specific verifiers would miss
- Familiar pattern, similar to ADR-018's LLM-as-Judge, but inline rather than offline

**Cons:**
- **Context window pressure.** By Stage 9, the verifier needs: original idea + concept anchor + 8 prior stage outputs + current output + verification instructions. This easily exceeds practical context limits, forcing the same truncation that causes S4.
- **Jack of all trades.** Checking whether competitor names are relevant to the concept (semantic reasoning) and whether story count matches appetite (arithmetic) and whether market stats are consistent across stages (data comparison) are fundamentally different tasks. A single prompt doing all of them will be mediocre at each.
- **Latency.** Every stage gets an additional full LLM call, roughly doubling pipeline execution time.
- **Hallucination verifying hallucination.** The QA review showed that self-check prompts already fail; the competitor analysis bias check endorsed gift registries as correct. A verifier agent is a more capable check (separate context, dedicated prompt), but it's still an LLM asked to judge another LLM. It can be confidently wrong in the same ways.

#### Variant B: Stage-Specific Verifier Agents

Each stage (or each phase) has a dedicated verifier with a focused prompt. The concept expansion verifier knows exactly what to check for Stage 1; the story generation verifier knows to check framework coherence and appetite bounds.

```
concept_expansion → output → concept_expansion_verifier → PASS/FAIL
market_context    → output → market_context_verifier    → PASS/FAIL
...
```

**Pros:**
- Focused prompts: each verifier is small, specific, and testable
- Lower context pressure: each verifier only needs the relevant inputs
- Can encode domain-specific checks: "Do the competitors actually operate in the same domain as the idea?" is a meaningful semantic check that programmatic validators struggle with
- Naturally aligns with ADR-018's LLM-as-Judge rubrics; the same evaluation criteria used offline could run inline

**Cons:**
- **N additional agents to maintain.** Every prompt change to a stage agent may require a corresponding verifier prompt update. The maintenance burden roughly doubles.
- **2x LLM cost per stage.** Each stage becomes two LLM calls (agent + verifier). For an 11-stage pipeline, this is 11 additional calls.
- **Verifier-agent arms race.** When a verifier rejects output and the agent re-runs with correction feedback, the agent may produce worse output on retry (LLMs often degrade when told "you were wrong, try again" without specific guidance). Retry logic needs careful design.
- **Diminishing returns for mechanical checks.** Counting stories, detecting framework conflicts, comparing numbers across stages: these are better done programmatically (100% reliable, zero cost, instant). Using an LLM for arithmetic is wasteful.

#### Why Phase-Boundary Verifiers Were Chosen

The original analysis classified failure modes into mechanical vs. semantic and concluded programmatic validators should handle the mechanical majority. **On review, this classification doesn't hold against the actual codebase.** With freeform markdown output:

| Failure Mode | Classified As | Actual Nature (on freeform markdown) | Best Checker |
|-------------|--------------|--------------------------------------|-------------|
| S1: Concept genericization | Semantic | Semantic | Phase-boundary verifier + anchor |
| S2: Fabrication | Mixed | Mostly semantic (source verification needs tool logs; competitor relevance is LLM territory) | Phase-boundary verifier + structured claims (Part 6) |
| S3: Inter-stage contradiction | Mechanical | **Semantic on prose** - comparing markdown paragraphs for contradiction requires understanding, not string matching | Phase-boundary verifier (until Part 6 provides structured fields) |
| S4: Context handoff loss | Structural | Structural | Infrastructure change (Part 5) |
| S5: Self-check failure | Meta | Meta | Independent verifier (by definition, the fix for "self-checks fail" cannot be another self-check) |
| S6: Appetite mismatch | Arithmetic | **Genuinely mechanical** - count story headers | Programmatic validator |

Only S4 and S6 are reliably handled by non-LLM mechanisms on the current output format. S3 and S5 require independent LLM judgment. S1 and S2 require semantic understanding. This makes the case for LLM-based verification at phase boundaries stronger than the original analysis concluded.

Phase-boundary verifiers (4 calls) are the compromise between per-stage verifiers (11 calls) and no verifiers (0 calls, relying on prompt self-checks that S5 proved don't work). They place LLM judgment where it's needed while keeping cost proportional.

**Empirical support.** Research on multi-agent scaling (Kim et al., 2025) validates this architectural choice. Their findings show:
- Independent agents (no verification) amplify errors **17.2×**
- Centralized verification reduces amplification to **4.4×** (a 74% reduction)
- The mechanism is "iterative verification where orchestrators cross-check outputs before aggregation," precisely what phase-boundary verifiers do
- Contradiction detection via BERTScore < 0.3 correlates with failure (2.3% contradictory tokens in successes vs. 8.1% in failures)

**Future evolution.** If Part 6 (structured output) is fully adopted, some phase-boundary verifier checks can be replaced by cheaper programmatic validators operating on structured fields. The verifiers then narrow to purely semantic checks (concept fidelity, competitor relevance) where LLM judgment is irreplaceable.

### A5: Retrieval-Augmented Generation for prior stage context
**Partially adopted** (Part 5c). The context retrieval tools already exist but are unused. Enabling them for key stages is lower risk than building new infrastructure. However, RAG alone doesn't solve concept drift; an agent that retrieves the original idea can still genericize it. The concept anchor provides the structured constraint that RAG cannot.

### A6: Hybrid - Programmatic Validators + Targeted Verifier Agents
**Adopted as the primary decision** (revised from "recommended as evolution path"). The original proposal deferred verifier agents to future work, but the enforcement gap in prompt-based anchor self-checks, combined with the freeform markdown output reality, makes phase-boundary verifiers necessary from the start. The hybrid is: phase-boundary verifiers for semantic checks now, programmatic validators for mechanical checks after structured output (Part 6) enables them.

### A7: Structured Output Enforcement
**Adopted as Part 6.** Not considered in the original alternatives analysis. Requiring all agents to produce structured output envelopes (Pydantic models wrapping freeform content) is the prerequisite that makes programmatic validators viable. Without it, "programmatic validation" on freeform markdown is either brittle regex or additional LLM calls, both of which undermine the rationale for choosing programmatic over LLM-based verification.

### A8: Swarm-Based Verification
**Adopted as enhancement (Part 1e).** Instead of a single verifier agent per phase, use a swarm of specialized agents that hand off to each other:

- **InvariantChecker.** Focuses only on anchor invariant preservation
- **GenericizationDetector.** Focuses only on identity feature genericization
- **ConsistencyValidator.** Focuses only on inter-stage contradictions
- **Coordinator.** Synthesizes findings into final verdict

**Pros:**
- **Specialization improves accuracy.** Each agent has a narrow mandate and focused prompt, avoiding the "jack of all trades" problem
- **Handoff enables deeper analysis.** When InvariantChecker finds a potential genericization, it can hand off to GenericizationDetector for deeper analysis
- **Matches research findings.** Kim et al. (2025) found that specialized agents with coordination outperform generalist agents on complex tasks

**Cons:**
- **3-5x cost per verification.** Each swarm run involves multiple LLM calls
- **Increased latency.** Serial handoffs add time at decision gates
- **More complex implementation.** Swarm coordination requires careful design of handoff tools and termination conditions

**Decision:** Adopt swarm verification for WHAT and STORIES phases where empirical data shows drift is worst. Use single-agent verification for WHY and HOW phases where simpler checks suffice. This hybrid concentrates verification investment where it has the highest impact while keeping total cost proportional.

---

## References

- QA_TASKS.md: Stage-by-stage critical review that motivated this ADR
- ADR-016: Four-phase workflow architecture (the pipeline being improved)
- ADR-018: LLM-as-Judge agent testing (complementary quality mechanism, extended by Part 7)
- ADR-019: System trait detection (Stage 7, where trait contradictions were observed)
- Kim, Y., et al. (2025). "Towards a Science of Scaling Agent Systems." arXiv:2512.08296. Empirical research on multi-agent error amplification, context fragmentation, and verification architectures. Provides quantitative support for the phase-boundary verifier pattern (17.2× to 4.4× error reduction) and the BERTScore < 0.3 contradiction detection threshold.
- Strands SDK Swarm Documentation: https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/swarm/. Multi-agent coordination pattern where specialized agents hand off to each other. Used for Part 1e swarm-based verification architecture.
