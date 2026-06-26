#!/bin/zsh
# stop-result-checklist.sh — Stop hook (warn-only, НЕ блокирует).
# Когда ответ заявляет результат (готово/деплой/вот ссылк/PASS/HTTP 200) —
# рендерит чек-бокс-таблицу из Acceptance criteria текущего recap.
# Детерминированно (bash+python, 0 LLM-токенов). Bypass: RESULT_CHECKLIST_OFF=1
set -u
[ "${RESULT_CHECKLIST_OFF:-}" = "1" ] && exit 0
command -v python3 >/dev/null 2>&1 || exit 0
DIR="${0:A:h}"
cat | python3 "$DIR/lib/result-checklist.py" 2>/dev/null || true
exit 0
