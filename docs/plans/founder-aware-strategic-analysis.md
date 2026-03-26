# Phase 1 Pipeline Restructure: Founder-Aware Strategic Analysis

## Context

The current Phase 1 pipeline validates startup ideas but is optimized for generic commercial MVPs. Dogfooding the system on itself (an OSS Claude Code plugin with community/credibility goals) revealed 5 gaps: no founder intent capture, no positioning analysis, single output path (GO/PIVOT/NO-GO), no vision pressure-testing, and project-type blindness (all ideas treated as commercial startups).

This restructure enriches the concept anchor with founder context, adapts research agents to project type, and expands the report-synthesizer with positioning, strategic options, and assumption analysis.

## Research Findings (informing design)

Research into intent analysis across AI agent frameworks, conversational AI, product strategy, and academia found:

- **No major system solves "raw idea -> structured intent."** All frameworks resolve intent-to-action. None model intent-to-understanding. This is Haytham's genuine gap.
- **Five-component intent model** (industrial automation): Expectations, Conditions, Targets, Context, Information. More rigorous than freeform expansion.
- **WHY-refinement** (goal-oriented requirements engineering): Ask "why does this goal exist?" to surface deeper intent beyond what's stated.
- **Theory of Change backward-chaining**: Start from desired impact, work backward. Inverts the current forward analysis.
- **Behavioral vs stated intent**: Probing beyond features to understand motivation dramatically improves outcomes.
- **Concept anchor pattern validated** by A2A Agent Cards, OpenAI scope-of-autonomy, and academic frameworks.
- **Don't over-formalize**: Intent is implicit. Enrich the concept anchor, don't create separate Intent objects.

Sources: Google A2A Protocol, Anthropic multi-agent research, OpenAI Model Spec (Dec 2025), Columbia Levels of Autonomy (June 2025), Plan-and-Act (2025), Stanford IS-Rec, Harvard Data Science Review (Dec 2024).

## Implementation Order

Changes follow the data-flow dependency chain. Upstream schema first, downstream consumers after.

### 0. Add Intent Analysis Standards to CLAUDE.md
**File:** `CLAUDE.md`

Add new section after "Agent UX Standards" codifying the research findings as design principles:

1. **Five-component decomposition**: Every idea intake extracts Expectations, Conditions, Targets, Context, Information
2. **WHY-refinement**: Agents analyzing ideas must probe why the founder is building, not just what
3. **Behavioral vs stated intent**: Don't treat feature descriptions as ground truth. Probe for underlying motivation and success criteria
4. **Backward-chaining evaluation**: Evaluate ideas from desired impact backward, not just forward from features
5. **Intent visibility**: Extracted intent must be reflected back to the user in editable form (concept anchor pattern)
6. **No separate Intent objects**: Enrich existing structures (concept anchor), don't add new schema layers

### 1. Expand idea-analyst with intent-aware analysis
**File:** `agents/idea-analyst.md`

Restructure the idea-analyst to apply the five-component intent model and WHY-refinement:

**A) Add `founder_intent` to concept anchor JSON** (Step 3, around line 141):
```json
"founder_intent": {
  "motivation": "learning | revenue | community | credibility | solving_own_problem",
  "success_criteria": "founder's free text from project.yaml, or 'not specified'",
  "expected_impact": "What change in the world does this create? (backward-chained from success_criteria)",
  "constraints": {
    "time_horizon": "weeks | months | quarters",
    "team": "solo | small_team | funded_team"
  }
}
```

**B) Add `growth_model` to existing `strategic_signals`** (after `distribution`):
```json
"growth_model": "viral | content | community | sales | organic_oss | ecosystem | unknown"
```

**C) Add WHY-refinement to Step 2 (Concept Expansion)**:
After Problem Analysis, add a new section "#### 0. Intent Analysis" (placed first, before problems):
- Map founder_context to the 5-component model: What do they expect (Expectations)? What constraints exist (Conditions)? Who is this for (Targets)? Why now (Context)? What do they already know (Information)?
- Apply WHY-refinement: "Why does this idea exist? What deeper goal does it serve?"
- Apply backward-chaining: "If this succeeds, what changes? Work backward from that change."
- Word budget: 80 words max

**D) Read `founder_context` from `.haytham/project.yaml`** if present. If absent, infer what's possible (default `unknown` for motivation, `"not specified"` for success_criteria).

### 2. Add Step 0 to orchestration commands
**Files:** `commands/validate.md`, `commands/haytham.md`

Insert new "## Step 0: Founder Context" section before Step 1 in both files.

Three questions:
1. Why are you building this? (learning / revenue / community growth / credibility / solving your own problem)
2. What does success look like in 3 months? (free text)
3. What are you working with? (solo + bootstrapped / solo + some funding / small team)

Write answers to `project.yaml` as `founder_context` section. Skip if resuming (step > 0) or if `founder_context` already exists. Allow user to say "skip" to proceed with inference.

Update roadmap text: "0. Founder Context (3 quick questions, ~30 sec)"

Update Step 1 digest to show founder intent after concept anchor is produced.
Update Step 4 (Founder Review) to include "Goals & motivation" dimension.
Update Step 5 digest to show recommended_path and positioning.
Update Step 6 (Gate) review prompts to reference positioning and strategic options.

### 3. Adapt market-researcher
**File:** `agents/market-researcher.md`

Add "### Project-Type Adaptation" section after "Archetype-Aware Research":
- Read `founder_intent`, `growth_model` from concept-anchor.json
- If `business_model: open-source` OR `growth_model: organic_oss/community`:
  - Market Size uses adoption metrics (developer population, GitHub stars, downloads) instead of dollars
  - Trends include ecosystem health
  - Risks include community-specific risks (maintainer burnout, fork risk)
- If `distribution: plugin_or_extension` OR `growth_model: ecosystem`:
  - Market Context researches platform ecosystem
  - Market Size uses platform install base and plugin adoption rates
- Otherwise: current commercial approach (dollars)

Make Section 3 (Market Size) format adaptive with two templates.

### 4. Adapt competitor-researcher
**File:** `agents/competitor-researcher.md`

Expand Competitive Framing section:
- If OSS/community: include community health metrics (GitHub stars, contributors, last commit, release cadence) in competitor profiles
- If `founder_intent.motivation` is `community` or `learning`: emphasize adoption friction over monetization gaps
- Add optional `Community (if OSS)` line to Section 1 competitor template

### 5. Expand report-synthesizer (biggest change)
**File:** `agents/report-synthesizer.md`

A) Update Inputs to explicitly read `founder_intent` and `growth_model`.

B) Add "Founder Intent Calibration" to the Founder Persona section:
- Calibrate entire report to founder's motivation
- Use `success_criteria` as viability yardstick
- Factor constraints into feasibility
- If motivation is `community`/`credibility`, don't default to commercial viability as primary axis

C) Add **PART 5: STRATEGIC ANALYSIS** after current PART 4 (3 new sections):

**Section 9: Positioning Analysis**
- Territory: one-line positioning statement
- Why this territory: evidence from research
- Defensibility: weak/moderate/strong with specific moat type
- Founder-market fit: does background give unfair advantage?

**Section 10: Strategic Options** (uses backward-chaining from Theory of Change)
- Start from founder's `expected_impact` and `success_criteria`, work backward to what path achieves it
- 2-3 paths (not just GO/PIVOT/NO-GO)
- Each: what you do (3 concrete actions), timeline, risks, when to choose this
- Path types: build_mvp, validate_first, build_community, content_first, experiment, pivot
- End with recommended path for this founder + one sentence why

**Section 11: Assumptions & Evidence** (uses WHY-refinement)
- 3-5 load-bearing assumptions (apply "why does this matter?" to surface hidden ones)
- Each: evidence level (supported/belief/untested), source, falsification test, cheapest test
- Multi-phase vision stress test if applicable
- Confidence summary

D) Update JSON schema to include:
```json
{
  "recommended_path": "build_mvp | validate_first | build_community | content_first | experiment | pivot",
  "positioning": {
    "territory": "string",
    "defensibility": "weak | moderate | strong",
    "founder_market_fit": "strong | moderate | weak"
  },
  "assumptions": [
    {
      "claim": "string",
      "evidence_level": "supported | belief | untested",
      "falsification_test": "string"
    }
  ]
}
```

E) Update section count: "5 narrative parts containing 11 sections"

### 6. Update schema validation
**File:** `scripts/validate_schema.py`

A) concept-anchor.json: validate `founder_intent` when present (motivation enum, constraints.time_horizon enum, constraints.team enum). Add `growth_model` to strategic_signals enum validation.

B) validation-report.json: validate `recommended_path` enum, `positioning.defensibility` enum, `positioning.founder_market_fit` enum, `assumptions` array structure with `evidence_level` enum.

All new fields validated only when present (backward compatible).

### 7. Add OSS benchmarks
**File:** `references/benchmarks.md`

Add "## Open Source / Community" section after "Developer Tool":
- GitHub stars growth: 50-300/month (early)
- Contributor retention (6mo): 5-15%
- Time to first contribution: <30 minutes
- npm/PyPI weekly downloads growth: 20-50% MoM (early)
- Issue response time: <48 hours
- Fork-to-star ratio: 0.1-0.3

### 8. Update test fixtures
**Files:**
- `tests/fixtures/valid_concept_anchor.json` - add `founder_intent` + `growth_model`
- `tests/fixtures/valid_concept_anchor_with_term_flags.json` - same additions
- `tests/fixtures/invalid_concept_anchor.json` - add invalid enums for new fields
- `tests/fixtures/valid_validation_report.json` - add `recommended_path`, `positioning`, `assumptions`
- `tests/fixtures/invalid_validation_report.json` - add invalid values for new fields

**New tests in** `tests/test_plugin_sanity.py`:
- `test_invalid_concept_anchor_founder_intent` - catches bad motivation enum
- `test_invalid_concept_anchor_growth_model` - catches bad growth_model enum
- `test_valid_validation_report_with_new_fields` - new fields pass
- `test_invalid_validation_report_bad_path` - catches bad recommended_path
- `test_invalid_validation_report_bad_positioning` - catches bad defensibility/fit

### 9. Retouch blog post
**File:** `docs/blog/posts/2026-03-22-the-validation-tool-that-couldnt-validate-itself.md`

The post documents exactly the gaps this work closes. Add an update section at the end (before the final paragraph) that bridges from "here's what broke" to "here's what we're building to fix it." Specifically:

- The three things the tool missed (identity crisis, Evolution insight, unvalidated core assumption) all stem from one root cause: the pipeline processes the idea but ignores the founder
- We researched intent analysis across AI agent frameworks, requirements engineering, and product strategy. Key finding: no major system solves "raw idea -> structured intent." This is genuinely unsolved.
- The fix: five-component intent decomposition (Expectations, Conditions, Targets, Context, Information), WHY-refinement to probe beyond stated goals, backward-chaining from desired impact, and strategic options that go beyond GO/PIVOT/NO-GO
- Honest framing: this is the design, not the result. We haven't validated that it works yet.

**Tone guidance** (from CLAUDE.md blog standards): Write from real experience, flag uncertainty, don't perform confidence we haven't earned. "I think this will help" not "this solves the problem."

## Key Design Decisions

- **`founder_intent` is optional**: If user skips Step 0, idea-analyst infers what it can. All downstream agents check `if present`. Backward compatible.
- **Concept anchor = context object**: All agents already read it. Enriching it carries project-type awareness without new files or dependencies.
- **Single agent for gaps 2/3/4**: Per single-agent lesson, positioning + strategy + assumptions are cross-referencing tasks that need full context. Report-synthesizer already has it.
- **Adaptive, not conditional agents**: Market-researcher adapts its output format based on project type, not a separate OSS-market-researcher agent.

## Verification

1. `python3 -m pytest tests/test_plugin_sanity.py -v` - all existing + new tests pass
2. Functional test with commercial idea: `/haytham:validate "a gym leaderboard with anonymous handles"` - verify Step 0 appears, report includes PART 5
3. Functional test with OSS idea: `/haytham:validate "an open source CLI for managing dotfiles"` - verify market research uses adoption metrics, report positioning analysis references OSS landscape
4. Check no breaking changes: validate.md `--from N` resume still works, haytham.md full flow still works
