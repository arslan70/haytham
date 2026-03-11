---
description: Set up a new project from Phase 4 specs, ready for OpenSpec implementation
argument-hint: <project-directory>
allowed-tools: Read, Bash, Glob
---

# Haytham: Build Setup (Phase 5 - BUILD)

You are setting up a new project directory from Haytham's Phase 4 OpenSpec output, ready for implementation with OpenSpec.

## Prerequisites

Verify `.haytham/session/phase-4-specs/openspec/config.yaml` exists. If it doesn't, tell the user:
> "Phase 4 (specification) must be completed first. Run `/haytham:plan` to start."

Check that the user provided a project directory argument. If not, read `.haytham/session/phase-4-specs/openspec/config.yaml`, extract the `name` field, and use it as the directory name.

## Step 1: Check OpenSpec CLI

Run:
```bash
command -v openspec
```

If not found, tell the user:
> OpenSpec CLI is not installed. Install it with:
> ```
> npm install -g @fission-ai/openspec@latest
> ```
> Then re-run `/haytham:build`.

Stop here if openspec is not installed. Do not proceed.

## Step 2: Create Project

Using the project directory argument (or the name from config.yaml):

1. Check if the directory already exists. If it does, ask the user if they want to overwrite.
2. Create the directory:
   ```bash
   mkdir -p <project-directory>
   ```
3. Copy the OpenSpec output into it:
   ```bash
   cp -r .haytham/session/phase-4-specs/openspec/ <project-directory>/openspec/
   ```

Tell the user:
> **Project created.** Copied OpenSpec to `<project-directory>/openspec/`.

## Step 3: Initialize OpenSpec

Run:
```bash
cd <project-directory> && openspec init --tools claude
```

Tell the user:
> **OpenSpec initialized.** Claude Code skills and commands are set up.

## Completion

Tell the user:

> **Build setup complete.**
>
> Your project is ready at `<project-directory>/`. To start building:
>
> 1. Open a new Claude Code session in the project directory:
>    ```
>    cd <project-directory>
>    claude
>    ```
> 2. Generate implementation tasks:
>    ```
>    /opsx:propose
>    ```
> 3. Implement task by task:
>    ```
>    /opsx:apply
>    ```
> 4. Verify against the spec:
>    ```
>    /opsx:verify
>    ```
