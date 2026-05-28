---
description: Compare declared intent against observed reality, then produce a ranked list of change proposals and a plain-language brief.
argument-hint: ""
allowed-tools: Read, Write, Glob, Bash, TodoWrite, Agent, mcp__analytics-mcp__get_account_summaries, mcp__analytics-mcp__get_property_details, mcp__analytics-mcp__run_report, mcp__analytics-mcp__run_funnel_report, mcp__analytics-mcp__get_custom_dimensions_and_metrics
---

# Haytham: Propose Next Steps

**Version:** 0.3 (2026-05-28 — dropped competitor context step; added narrator agent for human-friendly output; recent merged PRs feed synthesis)

Closes the reasoning-graph loop. Read the project's telemetry contracts, pull live observed values from the configured adapter, and produce a ranked list of change candidates the founder can route to `/haytham:evolve`.

**This is a single-LLM-call command, not a multi-agent pipeline.** All synthesis happens in the orchestrator with full context. Do not spawn sub-agents for analysis or ranking. The narrator agent runs after the proposals file is written, as a separate read-and-summarise step.

## Progress Tracking

After preconditions pass, if `TodoWrite` is available in this session, call it once with these items:

1. Load declared intent and telemetry contracts
2. Pull observed reality via analytics adapter
3. Synthesize ranked proposals
4. Write proposals file
5. Run narrator agent

Mark `in_progress` when each step starts and `completed` when its output exists. If `TodoWrite` is not available, skip the call and proceed.

## Preconditions

1. Check that `./openspec/` exists. If missing:

   > `openspec/` not found. Run `/haytham:propose-next-steps` from the project root that contains the reasoning graph.

   Then stop.

2. Glob `./openspec/specs/*/telemetry.derived.yml` and `./openspec/specs/*/telemetry.yml`. A capability has a contract if either matches. If the union is empty:

   > No telemetry contracts found. Either run `/haytham:derive-criteria <capability>` to produce a candidate contract from the reasoning graph, or hand-write at least one `openspec/specs/<capability>/telemetry.yml`. The contract is what makes the loop possible; without it the proposer would be guessing.

   Then stop.

3. Probe whether the analytics MCP is available (look for any tool starting with `mcp__analytics-mcp__`). If not available:

   > The `analytics-mcp` tools are not loaded. Install per https://github.com/googleanalytics/google-analytics-mcp, register with `claude mcp add`, restart Claude Code, then rerun.

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
- For each capability that has a contract, also read its `./openspec/specs/<capability>/spec.md`

**Filter by approval status (derived files only).** For each contract loaded from `telemetry.derived.yml`, filter every list field (`events`, `success_thresholds`, `anti_signals`, `regression_triggers`, `differentiates_from`) to keep only entries whose `status` is `approved` or `modified`. Drop `pending` and `rejected` entries silently. If after filtering a capability has zero entries across all lists, treat it as `unapproved` and surface an `intent_gap` finding in Step 3. Do not query observed reality for unapproved capabilities.

Legacy `telemetry.yml` files have no `status` field; treat all their entries as approved by default.

Also run:

```bash
git log --oneline --merges -10
```

This gives the last 10 merged PRs. Store the titles as `recent_work` context for Step 3. If the repo has no merge commits, fall back to `git log --oneline -10`. If git is unavailable, skip silently.

If any context file is missing, note it in the proposals output as `intent_gap` — don't stop.

## Step 2 — Pull observed reality

For each capability with an approved contract:

1. Read the property ID from `baseline_snapshot.property_id` in the contract. If absent, look for `./.haytham/config.yml` with a `ga_property_id` field. If neither, mark the capability `unmeasured` and continue.

2. **Enumerate firing events first.** Run one `run_report` on dimension `eventName`, metric `eventCount` + `sessions`, last-30-days window, no filters. Compute the set difference: `firing_events − union_of_contract_declared_events`. Any event present in GA4 but absent from every contract is a `revise-contract` candidate — surface it in Step 3.

3. **Cross-reference contract events against capability spec acceptance criteria.** For every event each contract declares, scan the corresponding spec for that event name. If the spec requires fields or parameters the contract marks as `gap_note` or `fired_today: false`, surface it as an `instrument` proposal (the implementation is missing what its own spec requires). This is the highest-leverage finding type — never skip it.

4. Build the queries the contract implies. For each entry under `success_thresholds`, `anti_signals`, and `minimum_sample`:

   - Use the last-30-days window unless the contract specifies otherwise.
   - **Use `run_funnel_report`** whenever the threshold describes "X sessions that did Y" or any condition joining two events within the same session.
   - **Use `run_report`** only for pure aggregations with no session-conditional logic.
   - If a dimension/metric combination is GA4-invalid, log the error and continue.

5. Run queries in parallel where possible (single message, multiple tool calls).

6. For every event marked `fired_today: false`, do not query GA4. Record it as a known instrumentation gap.

7. For every event marked `fired_today: true`, confirm it is still firing. If not, flag it as `event_regression`.

8. Compute observed values for every threshold and anti-signal. Store them as `observed[capability][metric_name] = {value, window, query_succeeded}`.

## Step 3 — Synthesize ranked proposals (SINGLE LLM PASS)

This is the only step where reasoning happens. Hold the full context in mind: intent, contracts, observed values. Do not spawn sub-agents.

Apply these rules. **They are hard constraints.**

**Rule 1 — Minimum sample gate.** If observed volume is below the contract's `minimum_sample`, only `instrument`, `revise-contract`, and `revise-spec` proposals are allowed. No `drop`, `redesign`, or `add` proposals. State the sample-gate reasoning explicitly.

**Rule 2 — Evidence trail required.** Every proposal must cite specific contract fields and specific observed values. A proposal without a traceable evidence trail is invalid.

**Rule 3 — Contracts can be wrong.** If observed reality persistently disagrees with the contract, prefer a `revise-contract` proposal before a capability-change proposal.

**Rule 4 — Past-proposal awareness.** Read the three most recent files under `./.haytham/proposals/` (if any). Do not re-propose something explicitly rejected unless new evidence has emerged. Cite which past proposal you are not re-raising and why.

**Rule 5 — Recent work alignment.** Use `recent_work` from Step 1 in two ways: (a) do not re-propose something a merged PR in the last 14 days already addressed — note the PR title instead; (b) when a proposal aligns with the active work direction (e.g. recent PRs are all tightening instrumentation), say so explicitly — it raises confidence. When a proposal cuts across the active direction, it needs stronger evidence.

For each proposal, emit this exact shape:

```
### Proposal: <short title>

**Capability:** <capability id>
**Change type:** instrument | revise-contract | revise-spec | drop | redesign | add
**Confidence:** low | medium | high
**Severity:** high | medium | low
**Rank score:** <severity_weight * confidence_weight, where high=3 medium=2 low=1>

**What's happening.** What is failing or mismatched, in plain language. Include the key number.

**What to do.** One paragraph. Specific. No jargon.

**Evidence.**
- Contract: `openspec/specs/<capability>/telemetry.yml` — specific field(s).
- Observed: metric name, value, window.

**Suggested evolve invocation.**
`/haytham:evolve "..."`

If the change type is `revise-contract` or `revise-spec`, the suggested invocation should be the explicit file edit.
```

Sort proposals descending by `rank_score`. Within ties, more recent signals first. Include a one-paragraph **Ranking rationale** at the top of the proposals section.

## Step 4 — Write the proposals file

Path: `./.haytham/proposals/<YYYY-MM-DD>-proposals.md` (append `-<n>` for multiple runs on the same day).

Structure:

```
# Proposals — <YYYY-MM-DD>

Generated by /haytham:propose-next-steps on <ISO-timestamp>.

## Inputs

- Capabilities with contracts: <list>
- Observed values pulled: <count> queries, <count> succeeded, <count> failed
- Past-proposal files consulted: <list-or-none>
- Recent merged PRs: <count>, last: <most recent PR title>

## Ranking rationale

<one paragraph>

## Proposals

<proposal blocks, ranked>

## Gaps and caveats

<Anything the proposer could not reason about: missing events, failed queries,
capabilities without contracts, etc.

Annotations:
- `intent_gap: <short-id> — <one-line description>`
- `event_regression: <event_name>`
- `event_unknown: <event_name>`>
```

## Step 5 — Run narrator agent

After writing the proposals file, launch the **next-steps-narrator** agent. Pass it:

- The full path of the proposals file just written
- Today's date

The narrator writes a plain-language brief to `./.haytham/proposals/<YYYY-MM-DD>-brief.md` and prints it to the terminal. Its output is the primary deliverable the founder reads. The proposals file is the supporting record.

## Step 6 — Wait for the founder

Do not auto-execute any proposal. When the founder names proposals to route, surface the suggested evolve invocations from the proposals file and stop. Routing happens in a separate `/haytham:evolve` invocation.
