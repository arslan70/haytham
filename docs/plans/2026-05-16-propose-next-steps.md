# Plan: `/propose-next-steps` (first step toward SENTIENCE)

**Date:** 2026-05-16 (plan), updated through 2026-05-18 (loop closed)
**Status:** Phase 1 done. Phase 2 v0.1 cold-validated, evolve commit landed on GiftKaro main, GA4 confirms loop closure. Next: proposer re-run today, then plan retrospective on past evolve changes (phase 3).
**Milestone:** SENTIENCE (early)

## Goal

Add a command that closes the reasoning graph loop: telemetry feeds back into proposed changes. The command reads a project's reasoning graph plus observed signals, finds mismatches, and produces ranked change requests that `/haytham:evolve` can execute.

This is the first SENTIENCE-aligned feature. v1 stays human-in-the-loop. Founder runs the command, reviews proposals, decides which to send to evolve. Autonomy graduates per change-type later.

## Why now

GiftKaro is live at giftkaro.pk, serving real customers, and iterated via `/haytham:evolve`. It is the only project with all three inputs the proposer needs: declared intent in openspec, observed reality from real traffic, and strategic context from prior research. SENTIENCE work is no longer a distraction from GENESIS, it is the next bet, and GiftKaro is the place to ground it.

## Progress (through 2026-05-18 — loop closed)

Use this section as the live state of the build. Update it as phases advance.

### Loop closure (2026-05-18)

The SENTIENCE loop has its first full real-world traversal:

- **Evolve commit `680a872`** landed on GiftKaro `design/gk-design-system` on 2026-05-17, merged to `main` overnight, deployed via Vercel.
- **GA4 confirms `itemCategory` populating.** Last-2-days query (2026-05-18 morning) returns non-zero rows for festive, birthday, apology. Yesterday the same query returned zero rows across all categories. The wire-format fix works.
- **Asymmetric distribution emerging.** 3 of 7 categories show non-zero itemsViewed in 2 days; 4 still at zero. Not yet a `dead_category` anti-signal (14-day window includes pre-fix days), but the next proposer run can reason about per-category conversion for the first time.
- **Plugin shipped at v0.3.21** with the new `/haytham:propose-next-steps` command. The command is now available to anyone using the haytham plugin from the marketplace.

This is the prerequisite for the SENTIENCE thesis test. Today's proposer re-run is the first run where output quality can be compared against "what the founder would have noticed manually." If the re-run produces a finding from per-category data that wasn't obvious from a 5-minute GA4 scan, the loop is adding value, not just running.

### Done

- **Phase 1: Telemetry contract for one GiftKaro capability.** Hand-written, then calibrated against live GA4 via the analytics MCP. Lives at `/Users/amehboob/Documents/GitHubPersonal/giftkaro.pk/openspec/specs/gift-catalog/telemetry.yml` (v2).
  - Findings from writing it: contract format needed `fired_today`, `planned`, `gap_note`, and `instrumentation_blocker` fields the original plan didn't anticipate. v2 adds a `baseline_snapshot` block so future revisions can compare.
  - Team review surfaced four calibration corrections: target was fantasy at 30% (real is <15%), category distribution unknown, occasion-led wedge confirmed, instrument missing events before proposer ships.
  - GA4 baseline (2026-05-17): 92 sessions / 30d, 8 `view_item` sessions, 30.9% home bounce, 7 categories all within 50/5 distribution bounds, `itemCategory` parameter is empty on `view_item` (spec-conformance bug).

- **Analytics MCP wired.** Installed `analytics-mcp` (PyPI `analytics-mcp` v0.5.0) at user scope via `uvx`. GCP project `giftkaro-analytics`, OAuth Desktop client, ADC at `~/.config/gcloud/application_default_credentials.json`. The MCP serves as the v0 adapter — Haytham declares the contract, the MCP fulfills the read. Adapter-as-contract stance held.

- **Phase 2 v0 command written.** `commands/propose-next-steps.md` in the haytham repo. Single-LLM-call orchestrator, no sub-agents per the CLAUDE.md pitfall. Five hard rules baked into the prompt: minimum-sample gate, competitor pairing, evidence trail, contract-can-be-wrong bias, past-proposal awareness. Plugin sanity tests pass (33/33 command-related).

### Done-but-suspect

- **First end-to-end run against GiftKaro.** Produced `.haytham/proposals/2026-05-17-proposals.md` with four proposals (one substantive: instrument `item_category` on `view_item` events; three filler). **The run was hand-weaved.** The same Claude instance that wrote `commands/propose-next-steps.md` then "executed" it inside the same conversation, with the contract content, team review findings, and analytics MCP query results already in context. So the run validated:
  - The command file parses
  - The MCP returns useful data
  - A proposals-file shape can be produced

  And did **not** validate:
  - Whether the prompt itself carries the reasoning
  - Whether a cold session would find the spec-conformance cross-reference (`item_category` declared in `analytics/spec.md` CAP-F-006 but empty in GA4) or whether that finding was carried by conversation memory
  - Whether the five hard rules actually fire absent priming

  The hand-weaved run is a smoke test of the loop running, not a test of proposer quality.

### Cold-proxy test result (2026-05-17) — PASS, with prompt improvements identified

Ran the cold-proxy test by spawning a `general-purpose` Agent with zero prior context. Briefed it as a smart colleague who walked in cold: read `commands/propose-next-steps.md`, follow it verbatim against the GiftKaro project, write the proposals file, report back. The hand-weaved file was moved to `.haytham/handweaved/2026-05-17-handweaved.md` so the cold agent ran against an empty proposals directory.

**What the cold agent independently produced:**

- Located and read all the right artifacts (contract, concept-anchor, capabilities, architecture-decisions, spec, competitor-research) from the command file's instructions alone.
- Issued 5 GA4 queries via the analytics MCP, all succeeded.
- **Found the spec-conformance cross-reference** — the central test. Independently identified that `openspec/specs/gift-catalog/telemetry.yml` declares `view_item` with `item_id` only while `openspec/context/capabilities.json` CAP-F-006 requires `item_category`, then verified via GA4 that `itemCategory` returns zero rows. Same finding the hand-weaved run produced, **without priming**.
- Produced 5 ranked proposals with evidence trails, confidence/severity scores, and copy-paste evolve invocations matching the command's specified shape.
- Self-flagged where it stretched Rule 2 (Proposal 5 on delivery confirmation pairs a competitor signal to add a missing `differentiates_from` edge — honest acknowledgement that this is the edge case).

**Findings the cold agent caught that the hand-weaved run missed:**

- GA4 is firing `form_start` and `click` events that no contract or capability spec declares. Cold agent proposed either adding them to the contract or marking them as `non_canonical_events`. Hand-weaved missed this entirely.
- Catalog-conditioned conversion is currently a single-query *approximation* (14.7% via 14 view_item / 95 catalog landings), not a true session-scoped measurement. Cold agent flagged the math limitation explicitly and proposed using `run_funnel_report` or a custom session-scoped dimension. Hand-weaved silently used a different denominator (8/73 = 11%) without flagging the precision gap.
- Per-category minimum_sample floor (`weekly_per_category_sessions: 5`) — more sophisticated than my single site-wide floor.
- Conversion is already above the contract target (14.7% vs 12% target) — proposed raising target to 18%. Hand-weaved didn't catch this because it used a more conservative denominator.

**Conclusions:**

- The prompt carries the reasoning. The cross-reference finding is reproducible from a cold start.
- The prompt is in some ways *better* than what the hand-weaved run produced — more findings, sharper math, more honest self-flagging.
- The cold-proxy test method works and should be the default validation step before declaring any new haytham command "done."

**Prompt improvements landed in v0.1 (2026-05-17):**

All five identified improvements applied to `commands/propose-next-steps.md`:

- Sharper `run_report` vs `run_funnel_report` guidance: any threshold definition with "sessions that", "of sessions", or any session-scoped condition between two events now explicitly requires `run_funnel_report`. Single-query ratio approximations are flagged as the wrong tool.
- `intent_gap` annotations now have an explicit home in the "Gaps and caveats" section of the output, alongside two new annotation types (`event_regression` for previously-firing events gone silent, `event_unknown` for events firing without contract coverage).
- New Step 2.3 mandates the contract-vs-spec cross-reference for every event in every contract, flagged as **"the highest-leverage finding type the proposer can produce — always do this cross-reference, never skip it."** The instinct that produced the hand-weaved run's best finding is now encoded.
- TodoWrite now gracefully degrades: command checks if the tool is available and proceeds without it if not, rather than failing or skipping silently.
- New Step 2.2 enumerates all firing events first (single `run_report` on `eventName`) and computes the set difference against contract-declared events. Unknown events become first-class proposal candidates. This is what surfaced `form_start` / `click` in the cold run.

Also: Rule 2 now allows a `revise-contract` proposal that adds a new `differentiates_from` edge to be grounded in competitor signal alone (with low/medium confidence required), so competitor patterns the contract doesn't yet model can be surfaced rather than dropped.

Plugin sanity tests pass (33/33 command-related). Version annotation added to the command file header for future cold-test cycles.

These improvements unblock phase 3 with no further prompt work expected. A second cold-proxy test against v0.1 is optional — the changes were derived from cold-agent feedback so they should be reproducible, but a rerun would confirm.

### After the cold-proxy test passes

- **Route Proposal #1 to `/haytham:evolve` on GiftKaro.** First real demonstration that the loop closes end-to-end: telemetry → proposer → evolve → ship → next proposer run sees the gap close.
- **Run #2 of the proposer one week from now, with `item_category` shipped.** The first run that has any chance of producing capability-level findings the founder couldn't get from a 5-minute scan of contract + GA4.
- **Retrospective calibration on past evolve changes.** Phase 3 in the original plan, now unblocked.

### Artifacts

- Plan: `docs/plans/2026-05-16-propose-next-steps.md` (this file)
- Command: `commands/propose-next-steps.md` (haytham repo)
- Contract: `openspec/specs/gift-catalog/telemetry.yml` (GiftKaro repo, v2)
- First (hand-weaved) proposals run: `.haytham/handweaved/2026-05-17-handweaved.md` (GiftKaro repo, quarantined to avoid contaminating cold tests)
- Cold-proxy proposals run (canonical v0 output): `.haytham/proposals/2026-05-17-proposals.md` (GiftKaro repo)
- MCP registration: user-scoped `analytics-mcp` in `~/.claude.json`

## What we're really adding

A new edge in the reasoning graph: `telemetry → next change`. Today the graph ends at code. SENTIENCE closes it.

```
concept anchor → capabilities → architecture → specs → code → telemetry
                                                                  │
                                                                  ▼
                                                          /propose-next-steps
                                                                  │
                                                                  ▼
                                                          change request
                                                                  │
                                                                  ▼
                                                          /haytham:evolve
```

## The hidden prerequisite: telemetry contract

The prerequisite is not "integrate with Google Analytics." That is data plumbing, and per principle #7 Haytham should not own it. The real prerequisite is a **telemetry contract** attached to every capability.

Every capability declares:

- **Events emitted.** What gets logged when this capability runs.
- **Success thresholds.** What "working" looks like (e.g., "70% of users who reach onboarding step 2 reach step 3").
- **Anti-signals.** What "broken" looks like (e.g., "p95 latency > 2s for 24h", "support tickets matching pattern X > 5/week").
- **Regression triggers.** What change warrants a proposal (e.g., "completion rate drops by 10pts week-over-week").
- **Minimum sample.** Below this volume, the proposer treats all signals as noise. Critical for early-stage projects with low traffic.

Without this, the proposer is running an LLM over raw metrics and guessing. With it, the proposer is doing a structured comparison against declared intent.

**Key insight: the contract is a hypothesis, not a constraint.** Whoever writes the first thresholds (human or agent) will get them wrong because nobody knows the right ones pre-launch. The proposer must be able to propose contract updates as a valid change type. That is how the loop stays honest. It can be wrong, and the loop corrects it.

### Shape of the contract

One file per capability, alongside the existing per-capability spec. If a capability lives at `openspec/specs/category-browse/spec.md`, the contract lives at `openspec/specs/category-browse/telemetry.yml`. Same lifecycle, same versioning, same review.

Worked example for the category-browse capability on GiftKaro:

```yaml
capability: category-browse
purpose: |
  Users land on the home page, pick a category tile, and reach a
  product list. This replaced the previous search-first home.

events:
  - id: category_tile_clicked
    dimensions: [category_id, position, device]
  - id: product_list_viewed
    dimensions: [category_id, product_count, device]
  - id: product_clicked_from_category
    dimensions: [category_id, product_id, position]

success_thresholds:
  - name: category_to_product_conversion
    definition: |
      Sessions firing category_tile_clicked that also fire
      product_clicked_from_category within the same session.
    target: ">= 35%"
    confidence: low
    rationale: |
      Old search-first IA was ~22% search-to-click. 35% is a guess
      that the category-first redesign meaningfully helps.

anti_signals:
  - name: empty_category_views
    definition: product_list_viewed fires with product_count == 0
    threshold: "> 5% of category_views per week"
  - name: category_bounce
    definition: |
      Sessions where category_tile_clicked fires but no
      product_clicked_from_category follows.
    threshold: "> 70% over a 7-day window"

regression_triggers:
  - category_to_product_conversion drops >= 10pts week-over-week
  - any anti_signal fires for two consecutive weeks
  - a single category accounts for > 50% of bounces

minimum_sample:
  weekly_sessions: 200
```

The `confidence: low` field on thresholds is load-bearing. It tells the proposer when a gap is more likely a bad threshold than a bad capability.

### Optional competitor edges (minimal version, v1)

Capabilities may declare which competitor positions they differentiate against:

```yaml
differentiates_from:
  - competitor: competitor_y
    dimension: same-day-delivery
```

This is the cheapest possible version of capability-to-competitor edges. One optional list per capability. The proposer reads the latest competitor snapshot and specifically checks whether the listed competitors closed the listed gap. Without this, competitor reasoning stays generic and noisy. With it, the proposer can produce sharp findings on the capabilities the founder marked as competitive wedges.

## The three legs of the proposer call

Single LLM call. No multi-agent. Per the pitfall in CLAUDE.md, splitting "analyze metrics" from "propose changes" from "rank by confidence" creates exactly the inconsistency-validator problem that killed the earlier pipeline. The proposer needs cross-cutting context.

Three input categories, kept distinct because they have different cadence and reliability:

1. **Declared intent** (the reasoning graph). Concept anchor, capability model, telemetry contracts, architecture decisions. Founder-owned, slow-changing.
2. **Observed reality** (read on-demand each run). Product metrics, operational metrics.
3. **Strategic context** (stored snapshots, refreshed on their own cadence). Latest competitor snapshot, change log from evolve.

A proposal is the LLM finding a mismatch between any two of these.

Examples:

- Declared intent says "retention is the success metric for capability X." Observed reality shows retention dropped 12pts. Strategic context says competitor Y launched a similar feature last month. Proposal: "Differentiate capability X on Z, or drop it. Evidence: retention drop, competitor parity."
- Declared intent says nothing about pricing pressure. Strategic context shows two competitors cut prices. Observed reality shows funnel drop-off at checkout. Proposal: "Add pricing as a tracked dimension; consider price test." This proposal updates the contract, not just the product.

## Adapters as contracts, not Haytham code

Per principle #7, Haytham does not own analytics integration. The proposer reads a normalized JSON file the project produces however it wants: a cron job hitting GA, a Vercel Analytics export, a manual paste, an MCP server, whatever. Haytham specifies the file format; the project owns the ingestion.

This stays true even when "real adapters" become tempting. A GA adapter built into Haytham becomes a maintenance burden the moment GiftKaro switches tools or the next project uses Mixpanel. The contract-as-format stance scales; the adapter-as-code stance does not.

The file lives at `.haytham/observed.json` in the project. Its shape is dictated by the union of telemetry contracts. The proposer fails fast and clearly if a contract references an event the file does not provide.

### The mapping problem

A telemetry contract says "event: `category_tile_clicked`." The project's analytics tool probably calls it something else. The mapping lives in the project at `.haytham/telemetry-mapping.yml`, written once when the project is first wired up:

```yaml
category_tile_clicked:
  source: ga4
  event_name: select_item
  filter: item_list_name == "home_categories"
```

This is what makes the "produce a normalized observed.json" step concrete. It is also where most of the founder's setup time will actually go. The contract is fast to write; the mapping is the real UX problem because founders will paste exports, miss dimensions, and get confused about which event corresponds to which capability.

v1 ships with a `stub` source type that means "I will paste numbers by hand each run." This is what unblocks the proposer before any real integration.

## Competitor handling

Competitors are a different kind of signal. Telemetry is high-frequency, structured, deterministic. Competitor intelligence is low-frequency, unstructured, and LLM-derived (so noisier). If we treat them the same, two things break: the proposer gets slow (web research on every run), and the proposer becomes non-deterministic on the same inputs.

Solution: a sibling command `/haytham:refresh-competitors` reuses the competitor-researcher agent from Phase 1 and writes a dated snapshot. The proposer reads the latest snapshot. If it is older than a founder-tunable threshold (default two weeks), the proposer warns and offers to refresh before running.

Competitor research stays an explicit, owned action. Same-input-same-output for the proposer.

## Discipline on competitor signal

The LLM will find something interesting in any competitor snapshot, because competitors always have features we do not. The proposer prompt must enforce: competitive findings only justify a proposal when paired with either (a) declared intent saying we care about that dimension (the `differentiates_from` field), or (b) telemetry showing a corresponding drop on our side. "Competitor has feature X" alone is not a proposal.

## State management

Three things to persist in the project's `.haytham/` directory:

1. **Proposal log.** Every run writes a dated proposal file. Future runs read recent proposals to avoid re-proposing things the founder explicitly rejected.
2. **Outcome tracking.** When a proposal becomes a change via evolve, link them. When the change ships, the next run checks whether the metric actually moved. This is the feedback signal for confidence calibration.
3. **Contract version history.** When the proposer suggests a contract update and the founder accepts, the old threshold is not deleted, it is superseded. Future proposals see "this threshold has been revised twice."

GiftKaro makes outcome tracking shippable in v1. There is already a history of `/haytham:evolve` runs against live traffic, so the first run of the proposer can backfill outcomes for the last several changes and produce its own initial confidence calibration. That turns the proposer's biggest weakness (uncalibrated scoring) into a real demo on day one.

## Output shape

A `/propose-next-steps` run produces a ranked list of change candidates. Ranking is `confidence × severity × recency` with ties broken by recency. The proposer prompt makes the formula explicit so the founder reading position 1 vs position 5 knows what the ordering means.

Each candidate carries:

- **Problem statement.** Capability X is underperforming on metric Y, anti-signal Z is firing, etc.
- **Proposed change.** Drop capability, redesign flow, add capability, update contract.
- **Confidence score.** Low / medium / high, with a one-line justification grounded in the calibration history.
- **Severity.** Impact on the affected capability's primary success metric.
- **Evidence trail.** Which graph nodes, which metric deltas, which competitor snapshot dates.
- **Change-request payload.** The structured input `/haytham:evolve` consumes directly.

The founder picks which to send to evolve. Auto-execute is explicitly out of scope for v1.

### Evolve interface

`/haytham:evolve` today takes a natural-language description as `$ARGUMENTS`. The structured payload above is fiction until evolve accepts it. Either: (a) the proposer renders the payload as a description string evolve can already consume, or (b) evolve gets extended to read a payload file when one is referenced. Decide before phase 2 ships. Option (a) is the obviously cheaper start.

## Sequencing

Built in order. Each phase is shippable on its own. Phases are deliberately ordered so the expensive upstream-agent changes happen last, with evidence rather than guesses behind them.

1. **Hand-write a telemetry contract for one GiftKaro capability.** One file. Pick the capability with the most traffic and the clearest success metric (category-browse is the obvious choice — recent evolve change, live data, known intent). About a day of work with the team. Validates that the format is expressive enough.
2. **Proposer v0 with stub adapters.** Manual paste for product/ops metrics, manual paste for competitor snapshot, the hand-written contract as declared intent. End-to-end LLM reasoning validated on GiftKaro. Cheapest way to learn whether the proposals are useful at all.
3. **Retrospective calibration on GiftKaro.** Run the proposer against the last 3-5 evolve changes that already shipped: what metric was each change supposed to move, did it actually move, how confident was the proposer? This is the first real calibration data and the first demo of the closed loop.
4. **`/haytham:refresh-competitors`.** Reuses existing competitor-researcher. Snapshot becomes a first-class artifact. Lets the proposer reason against current competitive context.
5. **Generalize the contract format into `mvp-scoper` and `spec-generator`.** Only after phase 3 produces a contract format we believe in. Until then, retrofitting the upstream agents is committing to a schema we will rewrite.
6. **Real adapters as project-side scripts.** Specify the `observed.json` format. Founders own ingestion in their own repos. No GA adapter inside Haytham.

Do not build phase N+1 before phase N ships.

## What this plan deliberately defers

- **Automated loop / scheduled runs.** v1 is on-demand only. Automation needs calibrated confidence, and we only get that after the retrospective in phase 3 has been validated over time.
- **Business metric adapter.** Out of v1 scope. Revisit when a real signal needs it.
- **Threshold-driven firing.** End state, wrong starting point. Needs anti-signals to be calibrated, which needs real data over time.
- **Auto-execute proposals.** Founder-in-the-loop only. Per-change-type autonomy graduation comes later.
- **Contracts for every capability up front.** One capability in phase 1. Others get contracts as they become interesting to the proposer.

## Risks and open questions

- **Contracts are hypotheses, but the team writing the first one will be confidently wrong.** The `confidence` field on thresholds is the mitigation. The proposer must give low-confidence thresholds far less weight when proposing capability changes, and instead lean toward proposing threshold revisions.
- **Proposer noise on small data.** The `minimum_sample` field is the mitigation. The proposer prompt must enforce this as a hard gate, not a soft hint. A funnel drop from 10 users to 8 must produce zero proposals.
- **Mapping ambiguity.** Already addressed via `telemetry-mapping.yml`, but expect the first time wiring up a real project to be slow. Budget time for it in phase 6, not as a footnote.
- **GiftKaro is a single test project.** v1 validates the loop on one product. Cross-project generalization is a real risk but not a v1 blocker; the proposer architecture has no project-specific code, so generalization is a question of contract quality, not engineering.

## Definition of done for v1

- A telemetry contract exists for at least one GiftKaro capability and the team agrees it reflects how they would judge whether that capability is working.
- `/propose-next-steps` exists, gated on the project having at least one telemetry contract.
- It runs end-to-end with stub adapters on GiftKaro.
- It produces at least one proposal that the founder routes to `/haytham:evolve`, evolve executes without manual reshaping, and the resulting change ships to giftkaro.pk.
- The retrospective calibration step has run at least once against past evolve changes, producing an initial confidence baseline.
- `/haytham:refresh-competitors` exists and writes a dated snapshot the proposer reads.

When all six are true, v1 is shippable and we have signal to design v2 (real project-side adapters, generalized contract schema in `mvp-scoper`/`spec-generator`, calibrated automation).
