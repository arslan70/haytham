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

3. Copy project context files:
   - Copy `.haytham/session/phase-4-specs/openspec/project.md` to `<project-directory>/openspec/project.md`, overwriting the default.
   - Copy `.haytham/session/phase-4-specs/openspec/config.yaml` to `<project-directory>/openspec/config.yaml`. This carries project metadata (name, description, tech choices) that downstream tools need.

4. Copy domain specs: copy all spec directories from `.haytham/session/phase-4-specs/openspec/specs/` into `<project-directory>/openspec/specs/`. Preserve the directory structure (each `{domain}/spec.md`).

5. Create the `initial-mvp` change directory and seed it:
   ```bash
   mkdir -p <project-directory>/openspec/changes/initial-mvp
   cp -r <project-directory>/openspec/specs <project-directory>/openspec/changes/initial-mvp/specs
   ```
   Then read `.haytham/session/phase-3-how/research-directives.json` and generate `<project-directory>/openspec/changes/initial-mvp/design.md` containing the resolved research findings for capabilities that have `research_required: true`. Format as a markdown document with one section per capability. For each capability, list the research findings (verified integration patterns, env var names, SDK methods, API details) as actionable implementation guidance. If a directive has both `questions` and `findings`, present the findings as resolved answers. If a directive has questions but no findings, flag them explicitly as **unresolved** and mark them as requiring resolution during implementation: "⚠️ UNRESOLVED: [question]. This must be resolved during implementation. Do not proceed with assumptions." The coding agent must resolve these before implementing the affected capability.

6. Copy upstream context into the project. This carries the reasoning graph (why the product exists, who it's for, market landscape) so post-build activities (go-to-market, feature prioritization, pivots) can reference the original analysis without going back to the plugin repo.

   ```bash
   mkdir -p <project-directory>/openspec/context
   ```

   Copy these files from `.haytham/session/` into `<project-directory>/openspec/context/`:

   | Source | File | Contains |
   |--------|------|----------|
   | phase-1-why/ | concept-anchor.json | Core identity, invariants, founder profile, strategic signals |
   | phase-1-why/ | idea-analysis.md | Problem analysis, target segments, UVP, lean canvas |
   | phase-1-why/ | market-research.md | Market sizing, JTBD, trends, risks |
   | phase-1-why/ | competitor-research.md | Competitor profiles, sentiment, pricing, gaps |
   | phase-1-why/ | validation-report.md | GO/PIVOT/NO-GO decision with evidence and action plan |
   | phase-2-what/ | mvp-scope.md | Scope boundaries, success criteria, user flows |
   | phase-2-what/ | capabilities.json | Structured capability model |
   | phase-2-what/ | system-traits.json | Non-functional trait classifications |
   | phase-3-how/ | architecture-decisions.json | Architecture decision records |
   | phase-3-how/ | build-buy.json | Build vs buy analysis |

   Do NOT copy: gate-decision.json (pipeline state), research-brief.md (superseded by validation report), validation-report.json (machine duplicate of .md), validation-report.pdf (export format).

7. Generate a `CLAUDE.md` at the project root. This file orients the coding agent in the implementation session. Read these files to generate it:
   - `.haytham/session/phase-4-specs/openspec/config.yaml` (project name, description)
   - `.haytham/session/phase-4-specs/openspec/project.md` (tech stack, architecture decisions, data schemas, project structure)
   - `.haytham/session/phase-2-what/mvp-scope.md` (constraints, what's in/out of scope)
   - `.haytham/session/phase-2-what/capabilities.json` (what the system does)

   Include applicable sections from the following (skip any that don't apply to this product type):
   - **What This Is:** One paragraph explaining the product (from config.yaml description + MVP scope)
   - **Tech Stack:** List from project.md
   - **Commands:** Build/run commands from project.md (e.g., npm scripts, CLI entry points, make targets)
   - **Project Structure:** File tree from project.md
   - **Key Architecture Decisions:** 3-5 bullet points summarizing the most important decisions (not all of them). Focus on decisions that a developer would get wrong without context (e.g., non-obvious data flow, server-side vs client-side boundaries, integration patterns).
   - **Data Model:** Schema summaries from project.md (database tables, config files, or data structures depending on product type)
   - **Constraints:** Hard constraints from MVP scope that a developer must not violate
   - **Environment Variables:** Configuration required from project.md (if applicable)
   - **Strategic Context:** A table listing each file in `openspec/context/`, what it contains, and when to use it. Frame it as: "Use these files when working on anything beyond code implementation: go-to-market strategy, feature prioritization, positioning, pivot decisions, or competitive analysis." Include all 10 files from step 6.
   - **Specification:** Pointers to the OpenSpec files with domain names and scenario counts

   Do NOT include the full architecture decisions prose. Keep it to what a developer needs to start coding correctly. Aim for under 170 lines.

## Cleanup

Delete the `.haytham/session/` directory. The phase-4 output is now in `openspec/` and the phase 1-3 intermediates are preserved in git history. `openspec/` is the single source of truth going forward.

```bash
rm -rf .haytham/session/
```

If `.haytham/` is now empty, remove it too:

```bash
rmdir .haytham/ 2>/dev/null
```

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
> For future changes after the initial build, use `/haytham:evolve` from the project directory. It reads the reasoning graph in `openspec/` and maintains it alongside your code change:
>
> ```
> /haytham:evolve "<description of the change>"
> ```
