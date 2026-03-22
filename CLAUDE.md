# CLAUDE.md

## Constitution

Haytham is a lifecycle control plane for AI-built products. It maintains a reasoning graph from founder intent to production telemetry, making every decision traceable, every change targeted, and every improvement evidence-grounded. Delivered as a Claude Code plugin, it orchestrates specialist agents across the full product lifecycle: validate, specify, build, deploy, monitor, improve.

The core asset is the reasoning graph: concept anchor → capabilities → architecture decisions → specs → code → telemetry. Three milestones increase autonomy over this graph:

1. **GENESIS** (CURRENT FOCUS): Idea to working MVP. Builds the reasoning graph. Delivered as a Claude Code plugin.
2. **EVOLUTION** (PLANNED): System + change request to targeted update. Navigates the graph to handle change without full rewrites.
3. **SENTIENCE** (VISION): Running system + telemetry to autonomous improvement. Walks the graph to detect, propose, and execute improvements.

### Guiding Principles

1. **Stay Focused**: Only work on features that advance the current milestone
2. **Stay Lean**: Minimum viable implementation. No gold-plating. No premature optimization
3. **Challenge Distractions**: If it doesn't advance the roadmap, push back. Defer polish, config options, UI enhancements, and premature abstractions
4. **Close the Loop**: Partial solutions have no value. Complete the feedback loop
5. **Trace Everything**: Every requirement traces to a capability. Every capability traces to a user need

Before starting work, ask: Does this advance the current milestone? Is it the minimum viable implementation? Can it be deferred? If so, challenge the request. See [VISION.md](./VISION.md).

6. **Fix the Root Cause**: When a problem surfaces, fix the underlying issue, not the symptom. Before proposing a workaround or patch, ask: why does this problem exist? Can the root cause be eliminated? A sync test between two files is a patch; putting the data in one file is the fix. Read the relevant documentation before adding scaffolding.

7. **Control Plane, Not Data Plane**: Haytham is an orchestrator, not an executor. When choosing between approaches, prefer the one where Haytham declares intent and delegates execution over the one where Haytham does the work itself. Haytham classifies, directs, and validates. Build agents, spec tools, and downstream systems execute. If a proposed change has Haytham doing something a downstream tool should do, push back. The test: "Is Haytham deciding WHAT needs to happen, or doing the work?" If the latter, delegate it.

   This principle compounds across milestones. GENESIS delegates build execution. EVOLUTION delegates change execution. SENTIENCE delegates improvement execution. Each milestone adds a new loop, but Haytham stays the control plane in all of them. A design decision that couples Haytham to execution in GENESIS will block delegation in EVOLUTION and autonomy in SENTIENCE.

### Meta-System Design

**Haytham is a factory that produces and maintains products, not just applications.** It must handle ANY valid startup idea (web app, CLI tool, API service, marketplace), not just specific examples. This means:

- **Generic prompts**: Enforce principles (traceability, consistency), not prescriptions (use Supabase, limit to 5 items). If a rule wouldn't apply to a CLI AND a web app AND an API, it's too specific.
- **Test across input classes**: Web app, CLI tool, API service, marketplace. A fix that works for one but breaks another is not a fix.
- **Read signals, don't hardcode**: Determine context from input rather than prescribing counts, services, or tech choices.
- **Enforce consistency, not content**: "Every capability must trace to an IN SCOPE item" (good) vs "Output should have 5 capabilities" (bad).
- **Self-checking agents**: Validate output against input constraints.

**Review test**: "Would this work for a CLI tool? An IoT system? A marketplace?" If no, find the generalization.

**Lifecycle test**: "Does this design decision work for build AND deploy AND monitor AND improve?" If it only serves the build phase, it's too narrow. The reasoning graph must support the full lifecycle.

### System Integrity Traits

When evaluating or making changes, consider these traits critical to the system's integrity:

- **Missing logical stages**: Are there gaps in the workflow where a necessary analysis or transformation step is absent?
- **Stage handoff quality**: Is information passed cleanly between stages, or is context lost/mangled at boundaries?
- **Information schema fit**: Is the schema between stages too tight (blocking valid inputs) or too loose (allowing garbage through)?
- **Prompt quality**: Are agent prompts clear, well-scoped, and producing consistent results?
- **Agent role burden**: Is any single agent overloaded with too many responsibilities? Split when a prompt tries to do too much.
- **Agent tooling gaps**: Do agents have the tools they need to do their job, or are they forced to hallucinate what a tool should provide?

---

## Project Overview

Haytham is a lifecycle control plane for AI-built products, delivered as a Claude Code plugin. It orchestrates specialist agents across the full product lifecycle: validate the idea, specify the MVP, design the architecture, generate implementation specs, and build the system. The current implementation covers validate → specify → build. The roadmap extends to deploy → monitor → improve.

Eight specialist agents across four phases, orchestrated via command and agent markdown files.

## Plugin Structure

```
.claude-plugin/
  plugin.json                    # Manifest (name, version, description)

agents/                          # 8 specialist agents (markdown with frontmatter)
  idea-analyst.md                # Concept expansion, gating, anchor extraction
  market-researcher.md           # Market intelligence + competitor analysis
  research-briefer.md            # Neutral formatting of research findings
  report-synthesizer.md          # GO/NO-GO/PIVOT verdict (single-agent synthesis)
  mvp-scoper.md                  # Scope definition, boundaries, core flows
  capability-modeler.md          # Capability extraction + system trait classification
  architect.md                   # Build/buy analysis + architecture decisions
  spec-generator.md              # OpenSpec generation with SHALL statements and Gherkin scenarios

commands/                        # User-facing commands
  haytham.md                     # Full 4-phase workflow (/haytham <idea>)
  validate.md                    # Phase 1 only (/haytham:validate <idea>)
  specify.md                     # Phase 2 only (/haytham:specify)
  design.md                      # Phase 3 only (/haytham:design)
  plan.md                        # Phase 4 only (/haytham:plan)

hooks/
  hooks.json                     # PreToolUse prereq checks, PostToolUse validation

scripts/
  check_phase_prereqs.sh         # Phase prerequisite verification
  validate_schema.py             # Output schema validation
  validate_som.py                # SOM arithmetic + regulated domain checks
```

## How to Modify

### Modifying an Agent

Edit the agent's markdown file in `agents/`. The file has YAML frontmatter (name, description, tools, model) and a system prompt body. Reload the plugin to pick up changes.

### Adding a New Agent

1. Create `agents/your-agent.md` with frontmatter (`name`, `description`, `tools`, `model`)
2. Reference it from the relevant command in `commands/`

### Adding a New Command

1. Create `commands/your-command.md` with frontmatter (`description`, `argument-hint`, `allowed-tools`)
2. The command becomes available as `/haytham:your-command`

### Testing

**Sanity tests (CI):** Run before every commit:

```bash
python3 -m pytest tests/test_plugin_sanity.py -v
```

Tests cover: frontmatter validation (agents + commands), script syntax, cross-reference integrity (agents referenced in commands exist, hook script paths valid), schema validation logic, and marketplace JSON structure.

**Functional testing:** Run the plugin against a test idea and check output files in `.haytham/session/`:

```
/haytham "a gym community leaderboard with anonymous handles"
```

---

## Documentation Editing Standards

- Write in plain, human-friendly language. Avoid jargon and verbose AI-sounding prose.
- Never use em dashes. Use commas, periods, or parentheses instead.
- Avoid LLM writing patterns: "Not X, but Y" contrasts, theatrical reversals ("That's not magic. It's engineering."), parallel triplets used more than once, and tidy wrap-up sentences that restate what was just said. Just say what the thing is.
- Don't assume the reader knows niche products, tools, or ecosystems. If you name-drop specific competitors or tools, provide enough context for a reader who has never heard of them. When the names aren't essential to the point, describe the category instead.
- Match word count to impact. High-impact moments (the key insight, the surprising result) earn more words. Setup, transitions, and supporting details should be tight. If a paragraph has a lot of words but low impact, cut it. If a sentence carries the whole point, give it room to land.
- Prefer diagrams (mermaid) over long explanatory paragraphs when showing architecture or flows.
- When editing docs, keep it concise. If the user asks for simplification, go further than you think necessary.

### Blog Writing Style

These apply to posts in `docs/blog/`. Write for a human taking a 5 minute coffee break.

**Voice:** Write like you're explaining something to a colleague. Conversational, not academic. Use active voice. Say "we found" and "I've seen", not "it was observed that." Think out loud. Show the reasoning that led to the conclusion, not just the conclusion itself.

**Tone:** This is an early-stage project with zero users. Write like someone sharing what they're learning, not someone lecturing from authority. Avoid declarative confidence ("The obvious answer is...", "This proves that...") when the project hasn't been validated by real usage yet. "I found" is better than "this shows." "It seems like" is better than "it's clear that." Don't perform certainty you haven't earned. The reader can tell when confidence outpaces evidence, and it costs credibility.

**Framing:** Describe what the user experiences, not what the system contains. Features are for READMEs. Blog posts are for people.

**Perspective:** Write about what the reader will learn, not what you did. The reader's question is always "why should I care?", not "what did you do?"

**Structure:** Prose paragraphs over bullet lists. Bullets are for genuinely parallel items (steps, options), not for decomposing an argument into fragments. Keep paragraphs to 2-4 sentences. Short paragraphs pull the reader forward. Every sentence should move the story forward. If a sentence only exists to sound good, cut it.

**Emphasis:** Bold only when introducing an unfamiliar term or for rare high-impact moments. Overusing bold destroys its power. Use italics where you'd stress the word if reading aloud.

**Clarity:** Lead with concrete examples, not abstractions. Explain unfamiliar terms at point of use. If a section makes your eyes glaze over, simplify it. Code examples should err toward simplicity over realism.

**Endings:** Point forward (further reading, open questions, what to try next). Don't restate what was just said.

**Rhythm:** Mix short and long sentences. A paragraph of uniformly long sentences puts readers to sleep. A short sentence after a complex one lands harder. Read paragraphs back and listen for monotony. Let thoughts connect the way they would in speech. Don't chop a flowing argument into dramatic fragments for effect.

**Credibility:** Write from real experience, not hypotheticals. Say when something does NOT work, not just when it does. Contra-indications build more trust than sales pitches. When you are speculating or lack data, say so explicitly ("I haven't tested this, but...", "Without more evidence, my guess is..."). Flagging uncertainty builds trust; pretending to know destroys it.

**Read aloud test:** If a sentence sounds awkward spoken, rewrite it.

---

## Key Design Decisions

See [docs/system-evolution.md](docs/system-evolution.md) for the full history. The most important lessons for working on the plugin:

### PITFALL: Splitting LLM Reasoning Across Multiple Agents

Do not split a task that requires holistic reasoning across multiple agents connected by deterministic glue. When an LLM needs to cross-reference findings (e.g., risk findings should inform next steps, market gaps should inform pivot rationale), it does this naturally when it has full context in a single call.

**The test**: If you're adding a validator to catch inconsistencies between two agents' outputs, ask whether a single agent with both agents' context would produce the inconsistency in the first place. If not, you have an architecture problem, not a validation problem.

**Evidence**: A single LLM call with upstream context scored 8 PASS / 4 PARTIAL / 0 FAIL on report quality criteria, versus 1 PASS / 3 PARTIAL / 8 FAIL from a 4-agent + 6-validator pipeline processing the same inputs.

**When multi-agent IS justified**: When agents need different tools (e.g., web search vs. analysis), different model tiers, or operate on genuinely independent tasks. The current 8 agents are split along these lines.

### PITFALL: LLM Text Overriding Deterministic Rules

Never let LLM-generated text override deterministic safety rules. If the system needs a property enforced, make the rule unconditional in hook scripts. The LLM's job is qualitative judgment (scoring, evaluating evidence). The hook scripts' job is deterministic rules (SOM arithmetic, schema validation, phase prerequisites). Keep this boundary sharp.

### PITFALL: Agents Re-deriving Known Values

Pass known values (e.g., GO/NO-GO recommendation, concept anchors) explicitly to downstream agents via files. Never embed them in prose for re-extraction. When a command orchestrates agents, it should read the upstream output file and provide the relevant values as context to the next agent. Treat agent inputs like function arguments.

### PITFALL: Evidence Must Match Evaluation

Don't create scoring dimensions in agent prompts that the upstream evidence can't populate. If you can't name the specific data source that populates a score, delete the score. Hallucinated scoring dimensions produce confident-sounding but unfounded analysis.

### Agent UX Standards

When writing or modifying command files that orchestrate agents, follow these patterns:

**Roadmap first.** Before launching any agents, emit a numbered step list showing what will happen, which steps involve user decisions, and roughly how long the phase takes. The user should see the plan before execution begins.

**Frame every agent call.** Before each agent call, state what the agent will do and why in plain language (not "Launching market-researcher agent" but "Checking if anyone else is solving this problem and how big the opportunity is"). After each agent call, read the output file and emit a one-line digest of what was found.

**Purpose over procedure.** Transition messages should explain why the next step exists relative to the user's goal, not just name the step. "Research gathered. Compiling a neutral summary for your review." not "Now launching Step 3: Research Brief."

**Guided questions.** When asking the user for review or approval, provide specific dimensions to evaluate (e.g., "Is the problem statement right? Are we missing competitors?") rather than open-ended "anything to correct?" prompts. Always include a low-effort escape ("say 'looks good' to continue").

**Soft checkpoints.** Between major steps, give the user a visible window to interject without requiring a response. State what just happened and what's about to happen. The user can steer if they want; the system proceeds if they don't.

**No blocking without reason.** Only use hard gates (explicit approval questions) at phase boundaries. Mid-phase checkpoints should be informational, not blocking. Too many mandatory stops make the workflow feel heavy.

---

## Plugin Marketplace Standards

Patterns derived from scanning `anthropics/claude-plugins-official` and external plugins (Stripe, etc.).

### Agent Frontmatter (Required)

Every agent in `agents/` must have `name` and `description` in YAML frontmatter. CI validates this. The `description` field should explain what the agent does and when to use it.

```yaml
---
name: your-agent
description: What it does and when to use it.
tools: Read, Write
model: sonnet
---
```

### Command Frontmatter (Required)

Every command in `commands/` must have `description` and `allowed-tools`. The `allowed-tools` field pre-approves tools for the command's execution so users don't get permission prompts for every file read/write during a run.

```yaml
---
description: What this command does
argument-hint: [optional argument description]
allowed-tools: Read, Write, Edit, Bash, Glob, Agent
---
```

**Tool selection per command:** Include the union of tools the orchestrating command and all its subagents need. Commands that launch agents using `WebSearch`/`WebFetch` (validate, design, haytham) must include those. Commands that only launch file-based agents (specify, plan) omit them.

### marketplace.json

Located at `.claude-plugin/marketplace.json`. Must include `$schema` for validation. Valid categories: `development`, `productivity`, `security`, `testing`, `design`, `database`, `monitoring`, `deployment`, `learning`.

**Version management:** The `version` field lives only in `marketplace.json` (inside `plugins[0]`), not in `plugin.json`. Claude Code uses this version to determine whether to update the plugin. Bump it with every release. See the [plugins reference](https://code.claude.com/docs/en/plugins-reference#version-management).

### Submission

Submit to Anthropic's official marketplace via the form at `claude.ai/settings/plugins/submit` or `platform.claude.com/plugins/submit`. PRs to the `anthropics/claude-plugins-official` repo are auto-closed.
