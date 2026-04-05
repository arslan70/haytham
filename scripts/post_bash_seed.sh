#!/usr/bin/env bash
# PostToolUse hook for Bash: detects openspec init and fixes config.yaml quoting.
# The initial-mvp seeding is handled explicitly by commands/build.md (steps 5-6).
# This hook only fixes YAML quoting issues that openspec init introduces.

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

exit 0
