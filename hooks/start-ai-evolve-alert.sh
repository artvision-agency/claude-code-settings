#!/bin/bash
# SessionStart hook: алерт если свежий ai-evolve-suggestions отчёт и /ai-evolve ещё не запускали
set -euo pipefail

SUGGESTIONS_DIR="$HOME/.claude/ai-evolve-suggestions"
LATEST="$SUGGESTIONS_DIR/latest.md"
APPLIED_MARKER="$SUGGESTIONS_DIR/.last-applied"

[ -f "$LATEST" ] || exit 0

# Если отчёт старше 10 дней — показывать нет смысла, cron не отработал
LATEST_AGE=$(( ($(date +%s) - $(stat -f %m "$LATEST" 2>/dev/null || echo 0)) / 86400 ))
[ "$LATEST_AGE" -gt 10 ] && exit 0

# Если marker новее отчёта — уже применили
if [ -f "$APPLIED_MARKER" ] && [ "$APPLIED_MARKER" -nt "$LATEST" ]; then
    exit 0
fi

cat << EOF

═══════════════════════════════════════════
  🧠 AI EVOLVE — новый weekly-отчёт ($LATEST_AGE дн. назад)
  Запусти в artvision-data: /ai-evolve
  Детали: $LATEST
═══════════════════════════════════════════

EOF
exit 0
