# Plan: URL Intake, Batch Mode, Export Pipeline

## Context

Haytham's MVP is built but has zero users. The strategy is to batch-run validation reports on real Reddit/HN side-project posts, export them to a `haytham-demos` GitHub repo, and share the reports with founders to get external signal. This requires four changes: accepting URLs as input, skipping interactive gates for batch runs, exporting outputs to a demos repo, and optionally generating PDFs.

This is the fastest path to external validation: zero-code-change user feedback in days, not months.

## Implementation

### 1. URL Intake Preprocessor

**Modify:** `commands/validate.md` (lines 13-41, Setup & Resume Detection section)

Insert a "URL Detection" subsection between the `--from N` check (line 15) and the "start fresh" branch (line 29). The command already has `WebFetch` in `allowed-tools`.

**Logic:**
- If argument matches `https?://(www\.)?reddit\.com/` -> Reddit post
  - Use `WebFetch` on the URL to get page content
  - Extract post title + body text
- If argument matches `https?://(www\.)?github\.com/` -> GitHub repo
  - Parse `{owner}/{repo}` from URL path
  - Use `WebFetch` on `https://raw.githubusercontent.com/{owner}/{repo}/main/README.md` (clean markdown, no page chrome)
  - Fall back to `HEAD` branch if `main` fails
  - Also fetch repo description from the GitHub page
- If neither -> plain text, pass through as-is

**Modify project.yaml schema** (line 32-40) to add `source:` field:
```yaml
idea: |
  [extracted text or plain text]
source:
  url: [original URL or null]
  type: [reddit_post | github_repo | text]
  fetched_at: [ISO timestamp]
created_at: ...
```

**Show the user what was extracted:**
> **Source:** [type] at [URL]
> **Extracted idea:** [first 200 chars]...

No changes to `agents/idea-analyst.md`. It reads `idea:` from project.yaml, which now contains extracted text. The `source:` field is metadata for export, not for analysis.

**Also modify:** `commands/haytham.md` (lines 30-43, Setup section) with the same URL detection logic.

---

### 2. `--batch` Flag

**Modify:** `commands/validate.md`

**A. Argument parsing (line 15):** Add alongside `--from N` detection:
- Check if argument contains `--batch`
- Strip `--batch` from argument, remainder is the idea/URL
- Set `BATCH_MODE = true`
- Can combine: `/haytham:validate --batch https://reddit.com/...`

**B. Roadmap (line 51):** When BATCH_MODE, show modified roadmap:
> **Phase 1: Idea Validation** (haytham vVERSION) -- BATCH MODE
> Running unattended. Skipping Steps 0, 4, 6 (no human review).

**C. Step 0 -- Founder Context (line 69):** Skip entirely when BATCH_MODE. No founder_context written; idea-analyst infers what it can.

**D. Step 4 -- Founder Review (around line 210):** Skip review prompt. Print "Step 4 skipped (batch mode)." Update state and continue.

**E. Step 6 -- Gate Decision (around line 266):** Auto-write gate-decision.json:
```json
{
  "phase": 1,
  "recommendation": "[from validation-report.json]",
  "user_decision": "batch-auto-approved",
  "notes": "Auto-approved in batch mode",
  "decided_at": "[ISO timestamp]"
}
```

**Also modify:** `commands/haytham.md` with the same `--batch` flag support.

---

### 3. Export Command

**Create:** `commands/export.md`

```yaml
---
description: Export validation report to a demos repository for sharing
argument-hint: [--target <path>] [--slug <name>] [--commit] [--pdf]
allowed-tools: Read, Write, Edit, Bash, Glob
---
```

**Steps:**

1. **Prerequisite check:** Verify `.haytham/session/phase-1-why/validation-report.md` exists.

2. **Parse flags:**
   - `--target <path>`: demos repo root (default: `../haytham-demos`)
   - `--slug <name>`: report directory name (auto-generated if omitted)
   - `--commit`: auto-commit after export
   - `--pdf`: generate PDF alongside markdown

3. **Auto-generate slug** (if not provided):
   - Reddit URL -> `reddit-{post_id}`
   - GitHub URL -> `github-{owner}-{repo}`
   - Plain text -> slugify first 50 chars of idea

4. **Copy files** to `{target}/reports/{slug}/`:
   - `validation-report.md`
   - `idea-analysis.md`
   - `concept-anchor.json`

5. **Generate `source.yaml`** with provenance:
   ```yaml
   idea: |
     [from project.yaml]
   source_url: [URL or null]
   source_type: [reddit_post | github_repo | text]
   exported_at: [timestamp]
   haytham_version: [from marketplace.json]
   verdict: [from validation-report.json]
   ```

6. **Generate per-report README.md** with verdict, source link, file index.

7. **Update `{target}/README.md` index** with a new row in the reports table.

8. **PDF generation** (if `--pdf`):
   - Check `pandoc` installed, suggest `brew install pandoc` if not
   - Run: `pandoc validation-report.md -o validation-report.pdf -V geometry:margin=1in -V fontsize=11pt`
   - Fallback gracefully if PDF engine missing

9. **Commit** (if `--commit`):
   - `git add reports/{slug}/ README.md && git commit -m "Add validation report: {slug}"`

---

### 4. Update argument-hint

**Modify:** `commands/validate.md` line 3:
```yaml
argument-hint: [startup idea | URL | --from N] [--batch]
```

**Modify:** `commands/haytham.md` line 3:
```yaml
argument-hint: [startup idea | URL] [--batch]
```

---

## Files Changed

| File | Action | What Changes |
|------|--------|-------------|
| `commands/validate.md` | Modify | URL detection, --batch flag, conditional gate skips, updated argument-hint |
| `commands/haytham.md` | Modify | URL detection, --batch flag, updated argument-hint |
| `commands/export.md` | Create | New export command with PDF support |

No agent files modified. No scripts modified. No hooks modified.

## Implementation Sequence

1. Modify `commands/validate.md` -- URL detection + --batch flag (largest change)
2. Modify `commands/haytham.md` -- mirror URL detection + --batch flag
3. Create `commands/export.md` -- new export command
4. Run `python3 -m pytest tests/test_plugin_sanity.py -v` -- verify no regressions

## Verification

1. **URL intake test:** Run `/haytham:validate https://www.reddit.com/r/SideProject/comments/[any-post]` and verify the post content is extracted and stored in project.yaml with source metadata.

2. **Batch mode test:** Run `/haytham:validate --batch "a todo app for dogs"` and verify the pipeline runs end-to-end without stopping for approval at Steps 0, 4, or 6.

3. **Combined test:** Run `/haytham:validate --batch https://reddit.com/r/SideProject/comments/[post]` and verify both features work together.

4. **Export test:** After a validate run, run `/haytham:export --target ../haytham-demos --commit` and verify files are copied, source.yaml is generated, README index is updated, and commit is created.

5. **Sanity tests:** `python3 -m pytest tests/test_plugin_sanity.py -v` passes (frontmatter validation, cross-reference integrity).

## Risks

- **WebFetch on Reddit may return noisy HTML** -- mitigated by extracting from the fetched content, not expecting clean text. The command should warn if extracted text is under 50 characters.
- **GitHub raw README URL may use `master` not `main`** -- mitigated by trying `main` first, falling back to `master`.
- **Slug collisions** -- mitigated by appending numeric suffix if directory exists, or user provides `--slug` override.
- **pandoc not installed** -- mitigated by making `--pdf` opt-in with clear install instructions.
