# ADR-019: System Trait Detection

## Status
**Proposed** — 2026-01-31

## Context

### The Problem

Story generation prompts assume web application patterns: pages, responsive design, URL navigation, browser-based auth flows. This is baked into the story skeleton and detail prompts, particularly Layer 4 (UI).

When a user inputs a non-web idea (CLI tool, API service, data pipeline), the system produces stories that are ~60% appropriate and ~40% web-biased noise. Examples of noise:

- "As a user, I can navigate to the dashboard page" — for a CLI tool
- "Implement responsive layout for mobile" — for a headless API
- "Add login page with OAuth redirect" — for a single-user local tool

The build/buy agent already detects deployment context well (explicit section in its prompt), but this information doesn't propagate to story generation.

### Why Traits

What story generation needs to know is not *what the system is called* but *what traits it has*: Does it have a UI? What kind? Does it need auth? How is it deployed?

Traits compose. A system with `interface: [terminal]` and `auth: none` and `deployment: [local_install]` produces the right story layers regardless of whether we call it a "CLI tool" or a "developer utility" or a "local automation script." This avoids maintaining a fixed taxonomy of system categories that grows with every new type of software and breaks down for hybrid systems.

Multi-component systems are common — a mobile app typically has a backend API, many SaaS products have a web app plus a marketing site. Traits that support multi-select for `interface` and `deployment` handle these naturally through union of story layers rather than forcing a single classification.

---

## Decision: Trait-Based System Detection

Introduce a dedicated **system_traits** stage and agent after capability_model. The agent proposes traits based on all upstream context. The user confirms or refines traits at a decision gate before the HOW phase begins.

### Where It Fits in the Workflow

```
PHASE 2: WHAT
  mvp_scope → capability_model → system_traits (NEW)
                                       │
                           ┌─────────────────────────┐
                           │   DECISION GATE: USER    │
                           │   confirms/refines traits │
                           └─────────────────────────┘
                                       │
PHASE 3: HOW                           ▼
  build_buy_analysis → architecture_decisions

PHASE 4: STORIES
  story_generation → story_validation → dependency_ordering
```

### Why a Dedicated Stage

1. **Traits shape all downstream output.** They determine which story layers are generated, which build/buy categories apply, and which architecture patterns are relevant. This warrants explicit human confirmation, not a subsection buried in another agent's output.
2. **Classification and scoping are different tasks.** MVP scope decides *what* to build. System traits classify *what kind of system* it is. Mixing them risks the classification being rubber-stamped during a scoping review.
3. **Placement after capability_model gives the richest context.** The capability model output reveals what the system actually does — if capabilities include "push notification delivery" and "offline data sync," that's strong signal for `mobile_native`. The trait agent reads idea analysis, MVP scope, and capability model output to make an informed proposal.
4. **The agent is lightweight.** No web search, no complex reasoning — just classification with justification. One of the cheapest Bedrock calls in the pipeline.

### Trait Schema

`interface` and `deployment` are multi-select (comma-separated list). All other traits are single-select.

```
SYSTEM TRAITS:
  interface:   [browser | terminal | mobile_native | desktop_gui | api_only | none]  (multi-select)
  auth:        multi_user | single_user | none
  deployment:  [cloud_hosted | app_store | package_registry | local_install | embedded]  (multi-select)
  data_layer:  remote_db | local_storage | file_system | none
  realtime:    true | false
```

Each trait is independently assigned. No trait implies another — but some combinations are unusual and warrant flagging (see [Cross-Trait Validation](#cross-trait-validation)).

### Trait Definitions

| Trait | Values | Multi-select | What It Controls |
|---|---|---|---|
| `interface` | `browser`, `terminal`, `mobile_native`, `desktop_gui`, `api_only`, `none` | Yes | Which interface story layers are generated (unioned) |
| `auth` | `multi_user`, `single_user`, `none` | No | Whether auth/identity stories are generated |
| `deployment` | `cloud_hosted`, `app_store`, `package_registry`, `local_install`, `embedded` | Yes | Which infrastructure and deployment stories are generated (unioned) |
| `data_layer` | `remote_db`, `local_storage`, `file_system`, `none` | No | Persistence and data access stories |
| `realtime` | `true`, `false` | No | Whether real-time communication stories are generated |

### Cross-Trait Validation

While traits are independently assigned, certain combinations are unusual enough to warrant a warning. The orchestrator (Python code, not the agent prompt) checks the finalized trait set against these rules and surfaces warnings at the decision gate:

| Rule | Condition | Warning |
|---|---|---|
| Headless auth | `interface: [none]` + `auth: multi_user` | "No user-facing interface but multi-user auth selected. Confirm this is intended (e.g., API-key auth for a bot or background service)." |
| App store without native UI | `deployment` includes `app_store` + `interface` excludes `mobile_native` and `desktop_gui` | "App store deployment selected but no native interface. Did you mean `package_registry`?" |
| Realtime without persistence | `realtime: true` + `data_layer: none` | "Real-time enabled but no data layer. Confirm what is being synced (e.g., ephemeral messages)." |
| Local install with remote DB | `deployment: [local_install]` + `data_layer: remote_db` | "Local install with remote database requires network connectivity. Consider whether `local_storage` is more appropriate." |

These are **warnings, not errors**. Every combination is technically valid — the warnings exist to catch likely misclassifications before they propagate downstream. The user can dismiss any warning at the decision gate.

New validation rules can be added to this table without changing the trait schema or agent prompt — they are pure orchestrator logic.

### Fallback

If the LLM cannot determine a trait, it defaults to the most common web assumption:
- `interface: [browser]`, `auth: multi_user`, `deployment: [cloud_hosted]`, `data_layer: remote_db`, `realtime: false`

This preserves current behavior for ambiguous inputs — the system degrades to today's web-biased output rather than producing something broken.

### Examples

| Idea | interface | auth | deployment | data_layer | realtime |
|---|---|---|---|---|---|
| Gym leaderboard app | [browser] | multi_user | [cloud_hosted] | remote_db | true |
| Markdown-to-PDF CLI | [terminal] | none | [package_registry] | file_system | false |
| Weather data API | [api_only] | multi_user | [cloud_hosted] | remote_db | false |
| Tutoring marketplace | [browser] | multi_user | [cloud_hosted] | remote_db | true |
| Mobile fitness tracker | [mobile_native, api_only] | multi_user | [app_store, cloud_hosted] | remote_db | true |
| Slack standup bot | [none] | multi_user | [cloud_hosted] | remote_db | false |
| Desktop note-taking app | [desktop_gui] | single_user | [local_install] | local_storage | false |
| SaaS with marketing site | [browser, api_only] | multi_user | [cloud_hosted] | remote_db | false |

---

## The System Traits Agent

### Input

The agent receives prose context from three upstream stages (assembled by the orchestrator as today):
- **Idea analysis** — the original idea and initial assessment
- **MVP scope** — what's in and out of scope, target users, appetite
- **Capability model** — functional and non-functional capabilities (`CAP-F-*`, `CAP-NF-*`)

### Prompt Structure

The agent's system prompt instructs it to:

1. Read the upstream context
2. Propose a value for each trait
3. Justify each choice in one sentence, referencing specific capabilities or scope decisions
4. Flag any trait where the classification is ambiguous

### Output Format

```
## SYSTEM TRAITS

- **interface:** [mobile_native, api_only]
  Mobile app with native UI for end users. Backend API serves the mobile client.

- **auth:** multi_user
  Multiple users with individual accounts per capability model (CAP-F-001: Identity Management).

- **deployment:** [app_store, cloud_hosted]
  Mobile app distributed via app stores. API and database hosted in cloud.

- **data_layer:** remote_db
  User data and leaderboards stored in remote database (CAP-NF-001: Data Persistence).

- **realtime:** true
  Leaderboard updates require real-time sync (CAP-F-003: Live Leaderboard).
```

### Human Review (Conditional Gate)

The decision gate is **conditional** — it is shown only when at least one of the following is true:

1. **Non-default traits detected.** Any trait differs from the web defaults (`interface: [browser]`, `auth: multi_user`, `deployment: [cloud_hosted]`, `data_layer: remote_db`, `realtime: false`).
2. **Ambiguity flagged.** The agent flagged one or more traits as ambiguous.
3. **Cross-trait warning triggered.** The orchestrator's validation rules produced a warning.

When all traits match web defaults and no ambiguity or warnings exist, the gate is **skipped silently** — traits are stored in Burr state and the workflow proceeds. This avoids adding a meaningless confirmation click for the majority case (web applications).

When the gate is shown, the user sees the proposed traits with justifications and any cross-trait warnings, and can:
- **Confirm** — traits are stored in Burr state and propagated downstream
- **Override** — change any trait value (e.g., add `browser` to interface if they also want a web dashboard)

This is the only point where traits are set. Downstream agents and prompts consume them as-is.

---

## How Traits Control Story Layers

### Resolution: Orchestrator, Not Prompts

Trait-to-layer resolution is performed by the **orchestrator** (Python code in `stage_executor.py`), not by LLM prompts. The orchestrator:

1. Reads the finalized `system_traits` dict from Burr state
2. Maps each trait value to its corresponding story layer descriptors using the table below
3. Unions the layers for multi-select traits
4. Injects **only the resolved layer descriptions** into the story skeleton prompt

The story skeleton prompt never sees raw trait values. It receives a pre-computed list like "Generate stories for these layers: Command Interface, Data Access, Infrastructure." This keeps conditional logic in deterministic Python code where it can be tested, rather than in LLM prompts where branching is unreliable.

### Trait-to-Layer Mapping

For multi-select traits, story layers are **unioned** — each selected value contributes its layers, and the combined set is generated.

| Trait Value | Story Layer Effect |
|---|---|
| `interface: terminal` | Add "Command Interface" layer (argument parsing, output formatting, help text) |
| `interface: browser` | Add UI layer (pages, responsive design, navigation) |
| `interface: mobile_native` | Add mobile UI layer (native components, gestures, platform conventions) |
| `interface: api_only` | Add "API Contract" layer (endpoint design, request/response schemas, versioning) |
| `interface: none` | No interface layer (bot, background worker) |
| `auth: none` | Skip auth/identity layer |
| `auth: single_user` | Skip multi-user auth. Add local config/preferences if needed |
| `deployment: cloud_hosted` | Add cloud infrastructure stories |
| `deployment: app_store` | Add app store submission and distribution stories |
| `deployment: package_registry` | Add packaging and distribution stories |
| `deployment: local_install` | Add installer/update mechanism stories |
| `realtime: false` | Skip WebSocket/SSE/polling stories |

**Example:** A mobile fitness tracker with `interface: [mobile_native, api_only]` and `deployment: [app_store, cloud_hosted]` generates mobile UI layer + API contract layer + app store stories + cloud infra stories. No browser UI stories are generated.

---

## Implementation

### New Files

| File | Purpose |
|---|---|
| `haytham/agents/worker_system_traits/` | New agent directory |
| `worker_system_traits_prompt.txt` | Agent system prompt (classification + justification instructions) |

### Changes to Existing Files

| File | Change |
|---|---|
| `agent_factory.py` | Add `create_system_traits_agent()` factory function and register in `AGENT_FACTORIES` |
| `stage_registry.py` | Add `system_traits` stage metadata (slug: `system-traits`, phase: WHAT, position: after capability_model) |
| `stage_executor.py` | Add `system_traits` config in `STAGE_CONFIGS`. Parse trait values from agent output, store as `system_traits` dict in Burr state. Add trait-to-layer resolution logic and cross-trait validation rules |
| `burr_workflow.py` | Add `system_traits` action and transition: `capability_model → system_traits → build_buy_analysis`. Add conditional gate logic (show gate only when traits are non-default, ambiguous, or trigger warnings) |
| `burr_actions.py` | Add `system_traits` action implementation |
| `story_skeleton_prompt.txt` | Replace hardcoded web layers with a `{ACTIVE_LAYERS}` placeholder. The orchestrator injects resolved layer descriptions before the prompt is sent to the LLM |

### Interface-Specific Story Detail Templates

Renaming `detail_ui_prompt.txt` to `detail_interface_prompt.txt` is the most significant prompt work in this ADR. Each interface type requires a dedicated template section that produces stories of equivalent quality to the existing browser UI prompt. This is non-trivial: the existing browser prompt has been refined through iteration, and each new interface type needs comparable depth.

| Interface Type | Template | Key Story Patterns |
|---|---|---|
| `browser` | Existing `detail_ui_prompt.txt` content (no change) | Pages, responsive layout, navigation, form handling |
| `terminal` | New section | Argument parsing (positional + flags), help/usage text, output formatting (table, JSON, plain), exit codes, stdin/stdout piping, interactive prompts |
| `api_only` | New section | Endpoint design (REST/GraphQL), request/response schemas, error response format, versioning strategy, rate limiting, API documentation |
| `mobile_native` | New section | Native component selection, gesture handling, platform conventions (iOS/Android), offline-first patterns, push notification handling |
| `desktop_gui` | New section | Window management, menu structure, keyboard shortcuts, system tray integration, file dialogs |
| `none` | Skip — no interface stories generated | N/A |

The orchestrator selects which template section(s) to inject based on the resolved `interface` trait values. For multi-select (e.g., `[mobile_native, api_only]`), both sections are injected.

**Note:** Writing the `terminal`, `api_only`, `mobile_native`, and `desktop_gui` template sections is implementation work that should be validated individually against test ideas before being considered complete.

### Implementation Priority

1. **Create system_traits agent and prompt** — new agent directory, prompt file, factory function
2. **Register stage and wire into workflow** — stage_registry, burr_actions, burr_workflow transitions
3. **Trait-to-layer resolution in orchestrator** — Python logic in stage_executor that maps traits to layer lists, including cross-trait validation warnings
4. **Refactor story skeleton prompt** — replace hardcoded layers with `{ACTIVE_LAYERS}` placeholder, wire orchestrator to inject resolved layers
5. **Write interface-specific detail templates** — one template per interface type (browser is existing, terminal/api_only/mobile_native/desktop_gui are new). Validate each independently
6. **Conditional decision gate** — Streamlit view that shows traits + justifications + cross-trait warnings, skipped when all traits are web defaults
7. **Add Streamlit view** — display proposed traits with justifications at the decision gate

---

## What We Explicitly Don't Do

| Rejected Approach | Why |
|---|---|
| Detect traits in MVP scope prompt | Mixes classification with scoping. Traits deserve explicit human confirmation, not a buried subsection |
| Detect traits from idea text alone | Too early — no capability context. After capability_model, the agent has the richest signal |
| Traits as agent input | Agents work best with prose context; traits control the orchestrator's prompt selection, not the agent's reasoning |
| Per-trait confidence scores | Adds complexity without a consumer. The human reviews and overrides at the gate |
| Single-select for all traits | Multi-component systems (mobile app + API, SaaS + marketing site) need multi-select on `interface` and `deployment` |
| Always-visible decision gate | For the majority case (web apps), traits match defaults and confirmation is a meaningless click. Gate is conditional — shown only for non-default, ambiguous, or warned trait sets |
| Trait branching in LLM prompts | LLMs are unreliable at conditional branching. The orchestrator resolves traits to layers in deterministic Python code and injects only the relevant layer descriptions into prompts |

---

## Validation

Validation covers two dimensions: **trait detection accuracy** and **downstream story quality**.

### Dimension 1: Trait Detection

Test that the agent assigns the expected trait values for each idea in the standard test matrix.

| Test Idea | Expected Traits | Pass Criteria |
|---|---|---|
| Gym leaderboard | [browser], multi_user, [cloud_hosted], remote_db, true | All traits match expected values |
| Markdown-to-PDF CLI | [terminal], none, [package_registry], file_system, false | All traits match expected values |
| Weather API service | [api_only], multi_user, [cloud_hosted], remote_db, false | All traits match expected values |
| Tutoring marketplace | [browser], multi_user, [cloud_hosted], remote_db, true | All traits match expected values |
| Mobile fitness tracker | [mobile_native, api_only], multi_user, [app_store, cloud_hosted], remote_db, true | All traits match expected values |

### Dimension 2: Story Quality Impact

For each non-web test idea, compare stories generated **with** trait detection against stories generated **without** (i.e., current web-default behavior). Measure:

| Metric | How to Measure | Pass Criteria |
|---|---|---|
| **Noise reduction** | Count stories referencing patterns from unselected interface types (e.g., "page," "responsive," "navigation" in CLI stories) | Zero noise stories for non-web ideas |
| **Layer coverage** | Verify that expected layers are present (e.g., "Command Interface" for CLI, "API Contract" for API service) | All expected layers have at least one story |
| **Regression** | For web-default ideas (gym leaderboard, marketplace), diff stories before and after. No meaningful quality loss | Story count and layer coverage within 10% of baseline |
| **Template quality** | For each new interface template (terminal, api_only, mobile_native, desktop_gui), review generated stories for domain-appropriate patterns | Stories use correct terminology and patterns for their interface type (e.g., CLI stories reference flags/exit codes, not buttons/modals) |

### Cross-Trait Validation Tests

| Trait Combination | Expected Behavior |
|---|---|
| `interface: [none]` + `auth: multi_user` | Warning surfaced at decision gate |
| `deployment: [app_store]` + `interface: [terminal]` | Warning surfaced at decision gate |
| `realtime: true` + `data_layer: none` | Warning surfaced at decision gate |
| All web defaults | Decision gate skipped silently |
| One non-default trait, no ambiguity | Decision gate shown |

### Conditional Gate Tests

| Scenario | Expected Gate Behavior |
|---|---|
| All traits match web defaults, no ambiguity flags | Gate skipped |
| `interface: [terminal]` (non-default) | Gate shown |
| All defaults but agent flags `realtime` as ambiguous | Gate shown |
| All defaults but cross-trait warning triggered | Gate shown |

---

## Schema Extensibility

The initial schema covers the traits needed to eliminate web-biased story noise. Future system types may reveal gaps — for example, batch processing pipelines, platform extensions (Slack/Shopify apps), or multi-tenant B2B products.

### Adding a New Trait

1. Add the trait to the schema table in this ADR (or a follow-up ADR if the change is significant)
2. Add the trait to the agent prompt (one line in the classification instructions)
3. Add trait-to-layer mapping entries in the orchestrator's resolution logic
4. Write story layer templates for any new layer the trait introduces
5. Update the fallback defaults
6. Add the trait to the test matrix

### Adding a New Value to an Existing Trait

1. Add the value to the schema table
2. Add the trait-to-layer mapping entry in the orchestrator
3. Write the story layer template for the new value
4. Add cross-trait validation rules if the new value creates unusual combinations
5. Add a test idea that exercises the new value

### What Does NOT Change When Extending

- The agent prompt structure (always: read context → propose traits → justify → flag ambiguity)
- The decision gate logic (always: show when non-default/ambiguous/warned)
- The story skeleton prompt (always: receives `{ACTIVE_LAYERS}`, never sees raw traits)
- Downstream agents (they never see traits directly)

The cost of adding a trait or value is localized to the orchestrator's resolution logic and the story detail templates. No structural changes to the workflow.

---

## Consequences

### Positive

- Non-web ideas produce appropriate stories without web-biased noise
- Multi-component systems (mobile + API, web + marketing) are handled naturally via multi-select
- New system types (bots, pipelines, extensions) work without taxonomy changes — just new trait values if needed
- Human explicitly confirms system classification before downstream generation begins
- Graceful degradation: unknown inputs fall back to web defaults (current behavior)

### Negative

- Adds one stage to the pipeline (lightweight — classification only)
- Adds a conditional decision gate (shown only for non-default/ambiguous/warned trait sets — no friction for the common web case)
- Trait-to-layer resolution logic in the orchestrator adds a code path that needs tests
- Writing interface-specific detail templates (terminal, api_only, mobile_native, desktop_gui) is significant prompt engineering work — each must match the quality of the existing browser template

### Risks

- LLM may assign traits inconsistently across runs — mitigate by requiring justification (forces reasoning) and by human review at the gate
- Some ideas genuinely have ambiguous traits (is a Slack bot `interface: [none]` or `interface: [api_only]`?) — mitigate with explicit fallback defaults, ambiguity flagging, and human override at gate
- Multi-select union could produce large story sets for complex systems — mitigate by trusting MVP scope to have already constrained what's in scope; traits only control *how* in-scope items are expressed, not *what* is in scope
- Cross-trait validation rules may produce false-positive warnings for unusual but valid combinations — mitigate by making all warnings dismissible and keeping the rule set conservative
