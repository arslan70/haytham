#!/usr/bin/env bash
# PostToolUse hook for Bash: detects openspec init and auto-seeds the change.
# Reads JSON from stdin with tool_input.command and tool_response.
# Only acts when the command contains "openspec init" AND research-directives.json exists.

set -euo pipefail

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null || echo "")

# Only trigger on openspec init commands
if ! echo "$COMMAND" | grep -q "openspec init"; then
  exit 0
fi

# Extract the project directory from the command (cd <dir> && openspec init ...)
PROJECT_DIR=$(echo "$COMMAND" | python3 -c "
import sys, re
cmd = sys.stdin.read().strip()
# Match: cd <path> && openspec init OR cd <path>; openspec init
m = re.search(r'cd\s+([^\s;&]+)', cmd)
if m:
    print(m.group(1))
else:
    print('')
" 2>/dev/null || echo "")

if [ -z "$PROJECT_DIR" ]; then
  exit 0
fi

# Resolve to absolute path
if [[ "$PROJECT_DIR" != /* ]]; then
  PROJECT_DIR="$(pwd)/$PROJECT_DIR"
fi

# Check if this is a haytham build (research-directives.json exists)
# The project dir is typically created adjacent to .haytham/, so check the parent
SESSION_DIR=""
PARENT_DIR="$(dirname "$PROJECT_DIR")"
for candidate in "$PARENT_DIR/.haytham/session" ".haytham/session"; do
  if [ -d "$candidate" ] && [ -f "$candidate/phase-3-how/research-directives.json" ]; then
    SESSION_DIR="$(cd "$candidate" && pwd)"
    break
  fi
done

if [ -z "$SESSION_DIR" ]; then
  exit 0
fi

# Check that specs exist (confirms this is a haytham build, not a random openspec init)
if [ ! -d "$SESSION_DIR/phase-4-specs/openspec/specs" ]; then
  exit 0
fi

# Fix config.yaml quoting: openspec init generates unquoted YAML values.
# User-provided fields (name, description) may contain colons, which break
# YAML parsing. Only fix those fields to limit blast radius.
CONFIG="$PROJECT_DIR/openspec/config.yaml"
if [ -f "$CONFIG" ]; then
  python3 - "$CONFIG" <<'PYEOF' 2>/dev/null || true
import re, sys
config_path = sys.argv[1]
lines = open(config_path).readlines()
fixed = []
for line in lines:
    m = re.match(r'^(\w+): (.+)$', line)
    if m and m.group(1) in ('name', 'description') and ': ' in m.group(2) and not m.group(2).startswith('"'):
        fixed.append(f'{m.group(1)}: "{m.group(2)}"\n')
    else:
        fixed.append(line)
open(config_path, 'w').writelines(fixed)
PYEOF
fi

# Create the change and seed it (all in a subshell so cd doesn't leak)
(
  cd "$PROJECT_DIR" || exit 0

  # Skip seeding if the change already exists (prevents overwriting manual edits on re-run)
  if [ -d "openspec/changes/initial-mvp" ]; then
    echo "[haytham] WARNING: initial-mvp change already exists, skipping seed" >&2
    exit 0
  fi

  openspec new change initial-mvp > /dev/null 2>&1 || true

  if [ ! -d "openspec/changes/initial-mvp" ]; then
    echo "[haytham] WARNING: Failed to create initial-mvp change" >&2
    exit 0
  fi

  # Copy specs into the change
  mkdir -p "openspec/changes/initial-mvp/specs"
  cp -r openspec/specs/* "openspec/changes/initial-mvp/specs/" 2>/dev/null || true

  # Generate design.md from research directives
  DIRECTIVES="$SESSION_DIR/phase-3-how/research-directives.json"
  python3 - "$DIRECTIVES" <<'PYEOF' || echo "[haytham] WARNING: Failed to generate design.md from research directives" >&2
import json, sys

directives_path = sys.argv[1]
with open(directives_path) as f:
    data = json.load(f)

directives = [d for d in data.get('directives', []) if d.get('research_required')]
if not directives:
    sys.exit(0)

lines = [
    '## Context',
    '',
    'Implementation design for the initial MVP build.',
    '',
    '## Pre-Implementation Research',
    '',
    'Some capabilities require domain research before implementation. For each item below, research the questions BEFORE writing code for that capability. Apply your findings to the implementation approach.',
    '',
]

for d in directives:
    name = d.get('capability_name', d.get('capability_id', 'Unknown'))
    cap_id = d.get('capability_id', '')
    classifications = ', '.join(d.get('classifications', []))
    lines.append(f'### {name} [{cap_id}]')
    lines.append(f'**Classification:** {classifications}')
    for q in d.get('questions', []):
        lines.append(f'- {q}')
    lines.append('')

lines.extend([
    '## Goals / Non-Goals',
    '',
    '**Goals:** Build the full initial MVP from specs.',
    '**Non-Goals:** No optimization, no deployment, no testing infrastructure beyond what specs require.',
    '',
])

design_path = 'openspec/changes/initial-mvp/design.md'
with open(design_path, 'w') as f:
    f.write('\n'.join(lines))

print(f'[haytham] Seeded design.md with {len(directives)} research directives', file=sys.stderr)
PYEOF
)

cat >&2 <<'HOOKEOF'
[haytham] Created initial-mvp change with specs and research directives.

IMPORTANT: Tell the user these exact next steps (NOT the openspec init output):

  The change initial-mvp has been pre-seeded with specs and research context.

  To implement, open a new Claude Code session in the project directory:
    cd <project-directory>
    claude

  Then run:
    /opsx:propose initial-mvp

  When it asks what you want to build, say:
    Build the full initial MVP from scratch. All requirements are already defined in the existing specs and design. Implement every domain.

  OpenSpec will skip the done artifacts (specs, design) and generate proposal.md and tasks.md.
  Then run /opsx:apply initial-mvp to implement task by task.
HOOKEOF
exit 0
