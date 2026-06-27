#!/usr/bin/env bash
# usmile-month-start-runner.sh — 10-го числа 10:00: ПИНГ Антону (НЕ авто-создание задач).
# Напоминание сформировать задачи договорного месяца + проверить дозапись приложений договора.
set -uo pipefail
export PATH="/usr/local/bin:/usr/bin:/bin"
"$HOME/.claude/scripts/tg-send.sh" anton "🗓 USmile: начался новый договорный месяц — сформировать задачи месяца в Asana + проверить дозапись приложений договора (правило project-tasks-single-source-reconciliation §7)." || true
exit 0
