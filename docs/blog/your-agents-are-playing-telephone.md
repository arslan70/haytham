# Your Agents Are Playing Telephone

*By someone who has stared at too many multi-agent pipelines and has opinions about it.*

---

![Agents Playing Telephone](telephone-comic.svg)

---

Here's a fun experiment. Take a startup idea, something with a real edge to it, like "a closed group therapy app where 8 people gather: 1 receiver and 7 givers, for existing patients only." Feed it into a multi-agent pipeline. Watch what comes out the other end.

What you'll get, reliably, is a generic async encouragement board with open signup. No groups. No structure. No patients. The distinctive thing, the thing that made the idea an idea, got smoothed away by five agents who each did their job perfectly in isolation.

This is the telephone game, except the players are LLMs and the message is your product.

## The Failure Modes Are Predictable

We've been building [Haytham](https://github.com/arslan70/haytham), a multi-agent system that validates startup ideas through ~12 stages. Along the way, we catalogued six specific ways agents corrupt information across handoffs. They're not exotic. They're almost boring in their predictability.

**Genericization.** Agents default to whatever pattern dominates their training data. A closed patient community becomes an open SaaS marketplace. A synchronous gathering becomes async messaging. The agent doesn't know it's wrong. It's just filling in gaps with the most probable completion.

**Fabrication.** An agent invents a statistic, marks it `[validated]`, and the next agent trusts it completely. There's no grounding enforcement between stages, so hallucinations propagate with increasing confidence.

**Contradiction.** Stage 7 says `realtime=false`. Stage 8 recommends "Supabase for real-time sync." Each stage validates only against its immediate inputs, not its siblings. Nobody notices.

**Context Loss.** This one's mechanical. Our context builder was extracting the first 200 characters from each prior stage's output. The "1:7 group structure" was in the body, not the first line. Gone. By Stage 5, the MVP scope agent was working from a 200-character summary of a nuanced idea.

**Self-Check Failure.** We tried asking agents "did you preserve the original concept?" They always say yes. LLMs asked to verify their own work are like students grading their own exams. The bias is structural.

**Appetite Mismatch.** A "2-week build" constraint somehow produced 20 stories across 4 frameworks. The appetite was expressed in prose, not enforced by the system. So the agent ignored it, politely.

Research backs this up. Kim et al. (2025) found that multi-agent systems had only 34% context overlap after 10 interactions, with error amplification of 17.2x in independent agent architectures. This isn't a bug in any specific system. It's a property of the architecture.

## Why It Happens

The root cause is deceptively simple: you're asking Agent N+1 to reconstruct meaning from Agent N's *output*, not from Agent N's *understanding*. Each handoff is a lossy compression. Stack enough of them and you get noise.

Three things make it worse:

**Truncation.** Token limits force you to summarize prior outputs. Summaries lose nuance. Nuance is where the product lives.

**Prose as protocol.** Most multi-agent systems pass information as natural language. Natural language is ambiguous by design. When Agent 2 reads "a therapy application for groups," it doesn't know if "groups" is the core innovation or a throwaway detail. So it guesses, usually wrong.

**LLMs love the median.** Given ambiguity, language models gravitate toward the most common pattern in their training data. Your distinctive idea gets pulled toward the center of the distribution, one stage at a time.

## What Actually Works

Here's what we found works in practice, after a lot of ideas got mangled.

### 1. Immutable Anchors

The single most effective pattern: extract the idea's distinctive features once, early, into a small structured artifact. Pass it to every downstream agent, unchanged.

```yaml
anchor:
  intent:
    goal: "group reflection app for existing patients"
    non_goals: ["open marketplace", "async messaging"]
  invariants:
    - property: "group_structure"
      value: "1 receiver + 7 givers per session"
    - property: "community_model"
      value: "closed, invite-only"
```

~500 tokens. Immutable. Every agent gets it. The key properties: it's small enough to never need truncation, and no downstream agent can modify it. Agents can respond to the anchor, but they can't rewrite it.

This alone dropped our genericization rate dramatically.

### 2. Structured Handoffs, Not Prose

When Stage N knows a value (say, `risk_level: HIGH`), pass it as a structured input to Stage N+1. Don't embed it in a paragraph and hope the next agent extracts it correctly.

```python
def init_scorecard(*, risk_level: str) -> None:
    """Pre-set values extracted by prior stages.
    The agent's tools use these directly."""
    if risk_level.upper() not in ("HIGH", "MEDIUM", "LOW"):
        raise ValueError(f"Invalid risk_level: {risk_level!r}")
    sc = _new_scorecard()
    sc["risk_level"] = risk_level.upper()
```

Treat agent inputs like function arguments. You wouldn't pass `risk_level` to a function by hiding it in a comment string. Don't do it with agents either.

### 3. Deterministic Rules Override LLM Text

This is the one people push back on, because it feels like you're not "trusting" the agent. Good. You shouldn't.

The LLM's job is qualitative judgment: scoring, evaluating evidence, weighing trade-offs. The system's job is deterministic rules derived from those judgments.

```python
# Risk veto: HIGH risk always caps GO -> PIVOT
if risk_level.upper() == "HIGH" and recommendation == "GO":
    recommendation = "PIVOT"  # unconditional
```

No agent can override this. The narrator might write a glowing report that says "GO" while the scorer's math says "PIVOT." The merge step corrects the text to match the numbers. Numbers always win.

Keep this boundary sharp. Every time you let LLM-generated text override a deterministic safety rule, you're adding another player to the telephone game.

### 4. Evidence Gates at Handoffs

Don't let agents make unsourced claims. If a scorer gives a 5/5, require a source tag:

```
REJECTED: score 5 requires '(source: market_context)' in evidence.
Cite a specific finding or lower the score to 3.
```

Reject evidence that parrots the scoring rubric. Reject high scores without citations. Do this at the handoff boundary, not as a self-check (remember: self-checks don't work).

### 5. Post-Validators Before State Entry

Run validators after an agent completes but before its output enters the pipeline state. Six validators check revenue evidence, claim origins, JTBD match, concept health, and market sanity. All before the next stage can see the output.

```python
for validator in self.config.post_validators:
    warnings = validator(output, state)
    validation_warnings.extend(warnings)
```

This is the difference between catching drift at the source and discovering it three stages later when your MVP spec describes a completely different product.

## The Uncomfortable Truth

You can't fix the telephone game by making agents smarter. Smarter agents are still playing telephone. The fix is structural:

1. **Anchors** for things that must never change
2. **Structured data** for things that must never be misinterpreted
3. **Deterministic rules** for things that must never be overridden
4. **Evidence gates** for things that must never be unsourced
5. **Validators** for things that must never go unchecked

The common thread: stop trusting prose as protocol. Every time you pass information between agents as natural language and hope it survives, you're playing telephone. Sometimes you'll get lucky. Mostly you won't.

The research quantifies this nicely: centralized verification drops error amplification from 17.2x to 4.4x. That's still not zero. But it's the difference between a product that resembles your idea and one that doesn't.

Your agents are doing their best. They're just playing a game they can't win. Change the game.

---

*All patterns described are from [Haytham](https://github.com/arslan70/haytham), an open-source multi-agent system for startup validation. The "Power of 8" case study is real. The encouragement board was not the product we wanted.*
