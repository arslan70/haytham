# Plan: Add GTM Strategy Command

**Status: DEFERRED.** Does not advance Genesis (idea to working MVP). GTM helps founders sell the MVP, not build it. Revisit after Phase 5 (Execute) and Phase 6 (Verify) are delivered, when the gap between "working MVP" and "what do I do with it" becomes the next real bottleneck.

## Context

Dogfooding revealed that the validation report's "next steps" included go-to-market activities (launch posts, community building, pricing, distribution channels) but Haytham didn't generate a structured strategy for them. The founder was left with action items they had to figure out themselves.

Phase 1 already produces everything a GTM strategy needs: target segments (with "where to find them"), competitor landscape (with pricing and traction data), market sizing, user sentiment quotes, and strategic signals (business model, success metric, competitive stance). A new agent can synthesize all of this into a ready-to-execute GTM plan.

## Design Decisions

- **Standalone command, not a new phase.** `/haytham:gtm` runs independently after Phase 1. Phase 5 is reserved for implementation (VISION.md). Adding GTM to Phase 1 would bloat a 6-step, ~7 min workflow. GTM belongs after a GO decision, not before it. Users opt in when they need it.
- **No web search.** Phase 1's market-researcher already ran 8-10 searches for competitors, traction, pricing, and sentiment. Re-searching is redundant and slow. The GTM agent synthesizes existing research.
- **Model: sonnet.** Structured synthesis from well-defined inputs, not complex cross-referencing. Report-synthesizer uses opus because it makes a nuanced GO/PIVOT/NO-GO judgment. GTM is more prescriptive: given these inputs, produce a strategy. Sonnet handles this well and keeps costs down.
- **Adapts by strategic signals, not separate templates.** Per CLAUDE.md's meta-system design: "Generic prompts that work for ANY idea." The agent contains conditional rules (if `business_model` is X, then...) that adapt output. Same pattern as report-synthesizer and market-researcher.
- **Output directory: `gtm/`, not `phase-1-why/`.** GTM is a standalone deliverable, not a Phase 1 artifact. Placing it in `phase-1-why/` would confuse the phase-to-directory mapping.
- **No gate decision.** GTM is a terminal deliverable. No downstream phase depends on it. A gate would be ceremony without purpose.

## Agent: `gtm-strategist`

### Inputs

| File | What it provides |
|---|---|
| `concept-anchor.json` | archetype, strategic_signals, founder_profile, identity |
| `idea-analysis.md` | segments ("where to find them"), UVP, problems, triggers |
| `market-research.md` | competitor traction/pricing, user sentiment, gaps, JTBD |
| `validation-report.md` | financial feasibility, revenue models, next steps |
| `validation-report.json` | recommendation, composite_score, risk_level |
| `founder-corrections.json` | founder's corrections (if exists) |
| `project.yaml` | original idea |

### Outputs

Two files in `.haytham/session/gtm/`:

**`gtm-strategy.md`** (full strategy document, 7 sections):

1. **Positioning** - Positioning statement, differentiation from competitors, core message. Adapts by `competitive_stance`: complementary positions as ecosystem enhancer, direct_competitor targets specific weaknesses, greenfield frames the unmet need.

2. **Target Audience & Channels** - Distribution channels ranked by segment fit. Uses "Where to Find Them" from idea-analysis.md. Adapts by `archetype`: developer_tool targets GitHub/HN/dev communities, consumer_app targets Product Hunt/social, b2b_saas targets LinkedIn/content marketing, marketplace focuses on supply-side first. Also adapts by `distribution`: plugin_or_extension targets the host platform's marketplace.

3. **Launch Sequence** - Phased timeline (Week 1-2, Week 3-4, Month 2-3). Pre-launch, launch, post-launch. Each action names the specific platform or tactic.

4. **Content & Messaging Strategy** - What to create, where to publish. Uses competitor gaps and user sentiment "wish" quotes as content angles. Adapts by `business_model`: open-source focuses on docs/tutorials/contribution guides, SaaS focuses on case studies/comparison posts.

5. **Community Building Plan** - How to build initial community. Adapts by `success_metric`: community_adoption focuses on Discord/forums/contributor onboarding, revenue focuses on customer advisory/beta program, usage focuses on waitlist/early access.

6. **Monetization Roadmap** - Revenue timeline and pricing approach. Uses financial feasibility data and competitor pricing benchmarks. Adapts by `business_model`: open-source suggests open core/support tiers, SaaS suggests freemium/trial, marketplace suggests take rates. Skipped entirely if `business_model: open-source` AND `success_metric: community_adoption` (monetization is premature, say so explicitly).

7. **Success Metrics & Milestones** - 30/60/90-day targets. Leading vs lagging indicators. Failure signals. Tied to `success_metric` from strategic_signals.

**`gtm-strategy.json`** (structured summary):

```json
{
  "positioning_statement": "One-line positioning",
  "primary_channel": "The single most important distribution channel",
  "channels": [
    {
      "name": "Channel name",
      "rationale": "Why this channel fits this segment",
      "priority": "primary | secondary | tertiary",
      "estimated_effort": "low | medium | high"
    }
  ],
  "launch_phases": [
    {
      "phase": "pre-launch | launch | post-launch",
      "timeframe": "Week 1-2",
      "actions": ["Specific action 1", "Specific action 2"]
    }
  ],
  "success_metrics": [
    {
      "metric": "Metric name",
      "target_30d": "30-day target",
      "target_90d": "90-day target",
      "measurement": "How to measure"
    }
  ],
  "monetization_approach": "Brief summary or 'deferred'",
  "biggest_gtm_risk": "The single biggest risk to the GTM strategy"
}
```

## Command: `/haytham:gtm`

3 steps:

1. **Generate** - Verify Phase 1 gate decision exists. Warn if recommendation was NO-GO. Create `gtm/` directory. Launch gtm-strategist agent. (~2 min)

2. **Review** - Present digest (positioning, primary channel, launch phases, key metrics, monetization). Output full `gtm-strategy.md` inline. Ask for review with numbered options:
   > 1. Looks good
   > 2. I have changes (say what to change)

3. **Done** - Strategy saved. Point to the output files.

## Integration Changes

| File | Change |
|---|---|
| File | Change |
|---|---|
| `agents/gtm-strategist.md` | Create (agent prompt) |
| `commands/gtm.md` | Create (command orchestration). `allowed-tools: Read, Write, Edit, Bash, Glob, Agent` (no WebSearch/WebFetch, agent synthesizes existing research) |
| `scripts/check_phase_prereqs.sh` | Add `gtm-strategist` to a new block requiring `.haytham/session/phase-1-why/gate-decision.json` (same pattern as Phase 2 agents, own block since it's not a phase agent) |
| `scripts/validate_schema.py` | Add `"gtm-strategy.json": ["positioning_statement", "primary_channel", "channels", "launch_phases", "success_metrics"]` to SCHEMAS |
| `tests/fixtures/valid_gtm_strategy.json` | Create test fixture |
| `tests/fixtures/invalid_gtm_strategy.json` | Create test fixture |
| `tests/test_plugin_sanity.py` | Add GTM schema validation tests |
| `commands/haytham.md` | Mention `/haytham:gtm` availability after Phase 1 gate |
| `CLAUDE.md` | Add `gtm-strategist.md` to agents list and `gtm.md` to commands list in Plugin Structure section |

## Sequencing

1. `agents/gtm-strategist.md` (bulk of the work)
2. `commands/gtm.md` (orchestration)
3. Hook + schema + test changes (small surgical edits)
4. Mention in `commands/haytham.md` (one line)
5. Run sanity tests
