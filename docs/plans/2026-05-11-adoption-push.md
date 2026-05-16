# 2026-05-11 Adoption Push

**Status:** Proposal. Supersedes [2026-04-18 Haytham Final Push](2026-04-18-haytham-final-push.md).

## What changed

The earlier plan was a kill-or-keep window with three litmus criteria, due 2026-05-16. Two of them already landed:

- GiftKaro shipped publicly. A real product runs at giftkaro.pk, built end-to-end with Haytham, with `/haytham:evolve` confirmed across two follow-up changes (bundle-categories scored 6/6 on the rubric; Stripe-to-WhatsApp showed full graph maintenance in the PR body).
- A second project (Giving Mode, mobile + AWS-native, source private) reached comparable graph depth: 13 spec domains, 87 SHALL requirements, 119 scenarios, and one `/haytham:evolve` run that correctly declined to edit the graph because the change implemented an existing decision.

TinyTales was the third criterion. It never ran. With two projects past the bar, it stops being load-bearing.

The remaining open question isn't "does this work." It's "will anyone else use it."

## What this plan is

An adoption push. The validation work is done. The next step is making the plugin discoverable, easy to start, and easy to explain to someone who has never seen it.

## What this plan is not

- Open-sourcing GiftKaro. Repo and openspec stay private.
- A spray-marketing campaign across every channel.
- A second showcase artifact for Giving Mode. Source is private and stays private.
- A pitch deck or pricing page. No monetization motion until adoption signal exists.

## Success metric

**Someone outside the founder runs `/haytham:evolve` on their own repo by 2026-06-15.**

The signal is concrete: another builder's repo gets an `openspec/` plus a commit that maintains it. One is enough to validate the bet; zero rejects it. Downloads, stars, and HN points are weaker proxies and don't count.

## In scope

1. **Plugin polish for first-time users.** The README on `arslan70/haytham`, error messages from `/haytham:validate` through `/haytham:evolve`, and the first-run experience from `claude plugin install` onward. Goal: a stranger goes from "I want to try this" to "I have an openspec/" without needing to ask a question.

2. **Two writeups in `docs/blog/`.**
   - **Why Haytham.** Plain-language case for the reasoning graph. Lead with the GiftKaro story (idea to live in 20 commits, 0 opex). Frame the problem, not the architecture.
   - **Evolution walkthrough.** Bundle-categories or Stripe-to-WhatsApp, retold for someone who has never seen Haytham. Use the existing experiment doc as the evidence base; rewrite the prose for a stranger.

3. **Marketplace submission.** Anthropic's plugin marketplace listing. Description, screenshots, version pinned. Submit by 2026-05-20 so the review queue clears before Show HN.

4. **One Show HN post.** Title points at the live product and the underlying claim. Body links to giftkaro.pk, the plugin source, and the evolution walkthrough. Post after marketplace approval, or at 2026-06-01 if there is no response by then.

## Out of scope

- Twitter/X campaign, LinkedIn post, Reddit drops
- A demo video
- An "Awesome Haytham" repo or template gallery
- TinyTales
- Open-sourcing anything private
- A separate showcase domain

## Channels

Two. Picked because they reach builders directly and don't depend on existing reach:

1. Anthropic plugin marketplace (discovery)
2. Hacker News Show HN (depth, one drop)

If neither lands an external user, that's signal to rethink the discovery approach, not the plugin.

## Risks

- **First user has a bad experience and bounces.** First impressions compound. Plugin polish (item 1) exists specifically to derisk this.
- **Show HN doesn't land.** It might not. The metric isn't HN traction; it's whether anyone clicks through and tries the plugin.
- **Marketplace queue is slow.** The 2026-06-01 backstop unblocks Show HN regardless.
- **Founder conviction outruns evidence.** Two private projects shipping is genuine signal, but it's still N=2. If no external user lands by 2026-06-15, the right move is to question whether the plugin solves a problem someone else has, not just one the founder has.

## Decision point

2026-06-15. If zero external users have run `/haytham:evolve` on their own repo:

- If there's external interest but no completions (HN comments, GitHub issues, DMs), the friction is the problem. Cut features, simplify onboarding.
- If there's no interest at all, the discovery approach is wrong. Try a different channel before rethinking the product.

The plugin works. The question is whether it solves a problem someone else has.
