# UX Improvement Plan: Agent Interaction Patterns

This plan is based on analysis of a real `/haytham:validate` run mapped against established agentic AI UX research from Smashing Magazine, Microsoft Design, Victor Dibia (AutoGen), UXmatters, Evil Martians, and Optimal Workshop.

The run analysed took ~6 minutes for Phase 1 alone. During that time the user saw opaque agent calls, generic status messages, and no sense of progress until the research brief appeared at the end.

---

## Problem 1: No Upfront Roadmap

### What happens now

The user types `/haytham:validate "idea"` and the system immediately starts working. There is no preview of what will happen, how many steps there are, or roughly how long each takes.

```
Starting Haytham Phase 1 - Idea Validation. Let me set up the project and begin analysis.
```

Then silence for 6+ minutes with collapsed agent calls in between.

### Why this is a problem

The "Intent Preview" pattern (Smashing Magazine, Feb 2026) says users should see the plan before execution begins. Victor Dibia calls this "Capability Discovery": users need to understand what the system will do before delegating. Without it, autonomy feels like something seized by the system rather than granted by the user.

### Proposed fix

Add a roadmap block to `commands/validate.md` (and the Phase 1 section of `commands/haytham.md`) between Setup and Step 1. Before any agent call, emit a summary like:

```
## Phase 1: Idea Validation

This will run 6 steps:
1. Idea Analysis - expand and classify your idea (~1 min)
2. Market Research - web search for competitors, sizing, sentiment (~3 min)
3. Research Brief - neutral summary of findings (~1 min)
4. Founder Review - you review and correct  <-- YOU DECIDE HERE
5. Validation Report - GO/PIVOT/NO-GO analysis (~1 min)
6. Gate Decision - you approve or reject

Estimated total: ~7 minutes. Starting now.
```

### Files to change

- `commands/validate.md`: Add "Roadmap" section between Setup and Step 1.
- `commands/haytham.md`: Add the same roadmap block before Phase 1's Step 1. Repeat the pattern for Phases 2-4 with their own step lists.

### Effort

Small. Text-only additions to command files.

---

## Problem 2: Opaque Agent Execution

### What happens now

```
haytham:market-researcher(Research market and competitors)
  Done (16 tool uses, 25.8k tokens, 3m 13s)
  (ctrl+o to expand)
```

3 minutes of silence, then a collapsed summary. The user has no idea what happened, whether the right competitors were found, or whether the agent got stuck.

### Why this is a problem

Microsoft's agent UX guidelines state that "agent status, what the agent is doing, should be clearly visible at all times." Victor Dibia lists "Observability and Provenance" as a core principle. Evil Martians' CLI UX research notes that long-running tasks without progress feedback "appear hung."

We cannot control what Claude Code shows during subagent execution (that is platform-level), but we control the framing before and after each agent call.

### Proposed fix

Add **pre-agent context** and **post-agent digest** instructions at each step.

**Before** launching an agent (example for Step 2):
```
Step 2/6: Market Research
Searching for competitors, market sizing, and user sentiment for [idea domain].
This is the longest step (~3 min) because it runs web searches.
```

**After** an agent completes (read from the output file and emit a one-liner):
```
Market Research complete.
Found 4 competitors (Lovable, Replit, Bolt, Devin), TAM estimated at $7.4B.
Moving to Step 3.
```

### Files to change

- `commands/validate.md`: Add pre-agent and post-agent text instructions at Steps 1-3 and Step 5.
- `commands/haytham.md`: Same changes in the Phase 1 section, and apply the pattern to Phases 2-4.

### Effort

Small. The post-agent summaries require reading from output files, which the commands already do at gate steps. Extend that pattern to every step.

---

## Problem 3: No Intermediate Results During Long Waits

### What happens now

Market research takes 3+ minutes. The user sees nothing until it finishes.

### Why this is a problem

UXmatters advocates "progressive disclosure", offering previews and intermediate results. Microsoft's guidance says to "show agents in progress, explain the wait with reasons for delays, and use progressive disclosure to offer previews."

### Proposed fix

Two options, in order of preference:

**Option A (simpler):** Improve the pre-agent message for market-researcher to be specific about what it will search for. Use information from the idea-analysis output (which is already written to disk at this point) to say something like: "Searching for competitors in the AI-powered SaaS builder space, checking market sizing data, and looking for user sentiment on existing tools."

This does not add intermediate results, but it tells the user what to expect, which reduces the perception of being stuck.

**Option B (more complex):** Split market research into two visible steps. First a "quick scan" agent call that reports competitor names and rough market size, then a "deep dive" that fills in sentiment, gaps, and detailed analysis. This gives a mid-point signal but adds orchestration complexity.

### Recommendation

Start with Option A. It is a one-line change to the pre-agent message. If users still report the wait as painful after that, consider Option B.

### Files to change

- `commands/validate.md`: Update the Step 2 pre-agent message to reference idea-analysis output.
- `commands/haytham.md`: Same.

### Effort

Option A: Small. Option B: Medium (new agent split, additional file handoff).

---

## Problem 4: No Interruptibility

### What happens now

Once `/haytham:validate` starts, there is no way to say "skip market research, I already know the landscape" or "focus on competitor X" or "stop, I want to change my idea." The system runs all steps sequentially without pause.

### Why this is a problem

Victor Dibia lists "Interruptibility" as one of four core design principles. Smashing Magazine calls it the "Autonomy Dial": autonomy should not be binary. The user should be able to adjust the level of automation.

### Proposed fix

Add a brief checkpoint after Step 1 (idea analysis), before launching market research. The idea analysis output already contains the concept expansion. Present a one-line summary and give the user a window to interject:

```
Your idea has been classified as VALID.
Core concept: [one-line from idea-analysis.md]

Proceeding to market research in a moment.
If you have specific guidance (e.g., "focus on competitor X",
"skip research, I know the market"), say it now.
```

This is not a hard gate. It does not require the user to type anything. It is a visible moment where the user knows they can speak up, but the system proceeds if they stay silent.

Important: this must not become a blocking confirmation prompt. The current flow already has two explicit gates (Founder Review and Gate 1). Adding a third mandatory stop would make the workflow feel heavy. The checkpoint should be a brief informational pause, not a question that demands an answer.

### Files to change

- `commands/validate.md`: Add a checkpoint instruction after Step 1, before Step 2.
- `commands/haytham.md`: Same in Phase 1.

### Effort

Small. But the wording matters. It needs to feel like an invitation, not a gate.

---

## Problem 5: Generic Status Messages

### What happens now

```
Idea analysis complete. Let me check for any clarification questions and then proceed.
No clarifications needed. Moving to Step 2: Market Research.
Market research complete. Now launching Step 3: Research Brief.
```

These messages describe what is happening but never why. They read like a task list being checked off. The user learns nothing from them.

### Why this is a problem

Smashing Magazine identifies "Explainable Rationale" as a core in-action pattern: the user should understand not just what the agent is doing, but why each step exists. UXmatters calls this "cognitive affordance": in agentic systems, the primary affordance is understanding what the system is thinking.

### Proposed fix

Replace task-list language with purpose-driven language. Each transition should explain the purpose of the next step relative to the user's goal.

| Current | Proposed |
|---------|----------|
| "Moving to Step 2: Market Research" | "Your idea is clear. Now checking if anyone else is solving this, and how big the opportunity is." |
| "Market research complete. Now launching Step 3: Research Brief" | "Research gathered. Compiling a neutral summary for your review. No scores or judgments, just facts." |
| "Research brief compiled. Let me read it and present it for your review." | "Here's what we found. Check if this matches your understanding of the market." |

### Files to change

- `commands/validate.md`: Rewrite transition text at each step boundary.
- `commands/haytham.md`: Same for Phase 1. Apply the same principle to Phases 2-4.

### Effort

Small. Text changes only, no logic changes.

---

## Problem 6: No Confidence Signals

### What happens now

The research brief presents findings as flat statements without indicating confidence levels or source quality:

```
- Market size: $7.4B TAM (AI code tools), with ~$1.5B serviceable market
- AI reliability is currently ~14% on complex tasks
```

Both are presented with equal visual weight despite very different evidence quality.

### Why this is a problem

Smashing Magazine identifies "Confidence Signal" as a core pattern: showing the "how certain" alongside the "why." UXmatters says agents should "surface their own confidence in their plans and actions" to help users "decide when to scrutinize a decision more closely."

The research-briefer agent already tags sources internally. But the founder-review presentation flattens everything to the same level.

### Proposed fix

Update the research-briefer to include simple confidence indicators in its output. Not numeric scores (those violate the briefer's neutrality rules), but source-quality markers:

- `[multiple sources]` for claims backed by 2+ independent sources
- `[single source]` for claims from one source
- `[estimated]` for extrapolated or calculated figures
- `[unverified]` for claims the agent could not independently confirm

These markers help the founder calibrate which findings to scrutinize during the review step.

### Files to change

- `agents/research-briefer.md`: Add source-quality marker instructions to the output format.
- `commands/validate.md`: Ensure Step 4 presentation preserves these markers.

### Effort

Medium. Requires updating the agent prompt and testing that markers appear consistently.

---

## Problem 7: Founder Review Question is Too Open-Ended

### What happens now

```
Does this accurately capture your idea and the market landscape?
Would you like to correct anything before we produce the validation report?
```

This is a good interaction point. But it asks two questions at once and does not guide the founder on what kinds of corrections are useful at this stage.

### Why this is a problem

Optimal Workshop's agentic AI research and Microsoft's guidelines emphasize that questions should be specific enough to be actionable. Open-ended "anything to correct?" questions create decision paralysis, especially after reading a dense research brief.

### Proposed fix

Replace the open question with guided prompts:

```
Review the brief above. Specifically:
- Is the problem statement right?
- Are we missing any key competitors?
- Is the market size in the right ballpark?

Reply with corrections, or say "looks good" to continue to the validation report.
```

This keeps the interaction lightweight (the user can still just say "looks good") but gives them specific dimensions to evaluate.

### Files to change

- `commands/validate.md`: Rewrite the Step 4 question.
- `commands/haytham.md`: Same in Phase 1.

### Effort

Small. Text change only.

---

## Problem 8: No Cost/Token Awareness

### What happens now

Token counts appear in collapsed agent summaries (`7.1k tokens`, `25.8k tokens`) but these are technical details in the platform UI, not user-facing cost information. The user has no sense of relative cost between steps.

### Why this is a problem

Victor Dibia identifies "Cost-Aware Action Delegation" as a principle: users should understand the cost implications of agent actions before and during execution.

### Proposed fix

This is partially a platform concern (Claude Code manages token display). But we can address it lightly:

1. In the roadmap block (Problem 1 fix), note which step is most resource-intensive: "Step 2 is the heaviest step (runs web searches)."
2. In the completion message, note the total number of agent calls made: "Phase 1 complete. Ran 4 agents across 6 steps."

This sets expectations without building token-tracking infrastructure.

### Files to change

- `commands/validate.md`: Add cost note to roadmap, add summary to completion.
- `commands/haytham.md`: Same.

### Effort

Small. Text additions only.

---

## Implementation Priority

| Priority | Problem | Fix | Effort | Impact |
|----------|---------|-----|--------|--------|
| 1 | No upfront roadmap | Add roadmap block before first agent call | Small | High |
| 2 | Opaque agent execution | Add pre/post-agent context and digest | Small | High |
| 3 | Generic status messages | Rewrite transitions with purpose-driven language | Small | Medium |
| 4 | Open-ended review question | Add guided review prompts | Small | Medium |
| 5 | No interruptibility | Add soft checkpoint after Step 1 | Small | Medium |
| 6 | No confidence signals | Add source-quality markers to research brief | Medium | Medium |
| 7 | No intermediate results | Better pre-agent framing (Option A) | Small | Medium |
| 8 | No cost awareness | Add cost notes to roadmap and completion | Small | Low |

| 9 | No blog post | Draft a post documenting the UX findings and fixes | Medium | Low |
| 10 | No codified UX standards | Add Agent UX Standards section to CLAUDE.md | Small | High |

Priorities 1-5 and 7-8 are all text changes to command files. They can be implemented in one pass with no logic changes. Priority 6 requires updating an agent prompt and verifying output consistency. Priority 10 (CLAUDE.md) should be done early since it ensures all other changes follow the same principles. Priority 9 (blog post) can be done last, after the fixes are implemented and tested.

---

## Action Item 9: Blog Post Draft

### What

Write a blog post for `docs/blog/` documenting the UX improvements: what we found, why it matters, and what we changed. This serves as both a public artifact and a reference for anyone building similar multi-agent CLI tools.

### Why

The UX problems we found are not unique to Haytham. Anyone building a multi-agent plugin for Claude Code (or any agentic CLI) will hit the same issues: opaque agent calls, no progress signals, generic status messages. A post that shares concrete findings, names the research sources, and shows before/after examples is genuinely useful to the community.

### Suggested structure

Follow the blog writing style in CLAUDE.md. Prose paragraphs, not bullet lists. Conversational voice.

1. **Opening**: Start with the concrete experience. "We ran our plugin against a test idea and watched 6 minutes of silence." No throat-clearing, no definitions of agentic AI.
2. **The 8 problems**: Group into three themes rather than listing all 8 sequentially:
   - *The user doesn't know what's happening* (Problems 1, 2, 3: roadmap, observability, intermediate results)
   - *The user can't participate* (Problems 4, 5, 7: interruptibility, generic messages, open-ended questions)
   - *The user can't calibrate trust* (Problems 6, 8: confidence signals, cost awareness)
3. **The research**: Name the sources and the specific patterns they describe. Link to them. Don't just say "best practices say X"; say "Smashing Magazine's Feb 2026 piece identifies six patterns along the agent lifecycle. The one that hit hardest for us was Intent Preview."
4. **What we changed**: Show before/after examples from the command files. Keep it concrete.
5. **What we couldn't fix**: Be honest about platform constraints. We can't add spinners or stream subagent output. Say so. Contra-indications build trust.
6. **Ending**: Point forward. What would we do differently if Claude Code added streaming subagent output? What's still unsolved?

### Files to create

- `docs/blog/ux-lessons-from-a-multi-agent-plugin.md` (draft)

### Effort

Medium. Writing takes time, but the research and examples are already in this plan.

---

## Action Item 10: Add UX Best Practices to CLAUDE.md

### What

Add a section to `CLAUDE.md` that codifies the UX principles from this plan as standing instructions. This ensures future changes to commands and agents follow the same patterns without needing to re-discover them.

### Why

CLAUDE.md is always loaded into context. If UX principles live only in this plan document, they will be forgotten the next time someone (or Claude) edits a command file. Putting them in CLAUDE.md makes them enforceable the same way "Documentation Editing Standards" and "Key Design Decisions" are enforced today.

### Proposed section

Add after the "Key Design Decisions" section in CLAUDE.md:

```markdown
### Agent UX Standards

When writing or modifying command files that orchestrate agents, follow these patterns:

**Roadmap first.** Before launching any agents, emit a numbered step list showing what will happen, which steps involve user decisions, and roughly how long the phase takes. The user should see the plan before execution begins.

**Frame every agent call.** Before each agent call, state what the agent will do and why in plain language (not "Launching market-researcher agent" but "Checking if anyone else is solving this problem and how big the opportunity is"). After each agent call, read the output file and emit a one-line digest of what was found.

**Purpose over procedure.** Transition messages should explain why the next step exists relative to the user's goal, not just name the step. "Research gathered. Compiling a neutral summary for your review." not "Now launching Step 3: Research Brief."

**Guided questions.** When asking the user for review or approval, provide specific dimensions to evaluate (e.g., "Is the problem statement right? Are we missing competitors?") rather than open-ended "anything to correct?" prompts. Always include a low-effort escape ("say 'looks good' to continue").

**Soft checkpoints.** Between major steps, give the user a visible window to interject without requiring a response. State what just happened and what's about to happen. The user can steer if they want; the system proceeds if they don't.

**Confidence markers.** When presenting research findings or analysis to the user, preserve source-quality indicators ([multiple sources], [single source], [estimated], [unverified]) so the user can calibrate which findings to scrutinize.

**No blocking without reason.** Only use hard gates (explicit approval questions) at phase boundaries. Mid-phase checkpoints should be informational, not blocking. Too many mandatory stops make the workflow feel heavy.
```

### Files to change

- `CLAUDE.md`: Add the section above after "Key Design Decisions."

### Effort

Small. The content is already written above; it just needs to be inserted.

---

## Scope and constraints

All changes are to command markdown files (`commands/validate.md`, `commands/haytham.md`) and one agent file (`agents/research-briefer.md`). No new files, no new agents, no structural changes.

The fixes work within Claude Code's current rendering constraints. We cannot add spinners, progress bars, or streaming intermediate output from subagents. What we can control is the text the orchestrating command emits before and after each agent call, and the structure of questions asked to the user.

---

## Sources

- [Designing For Agentic AI: Practical UX Patterns (Smashing Magazine, Feb 2026)](https://www.smashingmagazine.com/2026/02/designing-agentic-ai-practical-ux-patterns/)
- [UX Design for Agents (Microsoft Design)](https://microsoft.design/articles/ux-design-for-agents/)
- [4 UX Design Principles for Multi-Agent Systems (Victor Dibia)](https://newsletter.victordibia.com/p/4-ux-design-principles-for-multi)
- [Designing for Autonomy: UX Principles for Agentic AI (UXmatters, Dec 2025)](https://www.uxmatters.com/mt/archives/2025/12/designing-for-autonomy-ux-principles-for-agentic-ai.php)
- [CLI UX Best Practices: Progress Displays (Evil Martians)](https://evilmartians.com/chronicles/cli-ux-best-practices-3-patterns-for-improving-progress-displays)
- [Designing User Experiences for Agentic AI (Optimal Workshop)](https://www.optimalworkshop.com/blog/agentic-ai-the-next-frontier)
- [User Interfaces in Agentic CLI Tools (The New Stack)](https://thenewstack.io/user-interfaces-in-agentic-cli-tools-what-developers-need/)
