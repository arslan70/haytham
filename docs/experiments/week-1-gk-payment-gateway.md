# Week 1 Experiment: GiftKaro Payment Gateway Swap

**Date:** 2026-04-17
**Project:** GiftKaro (primary Evolution test project)
**Change type:** Integration change
**Experiment goal:** Does a fresh Claude Code session with the full reasoning graph produce a measurably better change than one with a well-documented CLAUDE.md alone?

## Why this change

Stripe doesn't onboard Pakistani-registered businesses, so GiftKaro's production payments are blocked. The team needs to replace it. This is also the "integration change" type the sprint plan predicts will show the strongest reasoning-graph delta, because payment gateways are picked to satisfy a specific constraint set (cross-border buyers, multi-currency, webhook pattern, idempotency, 60-second SLA) that the codebase doesn't document on its own.

## Change request (identical for both paths)

> Stripe doesn't work for GiftKaro — Pakistani-registered businesses can't onboard. Replace Stripe with a payment gateway that does work for us, and integrate it.

Spare on purpose. Both paths must derive constraints from what's in their context. A more specific prompt stops measuring what the reasoning graph adds.

## Pre-registered predictions

Written before either path runs. Do not revise after results come in.

### Context files expected to carry the delta (Path B only)

- `concept-anchor.json` invariants — `target_user: Pakistani diaspora living abroad` and `interaction_model: expat browses, pays internationally, recipient receives locally`. Establishes that the buyer is abroad, not in Pakistan. The code doesn't say this explicitly; CLAUDE.md mentions it in passing; the invariant list makes it a hard constraint.
- `architecture-decisions.json` DEC-PAYMENTS-001 — full constraint set Stripe was picked to satisfy: server-side Payment Intent (control over form layout), multi-currency USD/GBP/AED, idempotency via Payment Intent ID, webhook-driven confirmation.
- `architecture-decisions.json` DEC-NOTIFY-001 — ties the 60-second email SLA to webhook delivery speed.
- `architecture-decisions.json` DEC-INTEGRITY-001 — idempotency key semantics.
- `capabilities.json` CAP-F-002 acceptance criteria — literally says "Stripe payment widget accepts USD, GBP, and AED."
- `openspec/specs/checkout-and-orders/spec.md` — 11 Gherkin scenarios, likely mentioning Stripe-specific terms.

### Path A predictions (codebase + stripped CLAUDE.md)

1. Gateway choice may ignore the diaspora-abroad constraint. Path A may pick domestic Pakistani gateways (JazzCash, EasyPaisa) that primarily work for Pakistani buyers paying PKR. Without the concept anchor's hard invariants, "Pakistan" signals in CLAUDE.md can pull the wrong way.
2. `openspec/` is removed from the Path A branch, so no graph updates happen regardless. The agent won't notice it's missing.
3. Webhook signature verification may be looser. Different gateways have different signing schemes, and Path A may port the pattern without treating it as a first-class invariant.
4. Faster completion time (less context to read), but at the cost of graph-level work not happening.

### Path B predictions (codebase + full CLAUDE.md + openspec/)

1. Gateway choice explicitly rules out domestic-only gateways after reading concept anchor invariants. Candidate gateways (Safepay, Checkout.com, PayPro, or similar) are justified against the DEC-PAYMENTS-001 constraint set.
2. `DEC-PAYMENTS-001` is superseded or amended with the new decision and its rationale.
3. Cascading decisions are flagged: DEC-INTEGRITY-001 (idempotency key source), DEC-NOTIFY-001 (webhook signing), DEC-DB-001 (`stripe_payment_intent_id` column name).
4. `capabilities.json` CAP-F-002 acceptance criteria and relevant Gherkin scenarios in `specs/checkout-and-orders/spec.md` are updated to remove Stripe-specific references.
5. Webhook signature verification is treated as a first-class invariant and ported correctly.

### Expected parity

Both paths should: identify the right Stripe-touching files, install the new SDK, update env vars, preserve the server-side payment intent pattern (it's evident in the code structure), preserve multi-currency handling, and miss subtle production edge cases (3DS flow, refund semantics) that only surface when the founder runs the flow live.

## Evaluation rubric

Applied identically to both paths. Each criterion scored Pass / Partial / Fail with a one-line justification.

1. **Invariant check.** Does the chosen gateway satisfy the diaspora-abroad buyer model (international cards accepted, Pakistani settlement possible)?
2. **Capability boundary check.** Did the run touch the right capabilities (CAP-F-002, CAP-F-003, CAP-NF-002, CAP-NF-003) and leave the others alone? Were Stripe-specific acceptance criteria in `capabilities.json` updated?
3. **Scenario regression check.** Walk the 11 Gherkin scenarios in `specs/checkout-and-orders/spec.md`. For each: does the new implementation support it? Were Stripe-specific scenarios updated, or left stale?
4. **Architecture alignment.** Did the run preserve DEC-PAYMENTS-001's constraint set (server-side intent equivalent, multi-currency, webhook-driven, idempotency)? Did it update `architecture-decisions.json`?
5. **Context documentation.** Did the run keep `openspec/context/` consistent with the change? Drifted graph means less usable input for the next change.
6. **Objective metrics.** Time to complete; files touched.

## Procedure

Both paths branch from GK `main` at commit `9d47cf9` (feat: Add config.yaml for giftkaro service details and traits). Branches are already created:

- `experiment/path-a-payment-gateway` — setup commit `ab7182b` strips CLAUDE.md's Strategic Context + Specification sections and removes `openspec/`
- `experiment/path-b-payment-gateway` — identical to main at `9d47cf9`, no setup changes

Neither merges back. To run:

```bash
cd /Users/amehboob/Documents/GitHubPersonal/giftkaro.pk
git checkout experiment/path-a-payment-gateway   # or path-b when running Path B
claude                                             # fresh Claude Code session
```

Paste the change request prompt verbatim and let the agent run. Do not steer. Commit its output to the branch when done.

### Path A — control

1. From `main`, create `experiment/path-a-payment-gateway`.
2. Edit CLAUDE.md: delete the "Strategic Context" section and the "Specification" section. Leave everything else (project description, tech stack, project structure, Key Architecture Decisions summary, data model, coding rules, constraints, env vars).
3. `git rm -r openspec/` to remove the reasoning graph from this branch. Main still has it; this is branch-local.
4. Commit both changes.
5. Start a **fresh** Claude Code session in this branch. No prior conversation. No memory about openspec.
6. Paste the change request prompt verbatim.
7. Let it run to code completion. Don't steer. If it asks clarifying questions, answer factually but volunteer nothing about the graph.
8. Commit its output to the branch.
9. Record below: time to complete, files touched, gateway chosen, reasoning trail.

### Path B — treatment

1. From the same starting commit on `main`, create `experiment/path-b-payment-gateway`.
2. Leave CLAUDE.md and `openspec/` unchanged.
3. Start a **fresh** Claude Code session. No prior conversation.
4. Paste the same change request prompt.
5. Let it run. Don't steer.
6. Commit its output to the branch.
7. Record below: time to complete, files touched, which `openspec/` files the agent actually read, gateway chosen, reasoning trail.

## Results

_Empty until runs complete._

### Path A

- **Gateway chosen:** Paddle (Merchant-of-Record model)
- **Time to complete:** 1h 22m 56s
- **Files touched:** 16 files (277 insertions / 251 deletions). Added `src/lib/paddle.ts`, `src/app/api/webhooks/paddle/route.ts`. Removed `src/lib/stripe.ts`, `src/app/api/webhooks/stripe/route.ts`. Edited `src/components/checkout/PaymentWidget.tsx` in place to swap SDK. Modified `supabase/migrations/001_initial_schema.sql` directly (renamed `stripe_payment_intent_id` → `paddle_transaction_id` in the initial migration rather than adding 002).
- **Gateways considered:** Paddle (chosen), Safepay, 2Checkout/Verifone. Paddle justified as "preserves the current mental model... MoR model removes a whole category of cross-border tax risk from a solo-founder operation." Safepay ruled out on "founder takes on FX and tax burden." 2Checkout ruled out on developer experience.
- **Reasoning trail summary:** Agent spent the bulk of the session exploring payment gateway options via web research, then narrowing on the tax/compliance angle. Reasoning focused on founder-ops tax simplification rather than concept-anchor invariants. Webhook signature verification was not explicitly discussed. 60-second email SLA was not mentioned.
- **Rubric scores:**
  1. **Invariant check: PARTIAL.** Paddle accepts international cards (USD/GBP/AED) from diaspora buyers — satisfies the surface invariant. But MoR makes Paddle the seller of record, which introduces a business-model shift not authorized by `concept-anchor.json` (founder-operated supply chain, direct merchant relationship). The founder would need to evaluate whether MoR fits the bootstrapped-self-funded / founder-managed identity.
  2. **Capability boundary: N/A.** `openspec/` was removed by the setup commit, so the agent had no capability model to update. It could not fail a check that didn't exist.
  3. **Scenario regression: N/A.** Same reason — `specs/checkout-and-orders/spec.md` was removed by setup. No regression check possible.
  4. **Architecture alignment: PARTIAL.** Server-side payment init preserved (Paddle transactions). Multi-currency preserved. Webhook-driven order creation preserved. Idempotency migrates from PI ID to transaction ID — structurally intact. Gaps: webhook HMAC signature verification not explicitly discussed in reasoning trail; 60-second SLA not engaged with; DEC-PAYMENTS-001 rationale not visible to the agent (Key Architecture Decisions summary in CLAUDE.md survived the strip, but the constraint set behind it did not).
  5. **Context documentation: N/A.** No `openspec/` on branch; nothing to drift.

### Path B

- **Gateway chosen:** Safepay
- **Time to complete:** 8m 7s
- **Files touched:** 16 files (303 insertions / 306 deletions). Added `src/lib/safepay.ts`, `src/app/api/webhooks/safepay/route.ts`, and a new `supabase/migrations/002_replace_stripe_with_safepay.sql` (additive, preserves 001 history). Removed `src/lib/stripe.ts`, the Stripe webhook route, and `src/components/checkout/PaymentWidget.tsx` entirely (Safepay uses hosted checkout, so the widget became unnecessary — ~100 lines of UI code deleted).
- **openspec files actually read:** Zero. The agent ran `ls openspec/` twice and opened no files from the graph. It explicitly called `openspec/` "archived proposals" and left them untouched.
- **Gateways considered:** Safepay (chosen), 2Checkout/Verifone, Paddle/Lemon Squeezy. Safepay justified as "purpose-built for Pakistani-registered businesses, accepts international cards in USD/GBP/AED from your expat buyers." 2Checkout ruled out on local-settlement complexity. Paddle/Lemon Squeezy ruled out because MoR changes the merchant relationship.
- **Reasoning trail summary:** Fast, anchored decision. Agent identified Pakistani-registered + international-card-accepting constraint from `CLAUDE.md`'s product description ("e-commerce site for Pakistani expats... pay in USD/GBP/AED"), picked Safepay, and executed. Explicitly referenced HMAC-SHA256 webhook signature verification as an invariant to preserve. Followed Safepay's hosted-checkout pattern, which is why PaymentWidget.tsx could be deleted rather than rewritten.
- **Rubric scores:**
  1. **Invariant check: PASS.** Safepay is Pakistani-registered (direct match to the implicit business-model invariant) AND accepts international USD/GBP/AED cards (direct match to diaspora-abroad target_user invariant from `concept-anchor.json`, even though the agent didn't read that file).
  2. **Capability boundary: FAIL.** `capabilities.json` was available on branch. Agent did not read it and did not update CAP-F-002's Stripe-specific acceptance criteria. Graph is now stale.
  3. **Scenario regression: FAIL.** `openspec/specs/checkout-and-orders/spec.md` was available with 11 Gherkin scenarios. Agent did not read or update. Stripe-referenced scenarios left stale.
  4. **Architecture alignment: PARTIAL.** Code-level: all DEC-PAYMENTS-001 constraints preserved (server-side tracker init, multi-currency USD/GBP/AED, webhook-driven, idempotency via Safepay tracker ID mapping 1:1 to the old `stripe_payment_intent_id` role, explicit HMAC signature verification). Documentation-level: `architecture-decisions.json` not touched — DEC-PAYMENTS-001 still lists Stripe as the payment gateway. Graph and code diverged in a single commit.
  5. **Context documentation: FAIL.** `openspec/` drifted the moment Safepay landed. No cascading updates to DEC-PAYMENTS-001, DEC-INTEGRITY-001, DEC-NOTIFY-001, DEC-DB-001 (`stripe_payment_intent_id` column reference), `capabilities.json` CAP-F-002, or the Gherkin scenarios referencing Stripe.

### Path C (prompted traversal — added after A/B)

Same branch point as Path B (main at `9d47cf9`, full CLAUDE.md + openspec untouched). The only change from Path B was one added sentence in the prompt naming three openspec files to read and directing the agent to update any openspec files referencing Stripe.

- **Gateway chosen:** Safepay (same as Path B)
- **Active agent time:** 7m 46s (6m 20s before hitting the context window limit; 1m 26s after resumption in a fresh session). Wall clock 10h 16min due to an overnight pause between sessions — use active time for comparison to A/B.
- **Code files changed:** 24 files (494 insertions / 398 deletions). Same gateway-swap pattern as Path B (new `src/lib/safepay.ts`, Safepay webhook route, delete Stripe code, delete `PaymentWidget.tsx`, new migration 002) *plus* a `pending_checkouts` table to carry recipient/delivery metadata across the Safepay hosted-checkout redirect (Safepay's metadata field is too narrow). More robust than Path B's approach on this point.
- **openspec files read:** 15 unique. Prompted three (`concept-anchor.json`, `architecture-decisions.json`, `specs/checkout-and-orders/spec.md`) plus 12 the agent followed unprompted: `capabilities.json`, `build-buy.json`, `system-traits.json`, `mvp-scope.md`, `validation-report.md`, `specs/cross-cutting/spec.md`, `project.md`, `config.yaml`, and the three `changes/initial-mvp/*` historical proposal files.
- **openspec files modified:** 8. `architecture-decisions.json` (DEC-PAYMENTS-001 rewritten; DEC-NOTIFY-001, DEC-INTEGRITY-001, DEC-DB-001, DEC-STACK-001 updated for cascade); `capabilities.json` (CAP-F-002 acceptance criteria rewritten from Stripe widget to Safepay hosted checkout, CAP-F-003 SLA updated, added `payment_gateway` field); `build-buy.json`; `system-traits.json`; `mvp-scope.md`; `validation-report.md`; `project.md`; `specs/checkout-and-orders/spec.md` (all 11 Gherkin scenarios walked and updated — idempotency key → `safepay_tracker_id`, "payment widget" → "Safepay hosted checkout", "webhook verified" → "HMAC signature verified"). `concept-anchor.json` read but correctly left unedited (upstream invariant, not downstream record). Historical `changes/initial-mvp/*` also correctly untouched.
- **Gateway rationale:** "Safepay... the closest Pakistani equivalent to Stripe — Payment Intent–style API, webhook signing, accepts international Visa/Mastercard from USD/GBP/AED cardholders, and settles to a Pakistani business bank account." Concept-anchor invariants satisfied in outcome but not quoted verbatim in the trail. Paddle explicitly rejected by citing `architecture-decisions.json`.
- **Webhook signature:** Explicit HMAC-SHA256 with `timingSafeEqual` comparison, `x-sfpy-signature` header validation, 400 on mismatch. First-class invariant treatment — parity with Path B, stronger than Path A.
- **Rubric scores:**
  1. **Invariant check: PASS.** Safepay satisfies diaspora-abroad and Pakistani-settlement invariants. DEC-PAYMENTS-001 rewrite names both constraints explicitly.
  2. **Capability boundary: PASS.** CAP-F-002 acceptance criteria updated; CAP-F-003 SLA updated; `payment_gateway` summary field added; other capabilities untouched.
  3. **Scenario regression: PASS.** All 11 Gherkin scenarios walked and updated where Stripe-specific. Cross-cutting spec also read.
  4. **Architecture alignment: PASS.** Code preserves all DEC-PAYMENTS-001 constraints. `architecture-decisions.json` updated with Stripe→Safepay swap and four cascading DEC entries.
  5. **Context documentation: PASS.** Graph and code committed together. Zero divergence.

## Comparison

### Did pre-registered predictions hold?

Mostly no. Several predictions were wrong in directions that matter more than if they had been right.

**Wrong in Path A's direction:**
- Predicted Path A would pick a domestic-only gateway (JazzCash/EasyPaisa) without catching the diaspora-abroad constraint. It didn't — it picked Paddle (global MoR). But Paddle introduces a *different* invariant violation: MoR makes Paddle the seller of record, a business-model shift not authorized by the founder-operated / bootstrapped identity in the concept anchor. Different failure mode than predicted, but still a failure.
- Predicted Path A would be faster ("less context to read"). **Opposite: Path A took 10× longer (1h 22m vs 8m).** Stripping Strategic Context + Specification from CLAUDE.md didn't speed the agent up — it made the agent wander. With less anchoring, the solution space felt more open, so Paddle's "remove tax risk" angle pulled harder than it should have.

**Wrong in Path B's direction:**
- Predicted Path B would supersede `DEC-PAYMENTS-001`, update `capabilities.json` CAP-F-002, update the 11 Gherkin scenarios, and flag cascading decisions (`DEC-INTEGRITY-001`, `DEC-NOTIFY-001`, `DEC-DB-001`). **None of this happened.** Path B dismissed `openspec/` as "archived proposals" after a single `ls` and never opened the files.
- Predicted Path B's gateway choice would be "justified against the DEC-PAYMENTS-001 constraint set." The choice was correct (Safepay satisfies every constraint) but the justification in the reasoning trail came from `CLAUDE.md`'s product description, not the graph.

**Right:**
- Path B did treat webhook signature verification as a first-class invariant. Explicit HMAC-SHA256 discussion in the reasoning trail.
- Path B chose a gateway that satisfies the diaspora-abroad buyer model.

### Where did Path B's advantage actually come from?

Not from graph traversal. Path B had `openspec/` available and explicitly chose not to read it. So the mechanism isn't what was predicted.

Three candidate explanations:

1. **CLAUDE.md richness.** The full CLAUDE.md has the Strategic Context table (pointing to `concept-anchor.json`, `architecture-decisions.json`, etc.) and the Specification table (pointing to the spec files). The agent didn't open those files, but the *presence* of an authoritative-looking index may have narrowed the solution space — implicit signal that "there's a frame here, don't reinvent." This is the most plausible explanation.
2. **Stripping-induced drift.** Path A's stripped CLAUDE.md left the agent with no frame beyond tech stack. With less anchoring, the agent spent more time exploring meta-questions (tax/compliance/MoR) and less time matching the existing pattern.
3. **N=1 variance.** Single run per path. Some of the delta is noise.

Best guess: 1 + 2 together, with some 3. The reframe below assumes 1 is real.

### What the three runs showed together

Path A (stripped CLAUDE.md, no openspec on branch) took 10× longer than Path B and picked Paddle — whose Merchant-of-Record model shifts the business identity in a way the concept anchor does not authorize. Path B (full CLAUDE.md, openspec available but not named in the prompt) picked Safepay correctly and shipped clean code in 8 minutes, but explicitly dismissed `openspec/` as "archived proposals" and let the graph drift the moment the code landed. Path C (same as B plus one added sentence naming three graph files and demanding maintenance) picked Safepay in the same active time, then read 15 openspec files (the three named plus 12 it followed unprompted) and committed the code change alongside updates to 8 graph files.

The pattern across the three runs:

- **Graph absence** (A) produces slower, solution-space-drifting reasoning and a worse gateway choice.
- **Graph presence without traversal directive** (B) produces a correct code change but lets the graph go stale in a single commit.
- **Graph presence with a one-line traversal directive** (C) produces the same code change *plus* coherent graph maintenance at negligible extra active-time cost.

This inverts what I predicted. I expected the value to come from the richness of the graph itself. The value actually comes from the *prompt that points at the graph*. The graph is infrastructure; the prompt nudge is the orchestration.

### Gate 1: PASS. Proceed to Week 2.

The Evolution thesis holds in its prompted-traversal form. `/haytham:evolve` does not need a prescriptive update engine. The minimum orchestration it needs is:

1. The graph exists (GENESIS output).
2. The evolve prompt names entry-point graph files.
3. The evolve prompt issues an explicit maintenance directive ("update any files that reference the replaced element").

Week 2 should test generalizability. Path C demonstrated thin orchestration works for an **integration swap** (Stripe→Safepay). The next question is whether it holds for a change type that isn't a like-for-like replacement. Two candidates from the GiftKaro roadmap:

- **Feature addition.** Bundle categories (Festive/Birthday/Anniversary/Apology/Get-Well/Love/Family). Requires touching `capabilities.json` (new subcapability), `specs/gift-catalog/spec.md` (new Gherkin scenarios), data model (new column/table), and UI. Tests whether thin orchestration extends to capability *creation*, not just swap.
- **Scope change.** Extending delivery geography from Islamabad/Rawalpindi to Karachi. Requires revising `concept-anchor.json` (delivery_geography is currently a hard invariant), `mvp-scope.md`, fulfillment logic, and copy throughout. Tests whether thin orchestration extends to invariant *revision* — the hardest case.

Recommend **feature addition** (bundle categories) for Week 2. It's the more common change type for an in-flight product, and it exercises capability creation — the direction `/haytham:evolve` has to handle, not just the easy case. Scope change / invariant revision can slot into Week 5 as the three-sequential-changes test, where we also need variety.

Operational finding from Path C worth carrying into `/haytham:evolve` design: the full traversal + code-change + graph-maintenance pass nearly exhausted the context window and required a session resume. Comprehensive maintenance may not fit a single turn on larger changes. Either split code-change and graph-maintenance into explicit turns, or budget context headroom on the maintenance pass. Validate in Week 2.

### Limitations of this conclusion

- N=1 per path. Run each path a second time before building on Week 1 findings if the call is load-bearing.
- Single evaluator (me); evaluator authored the reasoning graph and the predictions. The "Path A is worse because Paddle introduces MoR" judgment may be overstated — the founder has final say on whether MoR fits the business model.
- Path C satisfied concept-anchor invariants in outcome but did not cite them verbatim in the reasoning trail. If founder-accountability (audit trail showing which invariants a decision honors) matters, the evolve prompt directive needs to be stronger than Path C's.
- The agent's willingness to follow a one-line maintenance directive (Path C) and its refusal to read the graph without one (Path B) may both be specific to this Claude Code version. Future model behavior could drift either way.
- Neither path reached production. Real integration edge cases (3DS flow, refund semantics, webhook retry under Safepay's specific retry policy) were not exercised.
- Path C's context-window exhaustion during maintenance suggests the thin-orchestration approach has a scale ceiling that's unmeasured here.

## Limitations

- Single evaluator; evaluator authored the reasoning graph. No blinding.
- Rubric is derived from the graph, which could bias toward Path B.
- N=1 project for Weeks 1-2. Cross-project consistency check happens in Week 5 (TinyTales).
- No automated test suite in GiftKaro; scenario regression is a manual walkthrough.
- Neither path reaches production. The real integration can build on whichever output is stronger, or be redone via `/haytham:evolve` in Week 4.

## Next steps

- [ ] Founder reviews this doc. Any prediction or rubric criterion wrong?
- [ ] Create `experiment/path-a-payment-gateway` branch in GiftKaro. Run Path A. Record results.
- [ ] Create `experiment/path-b-payment-gateway` branch. Run Path B. Record results.
- [ ] Fill Comparison section. Answer Gate 1.
- [ ] If delta is material: proceed to Week 2 change request (GiftKaro, different change type — feature addition, scope change, or bug-class fix).
- [ ] If not: fall back to Gate 1 failure path per sprint plan (shift to Genesis polish).
