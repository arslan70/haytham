---
description: Set up a new project from Phase 4 specs, ready for implementation
argument-hint: <project-directory>
allowed-tools: Read, Write, Bash, Glob
---

# Haytham: Build Setup (Phase 5 - BUILD)

You are setting up a new project directory from Haytham's Phase 4 OpenSpec output. Implementation happens in a SEPARATE Claude Code session to ensure the code is generated purely from specs, not from the current plugin context.

## Prerequisites

Verify `.haytham/session/phase-4-specs/openspec/config.yaml` exists. If it doesn't, tell the user:
> "Phase 4 (specification) must be completed first. Run `/haytham:plan` to start."

Check that the user provided a project directory argument. If not, read `.haytham/session/phase-4-specs/openspec/config.yaml`, extract the `name` field, and use it as the directory name.

Verify the OpenSpec CLI is installed:
```bash
command -v openspec
```

If not found, tell the user to install it with `npm install -g @fission-ai/openspec@latest` and re-run `/haytham:build`. Stop here.

## Build

1. Check if the project directory already exists. If it does, ask the user if they want to overwrite.

2. Create the directory and initialize OpenSpec:
   ```bash
   mkdir -p <project-directory> && cd <project-directory> && openspec init --tools claude
   ```

3. Copy project context: copy `.haytham/session/phase-4-specs/openspec/project.md` to `<project-directory>/openspec/project.md`, overwriting the default.

4. Copy domain specs: copy all spec directories from `.haytham/session/phase-4-specs/openspec/specs/` into `<project-directory>/openspec/specs/`. Preserve the directory structure (each `{domain}/spec.md`).

A PostToolUse hook automatically creates the `initial-mvp` change, copies specs into it, and seeds `design.md` with research directives when it detects `openspec init`. Check that `<project-directory>/openspec/changes/initial-mvp/` exists after the init completes.

## Completion

Tell the user:

> **Build setup complete.** Your project is ready at `<project-directory>/`.
>
> The change `initial-mvp` has been pre-seeded with your specs and research context. OpenSpec will skip the `done` artifacts (specs, design) and only generate the remaining ones.
>
> To implement, open a new Claude Code session in the project directory:
>
> ```
> cd <project-directory>
> claude
> ```
>
> Then run:
>
> ```
> /opsx:propose initial-mvp
> ```
>
> When it asks what you want to build, say:
>
> ```
> Build the full initial MVP from scratch. All requirements are already defined in the existing specs and design. Implement every domain.
> ```
>
> OpenSpec will find the existing change, skip the `done` artifacts (specs, design), and generate `proposal.md` and `tasks.md`. Then run `/opsx:apply initial-mvp` to implement task by task.
>
> This runs in a clean session so the implementation is generated purely from your specs.
>
> For future changes after the initial build:
>
> ```
> /opsx:propose <change-name>
> ```
