---
description: Validate a startup idea and produce an implementation-ready specification
argument-hint: [startup idea | URL] [--batch]
allowed-tools: Read, Write, Edit, Bash, Glob, Agent, WebSearch, WebFetch
---

# Haytham: Startup Idea Validation & Specification

You are orchestrating a 4-phase startup validation workflow. Follow each phase in order. Do not skip phases. In normal mode, do not proceed to the next phase without user approval at the gate. In BATCH_MODE, auto-approve all gates and skip all interactive review steps.

**IMPORTANT:** Always read agent output from files, not from conversation history. Before each phase, verify previous phase output files exist by reading them.

## Upstream Dependencies

| Phase | Agent | Reads From |
|-------|-------|------------|
| 1 | idea-analyst | `.haytham/project.yaml` (user input) |
| 1 | market-researcher | `phase-1-why/idea-analysis.md`, `phase-1-why/concept-anchor.json` |
| 1 | competitor-researcher | `phase-1-why/idea-analysis.md`, `phase-1-why/concept-anchor.json` |
| 1 | research-briefer | `phase-1-why/idea-analysis.md`, `phase-1-why/market-research.md`, `phase-1-why/competitor-research.md` |
| 1 | report-synthesizer | `phase-1-why/research-brief.md`, `phase-1-why/concept-anchor.json`, `phase-1-why/competitor-research.md`, `phase-1-why/founder-corrections.json` (if exists), `references/benchmarks.md` |
| 2 | mvp-scoper | `phase-1-why/validation-report.md`, `phase-1-why/idea-analysis.md`, `phase-1-why/concept-anchor.json` |
| 2 | capability-modeler | `phase-2-what/mvp-scope.md`, `phase-1-why/idea-analysis.md`, `phase-1-why/concept-anchor.json` |
| 3 | architect | `phase-2-what/capabilities.json`, `phase-2-what/system-traits.json`, `phase-2-what/mvp-scope.md` |
| 4 | spec-generator | `phase-2-what/capabilities.json`, `phase-2-what/mvp-scope.md`, `phase-2-what/system-traits.json`, `phase-3-how/architecture-decisions.json`, `phase-3-how/build-buy.json`, `phase-1-why/concept-anchor.json` |
| 5 | build (command) | `phase-4-specs/openspec/`, `phase-3-how/research-directives.json` |

All paths relative to `.haytham/session/`.

## Setup

### Flag Parsing

First, check if the argument contains `--batch`. If so:
- Remove `--batch` from the argument string (the remainder is the idea or URL)
- Set BATCH_MODE to true

### URL Detection

Check if the argument looks like a URL:

**If it matches `https?://(www\.)?reddit\.com/`** (Reddit post):
1. Use WebFetch to retrieve the URL content
2. Extract the post title and body text from the fetched content
3. Set IDEA_TEXT to the extracted title + body
4. Set SOURCE_URL to the original URL, SOURCE_TYPE to `reddit_post`

**If it matches `https?://(www\.)?github\.com/`** (GitHub repo):
1. Parse `{owner}/{repo}` from the URL path
2. Use WebFetch to retrieve `https://raw.githubusercontent.com/{owner}/{repo}/main/README.md` (fall back to `master` if 404)
3. Also use WebFetch on the GitHub repo page to extract the repo description
4. Set IDEA_TEXT to: repo description + "\n\n" + first 2000 characters of README content
5. Set SOURCE_URL to the original URL, SOURCE_TYPE to `github_repo`

**If neither** (plain text):
- Set IDEA_TEXT to the argument as-is
- Set SOURCE_URL to null, SOURCE_TYPE to `text`

If a URL was detected, tell the user what was extracted:
> **Source:** [SOURCE_TYPE] at [SOURCE_URL]
> **Extracted idea:** [first 200 chars of IDEA_TEXT]...

If the extracted text is under 50 characters, warn:
> **Warning:** Extracted text is very short. The analysis may be thin. Consider providing a text description instead.

### Initialize Project

1. Create `.haytham/` directory if it doesn't exist
2. Create `.haytham/session/phase-1-why/`, `.haytham/session/phase-2-what/`, `.haytham/session/phase-3-how/`, `.haytham/session/phase-4-specs/` directories
3. Write to `.haytham/project.yaml`:
   ```yaml
   idea: |
     [IDEA_TEXT]
   source:
     url: [SOURCE_URL or null]
     type: [SOURCE_TYPE]
     fetched_at: [current ISO timestamp]
   created_at: [current ISO timestamp]
   batch_mode: [true if BATCH_MODE, omit otherwise]
   state:
     phase_1:
       last_completed_step: 0
       updated_at: [current ISO timestamp]
   ```

## State Updates

After each step completes successfully, update `.haytham/project.yaml` to set the appropriate `state.phase_N.last_completed_step` and `updated_at`. Use the Edit tool to update only the state section.

---

## Phase 1: WHY (Idea Validation)

**Goal:** Understand the idea, research the market, and produce a GO/PIVOT/NO-GO recommendation.

Before launching any agents, read `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/marketplace.json` and extract the `version` field from `plugins[0]`.

If BATCH_MODE is true, tell the user:

> **Phase 1: Idea Validation** (haytham vVERSION) -- BATCH MODE
>
> Running unattended. Skipping Steps 0, 4, 6 (no human review).
> Steps: 1 (Idea Analysis) -> 2 (Market Research) -> 3 (Research Brief) -> 5 (Validation Report)
>
> Estimated total: ~6 minutes.

Otherwise, tell the user:

> **Phase 1: Idea Validation** (haytham vVERSION)
>
> This will run 7 steps:
> 0. Founder Context — 3 quick questions about your goals (~30 sec) ← YOU ANSWER
> 1. Idea Analysis — expand and classify your idea (~1 min)
> 2. Market Research — web search for competitors, sizing, sentiment (~3 min)
> 3. Research Brief — neutral summary of findings (~1 min)
> 4. Founder Review — you review and correct ← YOU DECIDE HERE
> 5. Validation Report — GO/PIVOT/NO-GO with strategic analysis (~1 min)
> 6. Gate Decision — you approve or reject
>
> Step 2 is the heaviest step (runs web searches). Estimated total: ~8 minutes.

### Step 0: Founder Context

**Skip this step if BATCH_MODE is true.** Also skip if a new idea was NOT provided (resuming from state). Also skip if `.haytham/project.yaml` already contains a `founder_context` section.

If skipped due to BATCH_MODE, do NOT write `founder_context`. The idea-analyst will infer what it can.

Ask the founder:

> Before we dive in, three quick questions so the analysis matches your goals:
>
> 1. **Why are you building this?** (learning / revenue / community growth / credibility / solving your own problem)
> 2. **What does success look like in 3 months?** (one sentence)
> 3. **What are you working with?** (solo + bootstrapped / solo + some funding / small team)
>
> Quick answers are fine. Say "skip" to let us infer from the idea.

If the user says "skip" or provides no answer, proceed to Step 1 without writing `founder_context`. The idea-analyst will infer what it can.

If the user answers, write the `founder_context` section to `.haytham/project.yaml` using the Edit tool:

```yaml
founder_context:
  motivation: [mapped to: learning | revenue | community | credibility | solving_own_problem]
  success_criteria: "[founder's free text answer]"
  time_horizon: [inferred: weeks | months | quarters]
  team: [mapped to: solo | small_team | funded_team]
```

Map the user's natural language answers to the enum values. If the time horizon is ambiguous, infer from the success criteria.

### Step 1: Idea Analysis

Tell the user:
> **Step 1/6: Idea Analysis**
> Expanding your idea into a structured concept so we have a clear foundation for research.

Launch an **idea-analyst** agent with this task:
> Read the startup idea from `.haytham/project.yaml`. Analyze it following your instructions. Write idea analysis to `.haytham/session/phase-1-why/idea-analysis.md` and concept anchor to `.haytham/session/phase-1-why/concept-anchor.json`.

If the agent writes `.haytham/session/phase-1-why/idea-clarification.md`, read it and present the clarification questions or suggestions to the user. Wait for their response, update `.haytham/project.yaml` with the refined idea, and re-run Step 1.

After the agent completes, read `.haytham/session/phase-1-why/idea-analysis.md` and `.haytham/session/phase-1-why/concept-anchor.json`. Present a structured digest:

> **Step 1 complete.** We analyzed your idea and saved two files:
> - `idea-analysis.md` — problem analysis, target segments, UVP, and concept health
> - `concept-anchor.json` — invariants that keep downstream agents faithful to your idea
>
> Here's the summary:
>
> - **Core concept:** [One-line summary of what this product does]
> - **Top problems:**
>   a. [Problem 1] (Pain: [intensity])
>   b. [Problem 2] (Pain: [intensity])
>   c. [Problem 3] (Pain: [intensity])
> - **Primary segment:** [The primary user segment and their defining behavior]
> - **UVP:** [The unique value proposition as written]
> - **Concept health:** Pain Clarity: [X], Trigger Strength: [X], WTP Signal: [X]

Then read `founder_intent`, `strategic_signals`, and `founder_profile` from `concept-anchor.json` and present them:

> **Founder intent** (from your answers + inference):
> - **Motivation:** [motivation]
> - **Success in 3 months:** [success_criteria]
> - **Expected impact:** [expected_impact]
> - **Team/resources:** [team] ([time_horizon] horizon)

> **Strategic assumptions** (inferred from your idea, correct anything wrong):
> - **Founder profile:** [technical_level] ([inference_basis])
> - **Business model:** [business_model]
> - **Growth model:** [growth_model]
> - **Success metric:** [success_metric]
> - **Distribution:** [distribution]

Then check if `concept-anchor.json` contains a non-empty `term_flags` array. If so, present them:

> **Ambiguous terms** (we picked an interpretation, check these):
>
> - **"[term]"** — Interpreted as: [chosen_interpretation]
>   - Alternative: [each alternative on its own line]
>   - Why it matters: [impact]

(Repeat for each flag.)

Then present options. If term_flags were shown, use 4 options; otherwise use 3:

> **What next?**
> 1. Looks good, continue to market research
> 2. I need to correct some assumptions (say which ones and what they should be)
> 3. I want to steer research toward specific competitors or topics
> 4. A term interpretation above is wrong (say which term and the correct meaning)

(Option 4 only appears when term_flags are present.)

If the user corrects any strategic signals, update `concept-anchor.json` using the Edit tool to reflect their corrections before proceeding.

**If the user picks option 4 (term correction):** Update `.haytham/project.yaml` by adding a `term_clarifications` section with the user's correction. Then re-launch the **idea-analyst** agent with this task:
> Read the startup idea from `.haytham/project.yaml`. The user clarified the following term(s): [paste user's correction]. Use the clarified meaning. Analyze it following your instructions. Write idea analysis to `.haytham/session/phase-1-why/idea-analysis.md` and concept anchor to `.haytham/session/phase-1-why/concept-anchor.json`.

After the agent completes, read the updated files and present the revised digest (same format as above). The corrected term should no longer appear in `term_flags`.

Update state: `last_completed_step: 1`.

### Step 2: Market & Competitor Research

Read `.haytham/session/phase-1-why/idea-analysis.md` to confirm it exists. Extract the domain/category.

Tell the user:
> **Step 2/6: Market & Competitor Research**
> Checking if anyone else is solving this, and how big the opportunity is. Running two research tracks in parallel: market intelligence and competitor analysis in [domain from idea analysis].
> This is the longest step (~3 min) because it runs web searches.

Launch BOTH agents in parallel:

1. A **market-researcher** agent with this task:
   > Read the idea analysis from `.haytham/session/phase-1-why/idea-analysis.md` and concept anchor from `.haytham/session/phase-1-why/concept-anchor.json`. Research the market. Write results to `.haytham/session/phase-1-why/market-research.md`.

2. A **competitor-researcher** agent with this task:
   > Read the idea analysis from `.haytham/session/phase-1-why/idea-analysis.md` and concept anchor from `.haytham/session/phase-1-why/concept-anchor.json`. Research competitors. Write results to `.haytham/session/phase-1-why/competitor-research.md`.

After both agents complete, read `.haytham/session/phase-1-why/market-research.md` and `.haytham/session/phase-1-why/competitor-research.md` and present a structured digest:

> **Market & competitor research complete.** Here's what we found:
>
> - **Market:** [Primary category], TAM: [X], SAM: [X], SOM: [X]
> - **Competitors:** [List each competitor name + one-line description]
> - **User sentiment:** [One key "love" and one key "hate" quote from real users]
> - **Key gap:** [The most significant gap or unmet need found]
> - **Top risk:** [The biggest market-structural risk or challenge]

Update state: `last_completed_step: 2`.

### Step 3: Research Brief

Tell the user:
> Research gathered. Compiling a neutral summary for your review. No scores or judgments, just facts.

Launch a **research-briefer** agent with this task:
> Read idea analysis from `.haytham/session/phase-1-why/idea-analysis.md`, market research from `.haytham/session/phase-1-why/market-research.md`, and competitor research from `.haytham/session/phase-1-why/competitor-research.md`. Compile a neutral research brief. Write to `.haytham/session/phase-1-why/research-brief.md`.

After the agent completes, read `.haytham/session/phase-1-why/research-brief.md` and output its FULL contents inline in your response. The user must be able to read the entire brief without expanding anything or opening a file. Do NOT summarize or abbreviate — print every line.

Update state: `last_completed_step: 3`.

### Step 4: Founder Review

**If BATCH_MODE is true:** Skip the review prompt. Tell the user:
> **Step 4 skipped (batch mode).** Auto-approving research brief.

Update state: `last_completed_step: 4`. Proceed directly to Step 5.

**Otherwise**, ask:
> **Review the brief above.** Check these dimensions:
> - **Problem statement** — is this the right problem?
> - **Competitors** — are we missing anyone, or including wrong ones?
> - **Market size** — in the right ballpark?
> - **Competitive positioning** — are you a direct competitor, complementary, or serving a different segment?
> - **Business model** — does the assumption match your intent?
> - **Goals & motivation** — does the analysis match what you're trying to achieve?
>
> **What next?**
> 1. Looks good, continue to the validation report
> 2. I have corrections (say which dimensions and what to change)

If the user provides corrections, write them to `.haytham/session/phase-1-why/founder-corrections.json`:
```json
{
  "corrections": [
    {
      "dimension": "problem | competition | market_size | positioning | business_model | other",
      "correction": "What the founder said, verbatim or close paraphrase"
    }
  ],
  "updated_at": "[ISO timestamp]"
}
```

Then update the relevant upstream files (re-run affected steps if factual corrections, or note the strategic corrections for the report-synthesizer). If the corrections are primarily about framing or positioning (not factual errors), you do NOT need to re-run research. Instead, proceed to Step 5 and the report-synthesizer will read the corrections file.

Update state: `last_completed_step: 4`.

### Step 5: Validation Report

Tell the user:
> **Step 5/6: Validation Report**
> Weighing the evidence to produce a GO, PIVOT, or NO-GO recommendation with positioning analysis and strategic options.

Launch a **report-synthesizer** agent with this task:
> Read all Phase 1 files (idea-analysis.md, market-research.md, competitor-research.md, concept-anchor.json, founder-corrections.json if it exists, project.yaml) and industry benchmarks from `${CLAUDE_PLUGIN_ROOT}/references/benchmarks.md`. Produce the validation report. Write to `.haytham/session/phase-1-why/validation-report.md` and `.haytham/session/phase-1-why/validation-report.json`.

After the agent completes, read `.haytham/session/phase-1-why/validation-report.md` and output its FULL contents inline in your response. The user must be able to read the entire report without expanding anything or opening a file. Do NOT summarize or abbreviate — print every line of the report.

After the full report, read `.haytham/session/phase-1-why/validation-report.json` and present key takeaways:

> **Key takeaways:**
> - **Verdict:** [recommendation] — **Recommended path:** [recommended_path]
> - **Position:** [positioning.territory] (defensibility: [positioning.defensibility], founder-market fit: [positioning.founder_market_fit])
> - **Critical assumptions:** [count] load-bearing assumptions ([X] supported, [Y] belief, [Z] untested)
> - **First action:** [executive_summary.closing_remark]
>
> Full report saved to `.haytham/session/phase-1-why/validation-report.md`

Update state: `last_completed_step: 5`.

### Step 6: Gate 1

**If BATCH_MODE is true:** Read the recommendation from `.haytham/session/phase-1-why/validation-report.json`. Auto-write gate decision:
```json
{
  "phase": 1,
  "recommendation": "[from validation-report.json]",
  "user_decision": "batch-auto-approved",
  "notes": "Auto-approved in batch mode",
  "decided_at": "[ISO timestamp]"
}
```
Tell the user:
> **Gate 1 auto-approved (batch mode).** Verdict: [recommendation]. Proceeding to Phase 2.

Update state: `last_completed_step: 6`. Skip to Phase 2.

**Otherwise**, ask:
> **Review the report above. Specifically:**
> - Does the evidence support the verdict?
> - Is the positioning analysis right? Is the territory you'd actually claim?
> - Do the strategic options make sense for your situation?
> - Are there load-bearing assumptions the report missed?
> - Do you agree with the recommended path?
>
> You can ask questions about the report, request changes, or say "approve" to proceed to MVP specification.

- If **NO-GO** and user agrees: Stop and explain the key reasons.
- If **PIVOT** and user agrees: Note the pivot direction, update `.haytham/project.yaml` with the pivoted idea, and restart from Step 1.
- If **GO** and user approves: Write gate decision and continue.
- If user disagrees with recommendation: Discuss and proceed based on their decision.

Write gate decision:
```json
// .haytham/session/phase-1-why/gate-decision.json
{
  "phase": 1,
  "recommendation": "GO|PIVOT|NO-GO",
  "user_decision": "approved|rejected|overridden",
  "notes": "Any user feedback",
  "decided_at": "[ISO timestamp]"
}
```

Update state: `last_completed_step: 6`.

---

## Phase 2: WHAT (MVP Specification)

**Goal:** Define what the MVP includes and model its capabilities.

Before launching any agents, tell the user:

> **Phase 2: MVP Specification**
>
> This will run 4 steps:
> 1. MVP Scope — define what's in, what's out, and the core flows (~1 min)
> 2. Scope Review — you shape the scope before capabilities are derived ← YOU STEER HERE
> 3. Capability Model — extract capabilities and system traits from your approved scope (~1 min)
> 4. Gate 2 — you approve the final capabilities ← YOU DECIDE HERE
>
> Estimated total: ~4 minutes.

### Step 7: MVP Scope

Verify `.haytham/session/phase-1-why/gate-decision.json` exists.

Tell the user:
> **Step 1/4: MVP Scope**
> Translating the validated idea into a concrete MVP definition. What's in, what's out, and what the core user flow looks like.

Launch an **mvp-scoper** agent with this task:
> Read the validation report from `.haytham/session/phase-1-why/validation-report.md`, idea analysis from `.haytham/session/phase-1-why/idea-analysis.md`, and concept anchor from `.haytham/session/phase-1-why/concept-anchor.json`. Define the MVP scope. Write to `.haytham/session/phase-2-what/mvp-scope.md`.

After the agent completes, read `.haytham/session/phase-2-what/mvp-scope.md` and present a structured digest:

> **MVP scope defined.** Here's the shape of your MVP:
>
> - **The One Thing:** [The single sentence MVP purpose]
> - **IN scope:** [List the key items that are in]
> - **OUT scope:** [List the key items explicitly excluded]
> - **Appetite:** [Time/effort budget]
> - **Core flow:** [One-line description of the primary user journey]

Update state: `last_completed_step: 7`.

### Step 8: Scope Review

This is a refinement loop. The user must approve the scope BEFORE capabilities are derived from it.

**If BATCH_MODE is true:** Skip the review. Tell the user:
> **Scope review skipped (batch mode).** Auto-approving MVP scope.

Update state: `last_completed_step: 8`. Proceed to Step 9.

**Otherwise**, ask:
> **Review the MVP scope above. Specifically:**
> - Is "The One Thing" right? Does it capture what matters?
> - Are the IN/OUT scope boundaries correct?
> - Is the appetite realistic?
> - Are the core flows right?
>
> Say "looks good" to proceed to capability extraction, or tell me what to change.

**If the user requests changes:**
1. Re-launch the **mvp-scoper** agent with this task:
   > Read the current MVP scope from `.haytham/session/phase-2-what/mvp-scope.md`, the validation report from `.haytham/session/phase-1-why/validation-report.md`, idea analysis from `.haytham/session/phase-1-why/idea-analysis.md`, and concept anchor from `.haytham/session/phase-1-why/concept-anchor.json`. The user reviewed the scope and requested these changes: [PASTE THE USER'S EXACT CORRECTIONS HERE]. Revise the MVP scope to incorporate these changes. Write the updated scope to `.haytham/session/phase-2-what/mvp-scope.md`.
2. Read the updated `.haytham/session/phase-2-what/mvp-scope.md` and present the revised digest
3. Ask the user to review again. **Repeat until the user approves.**

**If the user approves:** Proceed to Step 9.

Update state: `last_completed_step: 8`.

### Step 9: Capability Model

Tell the user:
> **Step 3/4: Capability Model**
> Scope approved. Now extracting the specific capabilities your MVP needs from the scope you just approved.

Read `.haytham/session/phase-2-what/mvp-scope.md` and count the number of IN SCOPE items in the MVP Boundaries table. Then launch a **capability-modeler** agent with this task:
> Read the MVP scope from `.haytham/session/phase-2-what/mvp-scope.md`, idea analysis from `.haytham/session/phase-1-why/idea-analysis.md`, and concept anchor from `.haytham/session/phase-1-why/concept-anchor.json`. The MVP scope has [N] IN SCOPE items. Produce one functional capability per distinct user-observable behavior. Simple IN SCOPE items produce one capability. Complex items (multi-step pipelines, processes with multiple distinct behaviors) produce one per behavior, each referencing the same serves_scope_item. Write to `.haytham/session/phase-2-what/capabilities.json` and `.haytham/session/phase-2-what/system-traits.json`.

After the agent completes, read `.haytham/session/phase-2-what/capabilities.json` and `.haytham/session/phase-2-what/system-traits.json` and present a structured digest:

> **Capability model complete.**
>
> - **Functional capabilities:** [Count] — [list capability names]
> - **Non-functional capabilities:** [Count] — [list capability names]
> - **System traits:** [List key traits like auth model, data sensitivity, etc.]
> - **Traceability:** Each capability traces to [IN SCOPE items / problems from Phase 1]

Update state: `last_completed_step: 9`.

### Step 10: Gate 2

**If BATCH_MODE is true:** Auto-write gate decision with `user_decision: "batch-auto-approved"`. Tell the user:
> **Gate 2 auto-approved (batch mode).** Proceeding to technical design.

Update state: `last_completed_step: 10`. Skip to Phase 3.

**Otherwise**, read `.haytham/session/phase-2-what/capabilities.json` and output the following inline in your response (the user must see this without expanding anything):
- Functional capabilities with traceability to scope items
- Non-functional capabilities
- System traits classification

Ask:
> **Review the capabilities. Specifically:**
> - Are the capabilities the right decomposition of the scope?
> - Are there capabilities that should be merged, split, or removed?
> - Are the non-functional requirements right for this type of product?
>
> Approve to proceed to technical design, or request changes.

**If the user requests changes:**
1. Re-launch the **capability-modeler** agent with this task:
   > Read the MVP scope from `.haytham/session/phase-2-what/mvp-scope.md`, idea analysis from `.haytham/session/phase-1-why/idea-analysis.md`, concept anchor from `.haytham/session/phase-1-why/concept-anchor.json`, and the current capabilities from `.haytham/session/phase-2-what/capabilities.json`. The user reviewed the capabilities and requested these changes: [PASTE THE USER'S EXACT CORRECTIONS HERE]. Revise the capability model to incorporate these changes. Write updated files to `.haytham/session/phase-2-what/capabilities.json` and `.haytham/session/phase-2-what/system-traits.json`.
2. Read the updated files and present the revised digest
3. Ask the user to review again. **Repeat until the user approves.**

**When the user approves**, write gate decision:
```json
// .haytham/session/phase-2-what/gate-decision.json
{
  "phase": 2,
  "user_decision": "approved|rejected",
  "scope_revisions": 0,
  "capability_revisions": 0,
  "notes": "Any user feedback",
  "decided_at": "[ISO timestamp]"
}
```

Set `scope_revisions` and `capability_revisions` to the number of times each was re-generated based on user corrections.

Update state: `last_completed_step: 10`.

---

## Phase 3: HOW (Technical Design)

**Goal:** Decide on infrastructure and architecture.

Before launching any agents, tell the user:

> **Phase 3: Technical Design**
>
> This will run 3 steps:
> 1. Architecture — build/buy analysis and technology decisions (~2 min)
> 2. Review — you review the architecture
> 3. Gate 3 — you approve the design ← YOU DECIDE HERE
>
> Estimated total: ~3 minutes.

### Step 11: Architecture

Verify `.haytham/session/phase-2-what/gate-decision.json` exists.

Tell the user:
> **Step 1/3: Architecture**
> Deciding what to build, what to buy, and how the pieces fit together.

Launch an **architect** agent with this task:
> Read the capabilities, MVP scope, and system traits. Produce build/buy analysis, architecture decisions, and research directives. Write to `.haytham/session/phase-3-how/build-buy.json`, `.haytham/session/phase-3-how/architecture-decisions.json`, and `.haytham/session/phase-3-how/research-directives.json`.

After the agent completes, read `.haytham/session/phase-3-how/build-buy.json`, `.haytham/session/phase-3-how/architecture-decisions.json`, and `.haytham/session/phase-3-how/research-directives.json` and present a structured digest:

> **Architecture designed.** Here's the technical plan:
>
> - **Stack:** [Key technologies chosen]
> - **Build vs Buy:** [Summary of what's built custom vs. third-party services]
> - **Key decisions:** [List the 2-3 most important architecture decisions]
> - **Research directives:** [N] capabilities flagged ([list classifications used])
> - **Estimated monthly cost:** [Cost range]
> - **Integration effort:** [Effort estimate]

Update state: `last_completed_step: 11`.

### Step 12: Review & Gate 3

**If BATCH_MODE is true:** Auto-write gate decision with `user_decision: "batch-auto-approved"`. Tell the user:
> **Gate 3 auto-approved (batch mode).** Proceeding to spec generation.

Update state: `last_completed_step: 12`. Skip to Phase 4.

**Otherwise**, read all three output files and output the following inline in your response (the user must see this without expanding anything):
- **Recommended Stack**: Service name, category, BUILD/BUY/HYBRID, rationale
- **Architecture Decisions**: ID, name, what it covers, capabilities served
- **Research Directives:** [N] of [M] capabilities require pre-implementation research
  - CAP-F-NNN (Capability Name): classification(s) — N questions
  - (Repeat for each non-standard capability)
- **Integration Effort**: Estimated days
- **Monthly Cost**: Estimated range

Ask:
> **Review the technical design. Specifically:**
> - Does the technology stack fit your team's skills?
> - Are the build/buy decisions reasonable?
> - Is the estimated cost acceptable?
>
> Approve to proceed to specification generation, or request changes.

Write gate decision:
```json
// .haytham/session/phase-3-how/gate-decision.json
{
  "phase": 3,
  "user_decision": "approved|rejected",
  "notes": "Any user feedback",
  "decided_at": "[ISO timestamp]"
}
```

Update state: `last_completed_step: 12`.

---

## Phase 4: SPECS (OpenSpec Generation)

**Goal:** Generate an implementation-ready OpenSpec that a coding agent can use to build the system.

Before launching any agents, tell the user:

> **Phase 4: Specification Generation**
>
> This will run 3 steps:
> 1. OpenSpec Generation — produce SHALL requirements with Gherkin scenarios (~2 min)
> 2. Review — you review the specification
> 3. Detail Review — drill into specific domains if needed ← YOU DECIDE HERE
>
> Estimated total: ~3 minutes.

### Step 13: OpenSpec Generation

Verify `.haytham/session/phase-3-how/gate-decision.json` exists.

Tell the user:
> **Step 1/3: OpenSpec Generation**
> Turning capabilities and architecture decisions into a complete specification with SHALL requirements and testable scenarios.

Launch a **spec-generator** agent with this task:
> Read all Phase 2 and Phase 3 outputs plus the concept anchor. Generate the OpenSpec directory tree. Write to `.haytham/session/phase-4-specs/openspec/` (config.yaml, project.md, and specs/*/spec.md).

After the agent completes, run validation:
```bash
python3 scripts/validate_openspec.py .haytham/session/phase-4-specs/openspec/ .haytham/session/phase-2-what/capabilities.json
```

If validation produces warnings, report them to the user before the digest.

Then read the generated files and present a structured digest:

> **OpenSpec generated.** Here's what was produced:
>
> - **Domains:** [count] — [list domain names]
> - **Requirements:** [count] SHALL statements across all domains
> - **Scenarios:** [count] Gherkin scenarios
> - **Architecture decisions:** [count] documented in project.md
> - **Coverage:** All [N] functional + [M] non-functional capabilities covered

Update state: `last_completed_step: 13`.

### Step 14: Final Review

**If BATCH_MODE is true:** Skip the review. Tell the user:
> **Final review skipped (batch mode).** Specification complete.

Update state: `last_completed_step: 14`. Skip to Completion.

**Otherwise**, read the OpenSpec files and output the following inline in your response (the user must see this without expanding anything):
- Domain list with requirement counts per domain
- Coverage check (all capabilities and decisions covered)
- config.yaml traits summary

Ask:
> **Review the specification. Specifically:**
> - Are the domain groupings right?
> - Do the SHALL statements capture what matters?
> - Are the scenarios testable?
>
> Say "looks good" or request changes.

Update state: `last_completed_step: 14`.

### Completion

Summarize what was produced:

```
Command               Output Directory
/haytham:validate  →  .haytham/session/phase-1-why/
/haytham:specify   →  .haytham/session/phase-2-what/
/haytham:design    →  .haytham/session/phase-3-how/
/haytham:plan      →  .haytham/session/phase-4-specs/openspec/
```

Tell the user:

> Your specification is complete. Ran 8 agents across 4 phases. All output files are in `.haytham/session/`. Run `/haytham:build` to set up your project for implementation with OpenSpec.
>
> **How did this go?** We're looking for honest feedback to make this better.
> Share your experience: https://github.com/arslan70/haytham/discussions
