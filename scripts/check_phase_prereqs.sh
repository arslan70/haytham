#!/usr/bin/env bash
# PreToolUse hook: Verify phase prerequisites before launching agents.
# Reads JSON from stdin (tool_input), checks if required gate-decision files exist.
# Exit 0 = allow, Exit 2 + stderr message = block.

set -euo pipefail

# Read the tool input JSON from stdin
INPUT=$(cat)

# Extract the agent description (used to identify which agent is being launched)
DESCRIPTION=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    tool_input = data.get('tool_input', {})
    # Check both prompt and description fields for agent name references
    prompt = tool_input.get('prompt', '')
    desc = tool_input.get('description', '')
    print(prompt + ' ' + desc)
except Exception:
    print('')
" 2>/dev/null || echo "")

# Normalize to lowercase for matching
DESCRIPTION_LOWER=$(echo "$DESCRIPTION" | tr '[:upper:]' '[:lower:]')

# Map agent names to required prerequisite files
check_prereq() {
    local prereq_file="$1"
    local phase_name="$2"

    if [ ! -f "$prereq_file" ]; then
        echo "BLOCKED: $phase_name gate decision not found." >&2
        echo "Required file: $prereq_file" >&2
        echo "Complete the previous phase first." >&2
        exit 2
    fi
}

# Phase 2 agents require Phase 1 gate decision
if echo "$DESCRIPTION_LOWER" | grep -qE '(mvp-scoper|capability-modeler)'; then
    check_prereq ".haytham/session/phase-1-why/gate-decision.json" "Phase 1 (WHY)"
fi

# Phase 3 agents require Phase 2 gate decision
if echo "$DESCRIPTION_LOWER" | grep -qE '(architect)'; then
    check_prereq ".haytham/session/phase-2-what/gate-decision.json" "Phase 2 (WHAT)"
fi

# Phase 4 agents require Phase 3 gate decision
if echo "$DESCRIPTION_LOWER" | grep -qE '(spec-generator)'; then
    check_prereq ".haytham/session/phase-3-how/gate-decision.json" "Phase 3 (HOW)"
fi

# All checks passed
exit 0
