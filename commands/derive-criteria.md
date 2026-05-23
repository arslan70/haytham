---
description: Derive a candidate telemetry contract for a capability — shape from the reasoning graph, numbers from observed reality. Output is review-ready, not authoritative; every entry has status pending until the founder approves it.
argument-hint: <capability-id>
allowed-tools: Read, Write, Glob, Bash, mcp__analytics-mcp__get_account_summaries, mcp__analytics-mcp__get_property_details, mcp__analytics-mcp__run_report, mcp__analytics-mcp__run_funnel_report, mcp__analytics-mcp__get_custom_dimensions_and_metrics
---

# Haytham: Derive Criteria

**Version:** 0.4 (2026-05-23 — adds founder-facing layer: every approvable entry now carries `founder_summary` (plain-English one-liner, no methodology vocabulary) and `why_it_matters` (founder-grade outcome link) so review can happen without translating GA4 jargon on the fly. Pairs with the new `/haytham:approve-criteria` command.)

Reads the reasoning-graph nodes for one capability, optionally queries observed reality from the analytics adapter, and produces a candidate `telemetry.derived.yml`. The criterion *shape* comes from the graph. The criterion *numbers* (targets, thresholds, sample sizes) come from the observed baseline when analytics is available, or are left as TBD when it is not. Every derived entry is `status: pending` and cites both the upstream line that justifies the shape and the observation that justifies the number. The founder then approves, modifies, or rejects each entry by editing the file.

**Why this command pulls observed reality.** The honest separation of work is: the system does what it can do from data (deriving shape from the graph, calibrating numbers from baseline observations); the founder does what only a founder can do (decide whether the criterion survives, override numbers with strategic intent, add back items derivation couldn't justify). Asking the founder to fill in numbers the system could have computed is data-entry by the wrong actor.

**This is a single-LLM-call command, not a multi-agent pipeline.** All derivation and calibration happens in one LLM pass with full upstream context and observed-baseline tool calls. Do not spawn sub-agents.

**This command must NOT read `telemetry.yml` if one already exists for the capability.** The whole point is a clean re-derivation that can be compared against any pre-existing hand-written contract. Reading the existing file would contaminate the derivation.

## Argument

`$1` — the capability id (e.g. `gift-catalog`). Must match a directory under `./openspec/specs/`.

## Preconditions

1. Check that `./openspec/` exists. If missing:

   > `openspec/` not found. Run this command from the project root that contains the reasoning graph.

   Then stop.

2. Check that `./openspec/specs/$1/spec.md` exists. If missing:

   > Capability `$1` has no spec.md. Either the capability id is wrong or the spec hasn't been written yet.

   Then stop.

3. Confirm `./openspec/specs/$1/telemetry.derived.yml` does not already exist. If it does, ask the founder:

   > A derived contract already exists at `./openspec/specs/$1/telemetry.derived.yml`. Overwrite it? (y/n)

   If no, stop. If yes, proceed and overwrite.

4. Probe whether the analytics MCP is available (look for any tool starting with `mcp__analytics-mcp__`). If available, derivation will calibrate numbers from observed baseline. If not, derivation will still run but every numeric field will be emitted as `TBD — calibrate when analytics is connected`. Note the chosen mode in the output file's header comment so the founder knows whether numbers were calibrated or left blank.

5. If analytics is available, determine the property ID. Order of resolution: `./.haytham/config.yml` `ga_property_id` field, else ask the founder. Persist the value the founder provides into `./.haytham/config.yml` so subsequent runs do not re-ask.

## Step 1 — Load upstream context

Read into context, in this order:

- `./openspec/specs/$1/spec.md` (SHALL statements and Gherkin scenarios)
- `./openspec/context/capabilities.json` (the entry whose id matches `$1`, plus its acceptance criteria)
- `./openspec/context/concept-anchor.json` (invariants and strategic signals — filter to ones that touch this capability)
- `./openspec/context/architecture-decisions.json` (decisions that constrain what's measurable for this capability)
- `./openspec/context/competitor-research.md` (only the sections relevant to this capability's dimension of competition)

Do **not** read `./openspec/specs/$1/telemetry.yml` even if it exists.

If any of these files is missing, note it in the derived output as an `intent_gap` comment at the top of the file and continue with what's available.

## Step 2 — Derive entries (SINGLE LLM PASS)

This is the only reasoning step. Hold the entire upstream context in mind and produce a candidate `telemetry.derived.yml`. The pass has two phases inside one LLM turn:

**Phase A — Derive shape.** From the upstream graph alone, decide which criteria, anti-signals, and events the capability needs. Follow Rules 1–7 below. The output of this phase is the criterion *shape*: name, definition, dimensions, derivation_notes, derived_from citations. Numbers are not set yet.

**Phase B — Calibrate (only if analytics is available).** For each derived criterion, run the GA4 queries its definition implies. Use `run_funnel_report` for any threshold whose definition describes sessions doing X then Y (per the same rules in `/haytham:propose-next-steps` Step 2). Use `run_report` only for pure aggregations. Last-30-day window unless the capability dictates otherwise. Compute the observed baseline. Then propose a calibrated target per Rule 6's policies (floor / stretch / invariant). Run queries in parallel where possible (single message, multiple tool calls). If a query fails, emit `observed_baseline: {query_succeeded: false, error: <message>}` and `target: "TBD — query failed; founder to set"` for that entry — never invent a number to paper over a failed query.

If analytics is unavailable, skip Phase B entirely and emit shape-only output (numbers as TBD strings, no observed_baseline blocks).

Follow these rules. They are hard constraints.

**Rule 1 — Every entry must cite an upstream line.** Each derived entry has a `derived_from` field listing the specific upstream artifact and line(s) that justify it. Example: `derived_from: ["openspec/specs/gift-catalog/spec.md:7-9 (CAP-F-001 SHALL statement)", "openspec/context/capabilities.json#gift-catalog.acceptance_criteria[0]"]`. An entry without a traceable citation is not allowed. If you cannot point to a specific upstream line, do not emit the entry.

**Rule 2 — Do not invent criteria.** If a SHALL statement or scenario does not imply a measurable success or failure, do not produce a criterion for it. Skipping is correct. The job is to derive, not to reach.

**Rule 2a — Events are schema, not criteria.** Events under `events:` are the measurement schema needed to populate the `success_thresholds` and `anti_signals` you emit. Emit an event when a threshold or anti-signal requires it. Do not emit events that no derived criterion uses. Events are not subject to Rule 2's "do not invent" bar in the same way criteria are — they are the *implied dimensions* of the criteria you derive.

**Rule 3 — Skip observation data.** Do not generate `baseline_snapshot`, `fired_today` flags, or any field that requires a live measurement. Those come from `propose-next-steps`, not from derivation. The derived file is the hypothesis. Observations are layered on later.

**Rule 4 — Skip runtime state.** Do not generate `version`, `revisions`, or any field that tracks contract history. The derived file is a fresh candidate. Versioning is added at approval time.

**Rule 5 — Status is always pending.** Every entry (each event, each success_threshold, each anti_signal, etc.) has `status: pending`. The founder edits this after reviewing.

**Rule 6 — Shape comes from the graph; numbers come from data.** A derived threshold like `target: ">= 12%"` cannot be justified by a SHALL statement (SHALL statements don't contain numbers). Derive the *shape* of the criterion ("of catalog-landing sessions, the fraction that reach a product detail page") from the graph. Then, if analytics is available, run the queries the shape implies against the last 30-day window, record the observed value as the baseline, and propose a calibrated target. Calibration policy:

- **Minimum-acceptable / floor thresholds** (where the SHALL describes something the system *must* do, e.g. "primary discovery mechanism"): target = observed baseline, rounded down to a "don't regress" floor. Confidence: medium.
- **Stretch / target thresholds** (where the upstream implies a goal, e.g. competitive differentiation): target = observed baseline + a modest lift the proposer can argue for from competitor data or strategic signals. Confidence: low.
- **Correctness / invariant thresholds** (where a SHALL is unconditional, e.g. "every product detail page must have these elements"): target = 100% (or 0 for negative SHALLs). Confidence: high. Do not compute from baseline — the SHALL itself sets the number.

Emit `observed_baseline: {value, window, sample_n, query_succeeded}` on every entry where analytics ran. Emit `calibration_rationale: |` on every entry explaining which policy applied and why the proposed number reflects it. If analytics is unavailable, emit `target: "TBD — calibrate when analytics is connected"` and skip the baseline/rationale.

**Rule 7 — Skip differentiation entries unless a specific competitor is paired with a specific dimension in one citation.** A `differentiates_from` entry requires a single upstream citation that names both a competitor (by name, not by category — "TCS SentimentsExpress" qualifies, "Pakistani gifting sites" does not) and the dimension on which this capability differentiates from that competitor. Two separate citations (a competitor mentioned in one place, a dimension mentioned in another) do not pair. Generic competitive intuition is not allowed. If the strategic signal is real but the citation isn't paired in one place, emit no entry and add an `intent_gaps` note saying the concept-anchor should be enriched.

**Rule 8 — Every approvable entry must carry a founder-facing layer.** Every entry that the founder will review (success_thresholds, anti_signals, regression_triggers, minimum_sample) must include two additional fields:

- `founder_summary:` — one sentence in plain English describing *what* is being measured, written the way the founder would describe it to a non-engineer. **No measurement vocabulary** — no "GA4", no "sessions that fire X", no "DOM", no "engaged sessions", no "ratio", no "denominator". Replace methodology with intent. Example: instead of *"Of sessions that include the home page (/), the fraction that are 'engaged sessions' per GA4 definition (session lasted >10s, had a conversion event, or had 2+ page views)"*, write *"Are visitors sticking around after landing on the home page?"*
- `why_it_matters:` — one sentence linking the criterion to a real outcome the founder cares about. **Not a SHALL citation; an outcome.** Example: *"If this drops, fewer buyers ever reach a product page, and the catalog stops doing its job."*

These fields are the wizard's display layer and the proposer's narrative layer. The technical `definition:` field stays for the GA4-querying machinery. Events do not need this layer (they are schema, not approvable judgments), but every other approvable entry must have both fields.

If the upstream graph does not provide enough context to write a non-trivial `why_it_matters`, write the most honest version possible (e.g., *"The spec considers this a hard requirement"* is acceptable for an invariant) — do not pad with vague language.

## Step 3 — Write the derived file

Path: `./openspec/specs/$1/telemetry.derived.yml`.

Shape (omit any section that has zero derived entries):

```yaml
# Derived telemetry candidate for the $1 capability.
# Generated by /haytham:derive-criteria on <ISO-timestamp>.
# Every entry below is status: pending. Edit this file to approve,
# modify, or reject. The proposer (/haytham:propose-next-steps) reads
# only entries with status: approved or status: modified.

capability: $1
spec_ref: openspec/specs/$1/spec.md
derived_at: <ISO-timestamp>
calibration_mode: <"calibrated" if analytics available, else "shape-only">

# Baseline observations used to calibrate the numbers below. Omit this
# entire block in shape-only mode. If a future re-derivation produces
# different baseline numbers, that drift is itself a signal — preserve
# the original here and append the new run below.
baseline_snapshot:
  measured_at: <ISO-date>
  window: last_30_days
  property_id: <ga4 property id>
  totals:
    <metric_name>: <value>
    ...
  derived:
    <ratio_name>: <value>
    ...

purpose: |
  <Derived from spec.md Purpose section. One paragraph. Verbatim
  or near-verbatim from the spec; do not paraphrase the founder's
  intent into something looser.>
purpose_derived_from:
  - openspec/specs/$1/spec.md#Purpose

events:
  - id: <event-name>
    status: pending
    description: <what this event represents>
    dimensions: [<dimension list needed to populate the criteria below>]
    derived_from:
      - <upstream citation>
    derivation_notes: |
      <Why this event is needed — which SHALL or scenario implies
      it. Do not include fired_today; that is observed at runtime.>

success_thresholds:
  - name: <criterion-name>
    status: pending
    founder_summary: |
      <One sentence in plain English per Rule 8. No GA4 jargon, no
      methodology. Describes what we're measuring as a founder would
      describe it. Example: "Are visitors sticking around after landing
      on the home page?">
    why_it_matters: |
      <One sentence linking to a real outcome. Example: "If this drops,
      fewer buyers ever reach a product page, and the catalog stops
      doing its job.">
    definition: |
      <The shape of the measurement, derived from the SHALL or scenario.
      Numerator/denominator phrased session-scoped where applicable.>
    target: "<calibrated number per Rule 6, e.g. '>= 20%'; or 'TBD —
      calibrate when analytics is connected' in shape-only mode>"
    derived_from:
      - <upstream citation>
    derivation_notes: |
      <What kind of threshold this is per Rule 6: minimum-acceptable
      floor, stretch target, or correctness invariant. Why the upstream
      implies this classification.>
    observed_baseline:                    # omit in shape-only mode
      value: <observed value>
      window: last_30_days
      sample_n: <denominator size>
      query_succeeded: true
    calibration_rationale: |              # omit in shape-only mode
      <Which Rule 6 policy applied (floor / stretch / invariant) and how
      the proposed number reflects it. One to three sentences.>

anti_signals:
  - name: <anti-signal-name>
    status: pending
    founder_summary: |
      <One sentence per Rule 8. Plain English, no methodology. Example:
      "Are too many visitors leaving the home page without exploring?">
    why_it_matters: |
      <One sentence outcome link. Example: "This catches regressions
      that quietly erode catalog entry before they hit conversion.">
    definition: |
      <The failure mode, derived from a scenario or invariant. What it
      looks like in measurable form.>
    threshold: "<calibrated number per Rule 6; or 'TBD — calibrate when
      analytics is connected' in shape-only mode>"
    derived_from:
      - <upstream citation>
    derivation_notes: |
      <Why this is a failure mode according to the upstream. What in the
      spec is violated when this fires.>
    observed_baseline:                    # omit in shape-only mode
      value: <observed value>
      window: last_30_days
      sample_n: <denominator size>
      query_succeeded: true
    calibration_rationale: |              # omit in shape-only mode
      <Which Rule 6 policy applied and how the threshold reflects it.>

regression_triggers:
  - status: pending
    founder_summary: |
      <One sentence per Rule 8. Plain English description of the
      trigger condition. Example: "Catalog discovery has been quietly
      dropping for two weeks running.">
    why_it_matters: |
      <One sentence outcome link. Example: "Two-week persistence rules
      out a noisy single week and points at a real regression.">
    text: |
      <Precise machine/proposer-grade phrasing of the trigger condition.
      Each trigger must derive from a specific upstream invariant or
      scenario. Avoid generic "drop in metric X" triggers unless the
      upstream implies a slope.>
    derived_from:
      - <upstream citation>

minimum_sample:
  status: pending
  founder_summary: |
    <One sentence per Rule 8. Example: "Below this weekly traffic level,
    we treat the week as too noisy to draw conclusions from.">
  why_it_matters: |
    <One sentence outcome link. Example: "Stops the proposer from raising
    alarms based on a sparse week that just happened to look bad.">
  value: <calibrated weekly sample floor — see rationale; or
    "TBD — calibrate when analytics is connected" in shape-only mode>
  rationale: |
    <In calibrated mode: derive the floor from observed weekly traffic
    volume for the capability's denominator population. Floor should be
    high enough to gate out single-week noise spikes but low enough to
    run at current traffic. State the observed weekly value and the
    fraction you chose.
    In shape-only mode: emit verbatim "Cannot derive without observed
    traffic. Founder or next calibration pass to set."
    Always keep this section — the founder needs a place to record the
    number at approval time.>
  observed_baseline:                    # omit in shape-only mode
    weekly_sessions_in_window: <value>
    window: last_30_days
  derived_from:
    - <upstream citation if the graph constrains the floor, otherwise
      the string "calibrated from observed traffic">

differentiates_from:
  - competitor: <name>
    dimension: <name>
    status: pending
    notes: |
      <Verbatim or near-verbatim from concept-anchor.json strategic
      signals or competitor-research.md. Do not synthesize.>
    derived_from:
      - <upstream citation>

# intent_gaps: optional. Comment-list of upstream nodes that were
# missing or that the derivation could not reason against. Example:
# - "openspec/context/competitor-research.md not found — competitive
#    differentiation entries skipped"
```

## Step 4 — Present the derivation summary

After writing the file, print to the user:

- The full path of the written file.
- One-line counts: N success_thresholds, N anti_signals, N events, N differentiates_from entries, N regression_triggers.
- Whether any sections were skipped (and why).
- A reminder: every entry is `status: pending`. The founder reviews and edits the file directly. The proposer will only read `approved` and `modified` entries.

End with:

> Open `./openspec/specs/$1/telemetry.derived.yml`, review each entry, and change `status: pending` to `status: approved` (or `modified` with edits, or `rejected` with a reason). When you're done, run `/haytham:propose-next-steps` to see how the proposals change.

## Step 5 — Stop

Do not auto-run `propose-next-steps` after derivation. The approval gate is the whole point of v1.
