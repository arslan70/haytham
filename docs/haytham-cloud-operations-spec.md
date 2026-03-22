# Haytham Cloud Operations: Implementation Spec

## Overview

Add cloud enrichment to Haytham's Phase 3 (Technical Design). A new `cloud-researcher` agent runs after the `architect` agent, querying live provider data (pricing, features, limits) to ground build-buy decisions in reality rather than training knowledge.

The agent is fully dynamic: it reads the architect's `build-buy.json`, identifies every BUY/HYBRID provider recommendation, and researches each one via web search. No static provider registry. Works for any provider the architect recommends, present or future.

### Scope Decision

This spec covers enrichment only. Provisioning and deployment (a `cloud-provisioner` agent, `/haytham:deploy` command, Phase 5) were considered and parked. Haytham is a control plane: it decides what needs to happen, it doesn't execute. Generating better architecture decisions with live data is control plane work. Calling MCP tools to create Supabase projects is execution. The user owns execution.

If users report wanting Haytham to provision infrastructure directly, revisit this decision.

---

## Design Principles (from CLAUDE.md)

These constrain every decision below:

- **Control Plane, Not Data Plane**: Haytham enriches architecture decisions with live data. It does not provision, deploy, or manage cloud resources.
- **Stay Lean**: One new agent, one modified command. No static registry to maintain.
- **Generic Prompts**: The cloud-researcher works for any provider the architect recommends. No provider-specific knowledge in the agent prompt or in reference files. The agent discovers everything at runtime via web search.
- **Trace Everything**: Every enriched provider traces to a `recommended_stack` entry in `build-buy.json`, which traces to capabilities.

---

## Component 1: Cloud Researcher Agent

**File**: `agents/cloud-researcher.md`

**Purpose**: During Phase 3, query live provider data to enrich build-buy decisions. Runs sequentially after the architect agent (needs `build-buy.json` as input to know which providers to research).

**Model**: sonnet (web search tasks, matches architect)

**Tools**: Read, Write, WebSearch, WebFetch

### Agent Design

```yaml
---
name: cloud-researcher
description: >
  Research current pricing, features, and limits for cloud/SaaS providers
  recommended in the build-buy analysis. Use during Phase 3 (HOW) after
  the architect agent has produced initial recommendations.
tools: Read, Write, WebSearch, WebFetch
model: sonnet
---
```

### Agent Instructions (body of the markdown file)

The cloud-researcher:

1. Reads `.haytham/session/phase-3-how/build-buy.json` (written by the architect agent)
2. Identifies every entry in `recommended_stack` with `recommendation: "BUY"` or `recommendation: "HYBRID"`
3. For each such entry:
   a. Extracts the provider name and category from `build-buy.json`
   b. Uses WebSearch to query `"{provider_name} pricing {current_year}"` and `"{provider_name} free tier limits {current_year}"`
   c. Uses WebFetch on the provider's pricing page if the search results aren't sufficient
   d. Extracts: current pricing tiers, free tier limits, rate limits, region availability, any recent changes
4. Writes findings to `.haytham/session/phase-3-how/cloud-enrichment.json`

### Why No Provider Registry

The architect's `build-buy.json` already contains everything the cloud-researcher needs: provider names, categories, and BUY/HYBRID/BUILD recommendations. A static registry would duplicate this information, add a maintenance surface, and create a false gate (providers not in the registry would need special handling). Web search is the agent's primary tool and can find any provider's pricing page in one query.

### Output Schema

```json
{
  "researched_at": "ISO timestamp",
  "providers_enriched": [
    {
      "provider_id": "supabase",
      "provider_name": "Supabase",
      "categories_served": ["database", "auth", "storage"],
      "pricing": {
        "free_tier": "Description of current free tier",
        "starter_tier": "First paid tier details",
        "relevant_limits": [
          "Database: 500MB on free, 8GB on Pro ($25/mo)",
          "Auth: 50K MAU on free, 100K on Pro",
          "Storage: 1GB on free, 100GB on Pro"
        ],
        "source": "URL where this was found",
        "confidence": "verified | estimated",
        "as_of": "Date of the pricing page"
      },
      "feature_check": {
        "features_confirmed": ["RLS", "Edge Functions", "Realtime"],
        "features_missing": [],
        "constraints": ["Edge Functions limited to 500K invocations/month on free"],
        "source": "URL"
      },
      "fit_assessment": "How well this provider fits the MVP requirements and appetite"
    }
  ],
  "cost_summary": {
    "free_tier_viable": true,
    "estimated_monthly_at_launch": "$0-$25",
    "scaling_threshold": "When you'd need to upgrade (e.g., >50K users, >500MB data)"
  },
  "warnings": [
    "Any pricing changes, deprecations, or gotchas found during research"
  ]
}
```

---

## Component 2: Modifications to Existing Files

### 2a. `commands/design.md` — Add Cloud Enrichment Step

Insert a new optional step between Step 1 (Architecture) and Step 2 (Review).

**Current flow**: Architect -> Review -> Gate
**New flow**: Architect -> Cloud Enrichment (optional) -> Review -> Gate

The new step:

```markdown
## Step 1b: Cloud Enrichment (Optional)

After the architect agent completes, read `.haytham/session/phase-3-how/build-buy.json`
and check if any `recommended_stack` entries have `recommendation: "BUY"` or
`recommendation: "HYBRID"`.

If yes, tell the user:

> **Step 1b/3: Cloud Enrichment**
> Checking current pricing and limits for the recommended services to make
> sure the cost estimates are grounded in reality.

Launch a **cloud-researcher** agent with this task:
> Read the build-buy analysis from `.haytham/session/phase-3-how/build-buy.json`.
> Research current pricing, limits, and feature availability for each BUY/HYBRID
> provider. Write findings to `.haytham/session/phase-3-how/cloud-enrichment.json`.

After the agent completes, read `cloud-enrichment.json` and append to the
architecture digest:

> **Cloud enrichment:**
> - [Provider]: [Free tier viable? Y/N], [Relevant limits], [Current pricing]
> - Estimated monthly cost at launch: $X (vs architect estimate: $Y)
> - Warnings: [Any gotchas found]

If there are no BUY or HYBRID recommendations, skip this step silently.
```

Update the roadmap message:

```markdown
> **Phase 3: Technical Design**
>
> This will run 3 steps:
> 1. Architecture — build/buy analysis and technology decisions (~2 min)
>    _+ optional: live pricing check for recommended services_
> 2. Review — you review the architecture
> 3. Gate 3 — you approve the design <- YOU DECIDE HERE
>
> Estimated total: ~3-4 minutes.
```

### 2b. `CLAUDE.md` — Update Plugin Structure

Add to the file map:

```
agents/
  cloud-researcher.md            # Live provider pricing/feature research
```

### 2c. `.claude-plugin/marketplace.json` — Update Metadata

Add keyword: `"cloud"`

### 2d. `tests/test_plugin_sanity.py` — Add Tests

See Testing Strategy section below.

---

## Data Flow Diagram

```
Phase 3 (existing)                    Phase 3 (new)
┌─────────────┐                      ┌──────────────────┐
│  architect   │──build-buy.json────>│ cloud-researcher  │
│   agent      │                      │    agent          │
└──────┬───────┘                      └────────┬──────────┘
       │                                       │
       │ architecture-decisions.json            │ cloud-enrichment.json
       │ research-directives.json               │
       v                                       v
┌──────────────────────────────────────────────────────┐
│                   Gate 3 Review                       │
│  (user sees architecture + enrichment data together)  │
└──────────────────────────────────────────────────────┘
```

---

## File Inventory

| File | Type | Status | Description |
|------|------|--------|-------------|
| `agents/cloud-researcher.md` | Agent | NEW | Live pricing/feature research |
| `commands/design.md` | Command | MODIFY | Add Step 1b (cloud enrichment) |
| `CLAUDE.md` | Docs | MODIFY | Update file map |
| `.claude-plugin/marketplace.json` | Manifest | MODIFY | Add keyword |
| `tests/test_plugin_sanity.py` | Test | MODIFY | Add cloud-researcher checks |

---

## Implementation Order

1. **`agents/cloud-researcher.md`** — Can test independently against any build-buy.json.
2. **`commands/design.md` modification** — Wire cloud-researcher into Phase 3.
3. **Remaining modifications** — CLAUDE.md, marketplace, tests.

---

## Testing Strategy

### Sanity Tests (extend `test_plugin_sanity.py`)

- `cloud-researcher.md` has valid frontmatter (name, description, tools, model)
- `design.md` references `cloud-researcher` agent (cross-reference check)

### Functional Tests

- Run `/haytham:design` on a test idea and verify `cloud-enrichment.json` is produced with real pricing data
- Run `/haytham:design` on an idea where the architect recommends only BUILD (no BUY/HYBRID) and verify cloud enrichment is skipped gracefully

---

## Errata: Consistency Fixes (from verification pass)

### Fix 1: design.md cloud-researcher insertion point

The cloud-researcher step (Step 1b) inserts between the existing Step 1 (Architecture) and Step 2 (Review). The existing design.md has 3 steps. With the insertion, numbering becomes:

- Step 1: Architecture (existing, unchanged)
- Step 1b: Cloud Enrichment (new, optional)
- Step 2: Review (existing, now includes enrichment data in the digest)
- Step 3: Gate 3 (existing, unchanged)

The step counter shown to the user stays at 3 steps (1b is marked optional and doesn't get its own number in the roadmap).

### Fix 2: Trigger condition

The previous spec gated cloud enrichment on whether `references/providers.json` exists. With no registry, the trigger is simpler: check `build-buy.json` for BUY/HYBRID recommendations. If there are any, run the cloud-researcher. If everything is BUILD, skip it.

---

## Parked: Provisioning & Deployment

The following components were designed but deliberately parked. They cross from control plane (deciding what to provision) into data plane (executing provisioning). Haytham stays in the control plane.

**Parked components:**
- `agents/cloud-provisioner.md` — agent that calls MCP tools to create cloud resources
- `commands/deploy.md` — Phase 5 command orchestrating provisioning
- `references/providers.json` — static provider registry (replaced by fully dynamic web search)
- Phase 5 directory, state tracking, and prerequisite hooks
- Modifications to `haytham.md` for Phase 5 mention

**Revisit when:** Users report wanting Haytham to provision infrastructure directly, rather than telling them what to provision.

**If revisited:** The deployment plan schema (mapping build-buy recommendations to provider-specific provisioning steps with dependency ordering) is the right control-plane artifact. The open question is whether Haytham should execute that plan or hand it to the user. The current answer is: hand it to the user.
