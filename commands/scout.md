---
description: Autonomous daily idea scout - extract problems from a harvest, screen them with a solution angle, deep dive the winner (headless; no human in the loop)
argument-hint: "[run_dir] (must contain harvest/ written by scout_harvest.py)"
allowed-tools: Read, Write, Bash, Glob, Agent, TodoWrite
---

# Haytham: Daily Scout (autonomous)

You are running the autonomous scout pipeline headless. There is no human to ask; never stop for clarification. Deterministic decisions (score floor, dedup, winner selection) belong to scripts — you orchestrate, you do not decide.

**IMPORTANT:** Always read agent output from files, not from conversation history.

## Hard rules

1. Never restart or re-run the pipeline because a verdict is PIVOT or NO-GO. One pass per day; the verdict is the result.
2. Maximum ONE deep dive per run.
3. Never edit the ledger or selection files — `scout_select.py` owns them.
4. If a stage fails or produces nothing, stop after recording what happened; the report script ships an honest-zero report from whatever artifacts exist. Shipping nothing is the only failure mode.

## Setup

RUN_DIR = `$ARGUMENTS` (a path relative to the working directory).

1. Verify `RUN_DIR/harvest/telemetry.json` exists. If not, write `RUN_DIR/scout-status.json` with `{"failed_at": "setup", "reason": "no harvest"}` and stop.
2. Read PERSONA from `config/persona.yaml` if it exists; otherwise use: "Solo technical founder building with AI tooling; wants ideas testable as a 1-2 week solo MVP; avoids heavy ops, sales-led GTM, regulated domains."
3. Call TodoWrite once with the steps below.

## Step 1 — Extract

Replay guard: if `RUN_DIR/candidates/candidates.json` already exists and parses with a non-empty `candidates` list, skip this step (replay/sampling run) and go to Step 2.

Launch the `idea-scout` agent. Tell it the RUN_DIR and give it PERSONA verbatim. It writes `RUN_DIR/candidates/candidates.json`.

Verify the file exists and parses. If it is missing or `candidates` is empty, write `RUN_DIR/scout-status.json` `{"failed_at": "extract", "reason": "<what happened>"}` and stop.

## Step 2 — Screen

Replay guard: if `RUN_DIR/screen/screening.json` already exists and parses with a non-empty `scorecards` list, skip this step and go to Step 3.

Launch the `feasibility-screener` agent. Tell it the RUN_DIR and give it PERSONA verbatim. It writes `RUN_DIR/screen/screening.json` and `screening.md`.

Verify screening.json exists and parses; on failure write scout-status.json `{"failed_at": "screen", ...}` and stop.

## Step 3 — Select (deterministic)

Replay guard: if `RUN_DIR/selected/selection.json` already exists and parses, do NOT run the script — a sampling workflow pre-selected the winner (possibly with gates deliberately bypassed) and re-running would overwrite it.

Otherwise run: `python3 scripts/scout_select.py "$RUN_DIR"`

Read `RUN_DIR/selected/selection.json`. If `decision` is not `deep_dive`, write `RUN_DIR/scout-status.json` `{"failed_at": null, "honest_zero": "<reason from selection.json>"}` and stop — this is a normal outcome, not an error.

Otherwise `RUN_DIR/selected/project.yaml` now describes the winner.

## Step 4 — Deep dive (Phase-1 agents, autonomous mode)

SESSION = `RUN_DIR/session/phase-1-why`. Include this override block verbatim in every deep-dive agent prompt:

> OVERRIDES (autonomous scout mode):
> - Session directory: read and write SESSION wherever your instructions say `.haytham/session/phase-1-why/`.
> - The idea comes from an automated scout. There is nobody to ask. On ANY path where your instructions say to stop, ask for clarification, or escalate, proceed with your best interpretation and log every assumption explicitly in your output file.
> - founder_context (treat as the founder): PERSONA
> - The idea statement lives in RUN_DIR/selected/project.yaml; treat it as `.haytham/project.yaml`. Its `pain_evidence` and `evidence` blocks are raw harvest quotes — treat them as primary sources; do not re-fetch those URLs from the web.

Sequence:

1. **idea-analyst** — adopt `agents/idea-analyst.md` (in the plugin) with the overrides. Writes idea-analysis.md + concept-anchor.json into SESSION.
2. **market-researcher and competitor-researcher in parallel** (two Agent calls in one message) — each adopts its plugin agent file with the overrides. Additionally give each the winner's evidence URLs from `RUN_DIR/selected/selection.json` with the instruction: "WebFetch these cited URLs directly before searching; they may be too fresh for search indexes."
3. **report-synthesizer** — adopts its plugin agent file with the overrides, plus this scout-mode scoring block verbatim:

   > SCOUT-MODE SCORING (overrides the agent file where they conflict):
   > - Composite rubric is FIXED across runs so scores are comparable day to day. Exactly these 5 dimensions, each 0-5, composite = their mean, on a /5 scale: problem_severity (how bad and how frequent is the pain in the evidence), evidence_confidence (how much of the thesis rests on verified data vs belief — this dimension, not a global cap, carries the day-0 penalty; do NOT apply the "composite above 3.5 not permitted" rule), market_openness (can a new entrant win: incumbent gaps, distribution paths), founder_fit (persona vs what winning requires), wedge_viability (does the solution angle survive the research).
   > - NO-GO is mandatory when direct disconfirming evidence exists (a free or bundled incumbent already serves the exact wedge for the same user, the pain is one-off, or the evidence contradicts the problem statement). GO is allowed when evidence_confidence >= 3 and no fatal finding survived. PIVOT is for a real problem with a wrong wedge — name the better wedge, AND put it in validation-report.json as a top-level `pivot_wedge` field: ONE sentence naming the better wedge (machine-read into the ledger's wedge backlog; omit the field entirely on GO/NO-GO).
   > - State the evidence basis ("machine-gathered, day-0, unreviewed") once in a fixed report field, not as a warning; warnings are only for findings specific to today.

   Also: "No founder reviewed the research and no founder-corrections.json exists. ALSO read RUN_DIR/screen/screening.json as a designated input and reconcile any competitor named there but missing from competitor-research.md — flag discrepancies, do not silently patch." Writes validation-report.md + validation-report.json into SESSION.

If a deep-dive agent dies, record it in scout-status.json and stop — do not retry more than once, do not substitute your own analysis.

## Step 5 — Finish

Write `RUN_DIR/scout-status.json`:

```json
{"completed": true, "winner_one_liner": "...", "recommendation": "GO|PIVOT|NO-GO", "composite_score": 0.0}
```

`winner_one_liner` is copied VERBATIM from `RUN_DIR/selected/selection.json` (`winner.candidate.one_liner`) — never paraphrase it. `recommendation` and `composite_score` come from validation-report.json.

Final message: one line — winner, recommendation, composite score. The report script does the rest.
