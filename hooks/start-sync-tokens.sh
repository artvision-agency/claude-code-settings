#!/bin/bash
# SessionStart hook — auto-pull tokens.json from VPS if remote is newer.
# Тихий: при ошибке SSH / нет VPS — выходит без шума, не блокирует старт.
# Лог: ~/.claude/logs/sync-tokens.log

set -u
SCRIPT="$HOME/.claude/scripts/sync-tokens.sh"
[ -x "$SCRIPT" ] || exit 0

# Запускаем в фоне с тайм-аутом, чтобы не тормозить старт сессии
(
  timeout 10 "$SCRIPT" pull 2>&1 | tail -1
) </dev/null >>"$HOME/.claude/logs/sync-tokens.log" 2>&1 &
disown 2>/dev/null || true

exit 0
