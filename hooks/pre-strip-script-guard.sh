#!/bin/bash
# pre-strip-script-guard.sh — PreToolUse(Bash) guard
#
# Блокирует запуск python-скриптов с именами *strip*.py / *clean*.py / *fix_inline*.py /
# *fix_clean*.py на путях clients/*/ без флага --dry-run при первом прогоне.
#
# Прецедент: ant-partners 24.02 — strip_inline_duplicates.py удалил 157 секций из 29 JSON
# при «29/29 PASS» валидаторе (ant-partners/patches/2026-02-24_content-strip-and-structure-incident.md).
# Также 03.03 — fix_clean_revision сократил 564→72 файла без явного бэкапа.
#
# Bypass: STRIP_FORCE=1
# Регистрация: ~/.claude/settings.json → hooks.PreToolUse → matcher "Bash"

set -euo pipefail

CMD="${CLAUDE_BASH_COMMAND:-${TOOL_INPUT_COMMAND:-}}"
[ -z "$CMD" ] && exit 0

# Bypass
[ "${STRIP_FORCE:-0}" = "1" ] && exit 0

# Совпадает ли с целевым паттерном?
# python ... (path)*strip*.py | *clean*.py | *fix_inline*.py | *fix_clean*.py
if echo "$CMD" | grep -qE 'python[0-9]*[[:space:]]+([^[:space:]]*/)?(.*strip.*|.*clean.*|.*fix_inline.*|.*fix_clean.*)\.py'; then
  # Только на путях clients/* или templates/* artvision-data
  if echo "$CMD" | grep -qE '(clients/|templates/|artvision-data/)'; then
    # Если есть --dry-run — пропускаем
    if echo "$CMD" | grep -qE -- '--dry[-_]?run'; then
      exit 0
    fi
    # Блокируем
    cat >&2 <<EOF
⛔ STRIP-SCRIPT GUARD: блокирую запуск.

Команда: $CMD

Прецедент: ant-partners 24.02 — strip_inline_duplicates.py удалил 157 секций из 29 JSON,
валидатор показал «29/29 PASS» (валидация по grep на CSS-классы вместо DOM).

Обязательный порядок:
  1. git stash ИЛИ feature branch перед запуском
  2. Прогон с --dry-run → ручная сверка количества затрагиваемых секций/файлов
  3. Реальный прогон + git diff --stat сразу после
  4. Если файлов/секций упало >10% — STOP, ручное подтверждение

Bypass (если уверен): STRIP_FORCE=1 <команда>
EOF
    exit 1
  fi
fi

exit 0
