# MVP Scope

## 1. THE ONE THING

The MVP will enable **developers with messy git histories** to **generate a categorized changelog** so they can **communicate changes to users without rewriting commit messages**.

## 2. PRIMARY USER SEGMENT

**Segment:** Developers who maintain projects with release notes or changelogs
**Profile:** They push code frequently, write commit messages of varying quality, and periodically need to summarize what changed between two points in the git history. They're comfortable with CLI tools and npm/brew.
**Why First:** Open-source maintainers have the most acute version of this pain. They need to communicate changes to external users who weren't involved in development.
**Key Need:** Turn a range of git commits into a readable, categorized changelog without requiring commit message conventions.

## 3. PRIMARY INPUT METHOD

**Input Method:** CLI command with git log as implicit input
**Why This Method:** The data already exists in the git history. The user shouldn't have to re-enter or restructure it.
**What This Excludes:** No web interface, no GitHub App, no IDE plugin. CLI only.

## 4. APPETITE

**Appetite:** Small (1-2 weeks)
**If we had HALF the time:** Cut configurable grouping categories. Ship with hardcoded defaults (Features, Fixes, Breaking Changes, Other) only.

---

## 5. MVP BOUNDARIES

| IN SCOPE (MVP v1) | Requires | OUT OF SCOPE (Future) |
|-------------------|----------|----------------------|
| Parse git log for a given commit range | Nothing | Multi-repo / monorepo support |
| AI-powered commit classification (feature, fix, breaking, chore, docs) | Git log parsing | Custom LLM provider selection |
| Markdown changelog output (grouped by category) | Commit classification | HTML/RST/other output formats |
| Configurable grouping categories via CLI flags or .changelogrc | Nothing | Web dashboard for changelog management |
| CLI with sensible defaults (`npx changelog` just works) | All of the above | CI/CD integration (GitHub Actions, etc.) |
| | | GitHub/GitLab release creation |
| | | Changelog diffing between versions |
| | | Team shared configuration |

## 6. SUCCESS CRITERIA

**Primary Metric:** Classification accuracy on real-world commits
**Target:** 80% accuracy across diverse repo styles -- realistic

**Validation Criteria:**
- [ ] Generates a usable changelog from a 100-commit range in under 30 seconds
- [ ] 80%+ of commit classifications match human judgment on a test suite of 200 commits from 5 OSS repos
- [ ] First run works with zero configuration (just `npx changelog`)

**Failure Signals:**
- Classification accuracy below 70% on repos with poor commit hygiene
- Users consistently edit more than 30% of the generated changelog before publishing

---

## 7. CORE USER FLOWS

### Flow 1: Generate Changelog (The Core Loop)

**Trigger:** Developer runs `changelog generate` (or `npx changelog`) in a git repo
**Steps:**
1. User runs CLI command, optionally specifying a commit range (default: last tag to HEAD)
2. System reads git log for the specified range (commit messages + optionally diffs)
3. System sends commits to LLM for classification (feature, fix, breaking, chore, docs)
4. System groups classified commits by category
5. System outputs formatted markdown changelog to stdout (or file with `--output`)
6. Outcome: User has a categorized changelog ready to paste into CHANGELOG.md or a GitHub release

**Success:** The changelog accurately reflects what changed, grouped in a way that makes sense to the project's users.

### Flow 2: Configure and Regenerate

**Trigger:** User wants to customize grouping or exclude certain commit types
**Steps:**
1. User creates `.changelogrc` or passes CLI flags (e.g., `--exclude chore,docs`)
2. System reads configuration and applies it to classification output
3. System regenerates changelog with custom grouping
4. Outcome: Changelog matches the user's preferred format and categories

**Success:** Configuration is minimal (a few lines) and the regenerated output reflects the user's preferences.

## 8. SCOPE METADATA

```
MVP_SCOPE_COMPLETE: true
PRIMARY_USER_SEGMENT: Developers maintaining projects with changelogs
INPUT_METHOD: CLI command (git log as implicit input)
APPETITE: Small
IN_SCOPE_COUNT: 5
OUT_SCOPE_COUNT: 6
FLOW_COUNT: 2
HALF_TIME_CUT: Configurable grouping categories
```
