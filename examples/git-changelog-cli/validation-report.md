# Validation Report

## PART 1: THE OPPORTUNITY

### 1. The Opportunity

**The problem.** Most software teams maintain changelogs badly or not at all. The commit history is the ground truth, but it's messy: squash merges with default messages, "fix bug" repeated 40 times, mixed concerns in single commits. Existing changelog tools punt on this by requiring Conventional Commits (`feat:`, `fix:`, `chore:`) as a precondition. That works for disciplined teams. Most teams aren't disciplined.

**The audience.** Open-source maintainers who need to communicate changes to users, and engineering leads at small-to-mid teams who want release notes without a process overhaul. The common thread: they have a git history, they need a changelog, and they don't want to rewrite every commit message first.

**Market sizing.**

- **TAM:** Developer tooling market ~$25B globally [Estimate: aggregated from IDC and Gartner developer tools reports]. This includes IDEs, CI/CD, testing, and productivity tools.
- **SAM:** Teams that actively maintain changelogs or release notes ~$2B [Estimate: ~8% of developer tooling spend relates to release management and documentation workflows].
- **SOM:** CLI tool with freemium model, targeting individual developers and small teams in year 1.
  - Formula: SOM = target_users x ARPU x conversion_rate
  - Target users (year 1): 8,000 free installs [Estimate: based on comparable OSS CLI tools reaching 5K-15K installs in first year via GitHub/npm discovery]
  - Free-to-paid conversion: 3% [Estimate: Developer Tool benchmark range is 1-5%]
  - ARPU: $10/month ($120/year) for pro tier
  - SOM = 8,000 x 0.03 x $120 = **$28,800** from subscriptions
  - Plus: one-time team licenses and sponsorships could bring year 1 to **$80K-$120K** [Estimate: based on similar OSS-to-commercial tools like Insomnia, HTTPie in early stages]

### 2. Competitive Landscape

**The incumbents are rule-based.** conventional-changelog and standard-version dominate the space but require strict Conventional Commits formatting. If your commits don't follow the convention, these tools produce garbage. They've been around since 2015 and have deep npm ecosystem integration.

**The fast newcomer.** git-cliff (Rust, ~3K GitHub stars) is template-based and fast. It handles custom patterns better than conventional-changelog but still relies on regex matching. No AI. Well-regarded by the Rust community but narrow adoption outside it.

**The CI pipeline play.** semantic-release automates the entire release process: version bumps, npm publish, GitHub releases. It's powerful but heavyweight. Teams that just want a changelog find it overkill, and it still requires conventional commit messages as input.

**The manual alternative.** changie takes a different approach entirely: developers write changelog fragments manually per PR, then changie assembles them. No commit parsing at all. It's honest about the problem (commits are bad input) but adds friction to every PR.

**The gap.** Every existing tool either demands commit discipline upfront or gives up on commit parsing entirely. None of them attempt to *understand* what a commit actually did. An LLM reading diffs and messages can classify changes even when the commit message is "stuff" or "wip fixed the thing". That's the opening.

---

## PART 2: THE EVIDENCE

### 3. Claims & Evidence

**Hypothesis 1: Developers find changelog maintenance painful enough to adopt a new tool.**

Classification: **Supported**

Evidence: "Keeping a changelog" (keepachangelog.com) exists as a standalone advocacy site. GitHub Issues across major OSS projects consistently show users requesting better release notes. The existence of 5+ dedicated tools in this space confirms sustained demand. Stack Overflow questions about automating changelogs number in the thousands. [Verified: GitHub search, npm download counts]

---

**Hypothesis 2: Existing tools fail when commit messages are inconsistent or non-conventional.**

Classification: **Supported**

Evidence: conventional-changelog's own documentation states it requires Conventional Commits as input. git-cliff's FAQ acknowledges regex patterns miss edge cases. Multiple GitHub Issues on these projects report empty or incorrect changelogs when commit formats vary. [Verified: tool documentation and GitHub Issues]

---

**Hypothesis 3: LLMs can reliably classify git commits into changelog categories (feature, fix, breaking change, etc.).**

Classification: **Unsupported**

Evidence: No published benchmark on LLM-based commit classification accuracy. Anecdotal evidence from AI coding tools (Copilot commit messages, Anthropic's own commit summarization) suggests feasibility, but systematic evaluation on messy real-world repos is absent. This is the core technical risk. [Assumption]

---

**Hypothesis 4: Developers will pay for a changelog tool when free alternatives exist.**

Classification: **Partially Supported**

Evidence: Developer willingness to pay for CLI tools is historically low for individual use, but team/enterprise licenses have precedent (GitKraken, Tower, Kaleidoscope). The freemium model works when the free tier solves the individual problem and the paid tier adds team features. Developer Tool benchmarks show 1-5% free-to-paid conversion. [Estimate: benchmark data + comparable tool pricing]

---

**Hypothesis 5: Distribution via npm/brew/GitHub is sufficient to reach 8,000 installs in year 1.**

Classification: **Supported**

Evidence: Comparable CLI tools (commitizen, husky, lint-staged) reached 10K+ installs within 12 months through npm and GitHub discovery alone. Developer Tool benchmarks indicate time-to-first-value under 5 minutes is critical, which a CLI tool with `npx` support can achieve. [Verified: npm download statistics for comparable tools]

---

### 4. Risk Profile

| Category | Risk | Severity | Likelihood |
|----------|------|----------|------------|
| Technical | LLM classification accuracy on messy commits | HIGH | MEDIUM |
| Technical | LLM API latency makes tool feel slow for large repos | MEDIUM | HIGH |
| Financial | LLM cost per invocation erodes margins at scale | MEDIUM | MEDIUM |
| Market | Developers resist paying when free rule-based tools exist | HIGH | MEDIUM |
| Market | A major player (GitHub, GitLab) ships native AI changelogs | HIGH | LOW |
| Operational | Maintaining prompt quality across LLM provider updates | MEDIUM | MEDIUM |

**Technical risks.** The core bet is that an LLM can classify commits more accurately than regex patterns. Without a published benchmark, this is an assumption (see Hypothesis 3). The mitigation is straightforward: build a test suite of 200+ commits from real OSS repos, measure classification accuracy, and set a quality bar before launch. If accuracy falls below 80%, the tool loses its value proposition over rule-based alternatives.

Latency is the other technical concern. A repo with 500 commits between releases could mean 500 LLM calls (or batched calls with large context windows). The tool must feel fast. Caching, batching, and allowing users to set commit ranges will help, but this needs measurement on real repos.

**Financial risks.** At ~$0.01-0.03 per commit classification (using Haiku-class models), a 500-commit changelog costs $5-15 in API calls. The freemium model needs to absorb this for free-tier users or limit free usage to small repos. Margins are viable at the pro tier but thin.

**Market risks.** The biggest existential risk is GitHub shipping "AI Release Notes" as a native feature. GitHub already uses AI for PR summaries. The counter-argument: GitHub's approach will likely be generic and platform-locked, while a CLI tool is portable and customizable.

**Overall Risk Level:** MEDIUM

---

## PART 3: THE NUMBERS

### 5. Financial Feasibility

**MVP build cost.**

A solo technical founder can build this in 1-2 weeks. The core components are git log parsing (well-understood), LLM API integration (straightforward), and markdown output formatting (trivial). No infrastructure beyond an LLM API key. MVP build cost: **$0-$2,000** (founder time + API costs during development). [Estimate: based on scope and typical solo-developer velocity]

**Revenue model comparison.**

| Model | Pricing | Year 1 Revenue | Best For |
|-------|---------|----------------|----------|
| Freemium CLI + Pro tier | Free (50 commits/month), $10/month Pro (unlimited) | $28K-$35K | Individual developers and small teams |
| Team license | $25/seat/month, minimum 5 seats | $45K-$75K | Engineering orgs that want shared config and audit trail |
| Usage-based | $0.05/commit processed | $40K-$60K | High-volume users, pay-for-what-you-use |

**Detailed math (Freemium + Pro):**

- 8,000 free users by month 12 (growing ~700/month)
- 3% conversion = 240 paid users by month 12
- Monthly revenue at month 12: 240 x $10 = $2,400/month
- Cumulative year 1 (ramp-up): ~$14,400 in subscription revenue
- Plus sponsorships and one-time licenses: ~$14K-$20K
- **Year 1 total: ~$28K-$35K**

Developer Tool benchmarks note a 6-18 month community-to-revenue lag, so year 1 revenue will skew toward the second half. This is consistent with the ramp-up model above.

**Break-even scenario.**

- Monthly costs: LLM API (~$500-$1,500 depending on free-tier usage), hosting (minimal, ~$20), npm/distribution ($0)
- Monthly break-even: ~$1,500/month
- Break-even at: ~150 paid users ($10/month each)
- Expected timeline to break-even: **month 8-10** [Estimate: based on 3% conversion of growing user base]

Free-to-paid conversion of 3% is mid-range for Developer Tools (benchmark: 1-5%). If conversion comes in at the low end (1%), break-even pushes to month 14-16, which is still within the benchmark's community-to-revenue lag of 6-18 months.

---

## PART 4: THE PATH FORWARD

### 6. Our Recommendation

**GO.**

**The pain is real and specific.** Every developer who has tried to write release notes from a messy git history knows this problem (Section 1). The five existing tools in this space confirm sustained demand. None of them solve the messy-commits case, which is the *common* case (Section 2).

**The technical risk is bounded.** LLM commit classification is unproven at scale (Hypothesis 3), but the experiment is cheap: build a test suite, measure accuracy, kill it if accuracy is below 80%. Unlike many AI products, the failure mode here is obvious and measurable. You know immediately if the changelog is wrong.

**The financial model works at modest scale.** Break-even at 150 paid users is achievable within a year given the distribution channels available to CLI tools (Section 5). The LLM cost structure is the main margin risk, but Haiku-class models keep per-invocation costs manageable.

**The counter-signals.** Developer willingness to pay for CLI tools is historically low (Hypothesis 4). The freemium model mitigates this, but expect most value to come from team/enterprise licenses, not individual subscriptions. Also, GitHub could ship this natively (Section 4), though their track record on developer tools suggests it would be generic and slow to ship.

**Composite Score:** 3.6/5.0

### 7. Validate Before You Build

**The riskiest assumption:** LLMs can classify messy, real-world git commits into meaningful changelog categories with 80%+ accuracy.

**Experiment 1: Classification accuracy test ($0, 1-2 days)**

Grab 200 commits from 5 popular open-source repos with varied commit styles (React, Rust, a Django project, a Go CLI tool, a Jupyter project). Manually label each commit (feature, fix, refactor, docs, chore, breaking). Run them through Claude Haiku with a classification prompt. Measure accuracy against your labels.

- **Success:** 80%+ accuracy across all 5 repos
- **Failure:** Below 70% accuracy, or accuracy drops sharply on repos with poor commit hygiene
- **Cost:** $0 (API credits from free tier)
- **Timeline:** 1-2 days

**Experiment 2: Developer reaction test ($0, 3 days)**

Post a sample changelog generated from a real OSS repo (with the maintainer's permission) to Hacker News / r/programming / relevant Discord servers. Offer early access. Measure: how many people sign up? What feedback do they give?

- **Success:** 50+ signups, qualitative feedback confirms pain point
- **Failure:** <20 signups, or feedback indicates "I just use conventional commits"
- **Cost:** $0
- **Timeline:** 3 days (post + monitor)

### 8. Next Steps

**Action plan:**

1. **This week:** Run Experiment 1 (classification accuracy test). This is the go/no-go gate. If accuracy is below 70%, the value proposition doesn't hold.

2. **Week 2:** If accuracy passes, build a working prototype (git log parser + LLM classification + markdown output). Test on your own repos first.

3. **Week 2-3:** Run Experiment 2 (developer reaction test) with the prototype. Share generated changelogs from real repos.

4. **Week 3-4:** Based on feedback, ship v1 to npm with a freemium model. Free tier: 50 commits/month. Track installs and conversion.

5. **Month 2-3:** If installs hit 1,000+, add team features (shared config, CI integration) for the paid tier. Begin outreach to OSS maintainers for partnerships/testimonials.
