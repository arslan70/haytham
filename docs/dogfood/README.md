# Dogfooding: Haytham Specs Itself

Haytham validates startup ideas and generates implementation specs. Haytham *is* a startup idea. We run it on itself to generate stories for the next version.

## What's Here

```
docs/dogfood/
  haytham-idea-statement.md          # The input fed to Haytham
  session-v1/
    phase-1-validation/              # Raw validation output
    phase-2-specification/           # Raw MVP scope + capabilities
    phase-3-design/                  # Raw build/buy + architecture
    phase-4-stories/                 # Raw stories
    annotations.md                   # Team commentary on outputs
```

## Why This Exists

1. **Proof by construction.** "Our system is good enough to specify its own next version" is a stronger claim than any benchmark.
2. **Contributor onboarding.** New contributors get a ready-made backlog of traced, scoped stories instead of vague "help wanted" labels.
3. **Transparent roadmap.** The community can see exactly what the system thinks its own gaps are.
4. **Recursive improvement.** Each release cycle, we re-run Haytham on itself and publish the diff.

## How to Contribute

1. Browse the [dogfood backlog](https://github.com/arslan70/haytham/labels/dogfood-v1)
2. Pick a story that interests you
3. Each story includes capability references, architecture decisions, and acceptance criteria
4. Follow the [Contributing Guide](../../CONTRIBUTING.md) for setup and PR workflow

## Session History

| Cycle | Status | Notes |
|-------|--------|-------|
| v1 | Planned | First dogfood run on Haytham's own idea statement |
