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

5. Create the `initial-mvp` change directory and seed it:
   ```bash
   mkdir -p <project-directory>/openspec/changes/initial-mvp
   cp -r <project-directory>/openspec/specs <project-directory>/openspec/changes/initial-mvp/specs
   ```
   Then read `.haytham/session/phase-3-how/research-directives.json` and generate `<project-directory>/openspec/changes/initial-mvp/design.md` containing the research questions for capabilities that have `research_required: true`. Format as a markdown document with one section per capability listing its questions.

6. Generate a `CLAUDE.md` at the project root. This file orients the coding agent in the implementation session. Read these files to generate it:
   - `.haytham/session/phase-4-specs/openspec/config.yaml` (project name, description)
   - `.haytham/session/phase-4-specs/openspec/project.md` (tech stack, architecture decisions, data schemas, project structure)
   - `.haytham/session/phase-2-what/mvp-scope.md` (constraints, what's in/out of scope)
   - `.haytham/session/phase-2-what/capabilities.json` (what the system does)

   The CLAUDE.md should include:
   - **What This Is:** One paragraph explaining the product (from config.yaml description + MVP scope)
   - **Tech Stack:** List from project.md
   - **Commands:** npm scripts (dev, build, lint)
   - **Project Structure:** File tree from project.md
   - **Key Architecture Decisions:** 3-5 bullet points summarizing the most important decisions (not all 7). Focus on decisions that a developer would get wrong without context (e.g., "currency conversion is server-side only", "orders created from webhooks not form submission").
   - **Database Schema:** Table summaries from project.md
   - **Constraints:** Hard constraints from MVP scope that a developer must not violate (delivery geography, photo privacy, guest-only checkout, catalog limits, supported currencies)
   - **Environment Variables:** List from project.md
   - **Specification:** Pointers to the OpenSpec files with domain names and scenario counts

   Do NOT include the full architecture decisions prose. Keep it to what a developer needs to start coding correctly. Aim for under 150 lines.

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
