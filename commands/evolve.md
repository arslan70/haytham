---
description: Apply a change to this project while maintaining the reasoning graph in openspec/
argument-hint: "description of the change"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, TodoWrite
---

# Haytham: Evolve

Apply a change to this project and maintain the reasoning graph in `openspec/` alongside the code change. Three variant proposers run in parallel, the orchestrator synthesizes, the user confirms, then the chosen variant executes.

## Progress Tracking

After preconditions pass, call `TodoWrite` once with these items:

1. Build reasoning-graph file list
2. Run three variant proposers in parallel
3. Synthesize and recommend a variant
4. Confirm choice with the user
5. Execute chosen variant (code + graph changes)
6. Self-check pass

Mark the active item `in_progress` when its step starts and `completed` when its output is produced. If the user picks a hybrid or asks for re-synthesis, set step 3 back to `in_progress`.

## Preconditions

1. If `$ARGUMENTS` is empty, tell the user:

   > Provide a change description, e.g., `/haytham:evolve "Add a category-first home page"`.

   Then stop.

2. Check that `./openspec/` exists in the current directory:

   ```bash
   test -d ./openspec && echo ok || echo missing
   ```

   If missing, tell the user:

   > `openspec/` not found in the current directory. Run `/haytham:evolve` from the directory that contains the reasoning graph (e.g., the project root, or `tiny-tales-studio/` for TinyTales).

   Then stop.

## Step 1 — Build the reasoning-graph file list

1. Glob `./openspec/specs/*/spec.md` to collect every per-capability spec file. If none exist (pre-initial-build state), proceed with only the context files below.

2. Build the file list:

   - `openspec/context/concept-anchor.json`
   - `openspec/context/capabilities.json`
   - `openspec/context/mvp-scope.md`
   - `openspec/context/architecture-decisions.json`
   - `openspec/context/system-traits.json`
   - `openspec/context/build-buy.json`
   - Each `openspec/specs/*/spec.md` returned by the glob

3. Render the list as a markdown bullet list (one file per line). This is `<FILE_LIST_BULLETS>` below.

## Step 2 — Launch three variant proposers in parallel

Run three `Agent` tool calls **in a single message** (subagent_type=general-purpose). Each agent receives the same change description and file list, with a different framing appended. Each agent is a **read-only proposer** — it must not write code, must not write graph files, must not commit.

Substitute `$ARGUMENTS` for `<CHANGE_DESCRIPTION>` and the rendered list for `<FILE_LIST_BULLETS>`. The common preamble for every variant:

```
Change request:

<CHANGE_DESCRIPTION>

You are one of three parallel proposers. Read the reasoning graph and propose how this change should be applied. Do not write code. Do not modify any files. Produce only a proposal.

Read these files before proposing:

<FILE_LIST_BULLETS>

Hard stops:
- If the change conflicts with an invariant in concept-anchor.json, return only `INVARIANT_CONFLICT:` followed by the invariant text and the conflict. Do not propose anything else.
- If the change violates a constraint in mvp-scope.md, return only `SCOPE_CONFLICT:` followed by the constraint and the violation. Do not propose anything else.

Output format (markdown, in this exact order):

### Variant: <variant name>

**Files touched:** list every file you would create or modify, one per line, with a one-line note for each.

**Graph delta:** count of new capability nodes, new architecture decisions, modified specs, and modified context files.

**Tradeoff:** one paragraph naming what this variant gives up and what it gains. Cite a specific file or roadmap item from mvp-scope.md to ground the tradeoff. No hand-waving.

**Confidence: <0-100>** in this variant being the right call, with a one-line reason.
```

Append one of these three framings to each agent's prompt:

**Variant A — Minimal graph touch:**

```
Framing: Apply the change with the smallest possible delta to the reasoning graph. Prefer extending existing capabilities over adding new ones. Optimize for shipping today, not for reuse. If the change can be done by editing one spec, do that. New capability nodes are a last resort.
```

**Variant B — Clean refactor:**

```
Framing: Apply the change in a way that pays for itself within the next two features on the roadmap. Read mvp-scope.md to see what's coming. Add new capability nodes where reuse is foreseeable. Accept extra implementation cost if it prevents a near-term migration.
```

**Variant C — Pragmatic middle:**

```
Framing: Apply the change minimally, but introduce one new capability node if doing so removes a sharp future migration you can name. Cite the specific migration you would avoid (from mvp-scope.md or capabilities.json). If there is no such migration, default to a minimal-touch proposal.
```

## Step 3 — Handle conflicts and degenerate cases

After all three agents return:

1. **Invariant or scope conflict:** if ANY variant returns `INVARIANT_CONFLICT:` or `SCOPE_CONFLICT:`, stop. Surface the conflict to the user verbatim. Do not synthesize. Do not propose execution. Ask the user how to resolve.

2. **Identical proposals:** if two or three variants propose substantively the same set of file touches and the same graph delta, say so explicitly:

   > Variants A and C converged on the same proposal. Treating them as one.

   Do not fabricate differences.

3. **Empty graph state:** if `openspec/specs/` was empty and all three variants concluded "this is an initial build, not an evolution," stop and tell the user to run `/haytham:plan` instead.

## Step 4 — Synthesize and recommend

Render a comparison table to the user:

```
| Variant | Files touched | Graph delta | Tradeoff (short) | Confidence |
|---------|---------------|-------------|------------------|------------|
| A | N files | +0 nodes, +0 decisions | <one phrase> | NN |
| B | N files | +M nodes, +K decisions | <one phrase> | NN |
| C | N files | +M nodes | <one phrase> | NN |
```

Then commit to a recommendation in one paragraph. The recommendation must:

- Name the chosen variant and the one specific reason it wins
- Cite a file (`mvp-scope.md`, `capabilities.json`, or a spec path) that grounds the reason
- Say what the rejected variants gave up that mattered, in one sentence each

This is the orchestrator having an opinion. Do not hedge. Do not say "depends on your priorities." If two variants are genuinely tied, pick one and say why the tie-break went that way.

## Step 5 — Confirm with the user

Ask:

> Proceed with Variant <X>, or pick a different one? (Reply with `A`, `B`, `C`, or describe what you want changed.)

Wait for the user's response. If the user picks a different variant or asks for a hybrid, accept the override and proceed with their choice.

## Step 6 — Execute the chosen variant

Now and only now, write code and update the graph.

1. Read every file in the file list with the Read tool. Don't skip files. The chosen variant's proposal is a guide, not a substitute for re-reading the source of truth.
2. Implement the change per the chosen variant's "Files touched" list.
3. Update every graph file the change invalidates or refines, as specified by the variant's "Graph delta."
4. Leave files alone if the change doesn't affect them. Don't over-maintain.
5. Commit the code and the graph changes together in a single commit. The commit message names the variant chosen ("evolve: <change> [variant B]").

If during execution you discover the proposal was wrong (a file the variant said to touch doesn't exist, or a graph update produces a contradiction), stop and surface the discrepancy. Do not silently deviate from the proposal.

## Self-check

After implementing the change and updating the graph, before committing, run a self-check pass. List any concerns you noticed during the work that you did NOT block on. For each concern, assign a confidence score 0-100:

- 90-100: Specific, evidence-backed risk with a quoted file/line. The kind of thing that should be a follow-up issue, not silent debt.
- 80-89: Named risk with lower blast radius (e.g., a single spec scenario you couldn't fully verify).
- 60-79: Plausible concern without specific evidence. Likely a nit.
- <60: Style preference or speculative.

**Surface only concerns with confidence ≥ 80** in your final message. Collapse the rest into a single trailing line:

> N concerns below threshold suppressed.

A confidence score without a specific file/line citation is invalid. Score the citation, not the vibe. If there are zero concerns ≥ 80, say so explicitly — silence is ambiguous.
