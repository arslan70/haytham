# Proposal 001: Documentation Review & Dogfooding Plan

## Part 1: Documentation Review for Open-Source Release

### Overall Assessment

The documentation is strong. 40+ markdown files, 24 ADRs, clear architecture guides, mermaid diagrams, and a recent rewrite pass that removed jargon. The project is better documented than most open-source projects at launch.

That said, "well-documented" and "easy to get into as a newcomer" are different things. Below are the specific issues that would create friction for community members.

---

### Issue 1: No Working Demo or Output Examples

**Problem:** A newcomer reads "feed Haytham a startup idea and get an implementation-ready backlog" but has no way to see what that actually looks like without setting up an LLM provider, configuring AWS credentials, and running the system.

The README has a table showing the gym leaderboard example, but it only shows phase names and one-line summaries. There are no screenshots, no sample session output, no "here's what the validation report looks like."

**Impact:** High. This is the #1 reason people bounce from open-source repos. They can't quickly answer: "Is this thing useful to me?"

**Recommendation:**
- Add a `docs/example-session/` directory with actual outputs from one run (the gym leaderboard). Include the validation report, MVP scope, capability model, architecture decisions, and final stories. Sanitize if needed, but show real output.
- Add 2-3 screenshots of the Streamlit UI to the README or `docs/how-it-works.md`. A picture of the gate approval screen alone would communicate the human-in-the-loop concept instantly.
- Consider a short (~2 min) demo video or animated GIF in the README.

---

### Issue 2: CLAUDE.md Is Overloaded

**Problem:** CLAUDE.md serves three audiences simultaneously: (1) AI coding assistants (Claude Code instructions), (2) human contributors (architecture patterns, code hygiene), and (3) newcomers trying to understand the system. At 370+ lines, it's the longest file in the repo and mixes operational instructions ("before every commit") with deep architecture patterns ("PITFALL: Agents Re-deriving Known Values").

**Impact:** Medium. Human contributors will struggle to find what they need. The file is effective for AI assistants but intimidating for people.

**Recommendation:**
- Keep CLAUDE.md as-is for AI assistant use (it works well for that).
- Extract the "Architecture Patterns" and "Code Hygiene Rules" sections into a `docs/contributing/architecture-patterns.md` and link to it from both CLAUDE.md and CONTRIBUTING.md.
- Keep only the constitution, project overview, commands, and commit checklist in CLAUDE.md itself.

---

### Issue 3: CONTRIBUTING.md Is Too Thin

**Problem:** The contributing guide is mostly "see CLAUDE.md." For an open-source project, this is a missed opportunity. Contributors want to know: What are good first issues? How do I test my changes against real LLM calls? What's the PR review process? How do I add a new agent end-to-end?

**Impact:** Medium. Reduces conversion from "interested visitor" to "first PR."

**Recommendation:**
- Add a "Your First Contribution" walkthrough (e.g., "add a new export format" or "improve an agent prompt").
- Document the agent testing workflow (`make test-agents`) as a contributor tool, not just a developer tool.
- Add a section on "How to Test Without Expensive LLM Calls" (fixtures, the LLM-as-Judge approach, unit tests that don't need API keys).
- Link to 3-5 "good first issue" labels or specific areas where help is wanted.

---

### Issue 4: Roadmap Is Internal-Facing

**Problem:** `docs/roadmap.md` reads like an internal planning document. It uses phrases like "foundational for everything below" and "the docs describe the Phase 4 story output as an execution contract." Community members want to know: What's coming? Where can I contribute? What's the big picture timeline?

**Impact:** Low-Medium. The roadmap exists (good), but it doesn't generate excitement or invite participation.

**Recommendation:**
- Add a brief intro section that frames the roadmap for external readers: "Here's where Haytham is headed and where you can help."
- Mark items with contribution-friendliness (e.g., "contributions welcome" vs. "core team").
- Add the dogfooding plan (Part 2 of this document) as a roadmap item, since it's the most community-engaging feature.

---

### Issue 5: ADR Volume Without Navigation

**Problem:** 24 ADRs is impressive but overwhelming. The ADR README is a flat list with status tags. A newcomer who wants to understand "how does the scoring work?" has to guess that it's ADR-023, not ADR-005 or ADR-006.

**Impact:** Low. ADRs are reference material, not onboarding material. But they're a selling point for the project's engineering quality.

**Recommendation:**
- Group ADRs by topic in the index (Core Architecture, Agents & Quality, Features, UX, Infrastructure) rather than by number. The categories already exist implicitly.
- Add a "Start Here" note at the top: "New to the project? Read ADR-016 (four-phase workflow) and ADR-022 (concept fidelity) first."

---

### Issue 6: No Architecture Diagram at System Level

**Problem:** `docs/how-it-works.md` has an excellent pipeline flowchart. But there's no diagram showing the system components (Burr, Strands, Session Manager, Agent Factory, Stage Registry) and how they relate. The architecture overview (`docs/architecture/overview.md`) is text-heavy.

**Impact:** Low-Medium. Contributors who want to modify the system (not just use it) need a mental model of the internals.

**Recommendation:**
- Add a single mermaid diagram to `docs/architecture/overview.md` showing: User Input -> Streamlit UI -> Burr Workflow -> Stage Executor -> Agent Factory -> Strands Agent -> Session Manager. Show the key data flows.

---

### Summary: Documentation Readiness

| Area | Status | Action Needed |
|------|--------|---------------|
| README | Good | Add screenshots/demo, example output |
| Getting Started | Good | No changes needed |
| How It Works | Strong | Add system-level architecture diagram |
| CONTRIBUTING | Needs work | Expand with walkthrough, testing guide |
| CLAUDE.md | Good for AI, heavy for humans | Extract patterns to separate doc |
| Roadmap | Functional but internal-facing | Reframe for community, add dogfooding |
| ADRs | Excellent content, weak navigation | Group by topic, add "start here" |
| Troubleshooting | Strong | No changes needed |
| Vision | Strong | No changes needed |
| Example outputs | Missing | Add example session directory |

---

## Part 2: The Dogfooding Plan

### The Pitch: "A System That Specs Itself"

Haytham validates startup ideas and generates implementation specs. Haytham *is* a startup idea. The most compelling proof of the system's value is using it on itself, publishing the results, and inviting the community to build from its own generated stories.

This isn't just a demo. It's a feedback loop: Haytham generates stories for its own improvement, the community implements those stories, and the improved Haytham generates better stories next time. ADR-010 already proves this works in miniature (the export feature came from a dogfooding session). The proposal is to formalize it and make it public.

---

### What Dogfooding Means Here

Run Haytham's four-phase pipeline on Haytham itself:

```
Input: "Haytham is a specification-driven control plane that transforms
        startup ideas into validated, implementation-ready specifications
        via multi-agent AI. It orchestrates 21 specialist agents through
        four phases (validation, specification, design, stories) with
        human approval gates at each boundary."

Output: GO/NO-GO verdict, MVP scope, capability model, architecture
        decisions, and implementation-ready stories for Haytham's own
        next milestone (Evolution).
```

Then publish every artifact and let the community work from the generated backlog.

---

### Why This Works for Community Engagement

1. **Proof by construction.** "Our system is good enough to specify its own next version" is a stronger claim than any benchmark or case study.

2. **Instant contributor onboarding.** New contributors get a ready-made backlog of traced, scoped stories instead of vague "help wanted" labels. Each story comes with capability references, architecture decisions, and acceptance criteria.

3. **Transparent roadmap.** The community can see exactly what the system thinks its own gaps are. This replaces hand-waved roadmaps with evidence-based planning.

4. **Recursive improvement narrative.** Each release cycle, re-run Haytham on itself. Publish the diff between successive runs. "Here's what Haytham v0.2 thinks about Haytham v0.3" is genuinely interesting content for the AI/agent community.

5. **Quality signal.** If the system produces garbage when pointed at itself, that's a signal. If it produces coherent, actionable stories, that's a different signal. Either way, the transparency builds trust.

---

### Execution Plan

#### Phase 0: Prepare the Input (pre-dogfood)

Write a high-quality idea statement for Haytham itself. This is critical because the system's output quality depends on input quality. The statement should describe:
- The problem Haytham solves (weeks of planning compressed into evidence-based process)
- The target user (technical founders, solo developers, agencies)
- The unique value (specification-driven, not just code generation; honesty over flattery)
- The current state (Genesis complete, Evolution planned)

Store this as `docs/dogfood/haytham-idea-statement.md` so the community can see and discuss the input.

#### Phase 1: Run the Pipeline

Execute Haytham on its own idea statement through all four phases:
1. **Validation (WHY):** Does the system honestly evaluate its own viability? Does the scorer find real risks? Does it produce GO, NO-GO, or PIVOT?
2. **Specification (WHAT):** Does the MVP scope match reality? Are the generated capabilities coherent with what actually exists?
3. **Design (HOW):** Do the build/buy decisions align with the actual tech stack? Does it recommend Burr, Strands, Streamlit, or does it suggest alternatives?
4. **Stories (TASKS):** Are the generated stories actionable? Do they advance the Evolution milestone?

Save all outputs to `docs/dogfood/session-v1/` and commit them to the repo.

#### Phase 2: Publish and Annotate

For each phase output, write a brief annotation:
- **What the system got right** (e.g., correctly identified the market gap)
- **What the system got wrong** (e.g., suggested a technology the team already evaluated and rejected)
- **What surprised us** (e.g., a risk we hadn't considered)

This honesty is the engagement hook. The annotations are more interesting than the raw output because they show the system's real strengths and limitations.

Publish as:
- `docs/dogfood/session-v1/annotations.md` (commentary)
- `docs/dogfood/session-v1/` (raw session outputs from each phase)

#### Phase 3: Community Backlog

Take the Phase 4 stories and publish them as GitHub Issues:
- Each story becomes an issue with the full context (capability reference, architecture decision, acceptance criteria)
- Label with `dogfood-v1`, `good-first-issue` (where appropriate), and difficulty level
- Link issues to the capabilities they implement

This gives contributors a curated, traced backlog to work from. Stories that advance the Evolution milestone become the community's immediate roadmap.

#### Phase 4: Iterate

After v1 stories are implemented (by community or core team):
- Re-run Haytham on itself (v2 session)
- Publish the delta: "Here's what changed between v1 and v2 assessments"
- New stories go into the next community sprint

This creates a recurring engagement loop. Each dogfood cycle produces content (the session outputs), work items (the stories), and a narrative ("the system that improves itself").

---

### Directory Structure

```
docs/dogfood/
  README.md                          # What this is, how to read it, how to contribute
  haytham-idea-statement.md          # The input fed to Haytham
  session-v1/
    phase-1-validation/              # Raw validation output
    phase-2-specification/           # Raw MVP scope + capabilities
    phase-3-design/                  # Raw build/buy + architecture
    phase-4-stories/                 # Raw stories
    annotations.md                   # Team commentary on outputs
  session-v2/                        # Next iteration (after v1 stories implemented)
    ...
```

---

### Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| System produces a NO-GO verdict for itself | Embarrassing but honest | Publish it anyway. Honesty builds more trust than perfection. Analyze why and use it to improve the scorer. |
| Stories are too vague to implement | Reduces contributor engagement | Annotate and supplement. Use it as evidence for where story generation needs improvement. |
| Output references wrong tech stack | Confusing for contributors | Annotate discrepancies. The system hasn't seen the codebase, only the idea statement. This is expected. |
| Community doesn't engage | Wasted effort | Minimal. The dogfood session itself provides value (testing, content). Community engagement is upside, not a requirement. |

---

### What This Unlocks

If the dogfooding loop works, it directly enables the project's stated milestones:

- **Evolution (M2):** The dogfood session is literally "existing system + change request = updated system." Implementing v1 stories, then re-running, proves the Evolution workflow.
- **Sentience (M3):** Recurring dogfood sessions with published diffs are the manual precursor to autonomous self-improvement. The pattern is the same (observe, analyze, propose, execute, validate). The automation comes later.
- **Community narrative:** "A system that specs its own next version" is a one-sentence pitch that generates interest. It's concrete, verifiable, and unusual.

---

### Suggested README Addition

Once the dogfood session is published, add a section to the README:

```markdown
## Dogfooding: Haytham Specs Itself

We run Haytham on its own idea to generate implementation stories for the
next version. The full session outputs, team annotations, and generated
backlog are published in [docs/dogfood/](docs/dogfood/).

Current cycle: **v1** — [Session outputs](docs/dogfood/session-v1/) |
[Annotations](docs/dogfood/session-v1/annotations.md) |
[Community backlog](https://github.com/arslan70/haytham/labels/dogfood-v1)

Want to contribute? Pick a story from the
[dogfood backlog](https://github.com/arslan70/haytham/labels/dogfood-v1)
and follow the [Contributing Guide](CONTRIBUTING.md).
```

---

### Next Steps

1. Review and approve this plan
2. Address documentation issues (Part 1) as a pre-release cleanup
3. Write the Haytham idea statement (Phase 0)
4. Run the dogfood session (Phase 1)
5. Annotate and publish (Phase 2)
6. Create GitHub issues from stories (Phase 3)
