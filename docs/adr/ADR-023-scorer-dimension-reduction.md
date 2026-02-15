# ADR-023: Evidence Enrichment & Scorer Dimension Reduction (8 → 6)

## Status
**Accepted** — 2026-02-11

## Context

### The Problem

The validation scorer evaluates startup ideas across 8 scored dimensions, each requiring distinct evidence cited from upstream stage outputs. Empirical testing reveals the scorer consistently fails to produce high-quality, dimension-specific evidence for all 8 dimensions.

Root cause analysis identified two issues:

1. **Evidence scarcity**: The upstream pipeline produces only ~5 distinct evidence clusters from ~2 real data sources (user's free-text idea + undirected web search). Eight dimensions drawing from 5 clusters forces evidence reuse, evidence-dimension mismatch, and unfalsifiable assessments.

2. **One genuinely overlapping pair**: Solution Feasibility and Operational Feasibility draw from the same risk_assessment claims and are hard to distinguish in practice.

### Why Not Just Reduce Dimensions?

The initial proposal (ADR-023 draft) was to reduce from 8 → 5 dimensions, dropping Founder-Market Fit, Operational Feasibility, and Adoption & Engagement Risk entirely. Analysis showed this treats the symptom (too many dimensions for available data) rather than the cause (too little data for the dimensions we need).

The real fix is two-pronged: **enrich the data sources** AND **reduce only the genuinely overlapping pair**.

### Current Data Sources (Before)

1. **User's free-text idea** + optional clarifying Q&A
2. **Undirected web search** — MI and CA agents search broadly with no domain filtering

This produces ~5 evidence clusters: pain signals, market sizing, competitive positioning, technical/operational claims, and revenue signals.

## Decision

### Part 1: Enrich Evidence Sources

#### 1a. Default Founder Persona

Add a `FounderPersona` frozen dataclass with sensible defaults (solo founder, bootstrapped, part-time, moderate risk appetite). Injected into:
- **Scorer query**: As `## Founder Context` section alongside upstream context blocks
- **Risk assessment query**: So operational risk claims can reference founder constraints

This enriches context for dimensions like Execution Feasibility (solo founder + marketplace = cold-start risk) and provides useful background for the risk assessment.

#### 1b. Directed Web Search

**Tier 1 — Prompt-level `site:` guidance** (zero code change): MI and CA prompts now include archetype-keyed `site:` operator examples (e.g., B2B SaaS → `site:g2.com`, Consumer → `site:reddit.com`).

**Tier 2 — Tool-level `include_domains` + `search_depth` params**: The `web_search` tool now accepts optional `include_domains` (list of domains) and `search_depth` ("basic" or "advanced"). Provider handling:
- **Tavily**: Passes both natively (already supported)
- **DuckDuckGo/Brave**: Translates `include_domains` into `site:` query prefix

#### 1c. Concept Health as Positive Evidence

Concept Health signals from concept expansion (pain clarity, trigger strength, WTP) are now used in BOTH directions by the scorer:
- **Negative** (existing): Weak signals cap scores
- **Positive** (new): Strong signals ARE evidence (Pain Clarity=Clear strengthens Problem Severity)

### Part 2: Dimension Reduction (8 → 6)

Merge **Solution Feasibility + Operational Feasibility → Execution Feasibility** and drop **Founder-Market Fit** (empirical testing showed the scorer consistently fails to cross-reference FounderPersona defaults with the idea description — this assessment is deferred to later stages).

| # | Dimension | Primary Evidence |
|---|-----------|-----------------|
| 1 | Problem Severity | Pain signals, concept health, directed forum search |
| 2 | Market Opportunity | TAM/SAM/SOM, directed industry reports |
| 3 | Competitive Differentiation | Gaps, switching costs, directed review sites |
| 4 | **Execution Feasibility** | Technical + operational claims (merged) |
| 5 | Revenue Viability | Revenue Evidence Tag, WTP, directed pricing search |
| 6 | Adoption & Engagement Risk | Trigger confidence, workaround effort, switching cost |

### Part 3: Evidence Deduplication

`record_dimension_score()` now rejects evidence with >70% word overlap (Jaccard) against any already-recorded dimension's evidence. Forces the scorer to find distinct evidence per dimension.

### Part 4: Scorer Prompt Updates

- **WHERE TO LOOK** hints per dimension, pointing to specific upstream sections
- Example domain changed from therapy/Therapeer to logistics SaaS/ShipFast
- Evidence dedup instruction: "Each dimension must cite distinct evidence"
- Tool call count updated: "Call record_dimension_score 6 times"
- Founder-Market Fit dimension and rubric removed

## Consequences

### Positive

- **More evidence per dimension**: FounderPersona + directed search expand the evidence pool from ~5 to ~7 clusters
- **Higher evidence quality**: Directed search targets high-value sources (G2, Crunchbase, Reddit) instead of generic web results
- **No forced evidence reuse**: 6 dimensions from 7+ evidence clusters eliminates the mismatch
- **Evidence dedup mechanically prevents the worst failure mode** (same quote for 3 dimensions)
- **Execution Feasibility is a cleaner concept**: "Can the MVP be built AND operated?" is a natural question; splitting it was artificial

### Negative

- **Slight composite recalibration**: 6 dimensions instead of 8 changes each dimension's weight from 12.5% to ~16.7%
- **Backward incompatibility**: Old session files with 8- or 7-dimension scorecards render correctly (dynamic iteration) but composite scores won't match if recomputed
- **Directed search depends on archetype accuracy**: If the anchor extractor misclassifies the archetype, `site:` guidance targets wrong sources

### Neutral

- **Threshold calibration unchanged**: GO (>3.5), PIVOT (2.1–3.5), NO-GO (≤2.0) remain the same
- **Counter-signals unchanged**: Minimum-2 check, reconciliation quality gates, consistency checker all preserved
- **dim8_inputs validator preserved**: Still validates Adoption & Engagement Risk against switching cost / trigger signals
- **Post-validators all preserved**: 6 cross-checks continue to run

## Alternatives Considered

### A. Reduce to 5 dimensions (original ADR-023 draft)

Drops Founder-Market Fit, Operational Feasibility, and Adoption & Engagement Risk. Treats the symptom (too many dimensions) rather than the cause (too little data). Loses valuable signal about behavioral change barriers.

### B. Keep 8 dimensions, add evidence dedup only

Mechanically blocks reuse but doesn't solve evidence scarcity. The scorer would be forced to retry with different (potentially lower-quality) evidence, or get stuck in rejection loops.

### C. Keep 8 dimensions, add multi-pass architecture

Forces evidence extraction before scoring. Triples latency/cost (3 agent calls) and still doesn't solve the fundamental overlap between Solution and Operational Feasibility.

## Files Affected

| Action | File |
|--------|------|
| Create | `docs/architecture/scoring-pipeline.md` |
| Edit | `CLAUDE.md` — add Scoring & Validation Pipeline subsection |
| Edit | `haytham/workflow/anchor_schema.py` — add FounderPersona dataclass |
| Edit | `haytham/workflow/stages/idea_validation.py` — inject persona into scorer query |
| Edit | `haytham/workflow/stages/configs.py` — inject persona into risk-assessment query |
| Edit | `haytham/agents/worker_validation_scorer/worker_validation_scorer_prompt.txt` — 7 dims, WHERE TO LOOK, new examples |
| Edit | `haytham/agents/worker_startup_validator/worker_startup_validator_prompt.txt` — reference founder context |
| Edit | `haytham/agents/worker_market_intelligence/worker_market_intelligence_prompt.txt` — add site: guidance |
| Edit | `haytham/agents/worker_competitor_analysis/worker_competitor_analysis_prompt.txt` — add site: guidance |
| Edit | `haytham/agents/utils/web_search.py` — add include_domains + search_depth params |
| Edit | `haytham/agents/tools/recommendation.py` — add evidence dedup |
| Edit | `haytham/agents/worker_validation_summary/validation_summary_models.py` — 8→6 description |
| Edit | `haytham/config.py` — 8→6 comment |
| Keep | `haytham/workflow/validators/dim8_inputs.py` — still validates Adoption & Engagement Risk |
| Keep | `tests/test_dim8_inputs.py` |
| Add | `tests/test_founder_persona.py` |
| Add | `tests/test_web_search_domains.py` |
| Edit | `tests/test_counter_signal_scoring.py` — add 7-dim new fixture |
| Edit | `tests/test_evidence_validation.py` — add evidence dedup tests |

## Verification

1. `pytest tests/ -v -m "not integration"` — full suite passes
2. `pytest tests/test_evidence_validation.py -v` — dedup + existing evidence gate tests pass
3. `pytest tests/test_counter_signal_scoring.py -v` — 7-dimension composite scores correct
4. `pytest tests/test_dim8_inputs.py -v` — dim8 validator still works
5. `pytest tests/test_founder_persona.py -v` — FounderPersona defaults and formatting
6. `pytest tests/test_web_search_domains.py -v` — domain filter translation
7. End-to-end: run psychologist idea — verify 6 scored dimensions with distinct evidence
