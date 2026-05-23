---
description: Walk the founder through pending entries in telemetry.derived.yml and capture approve / modify / reject decisions. Writes the updated file in place.
argument-hint: <capability-id>
allowed-tools: Read, Write, Edit, Glob, Bash, AskUserQuestion
---

# Haytham: Approve Criteria

**Version:** 0.1 (2026-05-23 — codifies the manual wizard pattern that ran on gift-catalog. Pairs with `derive-criteria` v0.4's `founder_summary` and `why_it_matters` fields.)

Walks the founder through a derived telemetry contract, one approvable entry at a time, capturing decisions and writing them back to the file. The wizard's display layer is the `founder_summary` and `why_it_matters` fields written by `/haytham:derive-criteria` v0.4+. For older files that lack those fields, fall back to the `definition` / `text` field with a note.

**This is an interactive command.** It uses `AskUserQuestion` to walk the founder through decisions. Do not spawn sub-agents — the wizard is a single sequential conversation between this command and the founder.

## Argument

`$1` — the capability id (e.g. `gift-catalog`). Must match a directory under `./openspec/specs/`.

## Preconditions

1. Check `./openspec/` exists. If missing:

   > `openspec/` not found. Run `/haytham:approve-criteria` from the project root that contains the reasoning graph.

   Stop.

2. Check `./openspec/specs/$1/telemetry.derived.yml` exists. If missing:

   > No derived telemetry for `$1`. Run `/haytham:derive-criteria $1` first.

   Stop.

3. Parse the file and enumerate entries whose `status` is `pending` across:
   - `success_thresholds[]`
   - `anti_signals[]`
   - `regression_triggers[]`
   - `minimum_sample` (single entry, treat as one)

   If zero pending entries:

   > Nothing to review — all entries in `telemetry.derived.yml` are already approved, modified, or rejected. To re-derive, delete the file and run `/haytham:derive-criteria $1` again.

   Stop.

## Step 1 — Overview

Print to the user:

- Total pending entries: N (broken down: M success_thresholds, X anti_signals, Y regression_triggers, Z minimum_sample)
- Legend: **approve** = accept as-is, **modify** = keep the shape, override the number, **reject** = drop with a reason.
- "We'll go in batches of up to 4. After the pass, you'll have a chance to add back items derivation refused or didn't produce."

If the file lacks `founder_summary` fields (e.g., it was derived under `derive-criteria` v0.3 or earlier), also print:

> Note: this file was derived before the founder-facing layer existed. The wizard will fall back to the technical `definition` for each entry, which may be wordy. You can rerun `/haytham:derive-criteria $1` (delete the existing file first) to regenerate with plain-English summaries.

## Step 2 — Wizard loop

Process pending entries in batches of up to 4 via `AskUserQuestion`, in this section order:

1. `success_thresholds`
2. `anti_signals`
3. `regression_triggers`
4. `minimum_sample` (single entry, on its own)

For each entry, construct the wizard question as:

> **{founder_summary}** — target/threshold: `{target_or_threshold_value}`. Approve?

If `founder_summary` is missing, use the first sentence of `definition` (or `text` for triggers), prefixed with `[no founder summary] `.

The header chip is the entry's `name` (or first 12 chars of the trigger text) truncated to ≤12 characters.

Options for each entry (multiSelect: false):

- `"Approve at {value}"` — description: `"Accept as-is. Status → approved."`
- `"Modify the number"` — description: `"Keep the shape, change the value. I'll ask for the new value next."`
- `"Reject"` — description: `"Drop this entry. I'll ask for a reason next."`

After each batch, hold the answers in memory. Do not write to the file until the full pass is done.

## Step 3 — Follow up on modifications and rejections

For every entry the founder marked **"Modify the number"**, ask (batch up to 4 modification follow-ups per `AskUserQuestion` call):

> `{entry_name}` is currently `{original_value}`. What should it be?

Options:

- One slightly tighter alternative (computed from the entry's baseline)
- One slightly looser alternative
- The exact observed baseline (no headroom) for floor/anti-signal entries, or a tightened version for invariants
- (Founder uses "Other" for an arbitrary value)

For every entry the founder marked **"Reject"**, ask:

> Why are you rejecting `{entry_name}`?

Options:

- `"Wrong contract"` — captured reason: `"Wrong contract type — does not belong in behavioral telemetry."`
- `"Too complex / unclear"` — captured reason: `"Too complex for me to understand."`
- `"Not load-bearing"` — captured reason: `"Not important enough to track right now."`
- (Founder uses "Other" for a custom reason)

## Step 4 — Optional add-back

After the wizard loop, ask:

> Are there any criteria or anti-signals you want to add as **manual** entries — things derivation didn't produce, but that you consider load-bearing? (Common reasons: the upstream graph is under-specified, or the criterion is strategic intuition the spec doesn't encode yet.)

Options:

- `"Nothing to add"` — description: `"Skip this step."`
- `"I have a list"` — description: `"I'll provide names and descriptions next."`

If the founder picks `"I have a list"`, ask in plain text for the list and walk through each one. For each manual entry, capture:

- A short name (kebab-case)
- The section it belongs in (success_threshold / anti_signal / regression_trigger / differentiates_from)
- A one-sentence `founder_summary`
- A `why_it_matters`
- For threshold/anti_signal: the target/threshold value
- A `manual_note` explaining why the founder added it (this is the equivalent of `derived_from` for derivation: it justifies the entry)

Use `AskUserQuestion` only where there are clear discrete options; otherwise ask in plain text and parse the response.

## Step 5 — Write the updated file

Read the current `telemetry.derived.yml` again so the write is based on the latest disk state (in case the user edited it in another window during the wizard).

For each pending entry, update its `status` field:

- **Approved**: `status: approved`. No other field changes.
- **Modified**: `status: modified`. Update `target` (or `threshold`, or `value` for minimum_sample). Add `modification_note` field with one sentence capturing why the founder chose this number.
- **Rejected**: `status: rejected`. Add `rejection_reason` field with the captured reason.

For manual add-backs, append new entries to the appropriate section with:

- `status: approved`
- `source: manual`
- `manual_note: |` (the founder's reason)
- The `founder_summary` and `why_it_matters` captured during the add-back step
- The `target` / `threshold` / `value` captured

**Preserve all other fields, comments, and ordering in the file.** The wizard does not touch `derived_from`, `observed_baseline`, `calibration_rationale`, `derivation_notes`, or any other field on existing entries — only `status`, plus the new `modification_note` or `rejection_reason` fields where applicable.

Validate the file parses as YAML before declaring the wizard done. If parsing fails, surface the error and stop without overwriting the file.

## Step 6 — Summary

Print to the user:

- The path of the updated file
- Counts: N approved, N modified, N rejected, N added manual
- For modifications: a one-line summary per entry (`{name}: {old} → {new}`)
- For rejections: a one-line summary per entry (`{name}: {reason}`)
- For manual add-backs: a one-line summary per entry (`{name}: {founder_summary}`)

End with a soft pointer to the next step:

> The contract is reviewed. Run `/haytham:propose-next-steps` to see proposals against the approved entries.

## Step 7 — Stop

Do not auto-run `propose-next-steps`. The approval gate is the human-in-the-loop step — it stops here, by design.

## What this command does NOT do

- Does not re-derive criteria. If you need new shape (different SHALL coverage, fresh calibration), delete `telemetry.derived.yml` and run `/haytham:derive-criteria` again.
- Does not query GA4. Numbers come from the file's `observed_baseline` blocks (already populated by derivation in calibrated mode).
- Does not approve in bulk without per-entry walk. The wizard pace is the price of honest review. If the founder wants bulk approval, they can edit the file directly and skip the command.
- Does not handle multiple capabilities in one run. Reviewing two capabilities at once invites confused context — run the command twice.
