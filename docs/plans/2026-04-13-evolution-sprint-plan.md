# Evolution Sprint Plan: Idea to Pitch-Ready Product

**Date:** 2026-04-13
**Goal:** Take Haytham from "working Genesis plugin + two live projects" to "demonstrable Evolution capability with evidence that the reasoning graph produces better change outcomes than specs alone."
**Timebox:** 8 weeks
**Test projects:** TinyTales (tinytales.pk), GiftKaro (giftkaro-pk.vercel.app)

---

## The Pitch You're Building Toward

> "I ran a real change request through two paths: Claude Code with just the codebase, and Haytham Evolution with the full reasoning graph. Here's what happened."

That's the demo. Everything in this plan works backward from making that sentence true and compelling.

---

## Week 1-2: Prove the Thesis (one change, manual, measured)

**Goal:** Answer the core question manually before building any infrastructure. Does the reasoning graph produce better change outcomes?

### Week 1: Baseline Measurement

Pick one real change request for TinyTales or GiftKaro. Something non-trivial but bounded. Examples:
- "Add story sharing via WhatsApp link" (TinyTales)
- "Add gift tracking dashboard for senders" (GiftKaro)

Run it through two paths:

**Path A (control):** Open a fresh Claude Code session in the project. Give it only the codebase and the change request. No reasoning graph, no Haytham context. Record:
- Time to complete
- Files touched
- Regressions introduced (run existing tests, manual check)
- Architectural decisions made (did it pick the right patterns?)
- Drift from original product intent (did it stay consistent with the product's identity?)

**Path B (treatment):** Open a fresh Claude Code session. Give it the codebase, the change request, AND the full `openspec/context/` directory (concept anchors, capabilities, architecture decisions, validation report). Record the same metrics.

**Deliverable:** A side-by-side comparison document. Honest. If Path B isn't materially better, the thesis doesn't hold and Week 3+ changes direction.

### Week 2: Second Change, Second Project

Repeat on the other project. Different change type (first was feature addition, second should be a pivot/scope change or a bug-class fix). This prevents overfitting to one change type.

Also: write up the Week 1 findings as a blog post draft. Don't publish yet. The writing will force clarity on what the reasoning graph actually contributed.

**Exit criteria for Weeks 1-2:**
- Two measured comparisons exist
- You can articulate in one paragraph what the reasoning graph changed about the outcome
- If the answer is "nothing meaningful," stop here and pivot to Genesis community (Path A from the strategic review)

---

## Week 3-4: Build the Minimum Evolution Command

**Goal:** Automate what you did manually in Weeks 1-2. Ship `/haytham:evolve`.

### Week 3: The Evolution Agent

Build one new agent (`agents/evolution-analyst.md`) and one new command (`commands/evolve.md`).

**The agent's job (single agent, not a pipeline):**
1. Read the change request (natural language)
2. Read the reasoning graph from `openspec/context/` (concept anchors, capabilities, architecture decisions, system traits)
3. Read the current OpenSpec from `openspec/specs/`
4. Classify the change: which capabilities are affected? Which architecture decisions constrain the implementation? Are any concept anchor invariants at risk?
5. Produce a spec delta: new/modified requirements, updated Gherkin scenarios, flagged constraints
6. Surface what the coding agent needs to know that it wouldn't figure out from the codebase alone

**The command's job:**
1. Verify the project has `openspec/context/` (reasoning graph exists)
2. Verify the project has `openspec/specs/` (specs exist)
3. Accept a change request as argument
4. Launch the evolution-analyst agent
5. Present the spec delta for human review
6. On approval, write the delta as a new OpenSpec change (e.g., `openspec/changes/add-whatsapp-sharing/`)
7. Hand off to `/opsx:propose` for implementation

**Design constraints:**
- Single agent. Do not split analysis and spec generation. The lesson from ADR-026 applies here harder than anywhere: the agent needs full context to reason about what the change affects
- The agent reads files, it does not execute code. Control plane, not data plane
- The output is a spec delta, not code. The coding agent implements

### Week 4: Validate on Both Projects

Run `/haytham:evolve` on TinyTales and GiftKaro with the same change requests from Weeks 1-2. Compare the automated output against the manual approach.

Fix what breaks. The first run will expose:
- Context that's missing from `openspec/context/` (what did you need manually that isn't in the files?)
- Cases where the agent misidentifies affected capabilities
- Spec deltas that are too broad or too narrow

Add a hook script that validates the spec delta references real capabilities from `capabilities.json`.

**Deliverable:** `/haytham:evolve "change request"` works end-to-end on both projects. The spec delta is reviewable and implementable.

---

## Week 5-6: Evidence and Polish

**Goal:** Build the evidence package that makes the pitch credible.

### Week 5: Run 5 Change Requests, Measure Everything

Across both projects, run 5 diverse change requests through Evolution:
1. Feature addition (new user-facing capability)
2. Integration change (swap or add a third-party service)
3. Scope expansion (add a new user segment or use case)
4. Bug-class fix (a structural issue, not a typo)
5. Constraint change (tighten security, change auth model, add rate limiting)

For each, record:
- Did the agent correctly identify affected capabilities?
- Did the spec delta preserve concept anchor invariants?
- Did the implementation from the spec delta introduce regressions?
- What did the reasoning graph add that codebase-only would have missed?

Build a results table. 5 changes, scored on correctness, traceability, and regression rate.

### Week 6: Blog Post + Demo Recording

**Blog post:** "I Ran 5 Change Requests Through an AI System That Remembers Why the Code Exists." Follow the existing blog style (honest, show failures, concrete examples). This is the key content piece for pitching.

**Demo recording (optional but high-leverage):** 3-minute screen recording showing:
1. The original Haytham run (fast-forward through Genesis)
2. The deployed product
3. A change request going through `/haytham:evolve`
4. The spec delta being reviewed
5. The implementation being applied
6. The result

This recording is the pitch deck. If you can show this in 3 minutes, you don't need slides.

---

## Week 7: Positioning and Narrative

**Goal:** Resolve the identity crisis. Ship the new story.

### Rewrite the README

The README currently says "validate, specify, design, build." After Evolution works, it says "build, evolve, and improve AI products with full traceability." Genesis becomes the onboarding, not the product.

Structure:
- Lead with the Evolution value prop (change requests that understand your product)
- Show Genesis as "how you get started" (not the main event)
- Link to the evidence (blog post, results table)
- Examples section: show a Genesis run AND an Evolution change on the same project

### Update VISION.md

Move Evolution from PLANNED to IN PROGRESS. Update the current state section with real results from the 5 change requests.

### Update marketplace.json

New description that leads with lifecycle, not validation.

### Cofounder brief update

Rewrite `docs/cofounder-brief.md` with Evolution evidence. The "Honest Assessment" section should now include real Evolution results instead of "EVOLUTION and SENTIENCE milestones are theoretical."

---

## Week 8: External Validation

**Goal:** Get the product in front of 5 people who aren't you.

### Target: developers who've built something with an AI coding agent

These people have felt the pain Evolution solves. They built an app with Cursor/Claude Code/Copilot, then needed to change it, and the agent didn't know why the original decisions were made. That's your audience.

### Channels (pick 2-3, don't spray)

- **r/ClaudeAI or r/SideProject:** Post the blog post. Not "check out my tool." Frame it as "I tested whether giving an AI system memory of why code exists produces better changes. Here's the data."
- **Claude Code plugin marketplace:** You're already there. The updated README and description should attract people browsing plugins
- **Direct outreach:** Find 3-5 Reddit/HN posts where someone describes the exact pain ("AI rebuilt my whole app when I asked for one change," "Cursor forgot why I structured it that way"). Comment with the blog post link. Not spam. Genuine contribution to their problem

### What you're measuring

Not signups or stars. Conversations. Did anyone run it? Did the Evolution output make sense to them? Did they hit a failure mode you didn't anticipate? 5 real conversations is the goal. If 2 of those 5 say "this solved a real problem for me," you have something to pitch.

---

## Decision Gates

### Gate 1 (end of Week 2): Does the reasoning graph matter?

If the manual comparison shows no meaningful difference between Path A (codebase only) and Path B (codebase + reasoning graph), stop. Either:
- The change requests were too simple (try harder ones)
- The reasoning graph doesn't carry enough signal (enrich it)
- The thesis doesn't hold (pivot to Genesis community play)

### Gate 2 (end of Week 4): Does automation work?

If `/haytham:evolve` produces spec deltas that are worse than what you'd write manually, the agent needs work before you build evidence on top of it. Spend Week 5 fixing the agent instead of running 5 changes.

### Gate 3 (end of Week 6): Is the evidence compelling?

If the 5-change results table shows <3/5 correct capability identification, or >1 regression introduced, or the blog post doesn't write itself because there's nothing interesting to say, extend polishing before going external.

---

## What This Plan Does NOT Include

- **Sentience (Milestone 3).** Too early. Evolution must work first
- **Multi-provider support.** The 5 open issues about Anthropic/OpenAI/Ollama providers are pre-plugin legacy. They're irrelevant now
- **Revenue model.** Premature before product-market signal. If 5 people use Evolution and 2 ask "can I pay for this?", then think about pricing
- **Scaling the community.** Community comes after the product works and the evidence exists. Building community around Genesis alone is building community around the wrong product
- **Stale issue cleanup.** Issues #24-29 (multi-provider), #31 (feedback agent), #36 (prose fragility) are all from the standalone era. Close them after Evolution ships, not before

---

## Success Criteria: "Pitch-Ready"

At the end of 8 weeks, you can say:

1. **"Haytham built two real products from ideas."** (TinyTales, GiftKaro, both live)
2. **"Then it evolved them."** (5 measured change requests across both projects)
3. **"The reasoning graph produced measurably better outcomes than codebase-only changes."** (Side-by-side comparison data)
4. **"Here's the evidence."** (Blog post with real numbers, demo recording)
5. **"Other people have tried it."** (5 conversations, 2+ positive signals)

That's not a half-baked product. That's a demonstrated thesis with evidence and early external validation. Enough to pitch to collaborators, angel investors, or an accelerator.
