---
description: Validate a URL (Reddit post, GitHub repo) in batch mode and export the report to a demos repository
argument-hint: <URL> [--target <path>]
allowed-tools: Read, Write, Edit, Bash, Glob, Agent, WebSearch, WebFetch
---

# Haytham: Demo Pipeline

You are running a batch validation on a URL and exporting the report for sharing. This command combines `/haytham:validate --batch` and `/haytham:export --commit` into a single unattended run.

## Steps

### Step 1: Parse Arguments

Parse the argument:
- The first non-flag argument is the URL (required). If no URL is provided, tell the user: `Usage: /haytham:demo <URL> [--target <path>]`
- `--target <path>`: Target demos repository root. Default: `../haytham-demos`

### Step 2: Validate Target

Check if the target directory exists:
```bash
ls [target]
```

If it does not exist:
> Target directory `[target]` does not exist. Create it first:
> ```
> git init [target]
> ```
> Then re-run this command.

Stop here if the target does not exist.

### Step 3: Run Validation

Read `${CLAUDE_PLUGIN_ROOT}/commands/validate.md`. Execute its full pipeline with `--batch` mode enabled and the URL as input. Follow all instructions in that file exactly.

When the pipeline completes, tell the user:
> **Validation complete.** Exporting report...

### Step 4: Export

Read `${CLAUDE_PLUGIN_ROOT}/commands/export.md`. Execute its full pipeline with `--target [target]` and `--commit`. Follow all instructions in that file exactly.
