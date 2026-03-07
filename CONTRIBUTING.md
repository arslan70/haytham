# Contributing to Haytham

Haytham is a Claude Code plugin. All agents are markdown files, all commands are markdown files, and testing is a mix of deterministic sanity checks and LLM-as-judge review skills.

---

## Project Structure

```
agents/           # 8 specialist agents (markdown with YAML frontmatter)
commands/         # User-facing commands (/haytham, /haytham:validate, etc.)
hooks/            # PreToolUse/PostToolUse hook definitions
scripts/          # Deterministic validation (schema, SOM arithmetic)
tests/            # Sanity tests (pytest, no API keys needed)
.claude-plugin/   # Plugin manifest and marketplace metadata
```

See CLAUDE.md for the full file map and conventions.

---

## Development Setup

```bash
git clone https://github.com/arslan70/haytham.git
cd haytham
```

No dependencies to install for most work. Agent prompts and command files are plain markdown. Tests require Python 3.10+ and pytest.

---

## Before Every Commit

```bash
python3 -m pytest tests/test_plugin_sanity.py -v
```

This runs 90+ structural checks: frontmatter validation, script syntax, cross-reference integrity, schema validation, and marketplace JSON structure. Takes under a second. If it fails, don't commit.

---

## What to Contribute

| Area | Difficulty | Examples |
|------|-----------|----------|
| Agent prompts | Beginner | Improve clarity, add missing instructions, fix output quality |
| Command files | Beginner | Improve UX framing, transition messages, review questions |
| Hook scripts | Intermediate | Add new validation rules, improve schema checks |
| Review skills | Intermediate | Add new review dimensions, improve evaluation criteria |
| Test coverage | Beginner | Add edge cases to sanity tests |

---

## Modifying an Agent

Edit the agent's markdown file in `agents/`. Each file has YAML frontmatter (`name`, `description`, `tools`, `model`) and a system prompt body.

1. Read the agent file and understand its current instructions
2. Make your changes to the prompt
3. Run sanity tests: `python3 -m pytest tests/test_plugin_sanity.py -v`
4. Run a functional test: `/haytham:validate "a test idea"` and check output quality
5. Run the relevant review skill(s) against the output (see Testing Strategy below)

## Modifying a Command

Edit the command file in `commands/`. Follow the Agent UX Standards in CLAUDE.md:

- Roadmap before first agent call
- Pre-agent framing (purpose, not procedure)
- Post-agent digest (one-line summary from output file)
- Guided review questions with low-effort escape
- Soft checkpoints (informational, not blocking)

---

## Testing Strategy

Haytham uses three testing layers. Each catches different kinds of problems.

### Layer 1: Sanity Tests (deterministic, fast, every commit)

```bash
python3 -m pytest tests/test_plugin_sanity.py -v
```

Checks structural integrity: frontmatter fields, script syntax, cross-references (agents referenced in commands exist, hook script paths resolve), schema validation logic, marketplace JSON. Runs in under a second, no API keys needed.

**What it catches:** Broken references, missing frontmatter, syntax errors, schema regressions.

**What it misses:** Everything about output quality, UX compliance, and content correctness.

### Layer 2: Review Skills (LLM-as-judge, per dimension, after test runs)

After running the plugin against a test idea, run review skills to evaluate output quality across five dimensions. Each skill checks prerequisites (required files) before evaluating, so it won't hallucinate on missing data.

```bash
# 1. Run the plugin
/haytham:validate "a gym community leaderboard with anonymous handles"

# 2. Save the conversation transcript to a file (manual step)

# 3. Run review skills
/haytham:ux-review path/to/transcript.md     # UX compliance (needs transcript)
/haytham:review-depth                         # Analysis depth (needs Phase 1)
/haytham:review-consistency                   # Cross-stage consistency (needs Phase 1+)
/haytham:review-fidelity                      # Concept drift detection (needs Phase 1+)
/haytham:review-actionability                 # Spec implementability (needs Phases 2-4)
```

#### Review Dimensions

| Skill | What It Evaluates | Required Input |
|-------|-------------------|----------------|
| `ux-review` | Roadmap, agent framing, transitions, guided questions, checkpoints, completion summary | Transcript file |
| `review-depth` | Evidence quality, source grounding, reasoning chains, risk specificity | Phase 1 output files |
| `review-consistency` | Cross-stage agreement, traceability, anchor preservation | Phase 1 minimum, scales with more phases |
| `review-fidelity` | Concept drift from original idea through each pipeline stage | project.yaml + Phase 1 minimum |
| `review-actionability` | Scope clarity, capability precision, story completeness, acceptance criteria testability | Phases 2-4 complete |

#### Finding Format

Every review skill produces findings in a consistent structure:

**Evaluation table** scores each criterion as PASS, PARTIAL, or FAIL with quoted evidence:

```
| # | Criterion              | Result  | Evidence |
|---|------------------------|---------|----------|
| 1 | Problem Articulation   | PASS    | "Solo gym-goers aged 20-35..." |
| 2 | Market Sizing Basis    | FAIL    | "$7.4B TAM" with no source cited |
```

**Suggested Improvements** follow the table. For each PARTIAL or FAIL, the skill states:
1. What was observed (with a quote from the output)
2. Which file needs the fix (`agents/*.md`, `commands/*.md`, `scripts/*.py`)
3. The **fix type**: missing instruction, weak instruction, wrong instruction, or structural gap

This classification makes every finding directly actionable. You know which file to open and what kind of change to make.

#### When to Run Review Skills

- **After agent prompt changes**: Run `review-depth` and `review-consistency` to verify output quality didn't regress.
- **After command file changes**: Run `ux-review` to verify UX patterns are followed.
- **After adding a new pipeline stage**: Run `review-consistency` and `review-fidelity` to verify the new stage integrates cleanly.
- **After a full 4-phase run**: Run all five skills for a comprehensive quality check.
- **Not on every commit.** Review skills require a full plugin run (expensive). Use them after meaningful changes, not routine edits.

#### Limitations

Review skills use LLM-as-judge, which means:
- Results are non-deterministic. The same output may score differently on different runs. Treat findings as signals, not verdicts.
- If a finding appears consistently across multiple reviews, it's real.
- Review skills can't measure timing, perceived wait time, or the feeling of being stuck. Those require manual observation during a live run.

### Layer 3: Manual Spot-Check (human judgment, after significant changes)

Run the plugin and watch the output in real time. No substitute for this when evaluating:
- Whether the interaction rhythm feels right
- Whether wait times are painful
- Whether the roadmap and framing actually help orient you as a user
- Whether the final output is something you'd act on

Do this once after any batch of UX or prompt changes. The review skills can verify structure, but only a human can judge whether it feels right.

### Testing Workflow Summary

```
Edit agent/command → Sanity tests (every time)
                   → Plugin run + review skills (after meaningful changes)
                   → Manual spot-check (after significant UX or prompt changes)
```

---

## Submitting Changes

1. Branch from `main` with a descriptive name (`feat/improve-market-researcher-prompt`, `fix/consistency-drift`)
2. Keep PRs focused on one change
3. Run sanity tests before pushing
4. If you changed an agent prompt or command file, include a summary of review skill results in the PR description (which dimensions you checked, scores, notable findings)

### Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add source-quality markers to research briefer
fix: strengthen concept anchor preservation in report synthesizer
docs: update contributing guide with review skill workflow
test: add frontmatter validation for new review commands
```
