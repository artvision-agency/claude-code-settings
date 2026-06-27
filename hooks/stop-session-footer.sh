#!/usr/bin/env bash
set -euo pipefail

HELPER="/Users/antonk/artvision-data/.agents/skills/artvision-session-context/scripts/session-footer.sh"
[ -x "$HELPER" ] || exit 0

INPUT="$(cat 2>/dev/null || true)"
printf '%s' "$INPUT" | "$HELPER" || true
