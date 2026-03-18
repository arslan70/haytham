# Plan: Evaluation Framework for Haytham

## Context

Haytham has strong deterministic validation (schema checks, phase gating hooks, cross-reference tests) but no automated evaluation of *output quality*. We can't answer: "Did the agent produce a good analysis?" or "Does this command trigger correctly from user prompts?"

Two tools from the Claude ecosystem are relevant:
1. **Anthropic eval patterns** (LLM-graded scoring): Likert scales, binary classification, ordinal scales with rubrics. Best practice: use a different model as grader than the one that generated the output.
2. **Skill-creator evals** (built into Claude Code): Parallel eval runs, blind A/B testing, benchmark mode. Useful if Haytham ships as skills; less relevant to our agent/command architecture.

The plan focuses on (1). Skill-creator evals are noted but deferred since Haytham uses agents/commands, not skills. Triggering evals (Phase 1) use the Claude Agent SDK directly with no third-party dependencies.

## Implementation: 3 Phases

### Phase 1: Component Triggering Evals (Agent SDK)

**Goal:** Verify commands and agents activate from the right user prompts. No third-party dependencies. Uses the Claude Agent SDK directly.

**Approach:** A Python test script sends user prompts to the Claude API with Haytham's plugin loaded, then checks which command or agent was triggered. Each test case is a prompt + expected activation pair.

**Files to create:**
- `evals/triggering/scenarios.json` - test scenarios for all 9 agents + 11 commands
- `evals/triggering/run_triggering_evals.py` - sends prompts via Anthropic Messages API, checks tool_use responses for expected agent/command activation
- `evals/triggering/results/` - .gitignored, stores JSON results per run

**Scenario types per component** (5 each):
- `direct`: explicit command invocation ("validate this idea")
- `paraphrased`: natural language that should trigger the same component ("is this idea any good?")
- `edge_case`: ambiguous or minimal input (empty string, single word, non-English)
- `negative`: prompts that should NOT trigger this component ("write me a poem")
- `semantic`: prompts near the boundary between two commands ("analyze the market" - should this be validate or design?)

**Config highlights:**
- Model: `claude-sonnet-4-20250514`, timeout 30s per scenario
- Pass threshold: 0.85 accuracy per component
- Read-only: disallow Write/Edit/Bash in the test harness to prevent side effects

**Run:**
```bash
python3 evals/triggering/run_triggering_evals.py --all
python3 evals/triggering/run_triggering_evals.py --component validate  # single command
```

**Cost:** ~$3-5/run. Run on PRs that touch `agents/` or `commands/`.

---

### Phase 2: Output Quality Evals (LLM-Graded)

**Goal:** Convert the 4 output-quality review commands into automated, scorable eval rubrics. `ux-review` is handled separately (see below). No new criteria invented, just codifying what already exists.

**Source mapping:**

| Review Command | Criteria Count | Target Rubric Files |
|---|---|---|
| `review-depth` | 7 | idea-analysis, competitor-research, market-research, validation-report |
| `review-fidelity` | 7+ | idea-analysis, capabilities, architecture, openspec, cross-phase |
| `review-consistency` | 10 | cross-phase (deterministic where possible) |
| `review-actionability` | 8 | capabilities, architecture, openspec |

Note: `review-depth` criteria 2 (Competitor Evidence) and 4 (Sentiment and Demand Signals) primarily target `competitor-research.md` with fallback to `market-research.md`. The `competitor-research.json` rubric must encode this fallback.

**ux-review (deferred):** The `ux-review` command evaluates runtime UX (roadmap shown, pre/post-agent framing, soft checkpoints) from a conversation transcript, not from session files. Automating it requires capturing or simulating a full interactive run and extracting the user-facing messages. This is deferred to Phase 3, where the e2e pipeline runner can capture transcripts and grade them against `ux-review` criteria.

**Files to create:**
- `evals/quality/reference_ideas.json` - 4 test ideas (web app, CLI tool, API service, marketplace per CLAUDE.md requirement)
- `evals/quality/grading_rubrics/` - one JSON per agent output, criteria extracted from review commands
- `evals/quality/run_quality_evals.py` - orchestrator that loads rubrics, runs grading calls via Anthropic Messages API, writes results
- `evals/quality/results/` - .gitignored, stores JSON results per run

**Grading model:** Agents mostly run on sonnet, so grade with opus. spec-generator runs on opus, so also grade with opus using a strict rubric to compensate for self-grading bias. The alternative (sonnet grading opus) risks the grader being less capable than the generator, missing subtle quality issues that a stronger model would catch. Strict rubrics with concrete PASS/PARTIAL/FAIL anchors reduce self-grading bias more reliably than using a weaker grader. Each criterion has explicit anchors already defined in the review commands.

**Reference test ideas:**
1. `web-app`: "a gym community leaderboard with anonymous handles" (community platform)
2. `cli-tool`: "a CLI that scans codebases for security vulnerabilities and generates fix suggestions" (developer tool)
3. `api-service`: "a REST API that takes food photos and returns nutritional breakdowns" (API service)
4. `marketplace`: "a marketplace connecting freelance music tutors with students with scheduling and payments" (marketplace)

**Run:**
```bash
python3 evals/quality/run_quality_evals.py --idea web-app --session-dir .haytham/session/
python3 evals/quality/run_quality_evals.py --all  # all 4 ideas
```

**Output:** JSON with per-criterion scores, summary pass rate, and comparison against previous runs for regression detection (see Regression Detection below).

**Cost:** ~$3-8/idea. Full suite (~$25). Run weekly or before releases. Deterministic subset (schema checks) runs free in CI.

---

### Phase 3: End-to-End Pipeline Evals

**Goal:** Run the full pipeline against reference ideas, capture outputs, verify cross-phase consistency, and grade runtime UX.

**Files to create:**
- `evals/e2e/consistency_checks.py` - automates the 10 checks from `review-consistency.md` (deterministic where possible: ID matching for traceability, LLM-graded for semantic checks)
- `evals/e2e/run_e2e_eval.py` - orchestrates a full pipeline run + grading
- `evals/e2e/gate_fixtures/` - pre-canned gate responses per reference idea (see Interactive Gate Bypass below)
- `evals/e2e/golden_outputs/` - reference outputs from known-good runs (see Golden Output Lifecycle below)
- `evals/e2e/ux_grader.py` - grades captured transcripts against `ux-review` criteria (7 checks from `commands/ux-review.md`)

#### Interactive Gate Bypass

The pipeline has interactive gates (founder review at phase boundaries). For automated runs:

1. **Fixture file per idea:** `evals/e2e/gate_fixtures/web-app.json` contains pre-canned responses for each gate (e.g., research brief approval: "looks good", MVP scope review: "looks good"). Fixtures simulate a founder who approves without changes, testing the happy path.
2. **Environment flag:** `run_e2e_eval.py` sets `HAYTHAM_EVAL_MODE=true`. Command files check this flag and read gate responses from the fixture file instead of prompting.
3. **Limitation acknowledged:** Pre-canned gates don't test the "founder requests changes" path. That remains a manual test scenario. The automated run validates that the pipeline produces consistent, quality output when gates are approved.

#### Golden Output Lifecycle

Golden outputs are reference baselines, not exact-match targets.

1. **Creation:** After a human-reviewed run scores well on quality evals (Phase 2), copy the session to `golden_outputs/{idea}/`. Tag the commit.
2. **Comparison method:** LLM-graded semantic similarity, not string matching. The grader checks: same capabilities identified? Same architecture decisions? Same risk themes? Scored as EQUIVALENT/DRIFTED/DIVERGED per section.
3. **Refresh trigger:** Golden outputs are refreshed when agent prompts change materially (not typo fixes). The PR that changes an agent prompt should note whether golden outputs need refresh. If quality eval scores improve after the change, refresh the golden outputs.
4. **Staleness guard:** `run_e2e_eval.py` warns if golden outputs are older than the most recent commit touching `agents/`. This is advisory, not blocking.

#### UX Evaluation

The e2e runner captures the orchestrator's user-facing output (agent framing messages, transition text, gate prompts) into a transcript file. `ux_grader.py` evaluates this transcript against the 7 criteria from `commands/ux-review.md`: roadmap, pre-agent framing, post-agent digest, purpose transitions, guided questions, soft checkpoints, completion summary.

**Run:**
```bash
# Deterministic consistency checks on existing session (free)
python3 evals/e2e/consistency_checks.py --session-dir .haytham/session/

# Full pipeline run + grade (expensive, ~$25/idea)
python3 evals/e2e/run_e2e_eval.py --idea web-app --live

# UX grading on a captured transcript (requires a live run first)
python3 evals/e2e/ux_grader.py --transcript evals/e2e/results/web-app/transcript.md
```

**Cost:** ~$25-40/idea for live runs. Deterministic checks are free and can run in CI. UX grading adds ~$1-2/transcript.

---

## File Structure

```
evals/
  README.md

  triggering/                        # Phase 1
    scenarios.json
    run_triggering_evals.py
    results/                         # .gitignored

  quality/                           # Phase 2
    reference_ideas.json
    grading_rubrics/
      idea-analysis.json
      competitor-research.json       # includes market-research fallback
      market-research.json
      validation-report.json
      capabilities.json
      architecture.json
      openspec.json
      cross-phase.json
    run_quality_evals.py
    results/                         # .gitignored

  e2e/                               # Phase 3
    consistency_checks.py
    run_e2e_eval.py
    ux_grader.py
    gate_fixtures/
      web-app.json
      cli-tool.json
      api-service.json
      marketplace.json
    golden_outputs/                  # populated after human review, tagged
      web-app/
      cli-tool/
      api-service/
      marketplace/
    results/                         # .gitignored

  baselines/                         # Regression detection (checked in)
    latest.json                      # most recent committed baseline
```

## Regression Detection

Quality eval results in `evals/quality/results/` are gitignored (they contain LLM output and vary per run). Regression detection works by comparing against a committed baseline.

1. **Baseline file:** `evals/baselines/latest.json` stores the per-criterion pass rates from the last known-good run. Checked into git. Structure: `{ "idea": { "criterion": "PASS|PARTIAL|FAIL" } }`.
2. **Comparison:** `run_quality_evals.py --compare-baseline` loads `latest.json`, runs the eval, and reports regressions (any criterion that moved from PASS to PARTIAL/FAIL, or PARTIAL to FAIL).
3. **Threshold:** A single criterion regression is a warning. 3+ regressions across any idea, or any regression on a previously-PASS criterion in 2+ ideas, is a failure.
4. **Updating the baseline:** After a quality-improving change lands, run the full suite and commit the new `latest.json`. The commit message should note what changed and why scores improved.

## CI Integration

- **Every PR:** Existing sanity tests + deterministic consistency checks (free)
- **PRs touching agents/commands:** triggering eval (~$3-5) + baseline regression check (~$8)
- **Weekly schedule:** Full quality eval suite against all 4 reference ideas (~$25)
- **Pre-release (manual):** E2E pipeline run against 1-2 ideas with UX grading (~$55)

## Verification

After Phase 1: Run `python3 evals/triggering/run_triggering_evals.py --all` and confirm all 20 components have >0.85 accuracy.
After Phase 2: Run `run_quality_evals.py --idea web-app` against existing session output and confirm results JSON is generated with scores per criterion. Run `--compare-baseline` and confirm regression comparison works.
After Phase 3: Run `consistency_checks.py` against existing session and confirm all deterministic checks produce PASS/PARTIAL/FAIL results. Run a live e2e eval and confirm transcript capture + UX grading produces scores for all 7 UX criteria.

## Sources

- [Anthropic: Define success criteria and build evaluations](https://platform.claude.com/docs/en/test-and-evaluate/develop-tests) - Eval patterns and scorer types
- [Anthropic: Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) - Agent eval best practices
- [Skill-creator evals blog post](https://claude.com/blog/improving-skill-creator-test-measure-and-refine-agent-skills) - Parallel testing and A/B comparison
