# Report Quality Redesign: DSPy PoC Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prove that a single LLM with upstream context produces a better validation report than the current 4-agent + 6-validator pipeline.

**Architecture:** Use DSPy to define a report synthesis Signature, feed it idea-analysis + market-research outputs, generate reports, and manually compare against current pipeline output. The existing pipeline is untouched.

**Tech Stack:** DSPy, AWS Bedrock (via LiteLLM), existing test fixtures

**Issue:** [#12](https://github.com/arslan70/haytham/issues/12) | **Branch:** `feature/report-quality-redesign`

---

## Context

### Why we're doing this

The current validation pipeline (risk-assessment + pivot-strategy + validation-summary) has systemic quality gaps (S1-S10 in issue #12). The root cause is over-engineering: a scorer agent invents numeric scores, a narrator turns them back into prose, and 6 validators patch inconsistencies. A single LLM reasoning holistically over the same context should produce more coherent output.

### What we have

- 6 test ideas in `tests/fixtures/test_ideas.json` (T1-T6)
- Cached concept_expansion outputs for T1, T2 in `tests/fixtures/agent_outputs/concept_expansion/`
- No cached market-context outputs yet (upstream_outputs dirs are empty)
- Bedrock models configured via env vars: `BEDROCK_REASONING_MODEL_ID`, `BEDROCK_HEAVY_MODEL_ID`

### Quality checklist (for manual review)

- [ ] Next steps are specific to THIS idea, not generic template text
- [ ] Financial section includes realistic cost/revenue estimates
- [ ] TAM/SAM/SOM is scoped to the idea's realistic reach (not the broadest industry)
- [ ] TAM/SAM/SOM shows arithmetic (formula, inputs, result)
- [ ] No tautological claims (echoing founder's words as "validated")
- [ ] Sections cross-reference each other
- [ ] Domain-specific risks flagged for regulated industries (T6: wellness/HIPAA)
- [ ] Network dependencies identified for multi-sided ideas (T4: marketplace)
- [ ] Pre-build validation experiment proposed for riskiest assumption
- [ ] Report reads as one coherent narrative, not independent sections
- [ ] UVP does not contain fabricated quantitative metrics

---

## Task 1: Add DSPy Dependency

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add dspy to optional dependencies**

Add a new optional dependency group in `pyproject.toml`:

```toml
dspy-poc = ["dspy>=2.6"]
```

Add it under the `[project.optional-dependencies]` section, after `ollama`.

**Step 2: Install**

Run: `uv sync --extra dspy-poc`
Expected: DSPy and its dependencies (including litellm) install successfully.

**Step 3: Verify import**

Run: `uv run python -c "import dspy; print(dspy.__version__)"`
Expected: Version number prints (2.6.x or higher).

**Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "build: add dspy optional dependency for report quality PoC"
```

---

## Task 2: Verify DSPy + Bedrock Integration

**Files:**
- Create: `tests/dspy_poc/__init__.py`
- Create: `tests/dspy_poc/test_bedrock_smoke.py`

**Step 1: Create directory and init**

Create `tests/dspy_poc/__init__.py` (empty file).

**Step 2: Write a smoke test**

Create `tests/dspy_poc/test_bedrock_smoke.py`:

```python
"""Smoke test: verify DSPy can talk to Bedrock."""

import os

import dspy


def main():
    model_id = os.environ.get("BEDROCK_HEAVY_MODEL_ID")
    region = os.environ.get("AWS_REGION", "us-east-1")

    if not model_id:
        print("BEDROCK_HEAVY_MODEL_ID not set, skipping smoke test")
        return

    lm = dspy.LM(
        f"bedrock/{model_id}",
        region_name=region,
    )
    dspy.configure(lm=lm)

    qa = dspy.Predict("question -> answer")
    result = qa(question="What is 2+2?")
    print(f"Answer: {result.answer}")
    print("Smoke test PASSED")


if __name__ == "__main__":
    main()
```

**Step 3: Run smoke test**

Run: `uv run python tests/dspy_poc/test_bedrock_smoke.py`
Expected: Prints an answer and "Smoke test PASSED". If LiteLLM has Bedrock issues, we'll debug here.

**Step 4: Commit**

```bash
git add tests/dspy_poc/
git commit -m "test: add DSPy + Bedrock smoke test"
```

---

## Task 3: Generate Baseline Reports from Current Pipeline

**Why:** We need current pipeline output for comparison. Start with T1 and T6 (one simple web app, one regulated wellness app with concept fidelity constraints).

**Step 1: Run current pipeline for T1**

Run the Haytham pipeline for test idea T1 (gym leaderboard). Use the Streamlit UI or CLI:

```bash
make run
```

Paste T1's idea text and let the pipeline complete through validation-summary.

**Step 2: Save T1 baseline**

```bash
mkdir -p tests/dspy_poc/baselines
cp session/validation-summary/output.md tests/dspy_poc/baselines/T1_baseline.md
```

Also save the upstream outputs we'll need as fixtures:

```bash
mkdir -p tests/dspy_poc/fixtures/T1
cp session/idea-analysis/output.md tests/dspy_poc/fixtures/T1/idea-analysis.md
cp session/market-context/output.md tests/dspy_poc/fixtures/T1/market-context.md
```

**Step 3: Run current pipeline for T6**

Reset session and run for T6 (Power of 8 wellness app):

```bash
make reset
make run
```

Paste T6's idea text and let the pipeline complete.

**Step 4: Save T6 baseline and fixtures**

```bash
cp session/validation-summary/output.md tests/dspy_poc/baselines/T6_baseline.md
mkdir -p tests/dspy_poc/fixtures/T6
cp session/idea-analysis/output.md tests/dspy_poc/fixtures/T6/idea-analysis.md
cp session/market-context/output.md tests/dspy_poc/fixtures/T6/market-context.md
```

**Step 5: Commit**

```bash
git add tests/dspy_poc/baselines/ tests/dspy_poc/fixtures/
git commit -m "test: add baseline reports and upstream fixtures for T1 and T6"
```

---

## Task 4: Define DSPy Signature and Report Prompt

**Files:**
- Create: `tests/dspy_poc/signatures.py`

**Step 1: Define the Signature**

Create `tests/dspy_poc/signatures.py`:

```python
"""DSPy Signature for single-agent report synthesis."""

import dspy


REPORT_INSTRUCTIONS = """\
You are a startup validation analyst. Given a structured idea analysis and market/competitive \
research, produce a comprehensive validation report.

## Report Sections (produce ALL of these)

### 1. Executive Summary
- State the GO / PIVOT / NO-GO recommendation upfront
- Identify the single key tension (the one factor most likely to make or break this idea)
- State your confidence level and why

### 2. Problem & Market Analysis
- Summarize the core problem and who experiences it
- Market sizing: TAM/SAM/SOM scoped to the idea's REALISTIC reach (not the broadest industry)
- Show arithmetic: state formula, state inputs, show calculation = result
- Tag each number as [verified: source] or [estimate: basis]
- If the idea targets a niche (e.g., one therapist's patients), size the market to that niche

### 3. Competitive Landscape
- Key competitors with traction evidence
- Pricing benchmarks
- Gaps the idea could exploit
- Switching costs and lock-in factors

### 4. Claims & Evidence Analysis
- Identify the idea's key testable hypotheses (NOT the founder's stated constraints)
- For each claim: what evidence supports/contradicts it from the market research?
- Do NOT treat the founder's own statements as "validated claims"
- Flag any claim where the only evidence is the idea description itself

### 5. Risk Assessment
- Categorize risks: market, technical, operational, financial
- If the idea is in a regulated domain (health, fintech, education, food, legal), flag specific \
compliance requirements (HIPAA, PCI-DSS, COPPA, etc.) and estimate compliance cost impact on MVP
- If the idea has network dependencies (marketplace, social, multi-user sessions), flag the \
cold-start problem, estimate minimum viable user counts, and assess distribution viability
- Rank risks by severity and likelihood

### 6. Dealbreaker Check
Answer these three questions directly:
- Problem Reality: Is there evidence real people experience this problem?
- Channel Access: Can the founder realistically reach target users?
- Regulatory/Ethical: Are there legal or ethical barriers that make this non-viable?
If any answer is "no" with evidence, the recommendation MUST be NO-GO.

### 7. Financial Feasibility
- MVP build cost range (order of magnitude, based on technical complexity)
- 2-3 revenue model options with back-of-napkin unit economics
- Break-even scenario under stated assumptions
- This is NOT an accounting exercise. Ranges and estimates are expected and useful.

### 8. Go/No-Go Recommendation
- State the recommendation with clear reasoning
- Cite specific evidence from the sections above
- Address counter-signals: if the recommendation is positive, explain why negative signals \
don't change it. If negative, acknowledge what IS working.

### 9. Validate Before You Build
- Identify the single riskiest assumption
- Propose 1-2 low-cost experiments ($0-$500) to test it before writing code
- Define success/failure criteria for each experiment
- Estimate cost and timeline

### 10. Next Steps
- 3-5 actions, ordered by priority (riskiest assumption first)
- Each step MUST include: timeframe (Week 1, Week 2-3, etc.), specific action, and decision \
criteria ("if X, proceed; if Y, reconsider")
- These must be specific to THIS idea, not generic startup advice

### 11. Pivot Options (if applicable)
- If recommendation is PIVOT or if significant risks exist
- For each pivot: what changes, what stays, why it's worth considering
- Reference specific competitive gaps or risk findings that motivate the pivot

## Rules
- Cross-reference between sections. Risk findings should appear in Next Steps. Market gaps \
should appear in Pivot rationale. Claims should reference market research evidence.
- Never fabricate quantitative metrics in the UVP. If no data supports a number, say \
"[suggested target, needs validation]".
- Write as one coherent narrative, not isolated sections.
"""


class ReportSynthesis(dspy.Signature):
    """Produce a startup validation report from idea analysis and market research."""

    idea: str = dspy.InputField(desc="The original startup idea as stated by the founder")
    idea_analysis: str = dspy.InputField(
        desc="Structured concept expansion: problems, segments, UVP, lean canvas"
    )
    market_research: str = dspy.InputField(
        desc="Market intelligence and competitor analysis from web research"
    )

    report: str = dspy.OutputField(desc="Complete validation report covering all 11 sections")
```

**Step 2: Commit**

```bash
git add tests/dspy_poc/signatures.py
git commit -m "feat: define DSPy Signature and prompt for report synthesis"
```

---

## Task 5: Build the Synthesis Runner

**Files:**
- Create: `tests/dspy_poc/synthesize.py`

**Step 1: Write the runner script**

Create `tests/dspy_poc/synthesize.py`:

```python
"""Run DSPy report synthesis for a test idea."""

import json
import os
import sys
from pathlib import Path

import dspy

from tests.dspy_poc.signatures import REPORT_INSTRUCTIONS, ReportSynthesis

FIXTURES_DIR = Path(__file__).parent / "fixtures"
OUTPUTS_DIR = Path(__file__).parent / "outputs"
IDEAS_FILE = Path(__file__).parents[1] / "fixtures" / "test_ideas.json"


def load_idea(idea_id: str) -> str:
    """Load the raw idea text from test_ideas.json."""
    with open(IDEAS_FILE) as f:
        data = json.load(f)
    for idea in data["ideas"]:
        if idea["id"] == idea_id:
            return idea["idea"]
    raise ValueError(f"Idea {idea_id} not found in {IDEAS_FILE}")


def load_fixture(idea_id: str, stage: str) -> str:
    """Load upstream fixture output for a given idea and stage."""
    fixture_path = FIXTURES_DIR / idea_id / f"{stage}.md"
    if not fixture_path.exists():
        raise FileNotFoundError(
            f"Fixture not found: {fixture_path}\n"
            f"Run the current pipeline for {idea_id} and save fixtures first (see Task 3)."
        )
    return fixture_path.read_text()


def synthesize_report(idea_id: str) -> str:
    """Generate a validation report for the given idea using DSPy."""
    model_id = os.environ.get("BEDROCK_REASONING_MODEL_ID")
    if not model_id:
        model_id = os.environ.get("BEDROCK_HEAVY_MODEL_ID")
    region = os.environ.get("AWS_REGION", "us-east-1")

    if not model_id:
        print("Set BEDROCK_REASONING_MODEL_ID or BEDROCK_HEAVY_MODEL_ID in .env")
        sys.exit(1)

    lm = dspy.LM(
        f"bedrock/{model_id}",
        region_name=region,
        max_tokens=8000,
    )
    dspy.configure(lm=lm)

    idea = load_idea(idea_id)
    idea_analysis = load_fixture(idea_id, "idea-analysis")
    market_research = load_fixture(idea_id, "market-context")

    predict = dspy.Predict(ReportSynthesis, instructions=REPORT_INSTRUCTIONS)
    result = predict(
        idea=idea,
        idea_analysis=idea_analysis,
        market_research=market_research,
    )

    return result.report


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m tests.dspy_poc.synthesize <IDEA_ID>")
        print("Example: python -m tests.dspy_poc.synthesize T1")
        sys.exit(1)

    idea_id = sys.argv[1].upper()
    print(f"Generating report for {idea_id}...")

    report = synthesize_report(idea_id)

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUTS_DIR / f"{idea_id}_output.md"
    output_path.write_text(report)

    print(f"Report saved to {output_path}")
    print("---")
    print(report)


if __name__ == "__main__":
    main()
```

**Step 2: Commit**

```bash
git add tests/dspy_poc/synthesize.py
git commit -m "feat: add DSPy report synthesis runner"
```

---

## Task 6: Generate First Report and Review

**Step 1: Run synthesis for T1**

Run: `uv run python -m tests.dspy_poc.synthesize T1`
Expected: Report prints to stdout and saves to `tests/dspy_poc/outputs/T1_output.md`.

**Step 2: Manual review**

Compare `tests/dspy_poc/outputs/T1_output.md` against `tests/dspy_poc/baselines/T1_baseline.md` using the quality checklist above. Copy-paste both to Claude for review.

**Step 3: Run synthesis for T6**

Run: `uv run python -m tests.dspy_poc.synthesize T6`

This is the key test: T6 is a regulated wellness app with concept fidelity constraints. The report should flag HIPAA-like considerations, scope the market to one psychologist's patient base (not billions), and preserve the 1:7 group structure.

**Step 4: Manual review of T6**

Compare against `tests/dspy_poc/baselines/T6_baseline.md`. Pay special attention to:
- Is TAM/SAM/SOM scoped to a solo psychologist's practice, not the global wellness industry?
- Are regulatory risks (health data, patient privacy) flagged?
- Is the 1:7 group structure preserved in the analysis?

**Step 5: Save outputs and commit**

```bash
git add tests/dspy_poc/outputs/
git commit -m "test: add first DSPy-generated reports for T1 and T6"
```

---

## Task 7: Iterate on Prompt (Repeat as Needed)

Based on manual review feedback:

**Step 1: Update the prompt**

Modify `REPORT_INSTRUCTIONS` in `tests/dspy_poc/signatures.py` based on review findings. Common adjustments:
- Strengthen sections that were weak
- Add examples for sections where the LLM was too generic
- Adjust market sizing guidance if numbers were still unrealistic

**Step 2: Re-generate and re-review**

```bash
uv run python -m tests.dspy_poc.synthesize T1
uv run python -m tests.dspy_poc.synthesize T6
```

**Step 3: Compare with previous iteration**

Keep previous outputs for comparison. Rename or version them if needed.

**Step 4: Commit each iteration**

```bash
git add tests/dspy_poc/
git commit -m "refine: iteration N - [what changed based on feedback]"
```

Repeat Tasks 6-7 until reports meet quality expectations.

---

## Task 8: Decision Gate

After iteration converges:

**If PoC succeeds (single-agent reports are better):**
- [ ] Write ADR documenting the decision to simplify the pipeline
- [ ] Plan the migration (replace risk-assessment + pivot-strategy + validation-summary with single stage)
- [ ] Identify what to preserve (knockouts as concepts, counter-signal reasoning)

**If PoC fails (current pipeline has advantages the single agent can't match):**
- [ ] Document which specific aspects failed
- [ ] Decide: fix within current architecture (original S1-S10 plan) or try hybrid approach
- [ ] Write ADR documenting the findings

---

## Directory Structure (Final)

```
tests/dspy_poc/
  __init__.py
  signatures.py           # DSPy Signature + report prompt
  synthesize.py            # Runner script
  test_bedrock_smoke.py    # Bedrock integration smoke test
  fixtures/                # Upstream outputs from current pipeline
    T1/
      idea-analysis.md
      market-context.md
    T6/
      idea-analysis.md
      market-context.md
  baselines/               # Current pipeline validation-summary output
    T1_baseline.md
    T6_baseline.md
  outputs/                 # DSPy-generated reports
    T1_output.md
    T6_output.md
```
