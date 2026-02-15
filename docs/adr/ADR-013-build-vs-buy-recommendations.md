# ADR-013: Build vs. Buy Recommendations for Technical Components

## Status
**Proposed** — 2026-01-19

## Context

### Current State

The MVP specification and story generation workflows produce technical recommendations, but they lack explicit "build vs. buy" guidance:

```json
{
  "title": "Authentication Foundation",
  "description": "Implement user authentication system with JWT tokens and secure password handling",
  "acceptance_criteria": [
    "Password hashing implemented with bcrypt",
    "JWT access token generation",
    "Token validation middleware"
  ]
}
```

### The Problem

**Solo founders waste time building commodity components.** The current output implies everything should be built from scratch:

| Component in Stories | Build Recommendation | Better Option |
|---------------------|---------------------|---------------|
| Authentication | "Implement JWT auth" | Use Auth0, Clerk, Supabase Auth |
| Payment Processing | "Create payment entity" | Use Stripe, Paddle |
| Email Sending | "Implement email service" | Use SendGrid, Resend, Postmark |
| File Storage | "Create file upload handler" | Use S3, Cloudflare R2 |
| Search | "Implement search indexing" | Use Algolia, Typesense, Meilisearch |

### Dogfood Evidence

The Haytham stories included:
- "Authentication Foundation" — 4-8 hours of custom auth
- "Data Anonymization Service" — 4-8 hours of custom encryption
- "AI Agent Performance Monitoring" — Custom observability

A solo founder following these literally would spend weeks on solved problems instead of using:
- **Auth:** Clerk (15 minutes to integrate)
- **Data Privacy:** AWS Macie, or built-in DB encryption
- **Monitoring:** Langfuse, Helicone (already referenced in codebase)

### User Impact

| Scenario | Without Build/Buy Guidance | With Build/Buy Guidance |
|----------|---------------------------|------------------------|
| Auth setup | 2 days building JWT flow | 2 hours integrating Clerk |
| Payment | 1 week custom Stripe integration | 4 hours using Stripe Checkout |
| Total MVP | 4-6 weeks | 2-3 weeks |
| Technical debt | High (custom security code) | Low (maintained by vendors) |

---

## Decision

### Add Build vs. Buy Analysis to Technical Components

We will enhance the capability model and story generation stages to include explicit build/buy recommendations for each technical component.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    BUILD VS. BUY ANALYSIS FLOW                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Capability Model                                                           │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐  │
│  │ Technical       │────▶│ Build/Buy        │────▶│ Recommendation      │  │
│  │ Capability      │     │ Analyzer Agent   │     │ + Alternatives      │  │
│  └─────────────────┘     └──────────────────┘     └─────────────────────┘  │
│                                   │                                         │
│                                   ▼                                         │
│                          ┌──────────────────┐                               │
│                          │ Decision Matrix  │                               │
│                          ├──────────────────┤                               │
│                          │ • Complexity     │                               │
│                          │ • Time to build  │                               │
│                          │ • Maintenance    │                               │
│                          │ • Cost at scale  │                               │
│                          │ • Lock-in risk   │                               │
│                          │ • Differentiation│                               │
│                          └──────────────────┘                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Recommendation Categories

#### Category 1: BUY (Use Existing Service)

**Criteria:**
- Commodity problem with mature solutions
- Security-critical (auth, payments, encryption)
- Not a differentiator for the product
- High maintenance burden if built

**Output Format:**
```json
{
  "component": "User Authentication",
  "recommendation": "BUY",
  "confidence": "high",
  "rationale": "Authentication is security-critical and commoditized. Building custom auth increases security risk and maintenance burden.",
  "suggested_services": [
    {
      "name": "Clerk",
      "tier": "recommended",
      "why": "Best DX, React components, generous free tier",
      "pricing": "Free up to 10k MAU, then $0.02/MAU",
      "integration_effort": "2-4 hours"
    },
    {
      "name": "Auth0",
      "tier": "alternative",
      "why": "Enterprise features, extensive integrations",
      "pricing": "Free up to 7k MAU",
      "integration_effort": "4-8 hours"
    },
    {
      "name": "Supabase Auth",
      "tier": "alternative",
      "why": "Good if already using Supabase for DB",
      "pricing": "Free tier included with Supabase",
      "integration_effort": "2-4 hours"
    }
  ],
  "if_you_must_build": "Only build custom auth if you have regulatory requirements that prohibit third-party auth providers, or if auth IS your product."
}
```

#### Category 2: BUILD (Custom Implementation)

**Criteria:**
- Core differentiator of the product
- Unique business logic
- No suitable existing solutions
- Competitive advantage from custom implementation

**Output Format:**
```json
{
  "component": "AI Validation Agent Orchestration",
  "recommendation": "BUILD",
  "confidence": "high",
  "rationale": "Multi-agent orchestration with custom validation logic is the core differentiator. No off-the-shelf solution matches the specific workflow requirements.",
  "build_guidance": {
    "suggested_approach": "Use Strands SDK for agent abstraction, implement custom orchestration layer",
    "key_decisions": [
      "Sequential vs parallel agent execution",
      "State management between agents",
      "Error handling and retry logic"
    ],
    "estimated_effort": "L (1-2 days)",
    "risks": ["Agent coordination complexity", "LLM latency accumulation"]
  },
  "partial_buy_options": [
    {
      "component": "LLM API calls",
      "service": "AWS Bedrock / Anthropic API",
      "why": "Don't build your own LLM"
    },
    {
      "component": "Observability",
      "service": "Langfuse",
      "why": "Agent tracing is complex to build"
    }
  ]
}
```

#### Category 3: HYBRID (Buy Foundation, Build Customization)

**Criteria:**
- Standard foundation with custom business logic
- Integration layer needed
- Some differentiation but not core

**Output Format:**
```json
{
  "component": "Market Intelligence Data Pipeline",
  "recommendation": "HYBRID",
  "confidence": "medium",
  "rationale": "Market data sourcing is commoditized, but the analysis and synthesis is custom to our validation workflow.",
  "buy_components": [
    {
      "what": "Web search API",
      "service": "Tavily / SerpAPI",
      "why": "Don't scrape search engines yourself"
    },
    {
      "what": "Company data",
      "service": "Crunchbase API / PitchBook",
      "why": "Authoritative startup/company data"
    }
  ],
  "build_components": [
    {
      "what": "Analysis synthesis",
      "why": "Custom prompt engineering for our validation framework"
    },
    {
      "what": "Caching layer",
      "why": "Cost optimization for repeated queries"
    }
  ],
  "integration_effort": "M (4-8 hours)"
}
```

---

### Decision Matrix

Each component is scored on six dimensions:

| Dimension | Score 1 (Build) | Score 5 (Buy) |
|-----------|-----------------|---------------|
| **Complexity** | Simple, well-understood | Complex, security-critical |
| **Time to Build** | Hours | Weeks |
| **Maintenance** | Minimal ongoing | Constant updates needed |
| **Cost at Scale** | Expensive services | Cheap/free tiers |
| **Lock-in Risk** | Low switching cost | High switching cost |
| **Differentiation** | Core to product | Commodity |

**Scoring Algorithm:**
```python
def compute_recommendation(scores: dict) -> str:
    """
    Compute build/buy recommendation from dimension scores.

    Higher scores favor buying, lower scores favor building.
    """
    # Weights reflect importance for solo founders
    weights = {
        "complexity": 1.5,      # Security complexity matters most
        "time_to_build": 1.3,   # Time is precious for solos
        "maintenance": 1.2,     # Ongoing burden is costly
        "cost_at_scale": 0.8,   # Less important early
        "lock_in_risk": 0.7,    # Acceptable tradeoff
        "differentiation": 1.5, # Don't outsource your moat
    }

    weighted_score = sum(
        scores[dim] * weights[dim]
        for dim in scores
    ) / sum(weights.values())

    if weighted_score >= 3.5:
        return "BUY"
    elif weighted_score <= 2.0:
        return "BUILD"
    else:
        return "HYBRID"
```

---

### Component Categories Reference

Pre-classified components to guide the analyzer:

#### Almost Always BUY

| Component | Recommended Services |
|-----------|---------------------|
| Authentication | Clerk, Auth0, Supabase Auth |
| Payments | Stripe, Paddle, LemonSqueezy |
| Email (transactional) | Resend, SendGrid, Postmark |
| Email (marketing) | ConvertKit, Mailchimp |
| File Storage | S3, Cloudflare R2, Uploadthing |
| Error Tracking | Sentry, Highlight |
| Analytics | PostHog, Mixpanel, Amplitude |
| Feature Flags | LaunchDarkly, Statsig, PostHog |
| Cron Jobs | Trigger.dev, Inngest |
| Database | Supabase, PlanetScale, Neon |

#### Usually BUILD

| Component | Why Build |
|-----------|-----------|
| Core business logic | Your differentiator |
| Domain-specific algorithms | No generic solution |
| Custom UI/UX | User experience is competitive advantage |
| Data models | Specific to your domain |
| API design | Reflects your product's structure |

#### Context-Dependent (HYBRID)

| Component | Buy If... | Build If... |
|-----------|-----------|-------------|
| Search | Simple full-text | Complex domain-specific ranking |
| Notifications | Basic alerts | Complex routing/preferences |
| Admin Dashboard | CRUD operations | Deep product integration |
| AI/ML | Using standard models | Custom fine-tuning needed |
| Integrations | Standard OAuth apps | Deep bi-directional sync |

---

### Enhanced Capability Model Schema

```json
{
  "capabilities": {
    "functional": [
      {
        "name": "User Authentication",
        "description": "...",
        "build_buy": {
          "recommendation": "BUY",
          "confidence": "high",
          "services": ["Clerk", "Auth0"],
          "rationale": "Security-critical commodity",
          "integration_stories": ["STORY-003"]
        }
      }
    ],
    "non_functional": [
      {
        "name": "AI Accuracy Monitoring",
        "description": "...",
        "build_buy": {
          "recommendation": "BUY",
          "confidence": "high",
          "services": ["Langfuse", "Helicone"],
          "rationale": "Complex observability, free tiers available"
        }
      }
    ]
  },
  "build_buy_summary": {
    "buy_count": 5,
    "build_count": 8,
    "hybrid_count": 2,
    "estimated_integration_time": "12-20 hours",
    "estimated_monthly_cost": "$50-150 at MVP scale"
  }
}
```

---

### Enhanced Story Format

Stories for "BUY" components become integration stories:

**Before (Build):**
```json
{
  "title": "Authentication Foundation",
  "description": "Implement user authentication system with JWT tokens and secure password handling",
  "acceptance_criteria": [
    "Password hashing implemented with bcrypt",
    "JWT access token generation and validation",
    "Secure session management"
  ],
  "estimate": "M (4-8h)"
}
```

**After (Buy with Clerk):**
```json
{
  "title": "Integrate Clerk Authentication",
  "description": "Set up Clerk for user authentication with social login and email/password",
  "acceptance_criteria": [
    "Clerk project created and configured",
    "ClerkProvider wrapped around app",
    "Sign-in and sign-up pages functional",
    "Protected routes check authentication state",
    "User object accessible in authenticated components"
  ],
  "estimate": "S (2-4h)",
  "build_buy": {
    "type": "BUY",
    "service": "Clerk",
    "documentation": "https://clerk.com/docs",
    "pricing_note": "Free up to 10k MAU"
  }
}
```

---

### User Interface

#### Capability Model View Enhancement

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  📦 CAPABILITY MODEL                                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  BUILD VS. BUY SUMMARY                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  🔧 BUILD     ████████████████░░░░░░  8 components                  │   │
│  │  🛒 BUY       ██████████░░░░░░░░░░░░  5 components                  │   │
│  │  🔀 HYBRID    ████░░░░░░░░░░░░░░░░░░  2 components                  │   │
│  │                                                                     │   │
│  │  Estimated monthly cost: $50-150 (at MVP scale)                     │   │
│  │  Time saved by buying: ~40-60 hours                                 │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  CAPABILITIES                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │ 🛒 User Authentication                              BUY     │   │   │
│  │  │    Recommended: Clerk                                       │   │   │
│  │  │    Integration: 2-4h | Cost: Free to 10k MAU                │   │   │
│  │  │    [View Details] [Integration Guide]                       │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                     │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │ 🔧 AI Validation Agent                              BUILD   │   │   │
│  │  │    Core differentiator - custom implementation              │   │   │
│  │  │    Estimate: L (8-16h)                                      │   │   │
│  │  │    [View Details]                                           │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                     │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │ 🔀 Market Data Pipeline                            HYBRID   │   │   │
│  │  │    Buy: Tavily API for search                               │   │   │
│  │  │    Build: Analysis synthesis layer                          │   │   │
│  │  │    [View Details]                                           │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Integration Guide Modal

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🛒 INTEGRATION GUIDE: Clerk Authentication                         [×]    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  WHY CLERK?                                                                 │
│  • Best-in-class developer experience                                       │
│  • Pre-built React components                                               │
│  • Handles security best practices                                          │
│  • Generous free tier (10k MAU)                                             │
│                                                                             │
│  QUICK START                                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  1. npm install @clerk/nextjs                                       │   │
│  │  2. Add CLERK_SECRET_KEY to .env                                    │   │
│  │  3. Wrap app with <ClerkProvider>                                   │   │
│  │  4. Add <SignIn /> and <SignUp /> components                        │   │
│  │  5. Use useAuth() hook for protected routes                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ALTERNATIVES                                                               │
│  • Auth0 - Better for enterprise requirements                               │
│  • Supabase Auth - Good if using Supabase for DB                            │
│  • NextAuth - Open source, more control, more work                          │
│                                                                             │
│  [📄 Full Docs]  [💻 Example Code]  [🎥 Video Tutorial]                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Implementation

#### Directory Structure

```
haytham/
├── agents/
│   └── worker_build_buy_analyzer/
│       ├── __init__.py
│       ├── build_buy_analyzer_prompt.txt
│       └── service_catalog.yaml      # Pre-classified services
├── workflow/
│   └── build_buy/
│       ├── __init__.py
│       ├── models.py                 # BuildBuyRecommendation, etc.
│       ├── analyzer.py               # Analysis logic
│       ├── catalog.py                # Service catalog loader
│       └── story_transformer.py      # Transform stories based on recommendations
```

#### Service Catalog

```yaml
# haytham/agents/worker_build_buy_analyzer/service_catalog.yaml

categories:
  authentication:
    default_recommendation: BUY
    services:
      - name: Clerk
        tier: recommended
        pricing: "Free up to 10k MAU, then $0.02/MAU"
        integration_effort: "2-4 hours"
        docs: "https://clerk.com/docs"
        best_for: "React/Next.js apps, best DX"
      - name: Auth0
        tier: alternative
        pricing: "Free up to 7k MAU"
        integration_effort: "4-8 hours"
        docs: "https://auth0.com/docs"
        best_for: "Enterprise features, extensive integrations"
      - name: Supabase Auth
        tier: alternative
        pricing: "Included with Supabase"
        integration_effort: "2-4 hours"
        docs: "https://supabase.com/docs/guides/auth"
        best_for: "Already using Supabase"

  payments:
    default_recommendation: BUY
    services:
      - name: Stripe
        tier: recommended
        pricing: "2.9% + $0.30 per transaction"
        integration_effort: "4-8 hours"
        docs: "https://stripe.com/docs"
        best_for: "Most use cases, best ecosystem"
      - name: LemonSqueezy
        tier: alternative
        pricing: "5% + $0.50 per transaction"
        integration_effort: "2-4 hours"
        docs: "https://docs.lemonsqueezy.com"
        best_for: "Digital products, handles tax"

  llm_observability:
    default_recommendation: BUY
    services:
      - name: Langfuse
        tier: recommended
        pricing: "Free tier, then usage-based"
        integration_effort: "1-2 hours"
        docs: "https://langfuse.com/docs"
        best_for: "Open source, self-hostable"
      - name: Helicone
        tier: alternative
        pricing: "Free tier available"
        integration_effort: "1 hour"
        docs: "https://docs.helicone.ai"
        best_for: "Simple proxy-based integration"

  # ... more categories
```

---

### Integration with Existing Workflow

#### Capability Model Stage Enhancement

```python
# In capability_model stage

def generate_capability_model(validation_summary, mvp_scope):
    # Existing capability generation
    capabilities = generate_capabilities(validation_summary, mvp_scope)

    # NEW: Analyze build vs buy for each capability
    for capability in capabilities:
        build_buy = analyze_build_buy(capability)
        capability["build_buy"] = build_buy

    # NEW: Generate summary
    summary = generate_build_buy_summary(capabilities)

    return {
        "capabilities": capabilities,
        "build_buy_summary": summary
    }
```

#### Story Generation Stage Enhancement

```python
# In story_generation stage

def generate_stories(capabilities):
    stories = []

    for capability in capabilities:
        if capability["build_buy"]["recommendation"] == "BUY":
            # Generate integration story instead of build story
            story = generate_integration_story(capability)
        elif capability["build_buy"]["recommendation"] == "HYBRID":
            # Generate both integration and build stories
            stories.extend(generate_hybrid_stories(capability))
        else:
            # Standard build story
            story = generate_build_story(capability)

        stories.append(story)

    return stories
```

---

### Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| Recommendation accuracy | >80% agreement with expert review | Manual audit of 50 outputs |
| Time savings | >30% reduction in MVP timeline | User survey |
| User trust | >70% follow recommendations | Post-project survey |
| Service coverage | >90% of common components covered | Catalog completeness |

---

### Rollout Plan

#### Phase 1: Service Catalog (Week 1)
1. Build service catalog YAML with top 20 categories
2. Implement catalog loader
3. Create `BuildBuyRecommendation` model

#### Phase 2: Analyzer Agent (Week 2)
1. Create build/buy analyzer agent prompt
2. Implement decision matrix scoring
3. Integrate with capability model stage

#### Phase 3: Story Transformation (Week 3)
1. Transform stories based on recommendations
2. Add integration guides to UI
3. Update exports to include build/buy data

#### Phase 4: Catalog Expansion (Ongoing)
1. Add more service categories
2. Update pricing and recommendations
3. Add user feedback loop

---

## Consequences

### Positive

1. **Faster MVPs** — Solo founders ship in weeks, not months
2. **Lower risk** — Security-critical components handled by experts
3. **Reduced maintenance** — Less custom code to maintain
4. **Better cost visibility** — Monthly costs estimated upfront
5. **Actionable guidance** — Not just "what to build" but "how to build"

### Negative

1. **Catalog maintenance** — Services change, pricing updates
2. **Opinionated** — May not match all preferences
3. **Vendor dependency** — Recommendations create lock-in

### Risks

1. **Stale recommendations** — Services change rapidly
   - **Mitigation:** Quarterly catalog review, user feedback loop

2. **Over-reliance** — Users may not evaluate alternatives
   - **Mitigation:** Always show alternatives, explain tradeoffs

3. **Context blindness** — AI doesn't know user's existing stack
   - **Mitigation:** Add "existing tech stack" input field

---

## Alternatives Considered

### Alternative A: Manual Curation Only

Maintain a static "recommended stack" document.

**Rejected because:**
- Doesn't adapt to specific project needs
- No integration with story generation
- Quickly becomes outdated

### Alternative B: User Self-Service Research

Point users to comparison sites (G2, Capterra).

**Rejected because:**
- Adds friction to workflow
- Users still don't know what's relevant to their project
- Our value is reducing research burden

### Alternative C: Full Integration Automation

Auto-generate integration code, not just recommendations.

**Rejected because:**
- Massive scope increase
- Each service has different integration patterns
- Better handled by service-specific docs/SDKs

---

## References

- [ADR-010: Stories Export](./ADR-010-stories-export.md)
- [ADR-011: Story Effort Estimation](./ADR-011-story-effort-estimation.md)
- [ADR-012: Visual Roadmap](./ADR-012-visual-roadmap.md)
- [Clerk Documentation](https://clerk.com/docs)
- [Stripe Documentation](https://stripe.com/docs)
- [Langfuse Documentation](https://langfuse.com/docs)
