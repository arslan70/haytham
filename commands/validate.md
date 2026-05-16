---
description: Run Phase 1 (WHY) - Validate a startup idea with market research and produce a GO/PIVOT/NO-GO recommendation
argument-hint: [startup idea | URL] [--batch] or [--from N] to resume from step N
allowed-tools: Read, Write, Edit, Bash, Glob, Agent, TodoWrite, WebSearch, WebFetch
---

# Haytham: Idea Validation (Phase 1 - WHY)

You are running Phase 1 of the Haytham validation workflow. This phase analyzes the startup idea, researches the market, and produces a recommendation.

**IMPORTANT:** Always read agent output from files, not from conversation history.

## Progress Tracking

After Setup completes (and before Step 0), call `TodoWrite` once with one todo per step that will actually run for this invocation. Steps 0, 4, 6 are skipped in BATCH_MODE; skipped steps must not be added to the todo list. If resuming from `--from N`, only include steps from N onward.

Default (interactive) todo set:
1. Step 0 — Founder context
2. Step 1 — Idea analysis
3. Step 2 — Market & competitor research
4. Step 3 — Research brief
5. Step 4 — Founder review
6. Step 5 — Validation report
7. Step 6 — Gate 1

Mark each todo `in_progress` when starting the step and `completed` when its output file is written (or the gate decision is recorded). If a step re-runs because the founder corrected something, set it back to `in_progress`.

## Setup & Resume Detection

### Flag Parsing

First, check if the argument contains `--batch`. If so:
- Remove `--batch` from the argument string (the remainder is the idea, URL, or `--from N`)
- Set BATCH_MODE to true

Then check if the user passed `--from N` as the argument (e.g., `/haytham:validate --from 5`). If so, set START_STEP to N.

### URL Detection

If the argument is not `--from N`, check if it looks like a URL:

**If it matches `https?://(www\.)?reddit\.com/`** (Reddit post):
1. Try WebFetch to retrieve the URL content
2. If WebFetch fails (blocked or errors), fall back to the Reddit JSON API via Bash:
   ```bash
   curl -s -H "User-Agent: haytham/1.0" "[URL].json"
   ```
   Parse the JSON response to extract `title` and `selftext` from `data.children[0].data`.
3. Extract the post title and body text from the fetched content
4. Set IDEA_TEXT to the extracted title + body
5. Set SOURCE_URL to the original URL
6. Set SOURCE_TYPE to `reddit_post`

**If it matches `https?://(www\.)?github\.com/`** (GitHub repo):
1. Parse `{owner}/{repo}` from the URL path
2. Use WebFetch to retrieve `https://raw.githubusercontent.com/{owner}/{repo}/main/README.md`
3. If that fails (404), try `https://raw.githubusercontent.com/{owner}/{repo}/master/README.md`
4. Also use WebFetch on the GitHub repo page to extract the repo description
5. Set IDEA_TEXT to: repo description + "\n\n" + first 2000 characters of README content
6. Set SOURCE_URL to the original URL
7. Set SOURCE_TYPE to `github_repo`

**If neither** (plain text):
- Set IDEA_TEXT to the argument as-is
- Set SOURCE_URL to null
- Set SOURCE_TYPE to `text`

If a URL was detected, tell the user what was extracted:
> **Source:** [SOURCE_TYPE] at [SOURCE_URL]
> **Extracted idea:** [first 200 chars of IDEA_TEXT]...
>
> This text will be analyzed as the startup idea.

If the extracted text is under 50 characters, warn:
> **Warning:** Extracted text is very short. The analysis may be thin. Consider providing a text description instead.

### Resume or Start Fresh

Check if `.haytham/project.yaml` exists and contains a `state` section. If it does, read it and check `state.phase_1.last_completed_step`:

- If `last_completed_step` exists and is between 1 and 5, tell the user:
  > **Resuming Phase 1.** Found previous progress:
  > - Last completed step: [N] ([step name])
  > - Starting from step: [N+1]
  >
  > To restart from scratch, run `/haytham:validate [your idea]` with a new idea.
  > To resume from a different step, run `/haytham:validate --from N`.

  Set START_STEP to last_completed_step + 1. Verify the required input files for that step exist before proceeding.

- If no state exists or a new idea was provided as the argument (not `--from`), start fresh from step 1:
  1. Create `.haytham/` and `.haytham/session/phase-1-why/` directories if they don't exist
  2. Write to `.haytham/project.yaml`:
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
  Set START_STEP to 1.

## State Updates

After each step completes successfully, update `.haytham/project.yaml` to set `state.phase_1.last_completed_step` to the step number and `state.phase_1.updated_at` to the current timestamp. Use the Edit tool to update only the state section, preserving the rest of the file.

## Roadmap

Before launching any agents, read `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/marketplace.json` and extract the `version` field from `plugins[0]`. Then tell the user (replacing VERSION with the actual version string you just read):

If BATCH_MODE is true, show the batch roadmap:

> **Phase 1: Idea Validation** (haytham vVERSION) -- BATCH MODE
>
> Running unattended. Skipping Steps 0, 4, 6 (no human review).
> Steps: 1 (Idea Analysis) -> 2 (Market Research) -> 3 (Research Brief) -> 5 (Validation Report)
>
> Estimated total: ~6 minutes.

Otherwise, show the standard roadmap:

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

If resuming (START_STEP > 1), show which steps will be skipped:
> Skipping steps 1–[START_STEP - 1] (already completed). Starting from step [START_STEP].

**Skip to the section for START_STEP.** Do not run steps before START_STEP.

## Step 0: Founder Context

**Skip this step if BATCH_MODE is true.** Also skip if resuming from step > 0. Also skip if `.haytham/project.yaml` already contains a `founder_context` section.

If skipped due to BATCH_MODE, do NOT write `founder_context`. The idea-analyst will infer what it can from the idea text.

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

Map the user's natural language answers to the enum values. If the time horizon is ambiguous, infer from the success criteria (e.g., "launch to 100 users" suggests months; "learn React" suggests weeks).

## Step 1: Idea Analysis

Tell the user:
> **Step 1/6: Idea Analysis**
> Expanding your idea into a structured concept so we have a clear foundation for research.

Launch an **idea-analyst** agent with this task:
> Read the startup idea from `.haytham/project.yaml`. Analyze it following your instructions. Write idea analysis to `.haytham/session/phase-1-why/idea-analysis.md` and concept anchor to `.haytham/session/phase-1-why/concept-anchor.json`.

If the agent writes `.haytham/session/phase-1-why/idea-clarification.md`, read it and present the questions/suggestions to the user. Wait for their response, update `.haytham/project.yaml`, and re-run.

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

## Step 2: Market & Competitor Research

Verify `.haytham/session/phase-1-why/idea-analysis.md` exists. Read it and extract the domain/category.

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
>
> Full details: `.haytham/session/phase-1-why/market-research.md` and `.haytham/session/phase-1-why/competitor-research.md`

Update state: `last_completed_step: 2`.

## Step 3: Research Brief

Tell the user:
> Research gathered. Compiling a neutral summary for your review. No scores or judgments, just facts.

Launch a **research-briefer** agent with this task:
> Read idea analysis from `.haytham/session/phase-1-why/idea-analysis.md`, market research from `.haytham/session/phase-1-why/market-research.md`, and competitor research from `.haytham/session/phase-1-why/competitor-research.md`. Compile a neutral research brief. Write to `.haytham/session/phase-1-why/research-brief.md`.

After the agent completes, read `.haytham/session/phase-1-why/research-brief.md` and output its FULL contents inline in your response. The user must be able to read the entire brief without expanding anything or opening a file. Do NOT summarize or abbreviate — print every line.

Update state: `last_completed_step: 3`.

## Step 4: Founder Review

**If BATCH_MODE is true:** Skip the review prompt entirely. Do NOT write founder-corrections.json. Tell the user:
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

## Step 5: Validation Report

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

## Step 6: Gate 1

**If BATCH_MODE is true:** Read the recommendation from `.haytham/session/phase-1-why/validation-report.json`.

If the recommendation is **NO-GO**, halt the pipeline:
> **Gate 1 (batch mode): NO-GO.** The validation report recommends against proceeding. Pipeline halted.
>
> Review the report in `.haytham/session/phase-1-why/validation-report.md` and re-run without `--batch` if you want to discuss or override.

Write gate decision with `"user_decision": "batch-auto-halted"` and stop. Do not proceed further.

Otherwise (GO or PIVOT), auto-write gate decision:
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
> **Phase 1 complete (batch mode).** Verdict: [recommendation]. Auto-approved.

Update state: `last_completed_step: 6`. Skip to the completion message.

**Otherwise**, ask:
> **Review the report above. Specifically:**
> - Does the evidence support the verdict?
> - Is the positioning analysis right? Is the territory you'd actually claim?
> - Do the strategic options make sense for your situation?
> - Are there load-bearing assumptions the report missed?
> - Do you agree with the recommended path?
>
> You can ask questions about the report, request changes, or say "approve" to proceed.

Write gate decision to `.haytham/session/phase-1-why/gate-decision.json`:
```json
{
  "phase": 1,
  "recommendation": "GO|PIVOT|NO-GO",
  "user_decision": "approved|rejected|overridden",
  "notes": "Any user feedback",
  "decided_at": "[ISO timestamp]"
}
```

Update state: `last_completed_step: 6`.

Tell the user: "Phase 1 complete. Ran 4 agents across 6 steps. Output saved to `.haytham/session/phase-1-why/`. Run `/haytham:specify` to proceed to Phase 2."
