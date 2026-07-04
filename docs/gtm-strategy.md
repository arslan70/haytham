# Go-To-Market Strategy: 2-Week Sprint

> **Status (2026-07-03): retired.** The sprint this strategy describes ended in April 2026, and Haytham has since been re-scoped to a personal tool with no go-to-market ambitions. This page is kept as a record.

**Goal:** 5 people run `/haytham` on their own idea and give feedback.
**Timeline:** March 19 - April 1, 2026
**Kill condition:** Fewer than 5 runs by April 1 = project enters wind-down.

---

## The Funnel

To get 5 people to *run* the plugin, work backwards:

| Stage | Conversion | Need |
|-------|-----------|------|
| See your content | — | ~500 people |
| Click through to repo/docs | ~20% | ~100 |
| Install the plugin | ~30% | ~30 |
| Actually run it | ~20% | ~5 |

The bottleneck is the top (reach) and the bottom (actually running it). The middle is fine if the content is good.

---

## Pre-Work (Day 0: March 19)

Do these before any promotion. They remove friction from every step of the funnel.

### 1. Create a sample output gallery

People won't spend 20 minutes on a tool they haven't seen the output of. Run Haytham on 3 diverse ideas and publish the full output:

- A B2C app (e.g., the gym leaderboard)
- A developer tool / CLI (e.g., a git changelog generator)
- A B2B SaaS (e.g., invoice reconciliation for small firms)

Put the raw output directories in a `examples/` folder in the repo. Link from README. This lets people judge the output quality *before* installing.

### 2. Record a 2-minute demo video

Screen recording. No editing needed. Just:
- `/haytham "a gym community leaderboard with anonymous handles"`
- Fast-forward through the 20 min run (or show key moments: concept anchor extraction, GO/NO-GO verdict, final OpenSpec tree)
- Show the output files

Host on YouTube (unlisted is fine). Embed in README and docs. LinkedIn and Reddit posts can link to it.

### 3. Fix the README for strangers

Current README is 63 lines and assumes context. Rewrite the top section for someone who has never heard of this:

```
## What is this?

You have a startup idea. Haytham tells you if it's worth building,
then produces an implementation-ready specification you can hand
to a coding agent.

Run one command. Get market research, a GO/NO-GO verdict,
MVP scope, architecture decisions, and OpenSpec output.
```

Add:
- The demo video
- A "See example output" link to the gallery
- A "What you get" section showing a real output tree with 2-3 annotated highlights
- Expected runtime ("~20 minutes, you'll be asked for approval at each phase")

### 4. Add a feedback mechanism

Create a GitHub Discussion category called "Show your run" where users can paste their idea and share what Haytham produced. This gives you:
- Social proof (others can see real runs)
- Direct feedback channel
- Content for future posts

Also add a one-liner at the end of the plugin's Phase 4 output:
> "How did this go? Share your experience: github.com/arslan70/haytham/discussions"

### 5. Consider the AGPL question

AGPL is a hard stop for anyone at a company. For a plugin with zero users trying to get traction, the license is costing you reach. Switch to MIT or Apache 2.0 for the GTM period. You can always relicense later (you're sole author). If you feel strongly about AGPL, keep it, but know it's a filter.

---

## Week 1 (March 19-25): Seed and Learn

The goal this week is to get the first 2 runs and learn what breaks.

### Reddit (Primary Channel)

Reddit is where developers with side project ideas hang out. Post in these subs, spaced 2-3 days apart to avoid looking spammy:

**Post 1 (Day 1-2): r/ClaudeAI**
This is the highest-signal subreddit. These people already have Claude Code.

Title: "I built a Claude Code plugin that validates your startup idea and generates an implementation-ready spec"

Body structure:
- What it does (3 sentences)
- What the output looks like (paste a trimmed example or link to gallery)
- How to try it (one install command)
- What you're looking for ("I want 5 people to try this on their own idea and tell me what sucked")
- Link to the 2-min demo video

Tone: Builder sharing work, asking for honest feedback. Not a product launch.

**Post 2 (Day 3-4): r/SideProject**
Title: "I made a tool that stress-tests your startup idea before you write code"

Different angle: focus on the validation/NO-GO verdict. These people have ideas and want honest feedback. Lead with "it told me my own project was HIGH risk with a $144K TAM" (the dogfooding result). That honesty is the hook.

**Post 3 (Day 5-6): r/artificial or r/LocalLLaMA or r/MachineLearning**
Title: "Lessons from building an 8-agent pipeline as a Claude Code plugin"

Technical angle. Share the concept anchor pattern, the single-agent-synthesis finding (8/4/0 vs 1/3/8), the telephone problem. Link to the "Agents Playing Telephone" blog post. Mention the plugin as "if you want to try the thing these lessons produced."

### LinkedIn (Secondary Channel)

**Post 1 (Day 1): The Hook Post**
Short-form. Personal voice.

"I ran my AI pipeline on its own idea. It said: GO, but high risk. TAM: $144K. Composite score: 3.2/5.

It was right.

[2-3 sentences about what Haytham does]

Looking for 5 developers to try it on their startup idea and tell me what's broken.

Link: [repo]
Demo: [video]"

**Post 2 (Day 4): The Lesson Post**
"Your AI agents are playing telephone. Here's what I mean..."

Repurpose the blog post as a LinkedIn article. End with a soft mention of the plugin.

### Direct Outreach (Force Multiplier)

Find 5-10 people in your LinkedIn/Reddit network who:
- Have posted about side projects or startup ideas recently
- Use Claude Code (check r/ClaudeAI post history)
- Are building with AI agents

Send a personal message:
> "Hey, I built a Claude Code plugin that validates startup ideas and generates specs. Looking for honest feedback from 5 people. Would you try it on one of your ideas? Takes ~20 min. Happy to return the favor on anything you're building."

This is the highest-conversion channel. Don't skip it.

---

## Week 2 (March 26 - April 1): Push Hard

### Reddit Round 2

**Post 4 (Day 8): r/startups or r/Entrepreneur**
Title: "Before you build your MVP: a free tool that tells you if your idea is worth it"

Non-technical angle. Focus on: saves you months of building the wrong thing. Lead with the GO/NO-GO verdict concept. Show a sample validation report.

**Post 5 (Day 10): r/ClaudeAI again (if rules allow) or r/ChatGPTCoding**
Share a follow-up: "5 people tried my Claude Code plugin last week. Here's what they found."

If you have feedback by now, this is social proof. If you don't, this post becomes "still looking for testers."

### Hacker News (One Shot)

**Show HN post (Day 9 or 10):**

Title: "Show HN: Haytham - Claude Code plugin that validates startup ideas and generates specs"

HN is high risk, high reward. You get one shot. The post should:
- Lead with what it does and why (the gap between idea and spec)
- Mention it's a Claude Code plugin (topical, AI-adjacent)
- Link to the repo
- Mention the dogfooding result (self-aware projects get respect on HN)

Best posting time: Tuesday or Wednesday, 8-9am ET.

If it gets traction, be in the comments answering every question for the first 2 hours.

### LinkedIn Round 2

**Post 3 (Day 8): Results Post**
Share what you learned from the first week. What feedback did you get? What broke? What surprised you? Authenticity compounds.

**Post 4 (Day 11): The Deeper Post**
"Why I might kill this project in 3 days" - share the kill criteria publicly. This is counterintuitively compelling. People respect founders who set honest deadlines.

---

## Content Assets (Create During Week 1)

| Asset | Purpose | Where to Use |
|-------|---------|-------------|
| 2-min demo video | Show before asking for commitment | README, all posts, DMs |
| 3 example outputs | Prove output quality | README, repo, posts |
| "Agents Playing Telephone" blog summary | Technical credibility | LinkedIn, r/MachineLearning |
| Dogfooding results one-pager | Honest self-assessment hook | All channels |
| GitHub Discussions "Show your run" | Feedback + social proof | End of plugin output |

---

## Daily Tracking

Track these numbers daily in a simple spreadsheet or note:

| Metric | How to Measure |
|--------|---------------|
| Repo views | GitHub Insights → Traffic |
| Repo clones | GitHub Insights → Traffic |
| Stars | GitHub repo page |
| Plugin installs | If marketplace provides analytics; otherwise infer from GitHub traffic |
| Confirmed runs | GitHub Discussions posts, DM feedback, issue reports |
| Feedback items | Any user-reported experience (good or bad) |

---

## Success Metrics (April 1 Decision Point)

### GO (continue investing)
- 5+ confirmed runs by real users
- At least 2 pieces of actionable feedback
- Any signal of organic spread (someone sharing it without being asked)

### PIVOT (change approach, not kill)
- 2-4 confirmed runs
- Feedback suggests the output is useful but distribution/UX is the blocker
- Action: fix the specific blockers, try again with a narrower audience

### KILL (extract learnings, archive)
- 0-1 confirmed runs despite full execution of this plan
- No engagement on posts (not even questions or criticism)
- Action: write a post-mortem blog post (good content for your brand), archive repo, extract reusable components (concept anchor pattern, eval framework, blog posts about multi-agent design)

---

## What NOT To Do

- **Don't buy ads.** At this stage, organic reach tells you if anyone cares. Paid reach hides the signal.
- **Don't build new features.** The product is good enough. The question is whether anyone wants it, not whether it needs more capabilities.
- **Don't cross-post the same content.** Each community gets a different angle. Same link, different framing.
- **Don't post and disappear.** Every comment on your posts is a potential user. Respond to everything within hours.
- **Don't optimize the funnel prematurely.** You need 5 users, not 5000. Personal outreach and authentic posts are enough.
- **Don't spend time on CI/CD, CHANGELOG, or code cleanup.** None of that matters if nobody uses it.

---

## Schedule Summary

| Day | Action |
|-----|--------|
| 0 (Mar 19) | Pre-work: example gallery, demo video, README rewrite, GitHub Discussions setup |
| 1 (Mar 20) | Reddit: r/ClaudeAI post. LinkedIn: hook post. Start direct outreach (5-10 DMs) |
| 3 (Mar 22) | Reddit: r/SideProject post |
| 4 (Mar 23) | LinkedIn: technical lesson post |
| 5 (Mar 24) | Reddit: r/artificial or r/MachineLearning post |
| 7 (Mar 26) | Checkpoint: how many confirmed runs? Adjust week 2 if needed |
| 8 (Mar 27) | Reddit: r/startups post. LinkedIn: results post |
| 9-10 (Mar 28-29) | Hacker News Show HN post (Tue/Wed) |
| 11 (Mar 30) | LinkedIn: "why I might kill this" post |
| 14 (Apr 1) | **Decision day.** Count runs. GO / PIVOT / KILL |

---

## The One Thing That Matters Most

Everything above is noise if you skip this: **direct outreach to 5-10 people who have startup ideas and use Claude Code.** Find them on r/ClaudeAI, in LinkedIn AI groups, or in your existing network. Send a personal message. Ask them to try it. Offer to hop on a call while they run it.

Public posts are lottery tickets. Personal messages are conversations. You need 5 users, not 5000 impressions.
