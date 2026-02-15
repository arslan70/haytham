# ADR-015: Google Stitch MCP Integration for UI Generation

## Status
**Proposed** — 2026-01-21

## Context

### What is Google Stitch?

[Google Stitch](https://stitch.withgoogle.com/) is an AI-powered UI design tool from Google Labs that uses **Gemini 2.5 Pro** to generate production-ready UI designs and code from:

- **Text prompts** — "Create a dashboard for tracking fitness goals"
- **Sketches/wireframes** — Upload hand-drawn mockups
- **Screenshots** — Reference existing apps for style inspiration

It outputs code in multiple frameworks: **Flutter, Jetpack Compose, SwiftUI, CSS, React, Angular, and Vue**.

### Official MCP Support

Google provides an **official MCP endpoint** at `stitch.googleapis.com/mcp`. This can be enabled via:

```bash
gcloud beta services mcp enable stitch.googleapis.com --project=$PROJECT_ID
```

### Available MCP Tools

The official Stitch MCP provides these tools:

| Tool | Description |
|------|-------------|
| `list_projects` | List all Stitch projects |
| `create_project` | Create a new project |
| `list_screens` | List screens within a project |
| `generate_screen` | Generate UI screen from text prompt |
| `fetch_screen_code` | Download generated code (HTML/React/Vue/etc.) |
| `fetch_screen_image` | Download screen as image asset |

### Pricing

Google Stitch is currently **free** as part of Google Labs:
- **Standard Mode (Gemini 2.5 Flash):** 350 generations/month
- **Experimental Mode (Gemini 2.5 Pro):** 50 generations/month
- No credit card required

---

## Decision

### Integrate Google Stitch MCP for UI Generation

We will add optional Stitch integration to enhance MVP deliverables with visual mockups and starter code.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STITCH INTEGRATION ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐    │
│  │ Capability Model │────▶│ Stitch MCP       │────▶│ UI Mockups in    │    │
│  │ (capabilities)   │     │ generate_screen  │     │ MVP Spec Output  │    │
│  └──────────────────┘     └──────────────────┘     └──────────────────┘    │
│                                                                             │
│  ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐    │
│  │ Build vs Buy     │────▶│ Stitch MCP       │────▶│ Starter Code     │    │
│  │ (BUILD items)    │     │ fetch_screen_code│     │ Download         │    │
│  └──────────────────┘     └──────────────────┘     └──────────────────┘    │
│                                                                             │
│                         Official Google API                                 │
│                    stitch.googleapis.com/mcp                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Authentication: Shared Service Account

To remove GCP setup friction for users, we use a **shared GCP service account** managed by the Haytham platform:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AUTHENTICATION ARCHITECTURE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐        │
│  │ User clicks  │────▶│ Haytham App  │────▶│ Google Stitch    │        │
│  │ "Generate"   │     │ (service account)│     │ MCP API          │        │
│  └──────────────┘     └──────────────────┘     └──────────────────┘        │
│                              │                                              │
│                              ▼                                              │
│                    ┌──────────────────┐                                     │
│                    │ Rate Limiter     │                                     │
│                    │ (per session)    │                                     │
│                    └──────────────────┘                                     │
│                                                                             │
│  Benefits:                                                                  │
│  • Zero GCP setup for users                                                 │
│  • Centralized quota management                                             │
│  • Usage monitoring and analytics                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Service Account Setup (One-Time, by Platform Admin)

```bash
# 1. Create dedicated GCP project for Haytham
gcloud projects create haytham-stitch-prod

# 2. Enable Stitch MCP API
gcloud beta services mcp enable stitch.googleapis.com \
  --project=haytham-stitch-prod

# 3. Create service account
gcloud iam service-accounts create stitch-generator \
  --display-name="Haytham Stitch Generator" \
  --project=haytham-stitch-prod

# 4. Grant Stitch API access
gcloud projects add-iam-policy-binding haytham-stitch-prod \
  --member="serviceAccount:stitch-generator@haytham-stitch-prod.iam.gserviceaccount.com" \
  --role="roles/serviceusage.serviceUsageConsumer"

# 5. Create and download key (store securely!)
gcloud iam service-accounts keys create stitch-sa-key.json \
  --iam-account=stitch-generator@haytham-stitch-prod.iam.gserviceaccount.com
```

#### Rate Limiting (Shared Quota Protection)

Since all users share the 350 generations/month quota, we implement per-session rate limiting:

```python
# haytham/integrations/stitch/rate_limiter.py

from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from pathlib import Path

@dataclass
class StitchQuota:
    """Track Stitch generation quota."""
    monthly_limit: int = 350
    per_session_limit: int = 10  # Max generations per user session
    warning_threshold: int = 50  # Warn when this many left

class StitchRateLimiter:
    """Rate limiter for shared Stitch quota."""

    def __init__(self, session_dir: Path):
        self.session_dir = session_dir
        self.quota_file = session_dir / "stitch_quota.json"
        self.global_quota_file = Path.home() / ".haytham" / "stitch_global_quota.json"

    def can_generate(self) -> tuple[bool, str]:
        """Check if generation is allowed."""
        # Check session limit
        session_count = self._get_session_count()
        if session_count >= StitchQuota.per_session_limit:
            return False, f"Session limit reached ({StitchQuota.per_session_limit} generations). Start a new project to generate more."

        # Check global quota
        global_count = self._get_global_count()
        remaining = StitchQuota.monthly_limit - global_count

        if remaining <= 0:
            return False, "Monthly quota exhausted. Quota resets on the 1st of each month."

        if remaining <= StitchQuota.warning_threshold:
            return True, f"Warning: Only {remaining} generations remaining this month."

        return True, ""

    def record_generation(self) -> None:
        """Record a generation against quotas."""
        self._increment_session_count()
        self._increment_global_count()

    def get_remaining(self) -> dict:
        """Get remaining quota info."""
        return {
            "session_remaining": StitchQuota.per_session_limit - self._get_session_count(),
            "monthly_remaining": StitchQuota.monthly_limit - self._get_global_count(),
            "resets_on": self._get_reset_date().isoformat(),
        }
```

#### Environment Configuration

```bash
# .env (platform deployment)
STITCH_ENABLED=true
GOOGLE_APPLICATION_CREDENTIALS=/secrets/stitch-sa-key.json

# No user configuration required!
```

---

### Integration Approach

**Decision: UI-Triggered Enhancement (Not a New Stage)**

Stitch integration will be a **user-triggered action from the Streamlit UI**, not a new Burr workflow stage. This approach was chosen because:

| Factor | New Stage | UI-Triggered |
|--------|-----------|--------------|
| Latency | Adds 5-10s per capability to workflow | On-demand, no workflow impact |
| User control | All-or-nothing | Generate for specific items |
| Failure handling | Blocks workflow progression | Graceful degradation |
| Cost control | Uses quota on every run | Users choose when to generate |

#### Existing Workflow (Unchanged)

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ idea_analysis│────▶│market_context│────▶│risk_assessment│
└──────────────┘     └──────────────┘     └──────────────┘
                                                  │
                                                  ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ stories_gen  │◀────│mvp_specification◀───│validation_   │
└──────────────┘     └──────────────┘     │ summary      │
       │                                   └──────────────┘
       ▼
┌──────────────┐
│ build_buy    │
│ analysis     │
└──────────────┘
```

#### Stitch Integration Points (UI-Triggered)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         STREAMLIT UI INTEGRATION                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  MVP Specification View                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Capability: User Dashboard                                           │   │
│  │ Description: Personalized dashboard showing...                       │   │
│  │                                                                      │   │
│  │ [🎨 Generate UI Mockup]  ◀── User clicks to trigger Stitch          │   │
│  │                                                                      │   │
│  │ ┌─────────────────────┐                                              │   │
│  │ │ Generated Mockup    │  ◀── Displayed after generation              │   │
│  │ │ [Get React Code ▼]  │                                              │   │
│  │ └─────────────────────┘                                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Build vs Buy View                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 🔧 BUILD: Custom Analytics Dashboard                                 │   │
│  │                                                                      │   │
│  │ [💻 Generate Starter Code]  ◀── User clicks to trigger Stitch       │   │
│  │                                                                      │   │
│  │ Framework: [React ▼]                                                 │   │
│  │ ┌─────────────────────┐                                              │   │
│  │ │ // Generated code   │                                              │   │
│  │ │ export function...  │                                              │   │
│  │ │ [📥 Download]       │                                              │   │
│  │ └─────────────────────┘                                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Why Not a New Stage?

1. **Latency** — Each Stitch generation takes 5-10 seconds; multiplied by many capabilities would significantly slow the workflow
2. **Selective generation** — Users typically want mockups for 2-3 key screens, not every capability
3. **Failure isolation** — If Stitch is down or rate-limited, it shouldn't block the core validation workflow
4. **Cost control** — Shared quota (350/month); users should control when to spend generations

#### Session Storage

Generated mockups are cached in the session directory:

```
session/
├── stitch-cache/
│   ├── capability_user_dashboard.png      # Cached mockup image
│   ├── capability_user_dashboard.json     # Screen metadata
│   └── capability_user_dashboard_react.tsx # Generated code
```

This allows mockups to persist across page refreshes without re-generation.

---

### Strands MCP Client

We will use the **Strands Agents MCP Client** tool directly - no wrapper class needed. This tool is part of the [strands-agents/tools](https://github.com/strands-agents/tools) package and provides:

- **Dynamic connections** — Connect to MCP servers on-the-fly
- **Tool discovery** — Automatically load available tools from connected servers
- **Multiple transports** — Supports stdio, SSE, and streamable HTTP
- **Connection management** — Thread-safe with proper cleanup

```python
# Install strands-tools
pip install strands-tools
```

---

### Implementation Plan

#### Phase 1: Create UI Generator Agent

Create a dedicated agent with `mcp_client` tool that can autonomously interact with Stitch:

```python
# haytham/agents/worker_ui_generator/agent.py

from strands import Agent
from strands_tools import mcp_client

STITCH_MCP_URL = "https://stitch.googleapis.com/mcp"

def create_ui_generator_agent(model_id: str | None = None) -> Agent:
    """Create an agent with MCP client capabilities for UI generation."""
    system_prompt = load_agent_prompt("worker_ui_generator")

    return Agent(
        system_prompt=system_prompt,
        model=model_id or get_bedrock_model_id(),
        tools=[mcp_client],  # Agent can dynamically connect to MCP servers
    )
```

#### Agent System Prompt

```text
# haytham/agents/worker_ui_generator/worker_ui_generator_prompt.txt

You are a UI Generator agent that creates UI mockups and code using Google Stitch.

## Your Workflow

1. Connect to the Stitch MCP server:
   ```
   mcp_client(
       action="connect",
       server_url="https://stitch.googleapis.com/mcp",
       transport_type="sse"
   )
   ```

2. Generate a screen from the user's prompt:
   ```
   mcp_client(
       action="call_tool",
       tool_name="generate_screen",
       tool_input={"prompt": "<user prompt>", "model": "gemini-2.5-flash"}
   )
   ```

3. Fetch the screen image:
   ```
   mcp_client(
       action="call_tool",
       tool_name="fetch_screen_image",
       tool_input={"screen_id": "<screen_id from step 2>"}
   )
   ```

4. Fetch code in the requested framework:
   ```
   mcp_client(
       action="call_tool",
       tool_name="fetch_screen_code",
       tool_input={"screen_id": "<screen_id>", "framework": "<framework>"}
   )
   ```

5. Always disconnect when done:
   ```
   mcp_client(action="disconnect")
   ```

## Guidelines
- Always disconnect after completing the task, even if errors occur
- Use "gemini-2.5-flash" model for faster generation
- Keep prompts focused on UI elements and layout
- Return the screen_id, image data, and code to the caller
```

#### Usage in Workflow

The agent is invoked directly when the user clicks "Generate UI Mockup":

```python
# haytham/integrations/stitch/generator.py

from haytham.agents.worker_ui_generator import create_ui_generator_agent
from haytham.integrations.stitch.rate_limiter import StitchRateLimiter

async def generate_ui_mockup(
    capability: dict,
    framework: str,
    session_dir: Path
) -> dict:
    """Generate UI mockup using the UI Generator agent."""

    # Check rate limits
    limiter = StitchRateLimiter(session_dir)
    can_generate, message = limiter.can_generate()
    if not can_generate:
        raise RateLimitError(message)

    # Build the prompt for the agent
    prompt = f"""
    Generate a UI mockup for this capability:

    Name: {capability['name']}
    Description: {capability['description']}

    Acceptance Criteria:
    {chr(10).join('- ' + ac for ac in capability.get('acceptance_criteria', [])[:5])}

    After generating, fetch the code in {framework} format.

    Return the screen_id, image data, and generated code.
    """

    # Create and run the agent
    agent = create_ui_generator_agent()
    result = agent(prompt)

    # Record the generation
    limiter.record_generation()

    return {
        "screen_id": result.screen_id,
        "image": result.image_data,
        "code": result.code,
        "framework": framework,
    }
```

This approach lets the agent autonomously:
1. Connect to `stitch.googleapis.com/mcp`
2. Discover available tools via `list_tools`
3. Generate screens and fetch code
4. Handle errors and retries
5. Disconnect when done

#### Phase 2: MVP Specification View Enhancement

Add "Generate UI Mockup" button to capability cards in the MVP Specification view:

```python
# frontend_streamlit/views/mvp_spec.py (enhancement)

from haytham.integrations.stitch import generate_ui_mockup, is_stitch_configured
from haytham.integrations.stitch.cache import get_cached_mockup, cache_mockup

def render_capability_card(capability: dict, session_dir: Path) -> None:
    """Render a capability card with optional Stitch mockup generation."""
    with st.container(border=True):
        st.markdown(f"**{capability['name']}**")
        st.write(capability['description'])

        # Check for cached mockup
        cached = get_cached_mockup(capability['name'], session_dir)
        if cached:
            st.image(cached['image_path'], caption="Generated UI Mockup")
            _render_code_download(cached, capability['name'])
        elif is_stitch_configured():
            # Framework selection
            framework = st.selectbox(
                "Framework",
                ["react", "vue", "flutter", "swiftui"],
                key=f"fw_{capability['name']}"
            )

            # Show generate button
            if st.button(
                "🎨 Generate UI Mockup",
                key=f"gen_mockup_{capability['name']}"
            ):
                _generate_and_display_mockup(capability, framework, session_dir)

def _generate_and_display_mockup(
    capability: dict,
    framework: str,
    session_dir: Path
) -> None:
    """Generate mockup using the UI Generator agent."""
    with st.spinner("Generating UI with Google Stitch..."):
        try:
            # Call the agent-based generator
            result = generate_ui_mockup(
                capability=capability,
                framework=framework,
                session_dir=session_dir
            )

            # Cache for future use
            cache_mockup(
                capability_name=capability['name'],
                result=result,
                session_dir=session_dir
            )

            # Display results
            st.image(result['image'], caption="Generated UI Mockup")
            st.code(result['code'], language=_get_language(framework))

            st.download_button(
                "📥 Download Code",
                result['code'],
                file_name=f"{capability['name']}.{_get_extension(framework)}",
                mime="text/plain"
            )

        except RateLimitError as e:
            st.warning(str(e))
        except Exception as e:
            st.error(f"Failed to generate mockup: {e}")
```

#### Phase 3: Build vs Buy View Enhancement

Add starter code generation for BUILD recommendations:

```python
# frontend_streamlit/views/build_buy.py (enhancement)

from haytham.integrations.stitch import generate_ui_mockup, is_stitch_configured

def render_component_card(component, session_dir: Path) -> None:
    """Render component card with optional Stitch code generation."""
    rec = component.recommendation
    rec_type = rec.recommendation

    with st.container(border=True):
        # ... existing card rendering ...

        # Add Stitch integration for BUILD items
        if rec_type == RecommendationType.BUILD and is_stitch_configured():
            with st.expander("💻 Generate Starter Code"):
                st.caption("Use Google Stitch to generate UI code scaffold")

                framework = st.selectbox(
                    "Framework",
                    ["react", "vue", "flutter", "swiftui"],
                    key=f"framework_{component.story_order}"
                )

                if st.button(
                    "Generate Code",
                    key=f"gen_{component.story_order}"
                ):
                    _generate_starter_code(component, framework, session_dir)

def _generate_starter_code(component, framework: str, session_dir: Path) -> None:
    """Generate and display starter code using the UI Generator agent."""
    with st.spinner(f"Generating {framework} code with Google Stitch..."):
        try:
            # Build capability dict from component
            capability = {
                "name": component.component_name,
                "description": f"{component.story_title}\n\n{component.component_name}",
                "acceptance_criteria": [],
            }

            # Use the same agent-based generator
            result = generate_ui_mockup(
                capability=capability,
                framework=framework,
                session_dir=session_dir
            )

            # Display code
            lang_map = {"react": "tsx", "vue": "vue", "flutter": "dart", "swiftui": "swift"}
            st.code(result['code'], language=lang_map.get(framework, "text"))

            # Download button
            ext_map = {"react": "tsx", "vue": "vue", "flutter": "dart", "swiftui": "swift"}
            st.download_button(
                "📥 Download Code",
                result['code'],
                file_name=f"{component.component_name}.{ext_map.get(framework, 'txt')}",
                mime="text/plain"
            )

        except RateLimitError as e:
            st.warning(str(e))
        except Exception as e:
            st.error(f"Failed to generate code: {e}")
```

---

### Directory Structure

```
haytham/
├── agents/
│   └── worker_ui_generator/
│       ├── __init__.py
│       ├── agent.py                      # Agent with mcp_client tool
│       └── worker_ui_generator_prompt.txt # Agent instructions
├── integrations/
│   └── stitch/
│       ├── __init__.py
│       ├── generator.py       # generate_ui_mockup() function
│       ├── config.py          # is_stitch_configured(), get_limits()
│       ├── rate_limiter.py    # StitchRateLimiter class
│       └── cache.py           # Mockup caching utilities

frontend_streamlit/
└── views/
    ├── mvp_spec.py            # Enhanced with mockup generation
    └── build_buy.py           # Enhanced with code export
```

---

### UI Enhancement

Add mockup preview to Capability Model view:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  📦 CAPABILITY: User Dashboard                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────┐  ┌────────────────────────────────┐ │
│  │ DESCRIPTION                       │  │ UI PREVIEW (Google Stitch)     │ │
│  │                                   │  │                                │ │
│  │ A personalized dashboard showing  │  │  ┌────────────────────────┐   │ │
│  │ user's projects, recent activity, │  │  │ [Header]               │   │ │
│  │ and quick actions.                │  │  │ ┌──────┐ ┌──────────┐  │   │ │
│  │                                   │  │  │ │Stats │ │ Activity │  │   │ │
│  │ Acceptance Criteria:              │  │  │ └──────┘ └──────────┘  │   │ │
│  │ • Show 5 most recent projects     │  │  │ [Projects Grid]        │   │ │
│  │ • Display activity feed           │  │  │ ┌───┐ ┌───┐ ┌───┐     │   │ │
│  │ • Quick action buttons            │  │  │ │   │ │   │ │   │     │   │ │
│  │                                   │  │  └────────────────────────┘   │ │
│  │ 🔧 BUILD | Estimate: M            │  │                                │ │
│  └───────────────────────────────────┘  │  [Get Code ▼]                  │ │
│                                         │  ├─ React                      │ │
│                                         │  ├─ Vue                        │ │
│                                         │  ├─ Flutter                    │ │
│                                         │  └─ SwiftUI                    │ │
│                                         └────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Configuration

#### Platform Deployment (`.env`)

```bash
# Google Stitch Integration
STITCH_ENABLED=true
STITCH_PROJECT_ID=haytham-stitch-prod
GOOGLE_APPLICATION_CREDENTIALS=/secrets/stitch-sa-key.json

# Rate limiting
STITCH_MONTHLY_LIMIT=350
STITCH_PER_SESSION_LIMIT=10
```

#### User Configuration

**None required!** The platform handles all GCP authentication via the shared service account.

#### Feature Flag Check

```python
# haytham/integrations/stitch/config.py

import os
from pathlib import Path

def is_stitch_enabled() -> bool:
    """Check if Stitch integration is enabled and configured."""
    if os.getenv("STITCH_ENABLED", "false").lower() != "true":
        return False

    # Check for service account credentials
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not cred_path or not Path(cred_path).exists():
        return False

    return True

def get_stitch_limits() -> dict:
    """Get rate limit configuration."""
    return {
        "monthly": int(os.getenv("STITCH_MONTHLY_LIMIT", "350")),
        "per_session": int(os.getenv("STITCH_PER_SESSION_LIMIT", "10")),
    }
```

---

## Consequences

### Positive

1. **Visual deliverables** — MVP specs include actual UI mockups
2. **Faster prototyping** — Solo founders get starter code in their preferred framework
3. **Reduced design burden** — AI-generated UI as starting point
4. **Framework flexibility** — Support for React, Vue, Flutter, SwiftUI, and more
5. **Free tier** — 350+ generations/month at no cost
6. **Official API** — Backed by Google, stable endpoint

### Negative

1. **Shared quota** — All users share 350 generations/month limit
2. **Platform cost** — GCP project costs (minimal, but non-zero)
3. **Service account security** — Must securely store and rotate credentials

### Risks

1. **API changes** — Stitch is still in Labs/experimental phase
   - **Mitigation:** Feature flag allows graceful degradation

2. **Quota exhaustion** — Heavy usage could exhaust monthly quota
   - **Mitigation:** Per-session limits (10/session), usage monitoring, upgrade to paid tier if needed

3. **Generation quality** — AI mockups may not match user expectations
   - **Mitigation:** Position as "starting point" not final design

4. **Service account compromise** — Leaked credentials could exhaust quota
   - **Mitigation:** Store in secrets manager, rotate regularly, monitor usage

---

## Rollout Plan

### Phase 0: GCP Setup (One-Time)
1. Create GCP project `haytham-stitch-prod`
2. Enable Stitch MCP API
3. Create service account with appropriate roles
4. Generate and securely store service account key
5. Configure secrets management for deployment

### Phase 1: Foundation
1. Create `haytham/integrations/stitch/` module
2. Implement `StitchClient` using Strands `mcp_client`
3. Add configuration helpers and feature flags
4. Implement rate limiter (per-session + global quota)
5. Implement session-based caching for mockups
6. Add `strands-tools` and `google-auth` to dependencies

### Phase 2: MVP Specification View
1. Add "Generate UI Mockup" button to capability cards
2. Display generated mockups inline
3. Add framework selection dropdown
4. Implement code download functionality
5. Show Stitch status indicator (configured/not configured)

### Phase 3: Build vs Buy View
1. Add "Generate Starter Code" expander for BUILD items
2. Framework selection with code preview
3. Download button for generated code
4. Cache generated code in session directory

### Phase 4: Polish & Documentation
1. Add loading states and error handling
2. Implement retry logic for rate limits
3. Update README with Stitch setup instructions
4. Add troubleshooting guide for GCP auth issues
5. Create example screenshots for documentation

---

## Alternatives Considered

### Alternative A: v0.dev by Vercel

Use Vercel's v0.dev for UI generation instead.

**Rejected because:**
- No official MCP support
- React/Next.js only (less framework flexibility)
- Requires separate account/API key

### Alternative B: Figma AI

Integrate with Figma's AI design features.

**Rejected because:**
- No MCP support
- Design-focused, not code generation
- Requires Figma subscription

### Alternative C: No UI Generation

Skip visual mockups entirely.

**Rejected because:**
- Reduces value of MVP deliverables
- Solo founders benefit from visual starting points
- Stitch is free and officially supported

---

## Dependencies

Add to `pyproject.toml`:

```toml
[project.optional-dependencies]
stitch = [
    "strands-tools>=0.1.0",
    "google-auth>=2.0.0",
]
```

Install with:

```bash
uv sync --extra stitch
```

---

## References

- [Google Stitch](https://stitch.withgoogle.com/)
- [Stitch MCP Documentation](https://stitch.withgoogle.com/docs/mcp/setup/)
- [Google Developers Blog - Introducing Stitch](https://developers.googleblog.com/stitch-a-new-way-to-design-uis/)
- [Strands Agents MCP Client](https://github.com/strands-agents/tools/blob/main/src/strands_tools/mcp_client.py)
- [davideast/stitch-mcp Helper CLI](https://github.com/davideast/stitch-mcp)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [ADR-013: Build vs Buy Recommendations](./ADR-013-build-vs-buy-recommendations.md)
