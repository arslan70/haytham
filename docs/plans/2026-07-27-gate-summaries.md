# Founder-readable gate summaries (issue #72)

## Context

Gates 2 and 3 ask the founder to approve work whose only on-disk form is JSON: `phase-2-what/capabilities.json`, `system-traits.json`, `phase-3-how/build-buy.json`, `architecture-decisions.json`, `research-directives.json`. The commands do render a digest inline at the gate (`commands/specify.md:101-110`, `commands/design.md:65-74`), but that digest is composed on the fly by whichever session is orchestrating, its quality varies, and it is never written to disk. The approval record in `gate-decision.json` therefore does not say what the founder actually read. Phase 1 does not have this problem because `validation-report.md` is already prose.

Outcome: each of the two gates gets a persisted, agent-authored `gate-summary.md`, the gate renders that file instead of improvising, and `gate-decision.json` records the path plus a SHA-256 of the exact text that was approved.

Decisions already taken:
- The specialist agent that owns the JSON writes the summary in the same pass. It is the only actor that knows the cuts it made and the questions it could not resolve, and none of that is in the JSON. Precedent: `agents/report-synthesizer.md:33` already produces `validation-report.md` and `validation-report.json` from one agent, with an explicit cross-artifact consistency rule at `:213`. `agents/feasibility-screener.md:75` does the lighter version of the same thing.
- Scope is Gate 2 and Gate 3 only. Phase 1 already ships prose, Phase 4 has no `gate-decision.json` at all.
- Provenance goes in `gate-decision.json` as `summary_shown` + `summary_sha256`.

## Artifact contract

One filename, both phases: `.haytham/session/phase-2-what/gate-summary.md` and `.haytham/session/phase-3-how/gate-summary.md`. Same name because it is the same concept (the thing rendered at a gate), and `gate-decision.json` sits next to it in both dirs.

Phase 2 sections (written by capability-modeler):

```markdown
# What we are building
[2-3 sentences: system purpose, who it is for]
## What is in
[one bullet per functional capability: name, what the founder gets, the IN SCOPE item it serves]
## What is out
[IN SCOPE items with no capability, and notable cuts, each with the reason]
## Judgment calls
[decisions that could reasonably have gone the other way, e.g. why two behaviors were kept as one capability]
## Open questions
[what the scope did not settle; "None" if empty]
```

Phase 3 sections (written by architect):

```markdown
# How we are building it
[2-3 sentences: shape of the system]
## The stack
[per component: name, BUILD/BUY/HYBRID, one line of why]
## Decisions that matter
[3-5 decisions a founder would regret getting wrong, each with the alternative that was rejected]
## What this costs
[monthly cost range, integration effort]
## Unknowns to resolve before building
[each research directive with research_required true, as a plain question]
```

Constraints to state in both agent prompts: prose only, no JSON blocks, under 600 words, no em dashes (`AGENTS.md:139-147`), no vendor API surface (`agents/architect.md:179`, `:218-235`), and explicitly **for the founder only, no downstream agent reads it** so it never becomes a re-derivation input (`AGENTS.md:195-197`).

Tone: reuse the founder-persona switch that `agents/report-synthesizer.md:54-60` and `:82-88` already define, reading `founder_profile` from `concept-anchor.json`. Both agents already read that file, so this costs nothing. Copy the rule, do not invent a second tone standard.

## Changes

### 1. Agents write the artifact

- `agents/capability-modeler.md`: add a Part 3 after the system-traits part with the section template above, and add `.haytham/session/phase-2-what/gate-summary.md` to the File I/O **Write to** block (`:240-242`). Add one self-check bullet: every functional capability appears in "What is in".
- `agents/architect.md`: add a Part 4 after research directives with the template above, and add the path to the File I/O **Write to** block (`:398-401`). Tools are already `Read, Write`, no frontmatter change.

### 2. Commands name the artifact in every launch prompt

The agent contract alone is not enough: the launch prompts enumerate write targets, and a prompt that lists two files while the agent lists three invites the agent to skip one. Append `and .haytham/session/phase-{N}/gate-summary.md` to every site that launches these agents:

- `commands/specify.md:99` (initial), `:145` (checker re-run), `:167` (gate revision)
- `commands/design.md:50`
- `commands/haytham.md:453`, `:506`, `:534` (phase 2 mirrors), `:583` (phase 3)

The dependency table at `commands/haytham.md:29-45` lists reads only, so it needs no change.

### 3. Gates render the file instead of improvising

- `commands/specify.md` Step 5 (`:152-155`): replace "Read `capabilities.json` and output the following inline" with "Read `.haytham/session/phase-2-what/gate-summary.md` and output it inline, verbatim. Then point at the JSON files for detail." Keep the existing gate questions (`:157-163`) unchanged.
- `commands/design.md` Step 2 (`:65-74`): same substitution against `phase-3-how/gate-summary.md`. Step 1's digest (`:55-63`) stays, it is a progress message, not the gate.
- `commands/haytham.md:519` (Gate 2) and `:600-611` (Step 13 Review) get the identical substitution. Batch mode branches (`:515`, `:603`) still write the summary, they just skip the human.

### 4. Provenance in gate-decision.json

Add to the JSON template at `commands/specify.md:171-183` and `commands/design.md:86-93` (and the mirrors at `commands/haytham.md:540`, `:624`):

```json
"summary_shown": ".haytham/session/phase-2-what/gate-summary.md",
"summary_sha256": "[shasum -a 256 of the file as shown]"
```

Both commands already have `Bash` in `allowed-tools`, so `shasum -a 256 <path>` is available. Instruct: compute the hash immediately after rendering, before asking the gate question, so a later edit to the summary is detectable.

### 5. Validation

`scripts/validate_schema.py`:
- New `if basename == "gate-summary.md"` branch in `validate_markdown()` (`:71-258`). Dispatch is by basename only, so branch on the parent directory inside it to pick the required section list per phase. Warn on: missing required section, a ```` ```json ```` fence (means the agent dumped the artifact instead of summarizing), word count over 600.
- Phase 2 coverage check: open the sibling `capabilities.json` and warn for any functional capability `name` that does not appear in the summary text. `research-brief.md` already reads sibling files this way (`:163`), so the pattern exists.
- `gate-decision.json`: leave `SCHEMAS` (`:19-36`) alone, the new fields are additive. Add a phase-aware check: if `phase` is 2 or 3 and `summary_shown` is absent, warn. Warnings are non-blocking by design (`:9`).

`tests/test_plugin_sanity.py`, in `TestSchemaValidation` (`:246+`), with new fixtures under `tests/fixtures/`:
- `valid_gate_summary_phase2.md` and a missing-section variant
- a phase-2 summary that omits a capability present in `capabilities_for_cross_check.json`
- `gate_decision_no_summary.json` at phase 2, expect the warning; a phase 1 one, expect none

### 6. Downstream and docs

- `commands/build.md:68`: add `gate-summary.md` to the **Do NOT copy** list, same treatment as `gate-decision.json`. It is a gate rendering, and the JSON it summarizes is already copied. The "all 10 files" count at `:85` stays correct.
- `commands/plan.md:106-114`: add the two `gate-summary.md` lines to the Phase 2 and Phase 3 blocks of the completion inventory.
- Completion messages that enumerate outputs: `commands/specify.md:187`, `commands/design.md:96`, and the `haytham.md` equivalents.
- Three copies of the artifact tree, all of which drift already: `README.md:63-90`, `docs/how-it-works.md:144-172`, `docs/getting-started.md:36-46`. Add one sentence to the `docs/how-it-works.md` Gate 2 and Gate 3 sections saying each gate now renders a persisted summary.
- Optional, after the end-to-end run: drop the produced `gate-summary.md` files into `examples/gym-leaderboard/` and list them in that example's README table, matching how `mvp-scope.md` and `validation-report.md` are already shown there.
- Bump `plugins[0].version` in `.claude-plugin/marketplace.json` (currently `0.4.0`).
- The repo keeps plan documents in `docs/plans/YYYY-MM-DD-slug.md`. Land this plan as `docs/plans/2026-07-27-gate-summaries.md` so the decision trail stays in the repo, and reference issue #72 in the commit.

## Risks

- **`haytham.md` drift.** Phase 2 and 3 logic is duplicated between the standalone commands and `commands/haytham.md`, and the copies have already drifted (`design.md:73` says "N findings resolved, N questions remaining" where `haytham.md:611` says "N questions"). Every edit above must land in both. Merging those files is a real fix but is out of scope here.
- **Prose drifting from JSON.** Mitigated by same-pass authorship plus the coverage warning, not eliminated. Accepted: the summary carries cuts and open questions that the JSON does not hold, so it cannot be a pure projection.
- **In-flight working tree.** `commands/specify.md`, `commands/haytham.md`, `AGENTS.md`, `docs/how-it-works.md` and the new `agents/capability-checker.md` are uncommitted (issue #71 work). Line numbers above are against the working tree, not HEAD. Land or stash that first.

## Verification

1. `python3 -m pytest tests/test_plugin_sanity.py -v` passes, including the new schema cases.
2. Direct validator exercise: write a deliberately broken `gate-summary.md` under a temp `.haytham/session/phase-2-what/` and call `validate_file()` on it, confirm each warning fires and that a good file produces none.
3. End to end on a real idea, which is the only check that proves the agents actually write the file:
   ```
   /haytham "a gym community leaderboard with anonymous handles"
   ```
   Confirm: both `gate-summary.md` files exist, each gate printed the file contents inline rather than an improvised digest, the sections are populated (not template placeholders), `gate-decision.json` in both phases carries `summary_shown` and a `summary_sha256` matching `shasum -a 256` of the file on disk.
4. Second run on a different product class (a CLI tool) to confirm the section templates are not web-app specific (`AGENTS.md:47`).
5. Run the phase 2 checker loop with at least one accepted proposal and confirm the re-run rewrites `gate-summary.md` rather than leaving the pre-addition version.
6. `/haytham:build` into a scratch dir: confirm `gate-summary.md` is not copied into `openspec/context/` and the context table still lists 10 files.
