# `/haytham:evolve` v1 Design

**Date:** 2026-04-19
**Status:** Retired. `/haytham:evolve` shipped and closed the loop on GiftKaro, then was removed in the 2026-07-03 re-scope (v0.4.0). The command is preserved at git tag `v0.3.27-full`. This design is kept as a record.
**Context:** Week 1 of the final push ([plan](../plans/2026-04-18-haytham-final-push.md)). The first real test is the GiftKaro bundle-categories change ([pre-registration](../experiments/week-2-gk-bundle-categories.md)); the bedrock test is the TinyTales cross-project run in Week 2.

## What v1 is

A Claude Code plugin command that takes a plain-English change description, tells the executing agent which reasoning-graph files to read, and demands maintenance alongside the code change. Thin orchestration — the command declares intent. The downstream Claude Code session does the reasoning and writing.

## What v1 is not

- **Not a classifier.** An earlier draft routed changes to per-type file lists via a `integration | capability | scope | invariant | non-structural` enum. Cut before shipping — it added a misrouting failure mode without earning it. The maintenance rule "leave files alone if the change doesn't affect them" lets the agent filter at read-time. Reading the full graph is cheap; routing it correctly is a judgment call we don't need to make at tool level.
- **Not a drift detector.** It doesn't compare graph to code after the fact.
- **Not a prescriptive update engine.** It doesn't write the openspec updates itself.
- **Not a validator.** It doesn't enforce that the agent actually updated the files. The prompt demands it, the user verifies.
- **Not multi-repo aware.** It operates on the CWD's `openspec/` and nothing else.
- **Not interactive.** One invocation, one run. No mid-run approvals.
- **Not a rollback tool.** If the output is bad, revert via git.

Each cut is deliberate. Earning any of them requires evidence that thin orchestration without them is insufficient. v1 ships without; we add back only what Weeks 2-3 force.

## Invocation

```
/haytham:evolve "<change description>"
```

One argument. Free text describing what should change. The command assumes the user's CWD contains `openspec/` (the reasoning graph lives per-repo). If `openspec/` isn't at CWD, v1 says so and exits.

GiftKaro has `openspec/` at repo root. TinyTales has it at `tiny-tales-studio/openspec/`. The founder runs `/haytham:evolve` from whichever directory contains the graph.

## How it works

Two ingredients.

### 1. The graph file list

Deterministic. Every invocation reads the same files — the full reasoning graph.

- `openspec/context/concept-anchor.json` (invariants: target user, interaction model, access model, product definition)
- `openspec/context/capabilities.json` (what the system does for users)
- `openspec/context/mvp-scope.md` (scope boundary)
- `openspec/context/architecture-decisions.json` (structural/technical decisions)
- `openspec/context/system-traits.json` (cross-cutting properties)
- `openspec/context/build-buy.json` (build-vs-buy decisions)
- Every `openspec/specs/*/spec.md` (Gherkin scenarios per capability, discovered by glob)

**Why the whole graph, every time:**
- Cheap. Typical projects have 10-15 small files, ~30-50KB of context. Well inside budget.
- Safer. The agent can't maintain a file it didn't read. Reading everything eliminates the "missed file" class of failure.
- Simpler. No routing logic to misfire.
- Filtering is a prompt responsibility, not a tool responsibility. The agent decides what's affected based on the change description.

**Implementation:** The tool names the files in the generated prompt. The agent reads them itself with Claude Code's Read tool — the tool doesn't load content, it instructs.

**Edge case:** If a project has no `openspec/specs/` folder (pre-initial-build state), the spec glob returns nothing and the prompt includes only context files. Change will be pre-spec; graph maintenance is limited to context files.

### 2. The prompt template

Parameterized on the change description and the file list.

```
Change request:

<CHANGE_DESCRIPTION>

Before implementing, read these reasoning-graph files:

<FILE_LIST_BULLETS>

Maintenance rules, non-negotiable:
- Update any file that the change invalidates or refines. Do it in the same commit as the code change.
- Leave files alone if the change doesn't affect them. Don't over-maintain.
- If the change conflicts with an invariant in concept-anchor.json, stop and surface the conflict before writing code.
- If the change surfaces a scope tension (a constraint in mvp-scope.md that the change would violate), stop and recommend a resolution before writing code.

Zero drift between the graph and the code is the ship criterion. If you can't maintain that, say so instead of shipping.
```

**Why this wording:**
- Path C validated that a short directive is enough. v1's template is longer only because it has to carry maintenance rules the manual prompter handled implicitly.
- "Non-negotiable" and "stop and surface" are load-bearing phrases. Path C's success depended on the agent treating the graph as authoritative, not advisory.
- "Don't over-maintain" is from Week 2's hard-case concern — category-first doesn't actually break the `interaction_model` invariant, but a maximally-cautious agent might edit it anyway.

## The command file

Lives at `commands/evolve.md`. Invoked as `/haytham:evolve`.

Frontmatter (per plugin marketplace standards):

```yaml
---
description: Apply a change to this project while maintaining the reasoning graph in openspec/
argument-hint: "description of the change"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---
```

Body (pseudocode):

1. Check that `./openspec/` exists in CWD. If not, tell the user to run from the directory containing the reasoning graph and exit.
2. Glob `./openspec/specs/*/spec.md` to build the per-capability spec file list.
3. Construct the prompt using the template, substituting `$ARGUMENTS` for `<CHANGE_DESCRIPTION>` and the file list (fixed context files + globbed specs) for `<FILE_LIST_BULLETS>`.
4. State the full generated prompt so it's captured in the session JSONL for evaluation.
5. Execute the generated prompt in the same session — read the files, implement the change, apply maintenance rules, commit.

Step 4 is what the Week 2 evaluation grades against.

## What ships with v1

- `commands/evolve.md` — the command file.
- No new agents. The command runs in the user's Claude Code session directly. Thin orchestration doesn't need a dedicated subagent.
- Smoke test: the Week 2 bundle-categories run on GiftKaro ([pre-registration](../experiments/week-2-gk-bundle-categories.md)).
- `commands/build.md` updated to point new-project users at `/haytham:evolve` for future changes (held back from the recent build.md commit specifically for this moment).

## Open questions

1. **Should the command execute in the same session or spawn a subagent?** v1 says same session for simplicity. Subagent gives isolated context but adds orchestration complexity and makes failures harder to debug. Revisit if same-session runs show context pollution.
2. **Do we log the generated prompt to a file, or just the session JSONL?** v1 says session JSONL (already captured per the experiment protocol). A separate log file adds persistence complexity we don't need yet.

## How we know v1 works

v1 passes if the Week 2 GiftKaro bundle-categories run scores ≥5 Pass on the 6-criterion rubric, AND the Week 2 (plan Week 2) TinyTales cross-project run stays coherent on a real TinyTales change. Those are also the relevant litmus-test criteria from the final push plan.

v1 fails if the agent reads the right files but still lets the graph drift. That's a thin-orchestration failure on a real change — a meaningful design pivot signal. The response is either more prescription (tighten the template, add explicit maintenance checklists per file) or rethink the premise.

## Next step

Agree on the file list and prompt template. Then write `commands/evolve.md`.
