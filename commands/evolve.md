---
description: Apply a change to this project while maintaining the reasoning graph in openspec/
argument-hint: "description of the change"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Haytham: Evolve

Apply a change to this project and maintain the reasoning graph in `openspec/` alongside the code change. Thin orchestration — this command declares intent, the same Claude Code session executes.

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

## Construct the prompt

1. Glob `./openspec/specs/*/spec.md` to collect every per-capability spec file. If none exist (pre-initial-build state), proceed with only the context files below.

2. Build the reasoning-graph file list:

   - `openspec/context/concept-anchor.json`
   - `openspec/context/capabilities.json`
   - `openspec/context/mvp-scope.md`
   - `openspec/context/architecture-decisions.json`
   - `openspec/context/system-traits.json`
   - `openspec/context/build-buy.json`
   - Each `openspec/specs/*/spec.md` returned by the glob

3. Assemble the prompt by substituting `$ARGUMENTS` for `<CHANGE_DESCRIPTION>` and the file list above (as a markdown bullet list, one file per line) for `<FILE_LIST_BULLETS>` in the template:

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

4. State the full assembled prompt as a fenced code block in the response before executing. This is the sanity record — it lets the user (and the Week 2 evaluation) confirm the tool correctly embedded the change description, the full graph file list, and the maintenance rules.

## Execute

Run the assembled prompt in the same session:

1. Read every file in the list with the Read tool. Don't skip files.
2. Apply the maintenance rules to judge what the change affects and what it leaves alone.
3. Implement the change.
4. Update every graph file the change invalidates or refines.
5. Commit the code and the graph changes together.

If at any point the change conflicts with a `concept-anchor.json` invariant or violates an `mvp-scope.md` constraint, stop and surface it to the user before writing code.
