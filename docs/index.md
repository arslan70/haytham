---
title: Haytham
hide:
  - navigation
  - toc
---

<div class="hero" markdown>

# From startup idea to implementation-ready spec

Haytham validates your idea with real market research, then generates a complete specification any developer or coding agent can execute. If the idea doesn't hold up, it tells you before you waste months building.

<div class="hero-buttons" markdown>

[Get Started](getting-started.md){ .md-button .md-button--primary }
[How It Works](how-it-works.md){ .md-button }

</div>
</div>

---

## Four phases. Four questions. Human decisions at every gate.

<div class="grid cards" markdown>

-   :material-magnify:{ .lg .middle } **Should this be built?**

    ---

    Market research, competitor analysis, and risk scoring produce a GO / NO-GO / PIVOT verdict backed by evidence.

-   :material-target:{ .lg .middle } **What exactly?**

    ---

    MVP scoping with capability mapping. What's in, what's out, core user flows, and success criteria.

-   :material-wrench:{ .lg .middle } **How to build it?**

    ---

    Build-vs-buy analysis and architecture decisions. Each linked to the capabilities it serves.

-   :material-format-list-checks:{ .lg .middle } **What are the tasks?**

    ---

    Ordered user stories with acceptance criteria, dependency ordering, and full traceability. Ready for a developer or coding agent.

</div>

```mermaid
flowchart TD
    idea(("Startup Idea"))

    idea --> P1

    subgraph genesis["Genesis -- What's built today"]
        P1["Should this be built?"] -->|Validation Report| G1{{"Founder Review"}}
        G1 -->|GO| P2["What exactly?"]
        P2 -->|MVP Spec| G2{{"Product Owner"}}
        G2 -->|APPROVED| P3["How to build it?"]
        P3 -->|Architecture| G3{{"Architect Review"}}
        G3 -->|APPROVED| P4["What are the tasks?"]
    end

    G1 -.->|NO-GO| stop(("Stop"))
    P4 -->|Stories| backlog["Implementation-Ready Backlog"]
```

---

## What you get

<div class="grid cards" markdown>

-   :material-gavel: **A verdict**

    ---

    GO, NO-GO, or PIVOT, backed by market research and risk scoring. If risks are high, pivot strategies are generated automatically.

-   :material-package-variant: **A scoped MVP**

    ---

    What's in, what's out, core user flows, and success criteria. Appetite-based scoping keeps the first version focused.

-   :material-sitemap: **A capability model**

    ---

    Functional and non-functional capabilities, each traceable to a user need. The traceability chain runs from idea to story.

-   :material-cog: **Architecture decisions**

    ---

    Build-vs-buy analysis, technology choices, and trade-offs. Each decision linked to the capabilities it serves.

-   :material-format-list-bulleted-square: **Ordered user stories**

    ---

    Acceptance criteria in Gherkin format, dependency ordering, and full traceability. Hand these to a developer or a coding agent.

-   :material-export:{ .lg .middle } **Agent-ready output**

    ---

    Output as [OpenSpec](https://github.com/Fission-AI/OpenSpec). Feed your spec directly to Claude Code or any coding agent.

</div>

---

## Quick start

```
/plugin marketplace add arslan70/haytham
/plugin install haytham@haytham
```

Then run the full workflow:

```
/haytham "your startup idea here"
```

Or run individual phases: `/haytham:validate`, `/haytham:specify`, `/haytham:design`, `/haytham:plan`.

See [Getting Started](getting-started.md) for details.

[View on GitHub :fontawesome-brands-github:](https://github.com/arslan70/haytham){ .md-button }
