# Research Brief Stage Design

**Date:** 2026-02-25
**Status:** Proposed
**Phase:** WHY (Idea Validation)

## Problem

Users can't see what the system understood about their idea or what research it gathered before receiving a GO/PIVOT/NO-GO recommendation. This creates two issues:

1. **Trust gap:** Users don't know what evidence backs the recommendation
2. **No alignment checkpoint:** If the system misunderstood the idea or researched the wrong things, the error propagates silently into synthesis

## Solution

Add a `research_brief` stage between `market_context` and `report_synthesis`. This stage produces a non-opinionated research document with two sections:

1. **Our Understanding of Your Idea** (from concept anchor): problems, target audience, value proposition
2. **What We Found** (from market context): market data, competitors, JTBD, TAM/SAM/SOM, data gaps, source confidence

The user reviews and refines the brief through conversation (same interaction pattern as other stages). A clear message tells the user that research accuracy affects recommendation quality. The final brief becomes the single source of truth for synthesis.

## Architecture

### Workflow Change

```
BEFORE: idea_analysis -> market_context -> report_synthesis -> GATE 1
AFTER:  idea_analysis -> market_context -> research_brief -> report_synthesis -> GATE 1
                                                |
                                          user reviews &
                                          refines via chat
```

### Data Flow Change

```
BEFORE:
  idea_analysis -----+
  market_context -----+-> report_synthesis -> GO/PIVOT/NO-GO
  concept_anchor -----+
  system_goal --------+

AFTER:
  idea_analysis ---+
  market_context ---+-> research_brief_agent -> [user refines via chat] -> research_brief
  concept_anchor --+                                                            |
                                                                                v
  system_goal ------+                                                   report_synthesis
  concept_anchor ---+-> (reads research_brief as single research input)     |
                                                                        GO/PIVOT/NO-GO
```

Report synthesis no longer reads raw `idea_analysis` or `market_context`. It reads the user-validated `research_brief`.

## Research Brief Agent

- **Name:** `research_brief`
- **Input:** `idea_analysis`, `market_context`, `concept_anchor_str`
- **Output:** Structured markdown (two sections)
- **Model tier:** LIGHT (formatting/extraction, not reasoning)
- **Interaction:** Conversational (multi-turn refinement with user)

### Prompt Constraints

- No scores, ratings, or rankings
- No recommendations or judgment language ("strong", "weak", "promising", "concerning")
- No comparative value statements ("better than", "worse than")
- Present facts, numbers, and quotes only
- Flag data gaps explicitly ("pricing data not found for 3/5 competitors")

### Output Structure

```markdown
## Our Understanding of Your Idea
- Problem: [from concept anchor]
- Target Audience: [from concept anchor]
- Value Proposition: [from concept anchor]

## What We Found

### Market Overview
- TAM/SAM/SOM numbers with sources
- Market trends (factual, no judgment)

### Jobs-to-be-Done
- Core job statement
- Current solutions people use

### Competitors Identified
- For each: name, what they do, traction numbers, pricing (if found), user sentiment quotes
- Data gaps flagged per competitor

### What We Couldn't Verify
- Explicit list of data gaps and low-confidence findings
```

### Post-Validation

Lightweight check for judgment language (blocklist of words like "strong", "promising", "recommend"). Works here because we're checking for absence of opinion, not presence of quality.

## Impact on Report Synthesis

### What Changes

- `run_report_synthesis` embeds `research_brief` in the query instead of `idea_analysis` + `market_context`
- Prompt references "the validated research brief" instead of "upstream research outputs"

### What Does NOT Change

- Report output structure (ValidationReport model, 8-section report)
- Post-validators (`validate_som_arithmetic`, `validate_regulated_domain_safety`)
- Gate 1 behavior
- All downstream workflows (MVP scope, capability model, etc.)

### Context Size

The brief may be more concise than raw outputs (~5K chars instead of ~15K). This is fine because:
- Same facts, without duplication and agent-specific formatting
- User corrections may add information raw research missed
- ADR-026's principle (full context beats fragmented) still holds: the brief IS the full validated context

## User Interaction

Same conversational pattern as other Haytham stages:

1. Brief renders in Streamlit UI
2. Message to user: "Please review the research below. Our recommendations are only as good as the research they're based on. If anything looks wrong, irrelevant, or missing, let us know before we continue."
3. User chats to refine ("you missed competitor X", "TAM looks off", "my audience is actually Y")
4. Agent updates the brief through conversation
5. User signals to continue when satisfied

## Files to Create

- `haytham/agents/worker_research_brief/worker_research_brief_prompt.txt`

## Files to Modify

- `haytham/workflow/stage_registry.py` - new StageMetadata
- `haytham/workflow/stages/configs.py` - new StageExecutionConfig
- `haytham/workflow/burr_actions.py` - new Burr action
- `haytham/workflow/burr_workflow.py` - updated transition (market_context -> research_brief -> report_synthesis)
- `haytham/workflow/entry_conditions.py` - new validator + update report_synthesis validator
- `haytham/config.py` - new AGENT_CONFIGS entry
- `haytham/workflow/stages/idea_validation.py` - update `run_report_synthesis` to read `research_brief`

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Brief as source of truth | Yes | Two artifacts (raw + brief) leaves gap for synthesis to use uncorrected data |
| Separate user_feedback key | No | User corrections incorporated into brief via conversation. Brief is the single artifact. |
| Model tier | LIGHT | Formatting and extraction, not reasoning or synthesis |
| Idea analysis in brief | Concept only | User knows their idea. Show system's interpretation for alignment, not research strategy details. |
| Post-validation | Judgment language blocklist | Checking for absence of opinion is a valid string-level check |
