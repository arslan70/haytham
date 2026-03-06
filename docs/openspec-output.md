# OpenSpec Output

After the STORIES phase completes, Haytham can export the full specification as [OpenSpec](https://github.com/Fission-AI/OpenSpec), a lightweight, capability-oriented format designed for AI coding agents.

## What Gets Exported

Every Haytham artifact maps to a specific location in the OpenSpec output.

| Haytham Artifact | OpenSpec Location |
|---|---|
| Capabilities (CAP-F-\*, CAP-NF-\*) | `specs/{domain}/spec.md` as SHALL statements |
| Acceptance criteria | Gherkin scenarios in `spec.md` |
| Architecture decisions (DEC-\*) | `project.md` |
| Build/buy recommendations | `project.md` |
| System traits | `config.yaml` |
| Non-functional capabilities | `specs/cross-cutting/spec.md` |

## Directory Structure

```
openspec/
  config.yaml                  # Project metadata, system traits, appetite
  project.md                   # Tech stack, architecture decisions, build/buy
  specs/
    user-authentication/
      spec.md                  # SHALL statements + Gherkin scenarios
    leaderboard-management/
      spec.md
    cross-cutting/
      spec.md                  # Non-functional requirements
```

## Using OpenSpec with Coding Agents

The OpenSpec output is designed to be dropped into a project root and consumed directly by coding agents.

### Claude Code

Add the spec directory to your `CLAUDE.md`:

```markdown
# Project Spec
See `openspec/` for the full specification.
Start with `openspec/project.md` for architecture context,
then implement specs in `openspec/specs/` order.
```

### Other Agents

Any agent that reads markdown files from disk can consume the format. Point the agent at `openspec/` and let it discover the structure.

## Links

- [OpenSpec repository](https://github.com/Fission-AI/OpenSpec)
