# Haytham Final Push (4-week kill-or-keep decision)

**Date:** 2026-04-18
**Decision day:** 2026-05-16
**Status:** Active. Supersedes [2026-04-13-evolution-sprint-plan.md](./2026-04-13-evolution-sprint-plan.md).

## Why this plan exists

Haytham has had months of development and reached end-of-GENESIS with EVOLUTION in progress. The Week 1 experiment on GiftKaro produced a genuine technical proof point (Path C: thin orchestration maintains the reasoning graph at negligible overhead). The question now is whether Haytham earns its keep on a real in-flight product and whether the evolution machinery generalizes beyond the repo it was built in.

This plan replaces the original 8-week Evolution sprint with a compressed 4-week final push optimized for forcing a kill-or-keep answer, not for polishing the product. After Week 4, one binary outcome:

- **CONTINUE** — expand scope, plan next 3 months, potentially raise or generate revenue.
- **KILL** — publish post-mortem, open-source what's worth keeping, move on.

No "conditional continue." Gray zones defeat the purpose.

External validation (tester cohorts, blog posts, LinkedIn/Reddit) is deliberately out of scope. Those channels are too noisy to produce a clean signal for a project at this stage. Validation is inward: does Haytham accelerate shipping a real product (GiftKaro), and does the evolution command generalize to another repo (TinyTales). GiftKaro going live is the success story — not a post about the success story.

## Execution model

This plan lives in the Haytham repo and tracks all progress here. The code changes themselves happen in the target repos — GiftKaro and TinyTales — via `/haytham:evolve` once the command is built. Runs are driven by the founder or by Claude when a session has access to the target repo. Either way, outcomes are reported back to this file's Next steps checklist and to the corresponding experiment doc in `docs/experiments/`.

The Haytham repo is the control plane. Target repos are where changes land. Keeping the split clean matters: it's the same pattern Haytham pitches externally (control plane directing work across products it doesn't live inside).

Target repos:
- GiftKaro: `/Users/amehboob/Documents/GitHubPersonal/giftkaro.pk` (openspec at repo root)
- TinyTales: `/Users/amehboob/Documents/GitHubPersonal/tinytales/tiny-tales-studio` (openspec here, not at the outer `tinytales/` wrapper). Graph is already mature — full context + specs for five capabilities + `initial-mvp` change tracked. No Week 1 graph-build needed.

`/haytham:evolve` operates on the CWD's openspec directory, not a fixed repo root. Running it on TinyTales means invoking it from inside `tiny-tales-studio/`.

## The litmus test

Haytham **succeeds** if, on 2026-05-16, at least **two of these three** are true:

1. **GiftKaro evolution coherence.** `/haytham:evolve` ships ≥2 real GiftKaro changes with the reasoning graph staying coherent — openspec updated alongside code, zero drift between what the spec says and what the code does. "Real change" means something the GiftKaro team actually needs, not something invented to test Haytham.
2. **GiftKaro publicly live.** giftkaro.pk is live by 2026-05-16 and taking real orders through Safepay, with the category-first IA from Week 1 shipped. Not staging, not "almost live."
3. **Cross-project generalization.** `/haytham:evolve` works on TinyTales for one real change — graph stays coherent, agent reads the right entry points, no catastrophic regressions.

Haytham **fails** if none of these clears, or if shipping GiftKaro is noticeably slower with Haytham than it would be without. The whole pitch is that the graph accelerates evolution. If it adds ceremony without compounding value, the thesis is wrong.

### Bedrock kill criterion (overrides everything else)

If `/haytham:evolve` does not generalize from GiftKaro to TinyTales, the EVOLUTION premise is broken. Kill even if GiftKaro ships fine — a tool that only works on the repo it was developed in is a one-project script, not a reusable system.

## Four-week plan

### Week 1 (through 2026-04-25)

- Build minimal viable `/haytham:evolve`. Three ingredients: change classifier (integration / capability / scope / invariant), file-name picker per change type, prompt template demanding maintenance. No prescriptive update engine.
- Run `/haytham:evolve` on the GiftKaro bundle-categories change (capability creation + IA restructure). This is the v1 evaluation — score against the rubric in `docs/experiments/week-2-gk-bundle-categories.md`.
- Promote Path C (Safepay + graph maintenance) to GiftKaro main.
- TinyTales graph already in place (full context + specs for five capabilities). No build work needed, but do a quick sanity read before Week 2 to pick a plausible real change to run the cross-project test against.
- **Deliverable:** `/haytham:evolve` v1 shipped; bundle-categories evaluation scored; Path C on main; TinyTales target change picked.

### Week 2 (2026-04-26 to 05-02)

- **Cross-project technical test.** Run `/haytham:evolve` on TinyTales for one real change. This is the bedrock criterion — if it fails badly, decide whether to kill early or fix.
- If Week 1's bundle-categories run surfaced fixable issues in `/haytham:evolve`, address them before the TinyTales run.
- **Deliverable:** cross-project test result; kill-or-continue gut check.

### Week 3 (2026-05-03 to 05-09)

- Ship additional GiftKaro changes via `/haytham:evolve`. Whatever's in flight for launch prep.
- Build toward GiftKaro public launch: Safepay hookup complete, category-first IA polished, ordering flow end-to-end.
- **Deliverable:** ≥1 additional GiftKaro change shipped via `/haytham:evolve`; GiftKaro launch-ready.

### Week 4 (2026-05-10 to 05-16)

- Launch GiftKaro publicly. Site live, Safepay hooked up, taking real orders.
- Tally litmus on 2026-05-16. Commit to the answer.
- **Deliverable:** GiftKaro live; go/no-go decision committed; if CONTINUE, 3-month plan drafted; if KILL, post-mortem drafted.

## What this cuts from the original 8-week plan

- External tester cohort → removed. Inward validation via real GiftKaro usage is the primary signal.
- Public blog post during the sprint → removed. LinkedIn and Reddit are too noisy; a launch-stage project doesn't get meaningful signal from them. GiftKaro going live is the story.
- Separate manual Week 2 experiment → folded into the first `/haytham:evolve` invocation. The tool is the recipe; testing the recipe via the tool is tighter than running the recipe by hand.
- Week 5 three-sequential-changes robustness test → folded into GiftKaro's real change stream.
- Weeks 6-8 polish, marketplace prep, pitch deck → only if CONTINUE.

## If CONTINUE (post-2026-05-16)

- 3-month plan for scaling Haytham beyond the founder's own projects.
- Start scoping SENTIENCE milestone.
- Pitch deck, marketplace polish, comprehensive docs.
- GiftKaro + TinyTales remain primary testbeds; add 1-2 more projects for breadth.

## If KILL (post-2026-05-16)

- Post-mortem: what was tried, what worked, what didn't, what's reusable for future projects.
- Open-source what's worth preserving: GENESIS agent patterns, reasoning graph schema, Evolution experiment methodology.
- Founder moves on without sunk-cost drag.

## Open dependencies

- Founder bandwidth — this plan assumes ~4-6 hours/day split between Haytham and GiftKaro for 4 weeks. GiftKaro work IS Haytham work under this plan.
- TinyTales graph state — the cross-project test needs a reasoning graph to operate on. If TinyTales doesn't have one, Week 1 includes building the minimum needed.

## Risks

- **`/haytham:evolve` v1 is broken on first real use.** The tool is doing real GiftKaro work from Week 1 onward; a buggy classifier or file-picker blocks shipping directly. Keep the tool minimal and debuggable — log the generated prompt so failures can be attributed to the right layer (classifier / picker / execution) without re-reading the tool code.
- **GiftKaro launch slippage.** If the site doesn't go live by 2026-05-16, criterion 2 fails. Scope launch ruthlessly — MVP, not perfect.
- **Haytham as drag, not accelerator.** If shipping GiftKaro is slower with Haytham than without, that's a kill signal by itself regardless of the other criteria. Watch for it honestly.
- **Founder conviction.** If conviction is lost mid-push, KILL is the honest call even if criteria pass technically. Litmus is necessary but not sufficient.

## Next steps

- [x] Plan approved 2026-04-18.
- [ ] `/haytham:evolve` v1 built and shipped as a plugin command.
- [ ] Bundle-categories evaluation run via `/haytham:evolve`; results scored in `docs/experiments/week-2-gk-bundle-categories.md`.
- [ ] Path C promoted to GiftKaro main.
- [x] TinyTales reasoning graph confirmed (openspec present at `tiny-tales-studio/openspec`, full graph ready).
- [ ] TinyTales target change picked for the Week 2 cross-project test.
- [ ] Cross-project test on TinyTales via `/haytham:evolve`.
- [ ] ≥1 additional GiftKaro change shipped via `/haytham:evolve` during launch prep.
- [ ] GiftKaro publicly live.
- [ ] Litmus tallied; decision committed on 2026-05-16.
