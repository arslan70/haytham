# Documentation Update Design: OpenSpec + Spec Kit Export

**Date:** 2026-03-01
**Status:** Design approved
**Goal:** Update all documentation to reflect the completed OpenSpec + Spec Kit export feature, plus create a blog post for community outreach in OpenSpec/Spec Kit Discord and Reddit channels.

## Context

OpenSpec and Spec Kit project-level exporters were added in PRs #37, #38, #39. The feature is fully implemented:

- `OpenSpecExporter` produces `openspec/` directory trees
- `SpecKitExporter` produces `.specify/` directory trees
- UI integration in Streamlit stories view (dropdown with zip download)
- Execution Contract Schema (ADR-028) provides the structured data layer

However, existing documentation doesn't mention the feature. The roadmap still lists it as planned. The README, landing page, how-it-works, getting-started, and example session pages describe story-level exports only.

## Approach

Full docs refresh (Approach A): update every page that describes Haytham's output, plus a new dedicated exports page, plus a blog post targeting OpenSpec/Spec Kit communities.

## Changes

### Part 1: Existing Page Updates

#### 1. README.md
Add one bullet to "What You Get":
- "Spec-driven exports: Download your specification as OpenSpec or Spec Kit, ready for any AI coding agent (Claude Code, Cursor, Copilot)."

#### 2. docs/index.md (landing page)
Add a fifth card to "What you get" grid:
- Icon: `:material-export:` or similar
- Title: "Agent-ready exports"
- Body: "Download as OpenSpec or Spec Kit. Feed your spec directly to Claude Code, Cursor, or Copilot."

#### 3. docs/how-it-works.md
Add a "Spec-Driven Export" subsection after the "Final Output" section at the end of Phase 4. Cover:
- Two export formats available after STORIES phase
- Brief comparison (OpenSpec for iterative specs, Spec Kit for greenfield GitHub-native projects)
- Link to the new exports page for details

#### 4. docs/getting-started.md
Add step 7 to "Your First Run": after stories are generated, export as OpenSpec or Spec Kit zip. One paragraph explaining where to find the export button and what the zip contains.

#### 5. docs/example-session/index.md
Add item 10 showing the OpenSpec/Spec Kit export (after the existing Jira export screenshot). Reference a sample export or describe the UI flow.

#### 6. docs/roadmap.md
Mark Item 5 (Spec-Driven Export) as **complete**. Update status text. Keep the item in place (it documents what was built). Update the sequencing diagram to show Item 5 as done.

#### 7. docs/architecture/overview.md
- Add `exporters/` to the Project Structure tree with a note about project-level exporters
- Brief mention in the component architecture section: project-level exporters aggregate full session context via `ExportableProject` and produce directory trees as zip archives

### Part 2: New Exports Page

#### docs/exports.md

Sections:
1. **Introduction**: Haytham exports to two spec-driven formats. Both are consumed by AI coding agents.
2. **Format Comparison**: Table with OpenSpec vs Spec Kit strengths and best-for scenarios
3. **What Gets Exported**: Mapping table (Haytham artifact to export format field)
4. **Directory Structures**: Tree diagrams for both `openspec/` and `.specify/`
5. **Using Exports with Coding Agents**: Brief instructions for Claude Code, Cursor, Copilot
6. **Where to Find It**: UI location (export dropdown after STORIES phase)
7. **Links**: OpenSpec repo, Spec Kit repo, ADR-028

#### mkdocs.yml
Add "Exports: exports.md" between "Example Session" and "Getting Started" in the nav.

### Part 3: Blog Post

#### docs/blog/posts/2026-03-01-idea-to-agent-ready-spec.md

**Title:** "From Startup Idea to Agent-Ready Spec in 20 Minutes"
**Categories:** Multi-Agent Systems, Architecture
**Audience:** OpenSpec/Spec Kit community members, AI coding agent users

Structure:
1. Hook: raw idea to validated OpenSpec/Spec Kit export in 20 minutes
2. The problem: coding agents need structured specs, someone has to write them
3. What Haytham does: 19 agents validate, scope, design, and plan
4. Show the output: real directory tree, sample spec.md, sample constitution.md
5. How to try it: quick start, link to repo
6. What's next: coding agent integration (Phase 5)

Style: follows CLAUDE.md blog writing guidelines (conversational, prose paragraphs, concrete examples, no bullet decomposition of arguments, active voice).

## Out of Scope

- No code changes. Documentation only.
- No new screenshots (use existing or describe UI). If the user provides sample exports, include them.
- No changes to the export implementation itself.
