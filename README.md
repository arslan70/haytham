# Haytham

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**AI can build your app in minutes. Haytham builds your product for years.**

Lovable, Bolt, and v0 build apps. Haytham builds products: validated, specified, traceable, and evolvable. Run one command inside Claude Code. Get market research, a GO/NO-GO verdict, MVP scope, architecture decisions, an implementation-ready [OpenSpec](https://github.com/Fission-AI/OpenSpec), and a working system. Every requirement traces to a capability. Every capability traces to a validated need.

<p align="center">
  <img src="docs/images/yes-machine-problem.png" alt="The Yes-Machine Problem: AI that builds without validating" width="500"/>
</p>

## Install

```
/plugin marketplace add arslan70/haytham
/plugin install haytham@haytham
```

No Python. No API keys. No environment variables. Works with your existing Claude Code subscription.

## Try it

```
/haytham "a gym community leaderboard with anonymous handles"
```

Takes ~20 minutes. You'll be asked for approval at each phase boundary. You can stop, correct, or redirect at any point.

## What you get

Four phases, each answering one question. You approve before each phase advances.

```
Phase 1: Should this be built?
  → Market research, competitor analysis, risk scoring
  → GO / NO-GO / PIVOT verdict backed by evidence
  → If it says NO-GO, it tells you why. That's the point.

Phase 2: What exactly?
  → MVP scope with clear in/out boundaries
  → Capability model with full traceability
  → System traits (auth, payments, real-time, etc.)

Phase 3: How to build it?
  → Build-vs-buy analysis per capability
  → Architecture decisions linked to capabilities
  → Cost and effort estimates

Phase 4: What are the specs?
  → OpenSpec with SHALL requirements
  → Gherkin scenarios for acceptance testing
  → Ready to hand to Claude Code or any coding agent
```

Every requirement traces to a capability. Every capability traces to a validated need. Every decision traces to the capabilities it serves.

## See example output

The [`examples/`](examples/) directory contains complete outputs from real Haytham runs across different idea types:

| Example | Type | Verdict |
|---------|------|---------|
| [Gym Leaderboard](examples/gym-leaderboard/) | B2C consumer app | GO (high risk) |
| [Git Changelog CLI](examples/git-changelog-cli/) | Developer tool | GO |
| [Invoice Reconciler](examples/invoice-reconciler/) | B2B SaaS | PIVOT |

Each example shows the full output tree: validation report, MVP scope, architecture decisions, and OpenSpec.

## Output structure

All output lives in `.haytham/session/`:

```
.haytham/session/
├── phase-1-why/
│   ├── idea-analysis.md          # Problem analysis, segments, UVP
│   ├── concept-anchor.json       # Invariants that prevent idea drift
│   ├── market-research.md        # TAM/SAM/SOM, trends, risks
│   ├── competitor-research.md    # Who else is doing this
│   ├── research-brief.md         # Neutral summary (no scores)
│   └── validation-report.md      # GO/NO-GO/PIVOT with evidence
├── phase-2-what/
│   ├── mvp-scope.md              # What's in, what's out, core flows
│   ├── capabilities.json         # Functional + non-functional capabilities
│   └── system-traits.json        # Auth, deployment, data layer, etc.
├── phase-3-how/
│   ├── build-buy.json            # BUILD/BUY/HYBRID per capability
│   ├── architecture-decisions.json
│   └── research-directives.json  # What to investigate before coding
└── phase-4-specs/
    └── openspec/
        ├── config.yaml
        ├── project.md
        └── specs/
            ├── domain-name/spec.md
            └── cross-cutting/spec.md
```

## How it works

Eight specialist agents across four phases. Market research agents run web searches. The report synthesizer weighs evidence and produces an honest verdict. If risks are high, it says so. If the idea doesn't hold up, it recommends NO-GO.

Concept anchors (extracted in Phase 1) are passed unchanged to every downstream agent, preventing the "telephone game" where your specific idea gets genericized into something bland.

Read more: [How It Works](https://arslan70.github.io/haytham/how-it-works/) | [System Evolution](https://arslan70.github.io/haytham/system-evolution/)

## Run individual phases

```
/haytham:validate "your idea"    # Phase 1: Should this be built?
/haytham:specify                 # Phase 2: What exactly?
/haytham:design                  # Phase 3: How to build it?
/haytham:plan                    # Phase 4: What are the specs?
```

## Share your experience

Tried Haytham? We want to hear about it.

- [Share your run](https://github.com/arslan70/haytham/discussions) on GitHub Discussions
- [Report a bug](https://github.com/arslan70/haytham/issues)
- [Read the blog](https://arslan70.github.io/haytham/blog/) for design decisions and lessons learned

## Documentation

- [Getting Started](https://arslan70.github.io/haytham/getting-started/)
- [How It Works](https://arslan70.github.io/haytham/how-it-works/)
- [OpenSpec Output](https://arslan70.github.io/haytham/openspec-output/)
- [System Evolution](https://arslan70.github.io/haytham/system-evolution/)
- [Blog](https://arslan70.github.io/haytham/blog/)

## License

[MIT License](LICENSE)
