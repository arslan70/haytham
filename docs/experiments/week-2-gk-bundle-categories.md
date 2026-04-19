# `/haytham:evolve` v1 Evaluation: GiftKaro Bundle Categories

**Date:** 2026-04-18 pre-registration; revised 2026-04-19 to run via `/haytham:evolve` v1 instead of a manual prompt
**Project:** GiftKaro
**Change type:** Feature addition with IA restructuring (capability creation, not capability swap)
**Experiment goal:** Does `/haytham:evolve` v1 — the three-ingredient recipe (change classifier + file-name picker + maintenance-demanding prompt template) wrapped in a deterministic tool — handle capability creation plus a discovery-model change as well as Path C's manual prompt handled the easier integration swap?

## Why this change

Week 1 Path C established that a one-line prompt directive flips a fresh Claude Code session from "ignore the graph" to "read 15 openspec files, maintain 8 of them coherently with code." That was tested manually, for a like-for-like integration swap — the easiest case.

This experiment is the first real invocation of `/haytham:evolve` v1. It tests two things at once: (1) does the tool's classifier and file-picker correctly route a capability-creation change to the right openspec entry points? (2) does thin orchestration still work when the change requires *creating* a new capability, *restructuring* the discovery model, and *possibly revising* a concept-anchor invariant — not just swapping one capability for another?

The change is real. The GiftKaro team wants bundle categories as the primary discovery mechanism so buyers can navigate by occasion (Festive, Birthday, Anniversary, Apology, Get-Well, Love, Family) rather than scanning a flat catalog. Not invented for the test.

## Change request

Single run, no A/B. Week 1 already established that unprompted sessions (Path B) ignore the graph; a control run would repeat a known finding. This experiment is the first `/haytham:evolve` invocation, not a comparison.

The change description passed to `/haytham:evolve`:

> Introduce bundle categories as the primary discovery mechanism for GiftKaro. Redesign the home page to be category-first: buyers land on the site, see the seven categories (Festive, Birthday, Anniversary, Apology, Get-Well, Love, Family), and drill into a category to browse the bundles in it. This replaces the current flat catalog listing as the main entry point. Use the existing logo and color palette as visual reference.

The tool is expected to:
1. Classify this as capability-creation + scope-change (not capability-swap and not pure-invariant revision).
2. Pick openspec entry points based on the classification — at minimum `concept-anchor.json`, `capabilities.json`, `mvp-scope.md`, `architecture-decisions.json`, and `specs/gift-catalog/spec.md`.
3. Generate a prompt that names those entry points and demands maintenance alongside implementation.
4. Hand off to the execution agent.

The change description deliberately does not resolve the 3-5 bundles / 7 categories tension. Whether the tool (or the downstream agent) surfaces that tension or silently expands the catalog is part of what we're measuring.

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
4. **Tool-layer failures (new for v1).** Does the classifier correctly identify capability-creation? Does the file-picker pick all five required entry points, or does it miss one — most likely `concept-anchor.json`, since the change doesn't obviously touch invariants? A misroute here contaminates the thin-orchestration test regardless of prompt quality, so the procedure logs each layer's output.

## Evaluation rubric

Six scored criteria. Each scored Pass / Partial / Fail with a one-line justification.

1. **Invariant check.** Does the new discovery model respect `concept-anchor.json` invariants (access_model, interaction_model, target_user, product_catalog)? Were any invariants correctly revised OR correctly left alone based on whether the change actually touched them?
2. **Capability boundary.** Was a new subcapability or capability created in `capabilities.json`? Were the right existing capabilities (CAP-F-001 catalog browsing, CAP-F-005 admin management) touched and the wrong ones (CAP-F-002 payments, CAP-F-003 notifications) left alone?
3. **Scenario regression.** Did the agent add new Gherkin scenarios for the category-first flow? Were the existing 4 scenarios in `specs/gift-catalog/spec.md` updated where affected (e.g., the browse scenario if the home page changed)?
4. **Architecture alignment.** Was the data-model choice (column vs table, enum vs reference) recorded in `architecture-decisions.json`? Did the agent preserve existing DEC entries that shouldn't change (DEC-STACK-001 Next.js, DEC-DB-001 Supabase)?
5. **Context documentation.** Is `openspec/` consistent with the change after the commit?
6. **Scope-tension surfacing.** Did the agent notice and flag the 3-5 bundles / 7 categories tension? Pass = surfaced and recommended a resolution. Partial = surfaced but didn't resolve. Fail = silently expanded the catalog or silently ignored empty categories.

Plus tool-layer observations (not scored Pass/Fail, but recorded so failures can be attributed to the right layer):
- Classifier output — which change type did it return?
- File-picker output — which openspec files did it name?
- Generated prompt — full text, logged separately.
- Did the generated prompt include the maintenance demand?

## Procedure

```bash
cd /Users/amehboob/Documents/GitHubPersonal/giftkaro.pk
git checkout -b experiment/week-2-bundle-categories 9d47cf9
claude   # fresh Claude Code session
# invoke:
/haytham:evolve "Introduce bundle categories as the primary discovery mechanism for GiftKaro. Redesign the home page to be category-first: buyers land on the site, see the seven categories (Festive, Birthday, Anniversary, Apology, Get-Well, Love, Family), and drill into a category to browse the bundles in it. This replaces the current flat catalog listing as the main entry point. Use the existing logo and color palette as visual reference."
```

Don't steer. If the agent asks clarifying questions, respond factually only (e.g., "yes, seven categories; don't add more") but volunteer nothing about predictions, rubric, or the 3-5-bundle tension. Log the full prompt `/haytham:evolve` generated, so classifier/picker behavior can be evaluated independently from execution behavior. Commit the agent's output to the branch when done. Capture the session JSONL to `docs/experiments/week-2-session.jsonl`.

## Results

_Empty until run completes._

- Active agent time:
- Code files changed (vs 9d47cf9):
- openspec files read:
- openspec files modified:
- Classifier output:
- File-picker output:
- Generated prompt (full text logged to separate file):
- Did the agent surface the 3-5 bundle / 7 category tension?:
- Reasoning trail summary:
- Rubric scores:
  1. Invariant check:
  2. Capability boundary:
  3. Scenario regression:
  4. Architecture alignment:
  5. Context documentation:
  6. Scope-tension surfacing:

## Interpretation

_Empty until scored._

Key questions:
- Did `/haytham:evolve` v1's deterministic scaffolding (classifier + file-picker) work, or did the tool misroute?
- Given correct routing, did thin orchestration handle capability creation + IA restructure?
- Does `/haytham:evolve` need anything beyond the three ingredients before the TinyTales cross-project test, or is the v1 build sufficient to proceed?

## Limitations

- N=1. Second data point for thin orchestration; more would tighten confidence.
- Same evaluator (me), same graph author. Rubric may favor graph-maintenance outcomes.
- Visual redesign is out-of-graph. Rubric captures structural/IA/capability work strictly; visual quality is noted qualitatively but not scored.
- Claude Code version-specific behavior. If the agent's willingness to follow prompted directives drifts in future versions, these results shift too.
- Tool v1 is minimal. A failure could live in the classifier, file-picker, prompt template, OR thin orchestration itself. Logging each layer's output is the only way to attribute failure correctly.

## Next steps

- [ ] `/haytham:evolve` v1 built (Week 1 of the final push plan).
- [ ] Run the experiment. Record results.
- [ ] Score rubric. Write Interpretation section.
- [ ] If the run passes: proceed to TinyTales cross-project test in Week 2 of the final push.
- [ ] If the run fails on tool scaffolding (classifier/picker): fix the tool and re-run before TinyTales.
- [ ] If the run fails on thin orchestration itself (agent has right entry points but still doesn't maintain the graph): identify the failure mode and decide whether `/haytham:evolve` needs more than three ingredients. This is a meaningful design pivot.
- [ ] Defer: promote Path C (Safepay + graph maintenance) to main when ready.
