---
description: Compare declared intent against observed reality and competitor context, then produce a ranked list of change proposals.
argument-hint: ""
allowed-tools: Read, Write, Glob, Bash, TodoWrite, mcp__analytics-mcp__get_account_summaries, mcp__analytics-mcp__get_property_details, mcp__analytics-mcp__run_report, mcp__analytics-mcp__run_funnel_report, mcp__analytics-mcp__get_custom_dimensions_and_metrics
---

# Haytham: Propose Next Steps

**Version:** 0.2 (2026-05-23 — reads `telemetry.derived.yml` when present and filters entries by approval status; legacy `telemetry.yml` still supported for capabilities that haven't migrated)

Closes the reasoning-graph loop. Read the project's telemetry contracts, pull live observed values from the configured adapter, fold in the latest strategic context, and produce a ranked list of change candidates the founder can route to `/haytham:evolve`.

**This is a single-LLM-call command, not a multi-agent pipeline.** All synthesis happens in the orchestrator with full context. Do not spawn sub-agents for analysis, ranking, or rewriting. (See CLAUDE.md pitfall on splitting LLM reasoning.)

## Progress Tracking

After preconditions pass, if `TodoWrite` is available in this session, call it once with these items:

1. Load declared intent and telemetry contracts
2. Pull observed reality via analytics adapter
3. Load strategic context (competitor snapshot)
4. Synthesize ranked proposals
5. Write proposals file and present summary

Mark `in_progress` when each step starts and `completed` when its output exists. If `TodoWrite` is not available (its schema is not in the loaded tool set), skip the call and proceed — progress visibility is a UX nicety, not a hard requirement. Either way, do not skip the underlying steps even if a section is empty (record the gap explicitly).

## Preconditions

1. Check that `./openspec/` exists. If missing:

   > `openspec/` not found. Run `/haytham:propose-next-steps` from the project root that contains the reasoning graph.

   Then stop.

2. Glob `./openspec/specs/*/telemetry.derived.yml` and `./openspec/specs/*/telemetry.yml`. A capability has a contract if either matches. If the union is empty:

   > No telemetry contracts found. Either run `/haytham:derive-criteria <capability>` to produce a candidate contract from the reasoning graph, or hand-write at least one `openspec/specs/<capability>/telemetry.yml`. The contract is what makes the loop possible; without it the proposer would be guessing.

   Then stop.

3. Probe whether the analytics MCP is available (look for any tool starting with `mcp__analytics-mcp__`). If not available:

   > The `analytics-mcp` tools are not loaded. Install per https://github.com/googleanalytics/google-analytics-mcp, register with `claude mcp add`, restart Claude Code, then rerun. Manual stub mode (`.haytham/observed.json`) is not supported in v0.

   Then stop.

4. Ensure `./.haytham/proposals/` exists:

   ```bash
   mkdir -p ./.haytham/proposals
   ```

## Step 1 — Load declared intent and telemetry contracts

Read into context:

- `./openspec/context/concept-anchor.json` (project invariants and strategic signals)
- `./openspec/context/capabilities.json` (capability model)
- `./openspec/context/architecture-decisions.json` (build/buy choices and constraints)
- For each capability that has a contract: prefer `./openspec/specs/<capability>/telemetry.derived.yml` if it exists; otherwise fall back to `./openspec/specs/<capability>/telemetry.yml`. Never read both for the same capability — the derived file is authoritative when present.
- For each capability that has a contract, also read its `./openspec/specs/<capability>/spec.md` (the Gherkin scenarios and SHALL statements)

**Filter by approval status (derived files only).** For each contract loaded from `telemetry.derived.yml`, filter every list field (`events`, `success_thresholds`, `anti_signals`, `regression_triggers`, `differentiates_from`) to keep only entries whose `status` is `approved` or `modified`. Drop `pending` and `rejected` entries silently — the proposer must not reason against unapproved hypotheses. If after filtering a capability has zero entries across all lists, treat it as `unapproved` and surface an `intent_gap` finding in Step 4: `intent_gap: <capability> — derivation exists but no entries approved yet`. Do not query observed reality for unapproved capabilities.

Legacy `telemetry.yml` files have no `status` field; treat all their entries as approved by default. This preserves existing behaviour for capabilities that haven't been migrated to the derive-and-approve flow.

If any context file is missing, note it in the proposals output as `intent_gap` — don't stop.

## Step 2 — Pull observed reality

For each telemetry contract:

1. Read the property ID from `baseline_snapshot.property_id` in the contract. If absent, look for `./.haytham/config.yml` with a `ga_property_id` field. If neither, mark the capability `unmeasured` and continue to the next.

2. **Enumerate firing events first.** Run one `run_report` on dimension `eventName`, metric `eventCount` + `sessions`, last-30-days window, no filters. This catalogs every event GA4 is recording on the property. Compute the set difference: `firing_events − union_of_contract_declared_events`. Any event present in GA4 but absent from every contract is a `revise-contract` candidate finding — surface it in Step 4 with a proposal to either model the event in the relevant contract or mark it as `non_canonical_events`.

3. **Cross-reference contract events against capability spec acceptance criteria.** For every event each contract declares, scan the corresponding capability spec (`./openspec/specs/<capability>/spec.md` and `./openspec/context/capabilities.json` acceptance criteria) for that event name. If the spec requires fields/dimensions/parameters the contract marks `gap_note`, `fired_today: false`, or otherwise indicates are not in the data, that disagreement is a finding. Surface it as a high-confidence `instrument` proposal (spec-conformance bug: implementation is missing what its own spec requires) or, if the contract is the wrong one, a `revise-contract` proposal. **This is the highest-leverage finding type the proposer can produce — always do this cross-reference, never skip it.**

4. Build the queries the contract implies. For each entry under `success_thresholds`, `anti_signals`, and `minimum_sample`:

   - Identify the dimensions and metrics needed.
   - Use the last-30-days window unless the contract specifies otherwise.
   - **Use `run_funnel_report` whenever the threshold definition describes "X sessions that did Y", "of sessions that landed on A, the fraction that fired B", or any condition that requires joining two events within the same session — even if the threshold is phrased as a single ratio.** These are session-scoped funnels; a single `run_report` cannot give you a clean numerator/denominator without a custom session-scoped dimension, and any approximation may be off by a meaningful amount.
   - Use `run_report` only when the threshold is a pure aggregation over events with no session-conditional logic (e.g., share of pageviews by category, total event count, bounce rate filtered to a landingPage).
   - **When in doubt:** if the threshold definition includes the words "sessions that", "of sessions", "in the same session", or describes any condition spanning two events — use `run_funnel_report`.
   - Only request dimensions and metrics that are GA4-valid pairs. If a contract requests a combination the API rejects, log the error in the proposals output and continue.

5. Run queries in parallel where possible (single message, multiple tool calls).

6. For every event the contract marks `fired_today: false`, do not query GA4. Record it as a known instrumentation gap.

7. For every event the contract marks `fired_today: true`, query and confirm it is still firing (count > 0). If a previously-fired event is now silent, flag it as `event_regression`.

8. Compute observed values for every threshold and anti-signal the contract names. Store them in memory as `observed[capability][metric_name] = {value, window, query_succeeded}`.

## Step 3 — Load strategic context

Read the latest competitor snapshot:

- Prefer `./.haytham/competitor-snapshots/` (most recent dated file) if it exists.
- Fall back to `./openspec/context/competitor-research.md` (the Phase 1 artifact).
- If neither exists, record `competitor_context: none` and continue without it.

If the chosen source is older than 30 days, emit a soft warning in the proposals file recommending the founder run `/haytham:refresh-competitors` (this command will exist after phase 4 of the plan; until then, the warning is just a reminder).

## Step 4 — Synthesize ranked proposals (SINGLE LLM PASS)

This is the only step where reasoning happens. Hold the entire context in mind: intent, observed values, strategic context. Do not split this into sub-agents.

For each capability with a contract, produce zero or more proposals according to these rules. **The rules are hard constraints; violating them produces invalid proposals.**

**Rule 1 — Minimum sample gate.** If observed catalog/capability volume is below the contract's `minimum_sample`, you may only produce these proposal types:

- `instrument` (add missing events or dimensions the contract declared as planned)
- `revise-contract` (suggest threshold or definition changes)
- `revise-spec` (suggest scope or capability-spec changes)

You may not produce `drop`, `redesign`, or `add` capability proposals. State the sample-gate reasoning explicitly in each proposal.

**Rule 2 — Evidence pairing for competitor findings.** A proposal grounded in a competitor observation is only valid when it is also paired with either (a) a `differentiates_from` edge in the contract naming that competitor and dimension, or (b) an observed mismatch in our own telemetry that the competitor signal explains. "Competitor X has feature Y" alone is not a proposal.

**One exception:** a proposal whose change type is `revise-contract` and whose proposed change is *adding a new `differentiates_from` edge* may be grounded in a competitor signal alone, provided the competitor evidence is strong (multiple snapshot citations or a consistent user-sentiment pattern). This lets the proposer surface a missing edge the contract should have, rather than staying silent on a real competitive dimension. Flag these proposals with low or medium confidence — they propose a hypothesis, not a verified mismatch.

**Rule 3 — Evidence trail required.** Every proposal must cite specific contract fields, specific observed values, and (if relevant) specific competitor-snapshot lines. A proposal without a traceable evidence trail is invalid.

**Rule 4 — Contracts can be wrong.** If observed reality persistently disagrees with the contract (e.g., a threshold that fires every run), prefer a `revise-contract` proposal before a capability-change proposal. The contract is a hypothesis; favor correcting the hypothesis until you have evidence it's right.

**Rule 5 — Past-proposal awareness.** Read the three most recent files under `./.haytham/proposals/` (if any). If a proposal there was very similar and explicitly rejected (founder did not route it to evolve), do not re-propose it unless new evidence has emerged. Cite which past proposal you are not re-raising and why, in your reasoning notes.

For each proposal, emit this exact shape (one block per proposal):

```
### Proposal: <short title>

**Capability:** <capability id>
**Change type:** instrument | revise-contract | revise-spec | drop | redesign | add
**Confidence:** low | medium | high
**Severity:** high | medium | low
**Rank score:** <severity_weight * confidence_weight, where high=3 medium=2 low=1; ties broken by recency of the underlying signal>

**Problem statement.** What is failing or mismatched, in two to four sentences. Anchor in numbers from observed reality.

**Proposed change.** What we should do. One paragraph. Specific.

**Evidence trail.**
- Contract: `openspec/specs/<capability>/telemetry.yml` — specific field(s).
- Observed: metric name, value, window. (e.g. catalog_to_product_conversion = 9.1% over last 30d, target ≥ 12%)
- Strategic context (if applicable): specific competitor and snapshot date.

**Confidence justification.** One line. Why this confidence level given the data quality.

**Suggested evolve invocation.** A copy-paste-ready `/haytham:evolve` command the founder can run. Render the proposal as a natural-language description in the same shape evolve already accepts. Example:
`/haytham:evolve "Add item_category parameter to view_item events in gift-catalog so category-level success can be measured."`

If the change type is `revise-contract` or `revise-spec`, the suggested invocation should be the explicit file edit (e.g. `Edit openspec/specs/gift-catalog/telemetry.yml: lower minimum_sample.weekly_catalog_landing_sessions from 50 to 40`).
```

**Ranking note.** Sort proposals descending by `rank_score`. Within ties, more recent signals first (e.g. an anti-signal that fired this week beats one that fired three weeks ago). Explain the ordering in a one-paragraph **Ranking rationale** at the top of the proposals file.

## Step 5 — Write the proposals file

Path: `./.haytham/proposals/<YYYY-MM-DD>-proposals.md` (use today's date in the project's timezone; if multiple runs the same day, append `-<n>` where `<n>` increments).

Structure:

```
# Proposals — <YYYY-MM-DD>

Generated by /haytham:propose-next-steps on <ISO-timestamp>.

## Inputs

- Capabilities with contracts: <list>
- Observed values pulled: <count> queries, <count> succeeded, <count> failed
- Strategic context: <path-or-none>, age <N days>
- Past-proposal files consulted: <list-or-none>

## Ranking rationale

<one paragraph>

## Proposals

<proposal blocks, ranked>

## Gaps and caveats

<Anything the proposer could not reason about: missing events, failed queries,
absent competitor data, capabilities without contracts, etc.

Annotations:
- `intent_gap: <short-id> — <one-line description>` for missing reasoning-graph
  inputs (e.g. a capability has no telemetry contract, a context file is missing).
- `event_regression: <event_name>` for events the contract said fired_today: true
  that returned zero counts this run.
- `event_unknown: <event_name>` for events firing in GA4 that no contract declares
  (raised in Step 4 as proposals; also listed here for the founder's scan).>
```

Then print to the user:

- The full path of the written file
- A one-line digest per proposal (title + change type + rank score)
- A reminder of how to route a proposal to evolve

End with the soft-checkpoint pattern: "Take a minute to read the file. Pick the proposals you want to route to evolve. Reply with the titles, or say 'none' if nothing is worth pursuing right now."

## Step 6 — Wait for the founder

Do not auto-execute any proposal. v1 is human-in-the-loop only. When the founder names proposals to route, surface the suggested evolve invocations for each (already in the file) and stop. Routing happens in a separate `/haytham:evolve` invocation.
