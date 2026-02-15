# ADR-021: Design & UX Workflow Stage via Google Stitch MCP

## Status
**Proposed** — 2026-01-31

**Milestone**: Genesis

**Prerequisite**: Spike must pass before implementation begins (see [Spike: Prerequisite Gate](#spike-prerequisite-gate))

**Supersedes**: [ADR-015](./ADR-015-google-stitch-mcp-integration.md) (UI-Triggered Enhancement)

## Context

### Why Genesis Is Incomplete Without This

The Constitution declares Genesis complete when Haytham can transform "a startup idea" into "a concrete, working, validated MVP." The Gym Leaderboard validated the *loop* — but the loop has a gap. Genesis produces stories that, for UI-facing MVPs, lack the design context needed to implement correctly on the first pass. This isn't polish — it's a missing input to story generation that causes rework in the implementation stage.

The argument for Genesis (not Evolution) rests on three points:

1. **Stories without design context produce incomplete implementation specs.** The story generator currently outputs acceptance criteria like "Dashboard loads within 2 seconds" and "Shows 5 most recent items" — but says nothing about layout, component structure, or visual hierarchy. When a coding agent (or human developer) implements these stories, they invent a layout. When design is applied later, that layout is wrong and must be reworked. This means Genesis does not produce a "concrete, working MVP" — it produces a plan that requires a design rework cycle before the MVP is actually working. Closing this gap completes Genesis; it does not extend it.

2. **Design direction is an input to story generation, not a layer on top.** This is the key distinction from ADR-015 (which proposed post-pipeline mockup generation). If design were purely cosmetic, it could be deferred to Evolution. But design decisions affect story structure — a capability that requires a multi-step wizard has different stories than one that uses a single-page dashboard. Establishing screen structure *before* stories means stories are correct the first time.

3. **The stage is conditional and zero-cost for non-UI projects.** CLI tools, API services, and IoT backends skip the stage entirely. It runs only when the architecture stage identifies a user-facing UI frontend and Stitch is configured. This satisfies the Constitution's "would this work for a CLI tool?" test — it doesn't run, rather than producing irrelevant output.

### Relationship to ADR-015

[ADR-015](./ADR-015-google-stitch-mcp-integration.md) proposed Google Stitch integration as a **UI-triggered enhancement** — users click a button to generate mockups on-demand after the pipeline completes. This ADR supersedes that approach because:

- On-demand generation produces screens *after* stories exist, so stories lack design context
- Retrofitting design onto implemented code causes rework
- Individual button clicks don't demonstrate autonomous orchestration
- No design consistency is enforced across screens

ADR-015 is superseded by this ADR. Its rate limiting and shared service account designs are carried forward and restated below so this ADR is self-contained.

### Rate Limiting (Carried Forward from ADR-015)

Since all users share the Stitch generation quota, we implement per-session rate limiting:

```python
@dataclass
class StitchQuota:
    """Track Stitch generation quota."""
    monthly_limit: int = 350          # Stitch free tier
    per_session_limit: int = 12       # Max generations per user session
    warning_threshold: int = 50       # Warn when this many left in month

class StitchRateLimiter:
    """Rate limiter for shared Stitch quota."""

    def __init__(self, session_dir: Path):
        self.session_dir = session_dir
        self.quota_file = session_dir / "stitch_quota.json"
        self.global_quota_file = Path.home() / ".haytham" / "stitch_global_quota.json"

    def can_generate(self) -> tuple[bool, str]:
        """Check if generation is allowed against session and global limits."""
        session_count = self._get_session_count()
        if session_count >= StitchQuota.per_session_limit:
            return False, f"Session limit reached ({StitchQuota.per_session_limit})."

        global_count = self._get_global_count()
        remaining = StitchQuota.monthly_limit - global_count
        if remaining <= 0:
            return False, "Monthly quota exhausted. Resets on the 1st."
        if remaining <= StitchQuota.warning_threshold:
            return True, f"Warning: {remaining} generations remaining this month."
        return True, ""

    def record_generation(self) -> None:
        """Record a generation against both session and global quotas."""
        self._increment_session_count()
        self._increment_global_count()
```

Limits are configurable via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `STITCH_PER_SESSION_LIMIT` | 12 | Max generations per session |
| `STITCH_MONTHLY_LIMIT` | 350 | Monthly global quota (matches Stitch free tier) |

### Shared Service Account (Carried Forward from ADR-015)

To remove GCP setup friction for end users, production deployments use a shared GCP service account:

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ User runs    │────▶│ Haytham App        │────▶│ Google Stitch    │
│ pipeline     │     │ (service account)│     │ MCP API          │
└──────────────┘     └──────────────────┘     └──────────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │ Rate Limiter     │
                  │ (per session)    │
                  └──────────────────┘
```

**Setup (one-time, by platform admin):**
1. Create GCP project (e.g., `haytham-stitch-prod`)
2. Enable Stitch MCP API: `gcloud beta services mcp enable stitch.googleapis.com`
3. Create service account with `roles/serviceusage.serviceUsageConsumer`
4. Generate key, store in secrets manager
5. Set `GOOGLE_APPLICATION_CREDENTIALS=/secrets/stitch-sa-key.json`

**Developer setup**: For personal/dev use, an API key from Stitch settings is sufficient — no GCP project needed.

**Environment configuration:**

```bash
# Required when STITCH_ENABLED=true
STITCH_ENABLED=true
# Choose one auth method:
STITCH_API_KEY=sk-...                           # Simple: API key from Stitch settings
GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json # Production: service account
```

### Google Stitch MCP: Official API

Google provides a **first-party MCP endpoint** at `stitch.googleapis.com/mcp`, documented at [stitch.withgoogle.com/docs/mcp/setup](https://stitch.withgoogle.com/docs/mcp/setup).

The endpoint exposes tools for programmatic UI generation:

| Tool | Description |
|------|-------------|
| `create_project` | Create a new Stitch project |
| `list_projects` | List all Stitch projects |
| `list_screens` | List screens in a project |
| `get_screen` | Get screen metadata |
| `generate_screen` | Generate UI screen from text prompt (Gemini 3 Pro or Flash) |
| `fetch_screen_code` | Retrieve generated code (HTML, React, Vue, Flutter, SwiftUI, and others) |
| `fetch_screen_image` | Download screen as high-res image |

**Authentication** supports two methods:
- **API Key** — simpler, from Stitch settings, backed by Google Cloud Managed Projects (good for personal/dev use)
- **Application Default Credentials (ADC)** — uses GCP credentials with IAM roles (good for production/shared use)

A community proxy ([davideast/stitch-mcp](https://github.com/davideast/stitch-mcp)) handles token refresh automatically, which suggests the raw auth flow has friction points that need validation in the spike.

**Pricing**: Stitch MCP is currently free as part of Google Labs.

**Note**: Community MCP servers (e.g., [auto-stitch-mcp](https://glama.ai/mcp/servers/@GreenSheep01201/auto-stitch-mcp)) extend the official tools with `extract_design_context`, `analyze_accessibility`, `generate_design_tokens`, and `batch_generate_screens`. This ADR intentionally uses only the official tools. Community tools can be explored as future enhancements.

### Strands MCP Client Tool

The [Strands Agents MCP Client](https://github.com/strands-agents/tools/blob/main/src/strands_tools/mcp_client.py) provides runtime MCP integration for Strands agents:

- **Dynamic connection**: Connect to any MCP server (stdio, SSE, or HTTP transport)
- **Tool discovery**: Automatically lists and loads tools from connected servers
- **Tool invocation**: Call MCP tools with arguments and receive results
- **Connection management**: Thread-safe, supports multiple concurrent connections

This means a Haytham agent can be given the `mcp_client` tool and autonomously connect to Stitch, discover its tools, generate screens, and extract code — all within a single agent turn.

**This integration path is unvalidated.** No evidence exists that `strands_tools.mcp_client` has been tested with the Stitch SSE endpoint, GCP auth token refresh during long agent turns, or binary responses (screen images). The prerequisite spike validates this before any implementation work begins.

---

## Decision

### Add an Optional Design & UX Stage Between Phase 3 and Phase 4

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    UPDATED WORKFLOW: WHY → WHAT → HOW → LOOK → STORIES     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PHASE 1: WHY (Idea Validation)         — unchanged                        │
│  PHASE 2: WHAT (MVP Specification)      — unchanged                        │
│  PHASE 3: HOW (Technical Design)        — unchanged                        │
│                                    │                                        │
│                        ┌───────────┴───────────┐                           │
│                        │    DECISION GATE 3    │                           │
│                        └───────────┬───────────┘                           │
│                                    │                                        │
│                    ┌───────────────┴───────────────┐                       │
│                    │ has_user_facing_ui?            │                       │
│                    │ AND stitch_enabled?            │                       │
│                    ├─── YES ───────┬─── NO ────────┤                       │
│                    │               │               │                       │
│                    ▼               │               ▼                       │
│  ╔═════════════════════════╗      │     (skip to Phase 4)                 │
│  ║ PHASE 3b: LOOK          ║      │                                       │
│  ║ (Design & UX)           ║      │                                       │
│  ║                          ║      │                                       │
│  ║ Sub-stage A:             ║      │                                       │
│  ║   design_sampling        ║      │                                       │
│  ║   → sample screen(s)     ║      │                                       │
│  ║   → user approves style  ║      │                                       │
│  ║                          ║      │                                       │
│  ║ Sub-stage B:             ║      │                                       │
│  ║   design_generation      ║      │                                       │
│  ║   → remaining screens    ║      │                                       │
│  ║     in approved style    ║      │                                       │
│  ╚════════════╤═════════════╝      │                                       │
│               │                    │                                        │
│               └────────────────────┘                                        │
│                        │                                                    │
│                        ▼                                                    │
│  PHASE 4: STORIES (Implementation)  — enhanced with design references      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### The Stage is Optional

Like `pivot_strategy` (gated on `risk_level="HIGH"`), the `ux-design` stage is **conditional**. It runs only when:

1. The MVP has user-facing UI capabilities (not CLI-only, not API-only)
2. Stitch integration is configured (`STITCH_ENABLED=true`)

This satisfies the Constitution's "would this work for a CLI tool?" test — it simply doesn't run for non-UI projects.

### Workflow Ordering: Where DESIGN_AND_UX Fits

The `StageRegistry.get_next_workflow()` method currently maintains a hardcoded ordering:

```python
workflow_order = [
    WorkflowType.IDEA_VALIDATION,
    WorkflowType.MVP_SPECIFICATION,
    WorkflowType.TECHNICAL_DESIGN,
    WorkflowType.STORY_GENERATION,
]
```

`DESIGN_AND_UX` is inserted between `TECHNICAL_DESIGN` and `STORY_GENERATION`:

```python
workflow_order = [
    WorkflowType.IDEA_VALIDATION,
    WorkflowType.MVP_SPECIFICATION,
    WorkflowType.TECHNICAL_DESIGN,
    WorkflowType.DESIGN_AND_UX,       # New — optional
    WorkflowType.STORY_GENERATION,
]
```

Because the workflow is optional, `get_next_workflow()` must handle the skip case. When `DESIGN_AND_UX` stages are skipped (non-UI project or Stitch not enabled), the method should return `STORY_GENERATION` as the next workflow after `TECHNICAL_DESIGN`. The implementation approach:

```python
def get_next_workflow(self, workflow_type: WorkflowType, skip_optional: bool = False) -> WorkflowType | None:
    """Get the next workflow in sequence.

    Args:
        workflow_type: Current workflow type
        skip_optional: If True, skip workflows whose stages are all optional

    Returns:
        Next WorkflowType or None if this is the last workflow
    """
    workflow_order = [
        WorkflowType.IDEA_VALIDATION,
        WorkflowType.MVP_SPECIFICATION,
        WorkflowType.TECHNICAL_DESIGN,
        WorkflowType.DESIGN_AND_UX,
        WorkflowType.STORY_GENERATION,
    ]
    try:
        idx = workflow_order.index(workflow_type)
        for next_idx in range(idx + 1, len(workflow_order)):
            candidate = workflow_order[next_idx]
            if skip_optional:
                stages = self.get_stages_for_workflow(candidate, include_optional=True)
                if stages and all(s.is_optional for s in stages):
                    continue
            return candidate
    except ValueError:
        pass
    return None
```

The `skip_optional` parameter defaults to `False` for backwards compatibility. Callers that need to skip disabled workflows (e.g., the Streamlit navigation builder) pass `skip_optional=True` when `STITCH_ENABLED` is `false` or `has_user_facing_ui` is `false`.

### Design Direction: Two Candidate Approaches

The spike determines which sampling approach to use. Both are documented here; the spike's Q4 result selects the winner.

#### Approach A: Single-Sample-with-Iteration (Preferred if Spike Q4 Passes)

Generate 1 screen, show it to the user, let them give text feedback, iterate. This uses fewer generations and gives the user more control.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SINGLE-SAMPLE-WITH-ITERATION                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. Agent identifies the MVP's primary user-facing capability               │
│  2. Agent generates 1 screen for that capability via Stitch                 │
│     (using a neutral, balanced style prompt)                                │
│  3. User sees the screen in Streamlit UI                                    │
│  4. User either:                                                            │
│     a) Approves → this screen establishes the design direction              │
│     b) Types feedback ("make it more minimal", "darker theme",             │
│        "use cards instead of a table") → agent regenerates                  │
│  5. Max 2 iterations (3 generations total worst case, 1 best case)         │
│  6. Agent generates remaining screens referencing the approved style        │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Generated Screen                                                    │    │
│  │  ┌──────────────────────────┐                                       │    │
│  │  │                          │                                       │    │
│  │  │   [Primary Capability]   │                                       │    │
│  │  │                          │                                       │    │
│  │  └──────────────────────────┘                                       │    │
│  │                                                                      │    │
│  │  [✓ Approve]  [✏ Refine: _________________________ ]                │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  Budget: 1 generation (best) to 3 generations (worst, with 2 refinements)  │
│  vs 3-sample approach: always exactly 3 generations                         │
│                                                                              │
│  Benefits:                                                                  │
│  • Lower generation budget (1-3 vs always 3 for sampling)                  │
│  • User gets *directed* control ("more whitespace") vs *selection* control │
│  • Feedback is composable — user can adjust multiple aspects iteratively   │
│  • Text feedback from the user doubles as style documentation              │
│                                                                              │
│  Drawbacks:                                                                 │
│  • Requires the user to articulate what they want (not just pick)          │
│  • Iteration loop is a new interaction pattern for Haytham                   │
│  • Stitch may not reliably incorporate text feedback (spike Q4 validates)  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Approach B: 3-Sample Visual Selection (Fallback if Spike Q4 Fails)

Generate 3 samples with different style moods, let the user pick one visually.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    3-SAMPLE VISUAL SELECTION                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. Agent identifies the MVP's primary user-facing capability               │
│  2. Agent generates 3 sample screens (each with a different style mood):   │
│     • "Clean, minimal, lots of whitespace"                                  │
│     • "Bold, modern, strong visual hierarchy"                               │
│     • "Warm, friendly, approachable"                                        │
│  3. User sees 3 screenshots side-by-side and picks one                     │
│  4. Chosen screen establishes the design direction                          │
│  5. Agent generates remaining screens referencing the chosen style          │
│                                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐               │
│  │  Option A       │  │  Option B       │  │  Option C       │               │
│  │  ┌──────────┐  │  │  ┌──────────┐  │  │  ┌──────────┐  │               │
│  │  │ Clean &  │  │  │  │ Bold &   │  │  │  │ Warm &   │  │               │
│  │  │ Minimal  │  │  │  │ Modern   │  │  │  │ Friendly │  │               │
│  │  └──────────┘  │  │  └──────────┘  │  │  └──────────┘  │               │
│  │  ○ Select      │  │  ● Select      │  │  ○ Select      │               │
│  └────────────────┘  └────────────────┘  └────────────────┘               │
│                                                                              │
│  Budget: Always exactly 3 generations for sampling                          │
│                                                                              │
│  Benefits:                                                                  │
│  • Zero articulation required — user just picks visually                   │
│  • Guaranteed variety across options                                        │
│  • Simple binary gate — select and continue                                │
│                                                                              │
│  Drawbacks:                                                                 │
│  • Always burns 3 generations (25% of a 12-generation session budget)      │
│  • 2 of 3 samples are discarded                                            │
│  • User has no fine-grained control beyond "this one"                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Sub-Stage Structure (Both Approaches)

Both approaches fit the existing Burr architecture as a **two-sub-stage pattern**:

| Sub-stage | Approach A (Iteration) | Approach B (3-Sample) |
|-----------|----------------------|----------------------|
| `design_sampling` | Generate 1 screen; iterate up to 2x on user feedback | Generate 3 screens with style variations |
| User gate | Approve / refine text input | Pick one of 3 |
| `design_generation` | Generate remaining screens in approved style | Generate remaining screens in chosen style |

The user gate between sub-stages mirrors the existing decision gate pattern between phases — it's a stage-boundary interaction, not a mid-agent pause. The `StageExecutor` handles each sub-stage independently, with the user gate implemented as a Streamlit view between them (identical to how decision gates between phases work today).

### Style Transfer: The Key Unknown

The spike must answer: **Does Stitch maintain style coherence across screens within a project?**

If yes, the flow is clean — the chosen sample establishes the style, and subsequent screens inherit it naturally.

If no, the agent must extract style cues from the chosen screen and inject them into subsequent prompts. Possible approaches:

| Approach | Complexity | Reliability |
|----------|-----------|-------------|
| Use same project in Stitch (if Stitch maintains project-level style) | Low | Unknown — spike validates |
| Extract style description from chosen screen via LLM vision | Medium | Moderate — depends on prompt quality |
| Use community `extract_design_context` tool | Medium | Unknown — third-party dependency |
| Include chosen screen image as reference in subsequent prompts | Low | Depends on Stitch multimodal support |

The spike determines which approach is needed. The implementation plan does not proceed until this is answered.

### Technology-Aware Design Prompts

The architecture decisions stage (Phase 3) already determines the frontend framework and deployment target. The agent reads this and includes it in every `generate_screen` prompt:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PROMPT COMPOSITION PER SCREEN                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  From architecture_decisions:          From chosen sample:                  │
│  ┌──────────────────────────┐          ┌──────────────────────────┐        │
│  │ framework: "React"       │          │ Style cues from the       │        │
│  │ platform: "web"          │          │ user-selected sample      │        │
│  │ css: "Tailwind CSS"      │          │ screen (method TBD by     │        │
│  └────────────┬─────────────┘          │ spike results)            │        │
│               │                         └────────────┬─────────────┘        │
│               └──────────────┬───────────────────────┘                      │
│                              ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ generate_screen prompt:                                              │    │
│  │                                                                      │    │
│  │ "Design a React web application screen using Tailwind CSS.           │    │
│  │  <style direction from chosen sample>                                │    │
│  │                                                                      │    │
│  │  This screen implements: CAP-F-003 User Dashboard                   │    │
│  │  Description: A personalized dashboard showing recent activity..."   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  The technology context flows automatically from architecture stage.        │
│  fetch_screen_code uses the matching framework for code export.             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

If the architecture chose a framework not supported by Stitch's code export, the agent falls back to the closest match and notes this in the output. Stitch supports React, Vue, Flutter, SwiftUI, Angular, HTML/CSS — covering most common choices.

### Agent Design

A single `ux_designer` agent orchestrates the full design workflow using the `mcp_client` tool. The sampling sub-stage behavior varies based on spike results:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         UX DESIGNER AGENT                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Tools: [mcp_client]                                                        │
│                                                                              │
│  Sub-stage A: design_sampling                                               │
│  ┌──────────────────────────────────────────────────────────────────┐       │
│  │ 1. Connect to Stitch MCP (official endpoint)                      │       │
│  │ 2. Create project for this MVP                                    │       │
│  │ 3. Read deployment_context from architecture-decisions JSON       │       │
│  │ 4. Identify primary user-facing capability                        │       │
│  │                                                                    │       │
│  │ IF single-sample-with-iteration (spike Q4 passed):                │       │
│  │    5a. Generate 1 screen with neutral style prompt                 │       │
│  │    5b. Fetch image                                                 │       │
│  │    → Output: 1 screen image for user approval/refinement          │       │
│  │                                                                    │       │
│  │ IF 3-sample visual selection (spike Q4 failed):                   │       │
│  │    5a. Generate 3 screens with style variations:                   │       │
│  │        • "Clean, minimal, lots of whitespace"                      │       │
│  │        • "Bold, modern, strong visual hierarchy"                   │       │
│  │        • "Warm, friendly, approachable"                            │       │
│  │    5b. Fetch images for all 3 screens                              │       │
│  │    → Output: 3 screen images for user selection                    │       │
│  │                                                                    │       │
│  │ 6. Disconnect                                                      │       │
│  └──────────────────────────────────────────────────────────────────┘       │
│                                                                              │
│  ── USER GATE ──                                                            │
│  Iteration mode: Approve / type refinement feedback (max 2 iterations)     │
│  Selection mode: Pick one of 3 options                                      │
│                                                                              │
│  Sub-stage B: design_generation                                             │
│  ┌──────────────────────────────────────────────────────────────────┐       │
│  │ 1. Connect to Stitch MCP                                          │       │
│  │ 2. For each remaining user-facing CAP-F-*:                        │       │
│  │    • generate_screen (with style direction + capability desc)      │       │
│  │    • fetch_screen_code (framework from architecture decisions)     │       │
│  │    • fetch_screen_image                                            │       │
│  │ 3. Disconnect                                                     │       │
│  │ → Output: Screens, code, and images for all capabilities          │       │
│  └──────────────────────────────────────────────────────────────────┘       │
│                                                                              │
│  Output: Structured markdown with screens, code, and style direction       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Downstream Impact: Enhanced Stories

When the `ux-design` stage has run, the `story_generator` agent receives design context and can produce richer stories:

```markdown
## Without Design Stage (current)
STORY-005: Build User Dashboard
As a user, I can view my personalized dashboard showing recent activity.
Acceptance Criteria:
- Dashboard loads within 2 seconds
- Shows 5 most recent items

## With Design Stage (proposed)
STORY-005: Build User Dashboard
As a user, I can view my personalized dashboard showing recent activity.
Implements: CAP-F-003
Design Reference: Screen-003 (user_dashboard)
Acceptance Criteria:
- Dashboard loads within 2 seconds
- Shows 5 most recent items
- Layout follows Screen-003 wireframe
- Generated starter code available in session/ux-design/
```

**Caveat**: The design references are useful as visual guides for human developers. For AI coding agents to use them directly, the agent would need image understanding or the generated code as a starting scaffold. Position the screen artifacts as reference material, not as executable specs.

---

## Concerns and Mitigations

### Concern 1: GCP Dependency

**Problem**: Haytham currently requires only AWS (Bedrock). Adding Google Stitch introduces a second cloud provider dependency.

**Mitigation**:
- Gated behind `STITCH_ENABLED=true` — zero impact when not configured
- Two auth options: API Key (simple, personal) or ADC (production, shared)
- For production: shared service account approach (see "Shared Service Account" section above) eliminates per-user GCP setup
- No GCP dependency for users who don't want design generation

### Concern 2: Rate Limits and Quota

**Problem**: Sampling + N capability screens per run. An MVP with 6 UI capabilities uses 7-9 generations depending on sampling approach.

**Budget analysis** (12-generation session limit):

| Sampling Approach | Sampling Cost | 6 UI Capabilities | Total | Remaining for Retries |
|-------------------|--------------|-------------------|-------|-----------------------|
| Single-sample, approved first try | 1 | 6 | 7 | 5 |
| Single-sample, 2 iterations | 3 | 6 | 9 | 3 |
| 3-sample selection | 3 | 6 | 9 | 3 |

**Mitigation**:
- Default per-session limit of 12 generations (configurable via `STITCH_PER_SESSION_LIMIT`)
- Single-sample-with-iteration (if spike Q4 passes) saves 0-2 generations vs 3-sample approach
- Agent prompt instructs: generate only for user-facing capabilities (`CAP-F-*`), skip non-functional (`CAP-NF-*`) and admin/system screens
- Cache generated screens in `session/ux-design/` — re-runs skip already-generated screens
- On re-runs, if a chosen design direction already exists, skip sampling entirely

### Concern 3: Non-Web MVPs

**Problem**: Stitch generates web/mobile UI. For CLI tools, API services, or IoT backends, this stage produces no value.

**Mitigation**: Conditional execution based on a structured flag extracted from the architecture stage output.

#### Extraction Mechanism for `has_user_facing_ui`

The `architecture_decisions` agent already produces structured JSON internally (with a `decisions` array, `coverage_check`, and `summary`), but the current `_run_architecture_decisions()` function in `stage_executor.py` discards the JSON and returns only markdown. This ADR requires two changes:

**Change 1: Preserve the structured JSON.** Modify `_run_architecture_decisions()` to save the parsed JSON to `session/architecture-decisions/decisions.json` alongside the existing markdown output. This is a small change — the JSON is already parsed via `extract_json_from_response()` at line ~420 of `stage_executor.py`; it just needs to be written to disk before being discarded.

**Change 2: Add `deployment_context` to the architecture agent's JSON schema.** Extend the existing JSON output format with a new top-level field:

```json
{
  "decisions": [ ... ],
  "coverage_check": { ... },
  "summary": "...",
  "deployment_context": {
    "platform": "web",
    "has_user_facing_ui": true,
    "frontend_framework": "React",
    "css_framework": "Tailwind CSS"
  }
}
```

The `deployment_context.platform` field is constrained to one of: `"web"`, `"mobile"`, `"desktop"`, `"cli"`, `"api"`, `"iot"`, `"hybrid"`. The `has_user_facing_ui` field is `true` when `platform` is `"web"`, `"mobile"`, `"desktop"`, or `"hybrid"`. The agent prompt already reasons about platform and framework — this change asks it to emit that reasoning as structured data instead of only prose.

**Reading the flag in Burr:** The `design_sampling` action reads `session/architecture-decisions/decisions.json`, extracts `deployment_context.has_user_facing_ui`, and stores it in Burr state. The transition is wired as:

```python
("architecture_decisions", "design_sampling", when(has_user_facing_ui=True, stitch_enabled=True)),
("architecture_decisions", "story_generation", default),
```

This follows the existing pattern used for `pivot_strategy` (gated on `risk_level="HIGH"`).

**Edge cases:**

| Input | `platform` | `has_user_facing_ui` | Design stage runs? |
|-------|-----------|---------------------|-------------------|
| Web app (gym leaderboard) | `"web"` | `true` | Yes |
| CLI tool (markdown converter) | `"cli"` | `false` | No |
| API service (weather API) | `"api"` | `false` | No |
| Mobile app | `"mobile"` | `true` | Yes |
| API + admin dashboard | `"hybrid"` | `true` | Yes |
| CLI with TUI (ncurses) | `"cli"` | `false` | No (Stitch can't generate TUIs) |
| IoT backend | `"iot"` | `false` | No |

### Concern 4: Framework Mismatch

**Problem**: Architecture may decide on a framework Stitch doesn't support for code export.

**Mitigation**:
- The agent reads framework from `architecture_decisions` and uses it in `fetch_screen_code`
- Stitch supports React, Vue, Flutter, SwiftUI, Angular, HTML/CSS
- If the architecture chose an unsupported framework (e.g., Svelte), the agent falls back to the closest match and notes this in the output
- Position generated code as "starter scaffolding" — stories reference screen layouts, not copy-paste the code

### Concern 5: Latency

**Problem**: Each Stitch generation takes several seconds. 3 samples + 6 screens could add meaningful time to the workflow.

**Mitigation**:
- The existing workflow already takes several minutes across all stages
- Show progress callbacks in the Streamlit UI ("Generating sample 2 of 3...", "Generating screen 4 of 6...")
- If latency is unacceptable, user can set `STITCH_ENABLED=false`

### Concern 6: Stitch is Experimental (Google Labs)

**Problem**: Google Labs products can be shut down. Building a workflow stage on it creates an external dependency.

**Mitigation**:
- The agent uses `mcp_client` generically — it connects to an MCP server and calls tools
- If Stitch is discontinued, the same agent could connect to a different MCP-compatible design tool
- Feature flag means removal is a one-line config change
- The stage output format (screens + code + images) is tool-agnostic

### Concern 7: Style Transfer Between Screens

**Problem**: It is unknown whether Stitch maintains visual consistency across screens within the same project, or whether each `generate_screen` call produces an independent style.

**Mitigation**: This is the primary question the spike (Q3) answers. See "Style Transfer: The Key Unknown" above for the decision matrix. No implementation work begins until this is resolved.

---

## Spike: Prerequisite Gate

**This ADR's decision is conditional.** The implementation plan below does not begin until this spike is complete and its results are documented. If the spike fails on question #1 or #2, this ADR is rejected with no wasted implementation effort.

The spike is a standalone investigation, tracked as its own task, producing a deliverable in `docs/spikes/spike-stitch-mcp.md`.

### Questions to Validate

| # | Question | Test | Pass Criteria |
|---|----------|------|---------------|
| 1 | Can Strands `mcp_client` connect to `stitch.googleapis.com/mcp` via SSE? | Create a minimal Strands agent with `mcp_client`, connect to Stitch, call `list_projects` | Successful connection, auth header passing, response parsing |
| 2 | Can the agent autonomously generate a screen and fetch image + code? | `generate_screen` → `fetch_screen_image` → `fetch_screen_code` in a single agent turn | All three calls succeed; binary image is retrievable; token budget fits in one turn |
| 3 | Does Stitch maintain style coherence across screens in the same project? | Generate 3 screens in the same project with similar style prompts, visually compare | Subjective visual comparison — document findings regardless |
| 4 | Does the single-sample-with-feedback loop work? | Generate 1 screen, describe a style adjustment in a follow-up prompt, regenerate | Second screen reflects the feedback; iteration is cheaper than 3-up sampling |

### Spike Outcomes and Decision Matrix

| Spike Result | ADR Action |
|--------------|------------|
| Q1 fails (no SSE connectivity) | **ADR rejected.** Revisit when Strands MCP client matures or Stitch adds HTTP transport. |
| Q2 fails (binary handling or token budget) | **ADR rejected.** The agent cannot complete the workflow autonomously. |
| Q3 passes (project-level style coherence) | Use same-project approach for style transfer (low complexity). |
| Q3 fails (no style coherence) | Use LLM vision extraction or image-reference approach (see Style Transfer section). |
| Q4 passes (iteration works) | Use single-sample-with-iteration as the sampling approach (saves 2 generations). |
| Q4 fails (iteration unreliable) | Use 3-sample visual selection as the sampling approach. |

### Spike Deliverable

A document in `docs/spikes/spike-stitch-mcp.md` containing:
- Pass/fail for each question with evidence (screenshots, logs, error messages)
- Latency measurements per `generate_screen` call
- Recommendation on sampling approach (single-sample vs 3-sample)
- Recommendation on style transfer approach
- Any auth friction encountered (token refresh, connection timeouts)

---

## Implementation Plan

**Prerequisite**: Spike complete with Q1 and Q2 passing.

### Phase 1: Foundation

1. Add `strands-tools` to optional dependencies:
   ```toml
   [project.optional-dependencies]
   stitch = ["strands-tools>=0.1.0"]
   ```

2. Add `DESIGN_AND_UX` to `WorkflowType` enum in `stage_registry.py`

3. Create two `StageMetadata` entries in `stage_registry.py`:
   ```python
   StageMetadata(
       slug="design-sampling",
       action_name="design_sampling",
       display_name="Design Sampling",
       display_index="8b",
       description="Generates sample UI screen(s) for the primary capability to establish design direction...",
       state_key="design_sampling",
       status_key="design_sampling_status",
       workflow_type=WorkflowType.DESIGN_AND_UX,
       query_template="Generate sample UI design(s) for the primary capability...",
       agent_names=["ux_designer"],
       is_optional=True,
       required_context=["capability-model", "architecture-decisions"],
   ),
   StageMetadata(
       slug="design-generation",
       action_name="design_generation",
       display_name="Design Generation",
       display_index="8c",
       description="Generates UI screens for all user-facing capabilities...",
       state_key="design_generation",
       status_key="design_generation_status",
       workflow_type=WorkflowType.DESIGN_AND_UX,
       query_template="Generate UI screens for remaining capabilities...",
       agent_names=["ux_designer"],
       is_optional=True,
       required_context=["capability-model", "architecture-decisions", "design-sampling"],
   ),
   ```

4. Add `StageExecutionConfig` entries in `stage_executor.py` with `programmatic_executor` functions (to inject MCP connection config and handle Stitch-specific logic)

5. Wire Burr transitions in the workflow:
   ```python
   ("architecture_decisions", "design_sampling", when(has_user_facing_ui=True, stitch_enabled=True)),
   ("architecture_decisions", "story_generation", default),
   ("design_sampling", "design_generation"),  # User gate handled in Streamlit
   ("design_generation", "story_generation"),
   ```

6. Add Burr actions for both sub-stages

### Phase 2: Agent & Stitch Integration

1. Create `worker_ux_designer/` agent directory:
   ```
   haytham/agents/worker_ux_designer/
   ├── __init__.py
   └── worker_ux_designer_prompt.txt
   ```

2. Register agent in `agent_factory.py` with `mcp_client` tool

3. Write `worker_ux_designer_prompt.txt` with:
   - MCP connection workflow (connect → create project → generate → fetch → disconnect)
   - Style prompts (single neutral prompt for iteration mode, or 3 variations for selection mode)
   - Instructions to read framework from architecture decisions
   - Instructions to generate only for user-facing capabilities (`CAP-F-*`)
   - Style transfer approach (determined by spike results)
   - Output format specification

4. Implement rate limiting (see "Rate Limiting" section above)

5. Add session caching for generated screens in `session/ux-design/`

### Phase 3: Streamlit UI — Design Selection Gate

1. Add design sampling view (`frontend_streamlit/views/design_selection.py`):
   - **If single-sample-with-iteration** (spike Q4 passed):
     - Display 1 generated screen
     - "Approve" button to accept and continue
     - Text input for refinement feedback + "Regenerate" button (max 2 iterations)
     - Store approved screen + user feedback history to `session/ux-design/chosen_sample.json`
   - **If 3-sample visual selection** (spike Q4 failed):
     - Display 3 generated sample screens side-by-side
     - Radio button or card selection for user to pick their preferred style
     - Store selection to `session/ux-design/chosen_sample.json`
   - "Continue" button triggers `design_generation` sub-stage

2. Add design results view (`frontend_streamlit/views/design.py`):
   - Display all generated screens as image gallery
   - Show generated code per screen (copyable)
   - Framework indicator per screen

3. Add to dynamic navigation in `Haytham.py`

### Phase 4: Story Generator Enhancement

1. Update `story_generator` prompt to consume design context when available
2. Add conditional context: if `design-generation` stage has output, include screen references
3. Stories reference Screen IDs when design context exists — but don't make them blocking acceptance criteria

### Phase 5: Testing

1. Add `ux_designer` to LLM-as-Judge criteria (ADR-018):
   - Sampling sub-stage produces at least 1 screen for the primary capability
   - Screens generated for each remaining user-facing capability
   - Output references capability IDs (CAP-F-*)
   - Framework matches architecture decisions
   - `deployment_context` extraction produces valid `has_user_facing_ui` flag
2. Test with both web app and CLI inputs (CLI should skip the stage entirely)
3. Test with `STITCH_ENABLED=false` (stage should be skipped)
4. Test `get_next_workflow()` with `skip_optional=True` when DESIGN_AND_UX is disabled

---

## Consequences

### Positive

1. **Demonstrates orchestration** — Haytham visibly integrates an external service (Google Stitch via MCP), proving its multi-service orchestration capability
2. **Avoids design rework** — Design direction is established before implementation stories are written
3. **Richer deliverables** — MVP output includes visual screens alongside specs and stories
4. **Intuitive user control** — Visual selection or text-based iteration requires zero design knowledge
5. **Framework-aware code** — Generated code matches the architecture's framework choice
6. **Replaceability** — MCP abstraction means any future design tool with MCP support can be swapped in
7. **Idempotent** — Chosen design direction stored locally; re-runs skip the selection step

### Negative

1. **Second cloud provider** — GCP dependency (optional but present when enabled)
2. **External service dependency** — Stitch availability affects stage completion
3. **GCP auth setup** — One-time configuration per developer (eliminated in production via shared service account)
4. **Workflow time increase** — Additional time for screen generation per run
5. **Sampling budget cost** — 1-3 generations spent on style selection (8-25% of session budget depending on approach and iteration count)

### Risks

1. **Spike failure** — Strands `mcp_client` may not work with Stitch's SSE endpoint
   - Mitigation: Spike is a prerequisite gate; if Q1 or Q2 fails, this ADR is rejected with no wasted implementation effort
2. **Stitch API discontinuation** (Google Labs product)
   - Mitigation: Feature flag, MCP abstraction, tool-agnostic output format
3. **No style coherence across screens** — Each screen may look visually different
   - Mitigation: Spike answers this; fallback approaches documented in "Style Transfer" section
4. **Generated UI quality** may not match user expectations
   - Mitigation: Position as wireframes/starting points, not final designs
5. **MCP client tool stability** (strands-tools is evolving)
   - Mitigation: Pin dependency version, test in CI

---

## Alternatives Considered

### Alternative A: Keep ADR-015 (UI-Triggered Only)

Stick with on-demand mockup generation from the Streamlit UI.

**Rejected because:** Does not feed design context into story generation. Each mockup is isolated — no design system, no consistency across screens. Does not demonstrate autonomous orchestration. Causes design rework when applied after implementation.

### Alternative B: Full Separate Phase with Multiple Sub-Stages

Create a `WorkflowType.DESIGN_AND_UX` with many sub-stages (UX flows, design system, accessibility, handoff).

**Rejected because:** Over-engineered for current needs. Two sub-stages (sampling + generation) are sufficient. Additional sub-stages can be introduced later if the design stage becomes too complex.

### Alternative C: Embed Design in Story Generation

Have the `story_generator` agent call Stitch directly to generate screens during story creation.

**Rejected because:** Violates separation of concerns. Story generation should focus on task decomposition, not UI design. Also makes testing harder — a story generation failure could be caused by Stitch issues rather than prompt problems.

### Alternative D: Color Palette Approval Instead of Visual Sampling

Agent proposes hex color palette → user approves → palette injected into all prompts.

**Rejected because:** Requires users to make abstract design decisions (hex codes). Requires mid-agent pause for approval (doesn't fit `StageExecutor` pattern). Visual sampling is more intuitive and produces a concrete reference point.

### Alternative E: Use v0.dev or Figma AI

Use Vercel's v0.dev or Figma AI instead of Stitch.

**Rejected because:**
- v0.dev: No MCP support, requires separate API key
- Figma AI: No official MCP endpoint, design-only (limited code generation), requires subscription
- Stitch: Official MCP endpoint, multi-framework code generation, free, Google-backed

---

## Dependencies

- [ADR-015: Google Stitch MCP Integration](./ADR-015-google-stitch-mcp-integration.md) — Superseded by this ADR (rate limiting and shared service account designs restated in full above)
- [ADR-016: Four-Phase Workflow](./ADR-016-four-phase-workflow.md) — Current workflow architecture being extended
- [ADR-018: LLM-as-Judge Agent Testing](./ADR-018-llm-as-judge-agent-testing.md) — Testing framework for the new agent

---

## References

- [Google Stitch](https://stitch.withgoogle.com/)
- [Stitch MCP Setup Guide](https://stitch.withgoogle.com/docs/mcp/setup) — Official setup documentation
- [Stitch MCP Endpoint](https://stitch.googleapis.com/mcp) — Official Google API
- [davideast/stitch-mcp](https://github.com/davideast/stitch-mcp) — Community proxy for auth token management
- [Strands Agents MCP Client](https://github.com/strands-agents/tools/blob/main/src/strands_tools/mcp_client.py)
- [Google Developers Blog — Introducing Stitch](https://developers.googleblog.com/stitch-a-new-way-to-design-uis/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [auto-stitch-mcp](https://glama.ai/mcp/servers/@GreenSheep01201/auto-stitch-mcp) — Community extension with additional tools
- [Gemini CLI Stitch Extension](https://github.com/gemini-cli-extensions/stitch)
