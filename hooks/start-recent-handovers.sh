#!/usr/bin/env bash
# Inject last 3 handovers' headers into SessionStart context.
# Cheap to read (~30-50 lines total), gives Claude immediate context for
# "yesterday/recently did X" questions without searching Drive/Asana first.

set -euo pipefail

HANDOVERS_DIR=""
for candidate in \
  "${CLAUDE_HANDOVERS_DIR:-}" \
  "$HOME/.claude/handovers" \
  "${CLAUDE_PROJECT_DIR:-}/handovers" \
  "$(dirname "$0")/../handovers"; do
  if [ -n "$candidate" ] && [ -d "$candidate" ]; then
    HANDOVERS_DIR="$candidate"
    break
  fi
done
[ -n "$HANDOVERS_DIR" ] || exit 0

mapfile -t recent < <(ls "$HANDOVERS_DIR"/HANDOVER-*.md 2>/dev/null | sort -r | head -3)
[ "${#recent[@]}" -gt 0 ] || exit 0

echo "## Recent handovers (read first when user asks about past work)"
echo ""
for f in "${recent[@]}"; do
  name=$(basename "$f")
  echo "### $name"
  head -10 "$f" | sed 's/^/  /'
  echo ""
done
echo "Full content: Read \`handovers/<filename>\` — search handovers/ BEFORE Drive/Asana."
