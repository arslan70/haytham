# Example Outputs

Representative outputs from Haytham runs across three different idea types. These show the format, depth, and quality of analysis you get from each phase.

Each example includes the validation report (Phase 1), MVP scope (Phase 2), and a summary of the OpenSpec output (Phase 4).

| Example | Idea | Type | Verdict | Why |
|---------|------|------|---------|-----|
| [gym-leaderboard](gym-leaderboard/) | Anonymous gym community leaderboard | B2C consumer app | GO (HIGH risk) | Real demand, but cold-start and anonymity constraints are hard |
| [git-changelog-cli](git-changelog-cli/) | AI-powered git changelog generator | Developer tool | GO (MEDIUM risk) | Clear pain point, crowded space but narrow focus wins |
| [invoice-reconciler](invoice-reconciler/) | Auto-matching invoices to POs for SMBs | B2B SaaS | PIVOT | Existing solutions dominate; pivot to niche vertical |

## Want to generate your own?

```
/plugin marketplace add arslan70/haytham
/plugin install haytham@haytham
/haytham "your startup idea here"
```

Output lands in `.haytham/session/`. Takes ~20 minutes with human approval at each phase.
