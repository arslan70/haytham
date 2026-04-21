# `/haytham:evolve` v1 Evaluation: GiftKaro Bundle Categories

**Date:** 2026-04-18 pre-registration; revised 2026-04-19 — runs via `/haytham:evolve` v1 (tool reads the full reasoning graph and applies a maintenance-demanding prompt template; no classifier).
**Project:** GiftKaro
**Change type:** Feature addition with IA restructuring (capability creation, not capability swap)
**Experiment goal:** Does `/haytham:evolve` v1 — the two-ingredient recipe (full-graph file list + maintenance-demanding prompt template) — handle capability creation plus a discovery-model change as well as Path C's manual prompt handled the easier integration swap?

## Why this change

Week 1 Path C established that a one-line prompt directive flips a fresh Claude Code session from "ignore the graph" to "read 15 openspec files, maintain 8 of them coherently with code." That was tested manually, for a like-for-like integration swap — the easiest case.

This experiment is the first real invocation of `/haytham:evolve` v1. It tests whether thin orchestration still works when the change requires *creating* a new capability, *restructuring* the discovery model, and *possibly revising* a concept-anchor invariant — not just swapping one capability for another like Path C did.

The change is real. The GiftKaro team wants bundle categories as the primary discovery mechanism so buyers can navigate by occasion (Festive, Birthday, Anniversary, Apology, Get-Well, Love, Family) rather than scanning a flat catalog. Not invented for the test.

## Change request

Single run, no A/B. Week 1 already established that unprompted sessions (Path B) ignore the graph; a control run would repeat a known finding. This experiment is the first `/haytham:evolve` invocation, not a comparison.

The change description passed to `/haytham:evolve`:

> Introduce bundle categories as the primary discovery mechanism for GiftKaro. Redesign the home page to be category-first: buyers land on the site, see the seven categories (Festive, Birthday, Anniversary, Apology, Get-Well, Love, Family), and drill into a category to browse the bundles in it. This replaces the current flat catalog listing as the main entry point. Use the existing logo and color palette as visual reference.

The tool is expected to:
1. Confirm `./openspec/` exists at CWD.
2. Name the full graph in the generated prompt: `concept-anchor.json`, `capabilities.json`, `mvp-scope.md`, `architecture-decisions.json`, `system-traits.json`, `build-buy.json`, plus every file under `openspec/specs/*/spec.md` (including `specs/gift-catalog/spec.md`).
3. Generate a prompt that demands maintenance alongside implementation.
4. Hand off to the execution agent in the same session.

The change description deliberately does not resolve the 3-5 bundles / 7 categories tension. Whether the agent surfaces that tension or silently expands the catalog is part of what we're measuring.

## Pre-registered predictions

Written before the run. Not revised after results.

### What `/haytham:evolve` v1 should produce if it works

1. **New subcapability added to `capabilities.json`.** Something like CAP-F-001.1 "Category-based browsing" or a new CAP-F-004. The existing CAP-F-001 (catalog browsing) is refined, not replaced.
2. **New Gherkin scenarios in `specs/gift-catalog/spec.md`.** Scenarios for: landing on category-first home, drilling into a category, viewing a category with no bundles, returning to home from a category. The existing 4 scenarios are updated or supplemented — not silently overwritten.
3. **Architecture decision recorded for the data-model choice.** New DEC entry in `architecture-decisions.json` covering: column on `bundles` table vs separate `categories` table; whether category is a string enum or a referenced row; how the home-page query is shaped. The choice itself isn't predicted; the recording is.
4. **`mvp-scope.md` updated.** Discovery model changing from "flat catalog" to "category-first" is a real scope refinement. Should appear in the scope section.
5. **Graph and code committed together.** Like Path C: zero divergence between what the code does and what the docs say it does.

### Hard cases to watch

1. **`concept-anchor.json` `interaction_model` invariant.** Currently reads "E-commerce browse-select-pay flow: expat browses catalog, selects gift, pays internationally, recipient receives locally." Category-first doesn't break this — "browses catalog" is still accurate — but a strict reading of the invariant could argue the mechanism matters. Prediction: the agent reads the invariant, notes it's not broken, and leaves it alone. Concern: the agent silently revises it (over-maintenance) or misses that it should be checked (under-maintenance).
2. **3-5 bundles / 7 categories tension.** The current constraint in `mvp-scope.md` and `CLAUDE.md` is a 3-5 bundle catalog. Seven categories means most categories will be empty at launch. Prediction: the agent surfaces this tension, either in a clarifying question, in the updated `mvp-scope.md`, or in a DEC entry, and recommends one of: (a) hide empty categories at launch, (b) expand the catalog, (c) keep 3-5 bundles but show all 7 categories with "Coming soon" affordances. Concern: the agent silently expands the catalog to "justify" 7 categories, or silently ignores the tension and ships empty categories.
3. **Visual redesign without a design brief.** The graph doesn't capture visual design. Agent has logo + color palette as the only anchors. Prediction: agent produces a reasonable category-first home with the existing palette, no catastrophic design regressions. Not rubric-scored at pixel level — noted qualitatively.

## Evaluation rubric

Six scored criteria. Each scored Pass / Partial / Fail with a one-line justification.

1. **Invariant check.** Does the new discovery model respect `concept-anchor.json` invariants (access_model, interaction_model, target_user, product_catalog)? Were any invariants correctly revised OR correctly left alone based on whether the change actually touched them?
2. **Capability boundary.** Was a new subcapability or capability created in `capabilities.json`? Were the right existing capabilities (CAP-F-001 catalog browsing, CAP-F-005 admin management) touched and the wrong ones (CAP-F-002 payments, CAP-F-003 notifications) left alone?
3. **Scenario regression.** Did the agent add new Gherkin scenarios for the category-first flow? Were the existing 4 scenarios in `specs/gift-catalog/spec.md` updated where affected (e.g., the browse scenario if the home page changed)?
4. **Architecture alignment.** Was the data-model choice (column vs table, enum vs reference) recorded in `architecture-decisions.json`? Did the agent preserve existing DEC entries that shouldn't change (DEC-STACK-001 Next.js, DEC-DB-001 Supabase)?
5. **Context documentation.** Is `openspec/` consistent with the change after the commit?
6. **Scope-tension surfacing.** Did the agent notice and flag the 3-5 bundles / 7 categories tension? Pass = surfaced and recommended a resolution. Partial = surfaced but didn't resolve. Fail = silently expanded the catalog or silently ignored empty categories.

One sanity record alongside the rubric (not scored): the generated prompt, full text, logged separately. Confirms the tool correctly embedded the change description, the full graph file list, and the maintenance demand before hand-off.

## Procedure

```bash
cd /Users/amehboob/Documents/GitHubPersonal/giftkaro.pk
git checkout -b experiment/week-2-bundle-categories 9d47cf9
claude   # fresh Claude Code session
# invoke:
/haytham:evolve "Introduce bundle categories as the primary discovery mechanism for GiftKaro. Redesign the home page to be category-first: buyers land on the site, see the seven categories (Festive, Birthday, Anniversary, Apology, Get-Well, Love, Family), and drill into a category to browse the bundles in it. This replaces the current flat catalog listing as the main entry point. Use the existing logo and color palette as visual reference."
```

Don't steer. If the agent asks clarifying questions, respond factually only (e.g., "yes, seven categories; don't add more") but volunteer nothing about predictions, rubric, or the 3-5-bundle tension. Log the full prompt `/haytham:evolve` generated so the tool's output can be reviewed independently from the agent's execution. Commit the agent's output to the branch when done. Capture the session JSONL to `docs/experiments/week-2-session.jsonl`.

## Results

Session JSONL: `docs/experiments/week-2-session.jsonl` (local only, gitignored). Merged PR: [arslan70/giftkaro.pk#1](https://github.com/arslan70/giftkaro.pk/pull/1) on branch `experiment/week-2-bundle-categories`, merged 2026-04-19 14:41 UTC.

- **Active agent time:** ~1h05m. Session opened 13:23:40Z; `/haytham:evolve` invoked 13:29:44Z; PR requested 14:34:52Z; last event 14:35:47Z.
- **Code files changed (vs `9d47cf9`):** 13 files — `src/lib/categories.ts` (new, single source of truth), `src/app/page.tsx` (home rewritten), `src/app/categories/[slug]/page.tsx` (new), `src/components/catalog/{CategoryCard,CategoryGrid}.tsx` (new), `src/components/admin/{BundleForm,BundleList}.tsx`, `src/app/admin/dashboard/page.tsx`, `src/app/api/admin/bundles/route.ts`, `src/types/index.ts`, `supabase/migrations/002_bundle_categories.sql` (new), `CLAUDE.md`, `next.config.js` (dev-only CSP fix for Next.js React Refresh, discovered during manual test).
- **openspec files read:** 11 — 6 context files + 5 spec files (all specs present in GiftKaro openspec: gift-catalog, admin-management, checkout-and-orders, cross-cutting, trust-signals).
- **openspec files modified:** 5 — `openspec/context/mvp-scope.md`, `openspec/context/capabilities.json`, `openspec/context/architecture-decisions.json`, `openspec/specs/gift-catalog/spec.md`, `openspec/specs/admin-management/spec.md`. Left alone: `concept-anchor.json`, `system-traits.json`, `build-buy.json`, `checkout-and-orders/spec.md`, `cross-cutting/spec.md`, `trust-signals/spec.md`.
- **Generated prompt:** matches the v1 template verbatim. Change description embedded as given. File list enumerated 6 context files + 5 globbed specs. Maintenance rules present in full. Emitted at 13:30:24Z as a fenced code block before execution, per spec. See session JSONL line 62.
- **Did the agent surface the 3-5 bundle / 7 category tension?:** Yes. At 13:31:02Z — before any code was written — the agent emitted "Scope tensions identified (none are invariant conflicts — all resolvable via graph updates)" and flagged three loci: `mvp-scope.md` § 5 ("3-5 pre-built bundles"), `capabilities.json` CAP-F-001 acceptance ("3-5 bundles"), and `gift-catalog/spec.md` scenario ("3-5 bundles"). Resolution path: replace the scope item with a category-first framing where category count is fixed at seven but bundle count per category is flexible. This is a hybrid of pre-registered options (b) expand the catalog and (c) keep 3-5 total but show all 7 categories — rather than hiding empty categories, the agent added both an acceptance criterion and a Gherkin scenario for "category with no active bundles is still displayed but marked."
- **Reasoning trail summary:**
  1. 13:30:24Z — assembled prompt stated as a code block.
  2. 13:30:24Z–13:31:00Z — read all 11 graph files.
  3. 13:31:02Z — surfaced three scope-tension loci; explicitly evaluated `interaction_model` ("browse-select-pay is extended, not violated"), `product_catalog` (unchanged), and the occasion set against the product identity. No invariant conflicts.
  4. 13:32:17Z — stated implementation plan. Step 6 listed graph updates, including `admin-management/spec.md`.
  5. 13:32:17Z–13:37:27Z — implemented code + migration + graph updates; first commit (`28ba82e`) shipped code and all 5 graph-file updates in lockstep.
  6. 13:38:10Z — user asked for local test; agent started dev server.
  7. 13:42:57Z — user steered: "We would also need changes to modify the admin panel for this change." (The agent's plan at 13:32:17Z already included `admin-management/spec.md`; the first commit already updated the admin form to require a category. The steer extended scope to the grouped dashboard view, not the capability boundary itself.)
  8. 13:53:18Z–14:18:37Z — debugging of admin auth (placeholder password) and a CSP `unsafe-eval` error from Next.js React Refresh. Resolved with a dev-only CSP relaxation in `next.config.js`.
  9. 14:34:13Z — second commit (`d1cd24d`) landed the grouped admin dashboard view.
  10. 14:34:52Z — user asked for a PR; agent created it.
- **Rubric scores:**
  1. **Invariant check: Pass.** `concept-anchor.json` left untouched. Agent explicitly reasoned about `interaction_model`, `product_catalog`, and the identity-level "occasion-specific gift bundles" framing, and concluded no invariant was violated. `mvp-scope.md`'s § "Flagged scope risks" discussion of `interaction_model` was updated (from 4-5 surfaces to 5-6) because that section references the interaction model, not because the invariant changed.
  2. **Capability boundary: Pass.** CAP-F-001 (catalog browsing) refined, not replaced. CAP-F-005 (admin management) updated. Payments (CAP-F-002), notifications (CAP-F-003), checkout/trust specs left alone. Caveat: the user nudged an admin-dashboard UX addition; without the nudge, the capability boundary would still have been right (admin-management spec update was already in the plan and in commit 1), only the dashboard-grouping polish would have been missing.
  3. **Scenario regression: Pass.** `gift-catalog/spec.md`: 2 new scenarios added (drill-in, empty category); all 4 existing scenarios correctly updated where the home-page change affected them. `admin-management/spec.md`: 1 new scenario (reject-without-category) and existing "admin creates a new bundle" updated to require category assignment. No scenarios silently dropped.
  4. **Architecture alignment: Pass.** New `DEC-CATEGORIES-001` recorded for the closed-taxonomy + text-slug decision, with 3 alternatives considered (admin-editable table, multi-category tags, client-side filter chips). `DEC-DB-001` updated minimally to describe the category column without touching the core Supabase/RLS rationale. Stack, Stripe, Vercel, Tailwind DECs untouched.
  5. **Context documentation: Pass.** Code and all 5 graph-file updates shipped in the same first commit (`28ba82e`). `openspec/` is consistent with the code after the merge.
  6. **Scope-tension surfacing: Pass.** Surfaced before writing code (13:31:02Z); recommended and applied a resolution (category-first scope item replaces "3-5 pre-built bundles"; bundle count per category noted as flexible). Did not silently expand the catalog or ship empty categories — explicit scenario + acceptance criterion added for the empty-category state.

**Score: 6/6 Pass.** Passes the ship criterion for v1 (≥5/6) with margin.

## Interpretation

**Did the tool correctly construct the prompt?** Yes. The generated prompt at 13:30:24Z matches the v1 template verbatim — change description embedded, 11 reasoning-graph files enumerated (6 fixed context + 5 globbed specs), four maintenance rules present, "zero drift" ship criterion stated. This confirms `commands/evolve.md`'s substitution and glob logic work.

**Did thin orchestration handle capability creation + IA restructure?** Yes, cleanly. The agent surfaced the pre-registered hard cases (interaction_model invariant, 3-5/7 scope tension, empty categories) without prompting and resolved them in a way that's consistent with the reasoning graph's existing shape. The prediction that `concept-anchor.json` would be left alone held. The prediction that the scope tension would be surfaced and resolved held. The agent's choice of resolution (category-first scope item with flexible bundle count, plus explicit handling for empty categories) went slightly beyond the options I'd pre-registered — this is a good sign that the agent read the scope intent rather than picking from a menu.

**The one contamination:** at 13:42:57Z the user steered with "We would also need changes to modify the admin panel." This did not affect the capability-boundary or graph-maintenance scores because the admin-management spec update was already in the agent's plan at 13:32:17Z and landed in commit 1. The steer added a grouped-dashboard UX polish (commit 2) that wasn't purely needed for the capability — but it also wasn't a graph update. N=1, so worth noting but not load-bearing.

**What this says about v1:** the two-ingredient recipe (full-graph file list + maintenance-demanding prompt template) is sufficient for capability creation + IA restructure, at least on a project the graph author understands well. The cuts made at design time — no classifier, no file-picker, no drift detector — did not cost this run anything. The "leave files alone" rule correctly filtered `concept-anchor.json`, `system-traits.json`, `build-buy.json`, and three orthogonal specs at read-time.

**Does `/haytham:evolve` need tightening before the TinyTales cross-project test?** No. Proceed to Week 2 of the final push plan as written. The TinyTales run is the actual cross-project bedrock — this result says v1 is worth spending that test on, not that v1 is universally proven.

## Limitations

- N=1. Second data point for thin orchestration; more would tighten confidence.
- Same evaluator (me), same graph author. Rubric may favor graph-maintenance outcomes.
- Visual redesign is out-of-graph. Rubric captures structural/IA/capability work strictly; visual quality is noted qualitatively but not scored.
- Claude Code version-specific behavior. If the agent's willingness to follow prompted directives drifts in future versions, these results shift too.
- Tool v1 is minimal. A failure could live in the tool (file list or prompt template) or in thin orchestration itself (agent ignoring or misapplying maintenance rules). Logging the generated prompt is how we distinguish them.

## Next steps

- [x] `/haytham:evolve` v1 built (Week 1 of the final push plan). Shipped as `commands/evolve.md` (haytham commit `b1e3d87`).
- [x] Run the experiment. Recorded in Results section.
- [x] Score rubric. Interpretation written.
- [x] Run passed (6/6): proceed to TinyTales cross-project test in Week 2 of the final push.
- [ ] Defer: promote Path C (Safepay + graph maintenance) to main when ready.
