# Plan: Polymorphic telemetry contracts (derived + approved)

**Date:** 2026-05-18
**Status:** Design proposal, pre-build
**Milestone:** SENTIENCE (foundational)
**Supersedes for telemetry concerns:** 2026-05-16-propose-next-steps.md (the proposer survives; the contract shape it reads needs to be rebuilt)

## Goal

Replace today's hand-written, single-shape `telemetry.yml` with a polymorphic contract that:

1. Is **derived** by the system from the upstream reasoning graph (concept-anchor, capability spec, mvp-scope, architecture decisions), then **gated by founder approval**.
2. Supports **multiple measurement frameworks** per capability, so capabilities that don't fit a funnel shape (trust signals, internal tools, non-functional invariants) can be measured honestly instead of pretzel-shaped.
3. Treats **cross-platform** (web, mobile, anything else) as an adapter-and-vocabulary concern, not a fundamental contract-shape concern.

Without this, the SENTIENCE loop is mostly synthetic: the proposer "discovers" gaps the founder pre-annotated, and only works for the one capability whose measurement style happens to match the current contract format.

## Why now

Three things converged that exposed the current design's limits.

**One.** The first end-to-end loop run (2026-05-17) demonstrated the engineering closes, but on audit, every "finding" the system surfaced was something the founder had hand-annotated into `telemetry.yml` a day earlier. The proposer relayed; it didn't reason. See [docs/blog/posts/2026-05-27-can-you-ask-claude-code-to-improve-your-system.md](../blog/posts/2026-05-27-can-you-ask-claude-code-to-improve-your-system.md) for the public version; the cheating audit was sharper than the blog admits.

**Two.** A polished sentence in that blog post ("the success threshold my contract used to judge this capability depended on a measurement that wasn't actually being captured, so the system couldn't tell whether the capability was working") triggered the right question: *which agent actually did that work?* Answer: none. The contract author did. The system surfaced an annotation.

**Three.** Walking through the existing GiftKaro capabilities surfaced that `telemetry.yml` only fits the one capability we've used it on. Trust signals (CAP-F-004) measure indirectly via A/B uplift. Admin management (CAP-F-005) is operator-grade, not funnel-shaped. Mobile-responsive (CAP-NF-001) is a manual checkpoint. USD accuracy (CAP-NF-003) is an invariant. The current shape forces all of them into "success_thresholds with targets," which produces low-leverage criteria for everything except user-flow capabilities on web.

The fix is one design move with three parts.

## The shape of the redesign

### Part 1 — Derive, don't declare

Success criteria for a capability are **inferred** by `/haytham:derive-criteria` from upstream graph nodes, not hand-written by the founder. Each inferred entry carries a `derived_from[]` provenance trace (which source files, which acceptance criteria, which strategic signals contributed) and an `approval` state machine (`pending` → `approved` | `modified` | `rejected`).

The founder reviews proposed criteria via `/haytham:approve-criteria`. Accepted entries become the active contract. Modifications are recorded with `founder_note`. Rejections stick (re-derivation won't keep re-proposing rejected entries unless evidence has changed).

The `telemetry.yml` file is the persistent record of approved criteria plus their provenance. It is not a source of truth; the source of truth is the upstream graph. The file is a cache the proposer reads.

### Part 2 — Polymorphic frameworks

A capability has zero or more **aspects**. Each aspect uses one of six frameworks:

| Framework | When to use | Core fields |
|---|---|---|
| `funnel` | Sequential user flows | `steps[]`, `target`, `anti_signals` |
| `sli` | Latency / error rate / availability / crash-free rate / retention metrics | `metric`, `target`, `window` |
| `invariant` | Must-be-true properties | `property`, `check_via`, `fires_when` |
| `ab_attribution` | Indirect effects (UX, trust, persuasion) | `variants`, `outcome`, `attribution_window` |
| `usage_and_error` | Internal tools, low-volume capabilities | `usage_signals[]`, `error_signals[]` |
| `qualitative_checkpoint` | Things the system can't quantify | `check_procedure`, `check_interval`, `last_result` |

Six covers what I can see today. A seventh (probably `reputation` for app-store ratings, NPS, review sentiment) might be added when a mobile-first project needs it. Defer until a real capability resists all six.

A capability can have multiple aspects. Catalog might have both `funnel` (does it convert?) and `sli` (does it render in time?). The aspects list is just a list; composition is at the list level.

### Part 3 — Cross-platform as adapter detail

Platforms are declared at the project level. Each aspect refers to logical events, not provider-specific names. An adapter resolves logical events to provider queries per platform at query time.

Two new project-level concerns:

- **Platforms declared in `concept-anchor.json`** as a new top-level field (`"platforms": ["web", "mobile_ios"]`). Founder-owned strategic fact.
- **Adapter config in `.haytham/adapters.yml`** (per-project, per-platform). Operator-owned. Carries provider IDs, query endpoints. Separate from strategic intent because the lifecycles are different.
- **Logical-event vocabulary in `openspec/event-vocabulary.yml`** with per-platform mappings. Bootstrapped by `/haytham:derive-vocabulary` (scans spec files, proposes default mappings, founder confirms).

A capability declares `applies_to_platforms: [web, mobile_ios]`. The proposer queries each applicable platform separately and surfaces large per-platform deltas as candidates.

## Concrete shape: worked examples

Three examples chosen to span the polymorphism. Same capability scaffold (`capability`, `spec_ref`, `applies_to_platforms`, `derivation`, `aspects`, `differentiates_from`, `observations`); the aspect contents differ by framework.

### Example A — `gift-catalog` (funnel + SLI)

```yaml
capability: gift-catalog
spec_ref: openspec/specs/gift-catalog/spec.md#CAP-F-001
applies_to_platforms: [web]

derivation:
  last_run: 2026-05-19T01:23:00Z
  inferred_from:
    - openspec/context/concept-anchor.json
    - openspec/context/capabilities.json#CAP-F-001
    - openspec/specs/gift-catalog/spec.md

aspects:
  - framework: funnel
    name: catalog_to_product_conversion
    steps:
      - event: catalog_landing
      - event: view_item
    target: ">= 12%"
    anti_signals:
      - name: collapse
        condition: "step2/step1 < 5% over 7d"
    derived_from:
      - source: openspec/specs/gift-catalog/spec.md
        cite: "Acceptance: Selecting a category navigates to ... each bundle links to a product detail page."
        why: |
          The capability's job is moving buyers from category tile to
          product detail. That's the natural funnel.
      - source: openspec/context/concept-anchor.json
        cite: strategic_signals.success_metric = "revenue"
        why: |
          Revenue decomposes through orders → checkout → product views;
          this capability owns the product-views step.
    approval: { state: approved, reviewed_at: 2026-05-19 }

  - framework: sli
    name: catalog_render_time
    metric: largest_contentful_paint_p75
    target: "< 2500ms"
    window: 7d
    derived_from:
      - source: openspec/specs/gift-catalog/spec.md
        cite: "diaspora buyers mostly land from social ads on mobile browsers"
        why: |
          Catalog conversion only matters if pages render before the buyer
          loses patience. LCP under 2.5s is the standard mobile threshold.
    approval: { state: pending }
```

### Example B — `trust-signals` (A/B attribution + invariant)

The capability that motivated polymorphism. Funnel framing doesn't work because the effect is indirect.

```yaml
capability: trust-signals
spec_ref: openspec/specs/trust-signals/spec.md#CAP-F-004
applies_to_platforms: [web]

aspects:
  - framework: ab_attribution
    name: trust_signal_uplift
    variants:
      a: trust_signals_visible_above_fold
      b: trust_signals_hidden
    outcome:
      event: begin_checkout
      attribution_window: same_session
    target_uplift: ">= 10% relative"
    derived_from:
      - source: openspec/context/competitor-research.md
        cite: "Trustpilot widget praised when present; rare among competitors"
        why: |
          The competitive evidence says trust signals move conversion when
          present. If the wedge is real, an A/B should show uplift.
    approval: { state: pending }

  - framework: invariant
    name: trust_band_visible_on_load
    property: |
      On catalog and product detail pages, the trust-signal band must be
      rendered above the fold on both 375px and 1280px viewports.
    check_via: visual_regression_test
    fires_when: violated
    derived_from:
      - source: openspec/specs/trust-signals/spec.md
        cite: acceptance criteria
        why: |
          If the signals load below the fold, they don't influence the
          decision. The capability's job depends on the invariant.
    approval: { state: pending }
```

### Example C — `admin-catalog-management` (usage + qualitative)

The operator-grade capability that doesn't have a user funnel at all.

```yaml
capability: admin-catalog-management
spec_ref: openspec/specs/admin-management/spec.md#CAP-F-005
applies_to_platforms: [web]

aspects:
  - framework: usage_and_error
    name: admin_operations
    usage_signals:
      - event: admin_bundle_created
        target: "at least 1 per week"
      - event: admin_bundle_edited
        target: "any positive rate"
    error_signals:
      - event: admin_action_error
        threshold: "< 2% of admin sessions"
    derived_from: [...]
    approval: { state: pending }

  - framework: qualitative_checkpoint
    name: admin_friction_review
    check_interval: monthly
    check_procedure: |
      Founder runs a typical bundle update end-to-end, notes any friction
      the metrics don't show (slow loads, confusing copy, missing fields).
    derived_from:
      - source: openspec/context/concept-anchor.json
        cite: founder_intent.constraints.team = "small"
        why: |
          Admin is operator-grade for one person. Quantitative measurement
          misses the actual concern: does it slow the founder down.
    approval: { state: pending }
```

## The derivation pipeline

```
For each capability:
  1. Read spec, concept-anchor, mvp-scope, architecture-decisions.
  2. Classify: which frameworks apply?
       user-flow gestures + acceptance criteria → funnel
       non-functional measurement field → sli or invariant
       indirect persuasion / UX → ab_attribution
       internal / operator-grade → usage_and_error + qualitative
       anything unquantifiable → qualitative_checkpoint
  3. Determine platform applicability from spec + project platforms.
  4. For each (framework, platform) pair, derive aspect candidates with
     full derived_from provenance.
  5. Write candidates to telemetry.yml with approval.state = pending.
```

The classification step is real reasoning the system has to do, and it can be wrong. That's why the approval gate exists. If the system classifies trust-signals as `funnel` (wrong) and the founder reviews and rejects, the rejection plus reason becomes part of the contract's history, and re-derivation reads that history before proposing again.

## Three new commands

- **`/haytham:derive-criteria <capability>`** — reads upstream graph nodes for the capability, classifies, derives aspect candidates per framework, writes them to `telemetry.yml` with `approval.state = pending`. Prints the diff.
- **`/haytham:approve-criteria <capability>`** — interactive walk-through of pending entries. Founder accepts each, modifies each, or rejects each with reason. Sets approval state.
- **`/haytham:derive-vocabulary [logical_event_name]`** — scans spec files for event references, reads platforms from concept-anchor, proposes default mappings, founder confirms.

`/haytham:propose-next-steps` doesn't change much in surface but changes in behavior: it now reads **only approved aspects** from the contract. Pending and rejected entries are visible in the file but not load-bearing for proposal logic.

## Migration

The existing `gift-catalog/telemetry.yml` v3 doesn't get hand-restructured. It gets **re-derived**:

1. Move v3 to `telemetry.legacy.yml` for reference (one-time, manual).
2. Run `/haytham:derive-criteria gift-catalog`. This produces a polymorphic version with `approval.state = pending` on every aspect.
3. Compare the derived version against the legacy version. The derived version's `funnel` aspect should look very similar to the legacy `success_thresholds`. Any divergence is informative — either the legacy was wrong, or the derivation is wrong, or both are valid framings the founder needs to pick between.
4. Founder approves (or modifies, or rejects) each aspect.
5. Delete `telemetry.legacy.yml` once parity (or chosen divergence) is confirmed.

The "compare derivation against my hand-written v3" step is also **the test of the architecture**. If the derived version is materially worse than what I wrote by hand, the derivation prompt isn't doing enough work. That's a finding before we ship.

## Decisions made (during 2026-05-18 design walkthrough)

1. **Six frameworks, not more, not fewer.** Add a seventh only when a real capability resists all six. Likely candidate: `reputation` for app-store ratings / NPS.
2. **`qualitative_checkpoint` is a framework, not a meta-flag.** Compose at the aspect-list level. Don't introduce a `qualitative_supplements[]` field on every aspect.
3. **Cross-platform mismatches: per-platform observation, proposer judges what to surface.** No declared `platform_parity` field. If parity is genuinely required, express it in the capability spec.
4. **Platform list in `concept-anchor.json`; adapter config in `.haytham/adapters.yml`.** Different lifecycles, different owners.
5. **`event-vocabulary.yml` is derive-bootstrapped + grows incrementally.** Missing entries cause the proposer to fail fast and prompt for a mapping.

## Open questions / risks

- **Classification can be wrong.** The hardest reasoning step is deciding which framework(s) apply. Mitigation: founder approval gate; provenance trace; re-derivation can be re-run when wrong classification is corrected.
- **The `derive-criteria` prompt is non-trivial.** It has to do real reasoning over multiple files, classify, then produce structured output per framework. Risks: hallucinated criteria, missed frameworks, sloppy `derived_from` citations. The cold-proxy test method we used for `/haytham:propose-next-steps` applies here too.
- **Approved aspects vs reality drift.** A founder approves an aspect today. Six months later the spec changes but the approved aspect doesn't. The provenance trace makes the staleness visible (the citation now points to text that has been edited), but we need a "re-derive when sources have changed" hook. Defer to v0.2.
- **The `event-vocabulary.yml` chicken-egg.** First-time setup requires the founder to know event names. Can be eased with `derive-vocabulary` but the spec has to reference events for the derivation to work. Mitigation: when the spec doesn't name events, the derivation should propose canonical names per framework defaults (e.g., funnel steps default to `step_<n>` placeholders).
- **The legacy `gift-catalog` contract may be hard to compare cleanly.** Some of v3's fields (`baseline_snapshot`, `revisions`) have no direct analog in the new shape. Mapping them to the new structure is a manual exercise. One-time cost.

## Sequencing

Five phases. Each is shippable on its own.

1. **Schema design + worked examples for all six frameworks.** No code. Just the contract spec written down as JSON Schema (or equivalent) so future agents can validate output. Probably ~1 day.
2. **`/haytham:derive-criteria` for one capability.** Pick `trust-signals` (it's the one where the current shape fails hardest — clearest signal of polymorphism payoff). Manual review of output. No `approve-criteria` command yet; founder edits the file by hand to flip approval states. Probably 2-3 days.
3. **`/haytham:approve-criteria` command.** Interactive walk-through; persists approval state. Probably 1-2 days.
4. **Update `/haytham:propose-next-steps`** to read approved-only aspects. The proposer logic per-framework — comparing observations to `funnel` targets vs `sli` thresholds vs `invariant` violations vs `ab_attribution` outcomes — is real work. Probably 3-5 days.
5. **Cross-platform / vocabulary / adapters.** Defer until we have a real mobile project. The schema supports `applies_to_platforms` from day one but the runtime dispatch can wait. When needed, build `/haytham:derive-vocabulary` and the adapter dispatch logic. Probably a week when triggered.

Phases 1-4 are the v1 deliverable. Phase 5 is on-demand.

## What this plan deliberately defers

- **Automated re-derivation on source changes.** Out of v1. Founders run `derive-criteria` when they want to re-check.
- **The seventh framework (reputation).** Until a project needs it.
- **Multi-project vocabulary sharing.** Each project has its own vocabulary file in v1. Could become a shared registry later.
- **Audit history of approval changes.** Approval state is current-snapshot in v1. Git history is the audit trail.

## Definition of done for v1

- `/haytham:derive-criteria trust-signals` produces a polymorphic contract for GiftKaro's trust-signals capability with at least two aspects across two frameworks, all entries with full `derived_from` traces.
- `/haytham:approve-criteria trust-signals` walks the founder through pending entries; founder ends the session with at least one approved, one modified, and one rejected aspect.
- `/haytham:propose-next-steps` reads only approved aspects from the trust-signals contract and produces (or correctly refuses to produce, per the minimum-sample gate) a proposal.
- The existing `gift-catalog` v3 contract is re-derived; the derived version's funnel aspect is within "obvious agreement" of the legacy `success_thresholds` (modulo refactoring for the new shape). Any meaningful divergence is documented as a finding.
- Plugin sanity tests pass, including schema validation for the new contract shape.

When all five are true, the SENTIENCE loop has actually closed on something the system reasoned about, not something the founder pre-annotated. That's the real first version.
