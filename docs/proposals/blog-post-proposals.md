# Blog Post Proposals: Learnings from Building a Multi-Agent System

Soft engagement campaign targeting engineers building agentic systems. Tone: honest, inquiry-driven, practical. Not thought leadership fluff. Each post shares a specific problem we hit, what we tried, what worked, and asks readers if they've seen the same thing.

Host on GitHub Pages. Keep posts short (800-1200 words). Include code snippets or diagrams where they clarify.

---

## Post 1: "Your Agents Are Playing Telephone (and Your Ideas Are Getting Worse)"

**Hook**: We built a 10-stage agent pipeline. By stage 10, a distinctive startup idea had been quietly genericized into something you'd find in a template library. No single agent did anything wrong.

**Core problem**: Progressive concept degradation across multi-agent pipelines. Each agent slightly normalizes, slightly generalizes, slightly strips what makes an idea distinctive. After 10 stages, the output bears only surface resemblance to the input. We measured this with embedding similarity: 34% between original idea and final output.

**What we tried that didn't work**:
- Adding "preserve the original concept" to every prompt (agents comply superficially)
- Self-check instructions ("verify you haven't drifted from the original idea") -- agents can't see drift they caused
- Longer context windows (more tokens != better fidelity)

**What worked**: The Anchor Pattern. Extract a small (~500 token), immutable concept anchor at pipeline start. Core intent, explicit constraints, non-goals, invariants. Pass it verbatim to every downstream stage. Independent phase-boundary verifiers (separate LLM calls) check compliance at each gate.

**Research backing**: Kim et al. 2025 on multi-agent error amplification. Independent agents: 17.2x error amplification. With centralized verification: 4.4x. That's a 74% reduction.

**Question to readers**: If you're chaining agents, have you measured output fidelity against input? What's your number?

---

## Post 2: "LLM Self-Checks Are Theater"

**Hook**: We added self-check instructions to every agent prompt. "Before returning your output, verify that you honored the original constraints." It made us feel better. It didn't make the outputs better.

**Core problem**: Asking an LLM to check its own work in the same context window doesn't catch the errors that matter. The violation is often invisible to the agent. If the agent drifted from the original concept, it doesn't know it drifted because the drift happened gradually across stages it hasn't seen. It's checking its work against its own (already-drifted) understanding.

**The analogy**: It's like asking someone to proofread a translation by re-reading only their translation, without the original text. They'll fix grammar. They won't catch meaning shifts.

**What actually works**: Independent verification. A separate LLM call, with access to the original input, checking the output. Phase-boundary verifiers that sit between stages and compare against the immutable anchor. The checker must have context the worker doesn't.

**Broader pattern**: This maps to a well-known principle in systems design: the entity performing work should not be the sole entity verifying that work. Separation of concerns applies to LLM pipelines too.

**Question to readers**: Are you relying on in-prompt self-checks for quality? Have you measured whether they actually catch anything?

---

## Post 3: "The Line Between LLM Judgment and Deterministic Code"

**Hook**: Our scoring agent was deciding whether a startup idea was viable. It scored risk as HIGH, then recommended GO anyway because the narrative sounded optimistic. The LLM talked itself out of its own assessment.

**Core problem**: Where should LLM judgment end and deterministic code begin? We learned this the hard way. An LLM is good at qualitative assessment (scoring evidence, weighing trade-offs, evaluating nuance). It's unreliable at enforcing rules derived from those assessments. If it scores risk as HIGH, a separate deterministic rule should cap the verdict at PIVOT. The LLM should never be in a position to override that.

**Our scoring pipeline as a case study**:
- LLM scores 6 dimensions based on evidence (qualitative judgment, good use of LLM)
- Deterministic code: if any dimension <= 2, cap average at 3.0 (rule enforcement)
- Deterministic code: if risk is HIGH, downgrade GO to PIVOT (safety rule)
- Deterministic code: if 2+ unaddressed red flags, subtract 0.5 (penalty)
- LLM writes the human-readable narrative from the computed verdict (prose generation, good use of LLM)

**The principle**: LLMs judge. Code enforces. Keep this boundary sharp. String-based quality gates (length checks, phrase blocklists) in prompts cannot reliably verify substance and will be bypassed.

**Question to readers**: Where do you draw this line in your systems? Have you been burned by an LLM overriding its own structured output in the narrative layer?

---

## Post 4: "Treat Agent Inputs Like Function Arguments, Not Prose"

**Hook**: Our risk assessment agent correctly identified risk as HIGH. The downstream scoring agent received that assessment as a block of markdown text and had to grep for "Overall Risk Level: HIGH" somewhere in thousands of characters. Sometimes it found it. Sometimes it re-derived risk as MEDIUM from the surrounding text.

**Core problem**: When you have a known, structured value (risk_level = HIGH), embedding it in prose for downstream agents to re-extract is the agent equivalent of passing data through a lossy channel. The information is there, but the agent might interpret it differently, miss it, or override it based on context.

**The fix**: Pass known values as structured inputs. Treat agent inputs like function arguments.

```python
# Wrong: bury a known value in prose
scorer_query = f"...Risk Assessment:\n{risk_assessment_text}..."
# Agent greps for risk level in thousands of chars

# Right: pass known values explicitly
risk_level = state.get("risk_level")
init_scorecard(risk_level=risk_level)  # typed, pre-set, unambiguous
```

**The broader pattern**: If the system already knows something, don't ask the LLM to re-derive it. Every re-derivation is a chance for disagreement. This applies to anything the pipeline has already decided: classifications, scores, IDs, enum values. Pass them as data, not text.

**Question to readers**: How much of your inter-agent communication is structured data vs. prose? Have you audited whether downstream agents faithfully extract what upstream agents produced?

---

## Post 5: "Testing Systems That Are Wrong Differently Every Time"

**Hook**: We run 13 agents against startup ideas. Every run produces different text. Traditional assertions (assertEqual, assertContains) are useless. So how do you catch regressions?

**Core problem**: LLM outputs are non-deterministic. A test that passes today might fail tomorrow with different but equally valid output. But you still need to catch when an agent starts producing garbage after a prompt change.

**Our approach: LLM-as-Judge**:
- Fixed test inputs (multiple categories: web app, CLI tool, API service, marketplace)
- Real agent execution (no mocks, agents hit actual LLMs)
- Separate judge LLM evaluates output against per-agent rubrics
- Binary PASS/FAIL with reasoning for failures

**What we deliberately didn't do**:
- Gate CI on it (too expensive at ~$5-10 per run, too slow, too flaky for blocking)
- Use string matching or regex (brittle, fails on valid variations)
- Test with mocked LLM responses (tests the mock, not the agent)

**The trade-off**: This is a developer tool, not automated quality assurance. You run it before releases or after prompt changes. It catches "the capability model agent stopped producing CAP-* IDs" but not "the market analysis got slightly less insightful." Catching the first class of failure is worth the cost. The second class requires human review.

**Question to readers**: How are you testing agent output quality? Have you found anything better than judge-based evaluation for non-deterministic outputs?

---

## Post 6: "Config Dicts, Not If/Elif Chains: Open/Closed for Agent Systems"

**Hook**: We had 13 agents. Every time we added one, we modified `create_agent_by_name()` with another elif branch. Adding a validator meant editing `get_next_available_workflow()`. Every addition touched existing code. Every touch risked breaking something.

**Core problem**: Agent systems grow by addition (new agents, new stages, new validators). The Open/Closed Principle says modules should be open for extension, closed for modification. In practice: register new things in config dicts, don't add branches to dispatch functions.

**Before**:
```python
def create_agent_by_name(name):
    if name == "market_analyst":
        return Agent(prompt=load("market.txt"), model=heavy)
    elif name == "risk_assessor":
        return Agent(prompt=load("risk.txt"), model=reasoning)
    elif name == "new_agent":  # every new agent modifies this function
        return Agent(prompt=load("new.txt"), model=light)
```

**After**:
```python
AGENT_CONFIGS = {
    "market_analyst": AgentConfig(prompt="market.txt", model="heavy"),
    "risk_assessor": AgentConfig(prompt="risk.txt", model="reasoning"),
    "new_agent": AgentConfig(prompt="new.txt", model="light"),  # just data
}

def create_agent_by_name(name):
    config = AGENT_CONFIGS[name]
    return Agent(prompt=load(config.prompt), model=resolve(config.model))
```

**Why this matters more in agent systems than typical software**: Agent systems accumulate components faster than most software. You're experimenting constantly, adding/removing agents, changing stage ordering, swapping validators. If every change requires modifying core dispatch logic, your experiment velocity drops and your regression risk climbs.

**Same pattern applies to**: stage configs, entry validators, workflow types, search providers. Anywhere you dispatch by name, use a dict.

**Question to readers**: How do you manage the proliferation of agents and stages in your systems? Do you use registries, or is there a better pattern?

---

## Post 7: "Building a Factory That Doesn't Know What It's Building"

**Hook**: Our system generates MVPs from startup ideas. It worked great for web apps. Then we tried a CLI tool. The system suggested authentication flows, responsive layouts, and database migrations. For a command-line utility.

**Core problem**: When you build a meta-system (a system that generates other systems), every assumption you bake in is a class of inputs you silently break. "Add a login page" is reasonable for a SaaS product and absurd for a CLI tool. But the agent didn't know that, because the prompt assumed web apps.

**Our review test**: For every prompt, rule, or constraint we add: "Would this work for a CLI tool? An IoT system? A marketplace?" If the answer is no, find the generalization.

**How we handle it**:
- System trait detection: classify the idea's interface (browser, terminal, mobile, API, none), auth model, deployment target, data layer
- Trait-to-layer resolution in deterministic Python code (not in prompts): map traits to which "story layers" apply
- Inject only relevant layers into downstream agent prompts
- Cross-trait validation: flag unusual but valid combinations (e.g., headless auth, app store without native UI)

**The meta-lesson**: Enforce consistency, not content. "Every capability must trace to a requirement" applies to any system. "Include a user authentication capability" only applies to some. Generic prompts that enforce principles (traceability, completeness, internal consistency) work across input classes. Prescriptive prompts that assume a specific system type break silently.

**Question to readers**: If you're building systems that generate or configure other systems, how do you prevent your assumptions from leaking into the output? How do you test across input classes?

---

## Post 8: "Error Amplification: Why Multi-Agent Pipelines Fail Quietly"

**Hook**: One agent makes a small mistake. The next agent builds on it. By stage 5, the mistake is load-bearing. By stage 10, removing it would require re-deriving half the pipeline. Nobody flagged it because each stage's output looked locally reasonable.

**Core problem**: In a sequential multi-agent pipeline, errors don't just persist. They amplify. Each downstream agent treats upstream output as ground truth. A fabricated market statistic becomes the basis for a risk score, which becomes the basis for a GO/NO-GO verdict, which shapes the entire MVP scope.

**The numbers**: Research on multi-agent scaling (Kim et al. 2025) found 17.2x error amplification with independent agents. That means a 1% error rate at stage 1 becomes a 17% effective error rate by the end.

**The failure modes we identified**:
1. **Fabrication propagation**: Agent invents a statistic. Downstream agents cite it as established fact.
2. **Inter-stage contradiction**: Stage 3 contradicts stage 2. No detection. Stage 4 picks whichever version suits its narrative.
3. **Context loss**: Key information truncated at handoff. Downstream agent fills the gap with plausible hallucination.

**What helps**:
- Phase-boundary verification (independent checks at gates, not self-checks)
- Structured output envelopes (every agent outputs a TL;DR, anchor compliance check, and claims list)
- Explicit claim tracking (which claims have outside backing vs. which are assumptions)
- Grounding enforcement (scores of 4+ must cite a specific earlier stage's evidence)

**What doesn't help**: More agents, longer prompts, or self-check instructions. These add cost without reducing amplification.

**Question to readers**: Have you measured error amplification in your agent chains? What's your strategy for catching errors before they become load-bearing?

---

## Publishing Plan

**Cadence**: One post every 2 weeks. Start with the highest-signal posts.

**Suggested order**:
1. Post 1 (Concept Drift / Telephone) - the most distinctive finding, likely to resonate
2. Post 3 (LLM vs. Code boundary) - immediately actionable, everyone hits this
3. Post 8 (Error Amplification) - backs up post 1 with research, broadens the argument
4. Post 2 (Self-Check Theater) - counterintuitive, good engagement driver
5. Post 4 (Function Arguments) - short, practical, shareable
6. Post 5 (Testing Non-Deterministic Systems) - everyone struggles with this
7. Post 6 (Open/Closed) - more conventional SWE, but applicable
8. Post 7 (Factory Problem) - niche but interesting for meta-system builders

**Cross-linking**: Each post should link to related posts once published. Posts 1, 2, and 8 form a natural trilogy about pipeline integrity.

**Call to action**: Each post ends with a genuine question. Consider adding a link to a GitHub Discussion or simple feedback form. The goal is conversation, not broadcast.
