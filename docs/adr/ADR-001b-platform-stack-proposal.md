# ADR-001b: Platform & Stack Proposal

**Status**: Proposed
**Date**: 2025-01-02
**Parent**: [ADR-001: Story-to-Implementation Pipeline](./ADR-001-story-to-implementation-pipeline.md)
**Depends On**: [ADR-001a: MVP Spec Enhancement](./ADR-001a-mvp-spec-enhancement.md)
**Scope**: Analyzing requirements and proposing platform/technology choices

---

## POC Simplifications

- **Test Case**: Simple Notes App → Web Application (SPA) with Python + React
- **Default Stack**: Python + React is the default recommendation for POC
- **No Custom Stack**: POC uses predefined stack templates only

**Example for Notes App:**
```
Platform: Web Application (SPA)
Rationale: User authentication, CRUD operations, search - all fit web app well
Stack: Python + React (recommended default)
```

---

## Context

Before stories can be interpreted into technical tasks, a fundamental decision must be made: **what kind of thing are we building?**

The MVP Specification describes *what* the system should do, but not *how* it should be built. The same set of user stories could be implemented as:
- A web application
- A mobile app
- A command-line tool
- An API service
- A desktop application
- A combination of the above

This decision:
1. **Affects all downstream chunks.** Entity schemas, capabilities, task generation all depend on platform
2. **Cannot be automatically determined.** Multiple valid approaches exist for most requirements
3. **Has significant implications.** Wrong choice creates friction; right choice enables velocity
4. **Requires user input.** The user (product authority) must decide

### Constraints

1. **Local Development Only**: All outputs must be locally runnable and testable (no cloud infrastructure)
2. **User Authority**: User makes final platform decision; system only proposes options
3. **Beginner Friendly**: Tech stack should prioritize ease of setup and debugging
4. **MVP Focus**: Choose technologies appropriate for rapid prototyping, not enterprise scale

---

## Decision

Implement a **Platform & Stack Proposal Agent** that:
1. Analyzes the enhanced MVP specification
2. Identifies platform-relevant signals in requirements
3. Generates ranked platform options with trade-offs
4. Proposes technology stacks for each option
5. Presents options to user in impact-oriented terms
6. Records the decision for downstream consumption

---

## Platform Analysis

### Platform Types

| Platform Type | Description | Best For | Local Dev Complexity |
|---------------|-------------|----------|---------------------|
| **Web App (SPA)** | Single-page app with API backend | Interactive UIs, real-time features, broad access | Medium |
| **Web App (MPA)** | Multi-page server-rendered app | Content-heavy, SEO-important, simpler interactions | Low |
| **API Service** | Backend only, no UI | Developer tools, integrations, headless systems | Low |
| **CLI Tool** | Command-line interface | Developer utilities, automation, scripts | Very Low |
| **Desktop App** | Native desktop application | Offline-first, system integration, performance | High |
| **Mobile App** | iOS/Android application | Mobile-first experiences, device features | High |
| **Hybrid** | Multiple platform types | Complex systems with multiple interfaces | Varies |

### Signal Detection

The agent analyzes the MVP spec for signals that suggest platform type:

#### Web App Signals
```yaml
signals:
  strong_indicators:
    - "dashboard" in features
    - "browser" mentioned
    - "responsive" or "mobile-friendly" UI
    - Multiple user roles with different views
    - Real-time updates or notifications
    - Sharing via URL

  moderate_indicators:
    - Visual data presentation (charts, graphs)
    - Form-based workflows
    - User authentication
    - Search functionality

  counter_indicators:
    - "offline-first" requirement
    - Heavy file system access
    - System-level integration (hardware, OS)
```

#### CLI Tool Signals
```yaml
signals:
  strong_indicators:
    - "command" or "terminal" mentioned
    - Developer audience explicitly stated
    - Automation or scripting use case
    - Pipeline or workflow integration
    - No UI/UX notes in spec

  moderate_indicators:
    - Single-user focus
    - File processing tasks
    - Batch operations

  counter_indicators:
    - Multiple user roles
    - Visual dashboards
    - Non-technical users mentioned
```

#### API Service Signals
```yaml
signals:
  strong_indicators:
    - "API" or "endpoint" mentioned
    - "integration" as primary purpose
    - Developer/machine consumers
    - Webhook requirements
    - No UI mentioned

  moderate_indicators:
    - Data transformation focus
    - Third-party integration heavy
    - Headless mentioned

  counter_indicators:
    - End-user UI described
    - Non-technical users
```

#### Mobile App Signals
```yaml
signals:
  strong_indicators:
    - "mobile app" explicitly mentioned
    - Device features (camera, GPS, push notifications)
    - "on-the-go" use cases
    - App store distribution mentioned

  moderate_indicators:
    - Location-based features
    - Offline capability important
    - Touch-first interactions

  counter_indicators:
    - Desktop-focused UI
    - Complex data entry
    - Large screen assumed
```

### Analysis Output

```yaml
# platform_analysis.yaml
analysis_timestamp: "2025-01-02T09:00:00Z"
analyzed_by: "platform-proposal-agent"

# Input summary
input_summary:
  feature_count: 5
  user_roles: ["visitor", "registered_user", "admin"]
  has_ui_requirements: true
  has_realtime_requirements: true
  has_offline_requirements: false
  external_integrations: 2

# Signal detection results
signals_detected:
  web_app:
    score: 0.85
    strong: ["dashboard mentioned", "multiple user roles", "authentication required"]
    moderate: ["form workflows", "data visualization"]
    counter: []

  cli_tool:
    score: 0.15
    strong: []
    moderate: ["single data processing task"]
    counter: ["multiple user roles", "dashboard UI", "non-technical users"]

  api_service:
    score: 0.40
    strong: []
    moderate: ["external integrations"]
    counter: ["end-user UI described"]

  mobile_app:
    score: 0.30
    strong: []
    moderate: ["on-the-go mentioned"]
    counter: ["desktop UI described", "complex forms"]

# Recommendation
primary_recommendation: "web_app_spa"
confidence: "high"
rationale: |
  The MVP spec describes interactive dashboards, multiple user roles,
  and real-time features. These strongly indicate a web application.
  No signals for mobile-specific features or offline requirements.
```

---

## Platform Options Presentation

Options are presented to the user in **impact-oriented terms**, not technical jargon.

### Template

```markdown
## Platform Decision Required

Based on your MVP specification, I've analyzed which type of application best fits your requirements.

### Recommended: Web Application

**What this means for you:**
- Users access your product through a web browser (Chrome, Firefox, Safari, etc.)
- Works on any device with a browser (computers, tablets, phones)
- No app store approval needed; deploy updates instantly
- Users don't need to install anything

**Why this fits your requirements:**
- Your dashboard and visualization features work best in a browser
- Multiple user roles (visitor, member, admin) are easy to manage
- Real-time updates you described are well-supported

**Trade-offs:**
- Requires internet connection to use
- Less access to device features (camera, GPS) than native apps
- Performance slightly lower than native apps for complex animations

---

### Alternative: Mobile App

**What this means for you:**
- Users download from App Store / Google Play
- Dedicated experience optimized for phones
- Can work offline and access device features

**Why you might choose this instead:**
- If your users are primarily on mobile devices
- If offline access is critical
- If you need push notifications or device sensors

**Trade-offs:**
- Two codebases (iOS + Android) or cross-platform complexity
- App store review process (1-7 days for updates)
- Higher development complexity for MVP

---

### Alternative: Command-Line Tool

**What this means for you:**
- Users run commands in a terminal
- Best for developer audiences or automation

**Why this probably isn't right for you:**
- Your spec describes visual dashboards and multiple user types
- Non-technical users would struggle with command-line interface

---

## My Recommendation

I recommend **Web Application** with high confidence based on your requirements.

**Please confirm or select an alternative:**
- [ ] Web Application (Recommended)
- [ ] Mobile App
- [ ] Command-Line Tool
- [ ] Other (please describe)
```

---

## Technology Stack Selection

Once platform is chosen, propose a technology stack optimized for:
1. **Local development ease.** Minimal setup, good debugging
2. **MVP velocity.** Fast iteration, not enterprise scale
3. **Single developer friendly.** Works without DevOps expertise
4. **Well-documented.** User can find help easily

### Stack Options by Platform

#### Web Application (SPA)

**Option A: Python + React (Recommended for most cases)**
```yaml
stack_id: "web-python-react"
name: "Python Backend + React Frontend"

backend:
  language: "Python 3.11+"
  framework: "FastAPI"
  why: "Modern, fast, excellent docs, easy to learn"
  orm: "SQLAlchemy"
  database: "SQLite (dev) / PostgreSQL (prod-ready)"

frontend:
  language: "TypeScript"
  framework: "React 18+"
  bundler: "Vite"
  styling: "Tailwind CSS"
  why: "Largest ecosystem, most resources available"

development:
  package_manager_backend: "uv"
  package_manager_frontend: "npm"
  linter: "ruff (Python), ESLint (TS)"

local_setup:
  steps: 3
  time_estimate: "5-10 minutes"
  prerequisites: ["Python 3.11+", "Node.js 18+"]

pros:
  - "Excellent documentation for both"
  - "Large community, easy to find solutions"
  - "Type safety on both ends"
  - "Hot reload for fast iteration"

cons:
  - "Two languages to work with"
  - "Separate frontend/backend processes"
```

**Option B: Python Full-Stack**
```yaml
stack_id: "web-python-fullstack"
name: "Python Full-Stack (HTMX)"

backend:
  language: "Python 3.11+"
  framework: "FastAPI or Flask"
  orm: "SQLAlchemy"
  database: "SQLite"

frontend:
  approach: "Server-rendered with HTMX"
  templating: "Jinja2"
  interactivity: "HTMX + Alpine.js"
  styling: "Tailwind CSS"

pros:
  - "Single language"
  - "Simpler mental model"
  - "Less JavaScript complexity"

cons:
  - "Less interactive than SPA"
  - "Smaller ecosystem for complex UI"
  - "May need rewrite for highly interactive features"
```

**Option C: JavaScript Full-Stack**
```yaml
stack_id: "web-js-fullstack"
name: "JavaScript Full-Stack (Next.js)"

fullstack:
  language: "TypeScript"
  framework: "Next.js 14+"
  database: "SQLite via Prisma"
  orm: "Prisma"

pros:
  - "Single language everywhere"
  - "Excellent developer experience"
  - "Built-in API routes"

cons:
  - "Heavier framework"
  - "More complex than Python for beginners"
  - "Node.js ecosystem churn"
```

#### CLI Tool

**Option A: Python CLI (Recommended)**
```yaml
stack_id: "cli-python"
name: "Python CLI"

cli:
  language: "Python 3.11+"
  framework: "Click or Typer"
  packaging: "uv"

pros:
  - "Simple and fast to build"
  - "Easy to install via pip/uv"
  - "Rich library ecosystem"

cons:
  - "Requires Python installed"
  - "Startup time slightly slower than compiled"
```

**Option B: Go CLI**
```yaml
stack_id: "cli-go"
name: "Go CLI"

cli:
  language: "Go 1.21+"
  framework: "Cobra"
  distribution: "Single binary"

pros:
  - "Single binary distribution"
  - "Fast startup"
  - "Cross-platform easy"

cons:
  - "Learning curve if unfamiliar with Go"
  - "Smaller library ecosystem than Python"
```

#### API Service

**Option A: Python API (Recommended)**
```yaml
stack_id: "api-python"
name: "Python API Service"

api:
  language: "Python 3.11+"
  framework: "FastAPI"
  database: "SQLite or PostgreSQL"
  orm: "SQLAlchemy"
  docs: "Auto-generated OpenAPI"

pros:
  - "Automatic API documentation"
  - "Type validation built-in"
  - "Async support"
```

---

## Stack Presentation to User

```markdown
## Technology Stack Decision

You've chosen **Web Application**. Now let's pick the technologies to build it with.

### Recommended: Python + React

**What this means for you:**
- Backend (server logic) written in Python, readable and well-documented
- Frontend (what users see) written in React, the most popular UI framework
- Works on your computer without any cloud services

**Setup time:** ~10 minutes
**Learning resources:** Abundant (most popular combination)

---

### Alternative: Python Full-Stack (Simpler)

**What this means for you:**
- Everything in Python, one language to learn
- Simpler architecture, but less interactive UI
- Good for: content-heavy sites, simpler interactions

**Choose this if:** You want to minimize complexity and don't need highly interactive UI

---

### Alternative: JavaScript Full-Stack (Next.js)

**What this means for you:**
- Everything in JavaScript/TypeScript
- Modern framework with lots of built-in features
- Good for: Complex interactive UIs, real-time features

**Choose this if:** You're comfortable with JavaScript and want modern tooling

---

## My Recommendation

I recommend **Python + React** because:
- Best documentation and community support
- Good balance of simplicity and capability
- Matches your requirements without over-engineering

**Please confirm or select an alternative:**
- [ ] Python + React (Recommended)
- [ ] Python Full-Stack (HTMX)
- [ ] JavaScript Full-Stack (Next.js)
- [ ] Other (please describe)
```

---

## Output Schema

The platform decision is recorded for downstream consumption:

```yaml
# Stored in state.json (stack property)
schema_version: "1.0"
decided_at: "2025-01-02T09:30:00Z"
decided_by: "chunk-1-platform-stack"
approved_by: "user"

# Analysis reference
analysis:
  signals_detected: { ... }  # From analysis phase
  confidence: "high"
  alternatives_considered: ["mobile_app", "cli_tool"]

# Platform decision
platform:
  type: "web_application"
  subtype: "spa"  # single-page-app
  rationale: "Interactive dashboards, multiple user roles, real-time features"

# Stack decision
stack:
  id: "web-python-react"
  name: "Python Backend + React Frontend"

  backend:
    language: "python"
    language_version: "3.11+"
    framework: "fastapi"
    framework_version: "0.100+"
    orm: "sqlalchemy"
    database: "sqlite"
    database_note: "SQLite for MVP, PostgreSQL-compatible for future"

  frontend:
    language: "typescript"
    language_version: "5.0+"
    framework: "react"
    framework_version: "18+"
    bundler: "vite"
    styling: "tailwindcss"

  testing:
    backend: "pytest"
    frontend: "vitest"
    e2e: "playwright"

  development:
    package_manager_backend: "uv"
    package_manager_frontend: "npm"
    linter_backend: "ruff"
    linter_frontend: "eslint"
    formatter_backend: "ruff"
    formatter_frontend: "prettier"

# Constraints derived from choices (stored as properties, not separate IDs)
derived_constraints:
  - "Python 3.11+ required"
  - "Node.js 18+ required for frontend"
  - "SQLite database (single file, no server)"

# Project structure template
project_structure:
  root: "/"
  backend_dir: "backend/"
  frontend_dir: "frontend/"
  shared_types: "shared/"
  documentation: "docs/"
```

---

## Agent Design

### Platform Proposal Agent

```python
class PlatformProposalAgent:
    """Analyzes MVP spec and proposes platform/stack options."""

    def analyze(self, mvp_spec: EnhancedMVPSpec) -> PlatformAnalysis:
        """Analyze MVP spec for platform signals."""

        signals = {
            "web_app": self._detect_web_signals(mvp_spec),
            "mobile_app": self._detect_mobile_signals(mvp_spec),
            "cli_tool": self._detect_cli_signals(mvp_spec),
            "api_service": self._detect_api_signals(mvp_spec),
            "desktop_app": self._detect_desktop_signals(mvp_spec),
        }

        # Score and rank
        ranked = self._rank_platforms(signals)

        return PlatformAnalysis(
            signals=signals,
            ranked_options=ranked,
            primary_recommendation=ranked[0],
            confidence=self._calculate_confidence(ranked)
        )

    def generate_proposal(
        self,
        analysis: PlatformAnalysis,
        user_constraints: List[str]
    ) -> PlatformProposal:
        """Generate user-facing proposal with options."""

        options = []
        for platform in analysis.ranked_options[:3]:  # Top 3
            stacks = self._get_stack_options(platform, user_constraints)
            options.append(PlatformOption(
                platform=platform,
                stacks=stacks,
                user_impact=self._describe_user_impact(platform),
                trade_offs=self._describe_trade_offs(platform),
                recommended=platform == analysis.primary_recommendation
            ))

        return PlatformProposal(
            options=options,
            recommendation=analysis.primary_recommendation,
            confidence=analysis.confidence,
            presentation=self._format_for_user(options)
        )

    def record_decision(
        self,
        proposal: PlatformProposal,
        user_choice: UserChoice
    ) -> StackDecision:
        """Record the user's platform and stack decision."""

        return StackDecision(
            platform=user_choice.platform,
            stack=user_choice.stack,
            decided_at=now(),
            approved_by="user",
            analysis_ref=proposal.analysis,
            derived_constraints=self._derive_constraints(user_choice)
        )
```

---

## Consequences

### Positive

1. **Informed Decision**: User understands trade-offs before committing
2. **Appropriate Technology**: Stack matches requirements, not over-engineered
3. **Local-First**: All recommendations prioritize local development
4. **Downstream Clarity**: System state records exact versions and structure

### Negative

1. **Limited Options**: Cannot cover every possible technology
2. **Opinionated**: Recommendations reflect specific preferences
3. **May Miss Nuance**: Signal detection is heuristic, not perfect

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Wrong recommendation | Low | High | User can override; alternatives presented |
| Stack becomes outdated | Medium | Low | Version ranges, not exact versions |
| User unfamiliar with stack | Medium | Medium | Prioritize well-documented options |

---

## Resolved Questions (POC)

1. **Custom Stack Support**: ~~Allow custom stacks?~~ → **No.** User picks from predefined options only. Custom stacks add complexity.

2. **Stack Validation**: ~~Validate stack can implement features?~~ → **No.** Trust user's choice. If issues arise during implementation, surface then.

3. **Migration Path**: ~~Handle platform change later?~~ → **Re-run from scratch.** No migration support. Start over if different platform needed.

4. **Hybrid Platforms**: ~~Handle web + mobile?~~ → **Not supported.** Single platform only for POC. Pick one for MVP.

---

## Future Enhancements

- Custom stack specification
- Stack validation against MVP features
- Platform migration tooling
- Multi-platform support (web + mobile + API)
- Stack recommendation learning from successful projects

---

## Next Steps

Upon approval:

1. Implement signal detection logic
2. Define complete stack templates for each platform type
3. Create user-facing presentation templates
4. Integrate with system state initialization
5. Proceed to ADR-001d (Story Interpretation Engine)

---

## Related Documents

- [ADR-001: Story-to-Implementation Pipeline](./ADR-001-story-to-implementation-pipeline.md) (parent)
- [ADR-001a: MVP Spec Enhancement](./ADR-001a-mvp-spec-enhancement.md) (input)
- [ADR-001c: System State Model](./ADR-001c-system-state-model.md) (output destination)
