# Derive-and-Approve Criteria (Lean v1)

**Date:** 2026-05-22
**Supersedes:** `2026-05-18-polymorphic-telemetry-contracts.md` (deferred — see bottom)

## Goal

Make success criteria honest for Haytham-built products by removing the two sources of dishonesty in the current `telemetry.yml`:

1. The founder hand-writes the criteria, so they can drift from spec or be set on aspiration.
2. The proposer reasons against whatever criteria exist, with no gate, so hallucinated or stale criteria silently become authority.

The fix is two changes: **derive the criteria from upstream graph nodes** and **gate them through founder approval** before the proposer can use them.

## Scope

One capability: `gift-catalog`. We already have the hand-written `telemetry.yml` v3 to compare against. If the derive-and-approve loop produces a more honest set than v3, the loop works. If not, we know what specifically broke.

Everything else (polymorphism, six frameworks, error budgets, cross-platform vocabulary, adapter dispatch, audit history) is deferred until evidence asks for it.

## What changes

### 1. New command: `/haytham:derive-criteria <capability>`

Reads upstream graph nodes and produces a candidate criteria set. No new schema. Output is a YAML file in the same shape as the current `telemetry.yml`, but every entry has `status: pending` and a `derived_from` block citing the specific upstream lines that justify it.

Inputs the command reads:
- `openspec/specs/<capability>/spec.md` (SHALL statements and Gherkin acceptance criteria)
- `openspec/context/capabilities.json` (capability id, description, acceptance criteria)
- `openspec/context/concept-anchor.json` (invariants and strategic signals that touch this capability)
- `openspec/context/architecture-decisions.json` (build/buy choices that affect what's measurable)

Output path: `openspec/specs/<capability>/telemetry.derived.yml`. Separate file from the existing contract so we can diff them.

Single LLM call, no sub-agents (per CLAUDE.md pitfall). The prompt's job: for each acceptance criterion or SHALL statement, propose a measurable criterion if one is justified, and skip if not. Every proposed criterion must cite the upstream line it came from. Criteria not traceable to a specific upstream line are not allowed.

### 2. Approval as a YAML field, not a command

Every criterion in `telemetry.derived.yml` has `status: pending`. The founder approves by editing the file: change `pending` to `approved`, `modified` (and edit the criterion), or `rejected` (and add a `reason`).

No `/haytham:approve-criteria` command in v1. The editor is the UI. If we need a command later, we'll add it then.

### 3. Update `/haytham:propose-next-steps`

Two changes:

- Read `telemetry.derived.yml` if it exists, falling back to `telemetry.yml` for capabilities that haven't been derived yet.
- Filter to `status: approved` (and `status: modified`) entries only. Skip `pending` and `rejected`. If no approved entries exist for a capability, emit an `intent_gap` finding noting that derivation has not been approved yet.

That's it. The proposer logic is otherwise unchanged.

## Sequencing

Four steps, roughly half a day each.

1. **Write the derivation prompt.** Single LLM call. Inputs listed above. Output shape: same as current `telemetry.yml` plus `status` and `derived_from` per entry.
2. **Run derivation on `gift-catalog`.** Compare the derived file against the existing hand-written `telemetry.yml` v3. Three buckets:
   - **Derivation found something I missed.** Add to the case for derivation.
   - **My hand-written version had something derivation can't justify.** Either I had hidden context not in the graph (then enrich the graph), or I was wrong (then drop the criterion).
   - **Same in both.** Confirms the graph already encoded the intent; derivation is reproducing it correctly.
3. **Add the `status` field and update the proposer** to read approved-only.
4. **Re-run `/haytham:propose-next-steps`** with the derived-and-approved contract. Compare the proposals against the prior run. The question is whether the proposals are different (better, worse, or just different), not whether they're "right."

## Definition of done

- A derivation prompt that produces a candidate `telemetry.derived.yml` for `gift-catalog`.
- Every derived criterion cites an upstream line.
- The bucket comparison (derived vs hand-written) is written up — even one paragraph.
- `propose-next-steps` filters by approval status.
- The re-run produces a comparable proposals file.

That's the v1. No new infrastructure beyond one prompt and one filter.

## Honest test for whether the loop works

If, after deriving and approving criteria for `gift-catalog`, at least one of these is true, the loop works:

- A criterion in the hand-written v3 turns out not to be derivable from any upstream node, which means either the graph is under-specified or the criterion was aspirational.
- Derivation surfaces a criterion I'd missed.
- The re-run of `propose-next-steps` produces a proposal that the prior run did not.

If none of those happen, derivation is just reformatting and the speculation about honesty was wrong. That's also a useful result — we'd know not to invest further.

## Deferred (intentionally, not forgotten)

The following were drafted in `2026-05-18-polymorphic-telemetry-contracts.md` and are **not in scope** for v1:

- **Six measurement frameworks (polymorphism).** Hypothesis from walking through other GiftKaro capabilities; no actual failure yet from one schema. Revisit after a second capability is onboarded and the single schema visibly breaks.
- **Error budgets and burn-state classification.** Amplification of a redesign we haven't built. Revisit if the approved-criteria proposals are still binary or shallow after the lean loop runs for a few weeks.
- **Cross-platform vocabulary, `event-vocabulary.yml`, adapter dispatch.** No mobile project in scope. Revisit when one arrives.
- **Approval state machine, audit history, multi-revision tracking.** YAML edits are enough for v1.
- **`/haytham:derive-vocabulary`, `/haytham:approve-criteria`.** Commands we don't need yet.

Each of these is a real future-want. None is justified by evidence right now.

## Open questions for the lean v1

1. Where does the property ID and baseline snapshot live in the derived file? Probably stays in the same place it does today, but worth confirming once we see what derivation actually emits.
2. When a founder modifies a criterion (`status: modified`), should the derivation note that on the next re-run and preserve the modification, or should re-derivation start fresh? Lean answer: preserve modifications, surface diffs.
3. Should `telemetry.derived.yml` replace `telemetry.yml` once approved, or coexist? Lean answer: coexist until we've seen one full loop, then decide.

These don't need to be resolved before starting. They're the kind of questions whose answer becomes obvious once the first derivation runs.
