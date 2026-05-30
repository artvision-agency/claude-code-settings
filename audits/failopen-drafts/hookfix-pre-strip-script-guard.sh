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

# Bypass (легитимный, сохранён как был)
[ "${STRIP_FORCE:-0}" = "1" ] && exit 0

# --- Чтение команды: env → stdin JSON (fail-CLOSED) ---------------------------
# Харнес PreToolUse обычно передаёт payload в stdin как JSON:
#   {"tool_name":"Bash","tool_input":{"command":"python strip_x.py ..."}}
# Старая версия читала CMD только из env и при пустом env делала exit 0,
# пропуская strip-скрипт без --dry-run (прецедент ant-partners 157 секций).
# Теперь: если env пуст — парсим stdin. Сбой парса/отсутствие jq на strip-payload
# = БЛОКИРОВАТЬ (exit 2), не пропускать.

CMD="${CLAUDE_BASH_COMMAND:-${TOOL_INPUT_COMMAND:-}}"

# Сигнатура опасного strip/clean/fix-скрипта (для grep по сырому payload).
DANGER_RE='python[0-9]*[[:space:]]+([^[:space:]]*/)?(.*strip.*|.*clean.*|.*fix_inline.*|.*fix_clean.*)\.py'

STDIN_RAW=""
if [ -z "$CMD" ]; then
  # Читаем stdin один раз (может быть пусто, если хук вызван без payload).
  STDIN_RAW="$(cat 2>/dev/null || true)"

  if [ -n "$STDIN_RAW" ]; then
    # Определяем, выглядит ли сырой payload как опасный strip/clean/fix вызов.
    raw_is_danger=0
    if echo "$STDIN_RAW" | grep -qE "$DANGER_RE"; then
      raw_is_danger=1
    fi

    if command -v jq >/dev/null 2>&1; then
      # Пытаемся распарсить command из tool_input. Захватываем код выхода jq
      # отдельно (без `|| true`, чтобы $? отражал реальный результат jq).
      set +e
      PARSED="$(printf '%s' "$STDIN_RAW" | jq -r '.tool_input.command // empty' 2>/dev/null)"
      JQ_RC=$?
      set -e
      if [ "$JQ_RC" -ne 0 ]; then
        # jq упал на парсе. Если payload пахнет strip/clean/fix — fail-CLOSED.
        if [ "$raw_is_danger" = "1" ]; then
          echo "⛔ STRIP-SCRIPT GUARD: stdin JSON не распарсился (jq error), но payload похож на strip/clean/fix вызов. Блокирую (fail-closed)." >&2
          echo "Payload (сырой): $STDIN_RAW" >&2
          echo "Bypass (если уверен): STRIP_FORCE=1" >&2
          exit 2
        fi
        # Иначе — не наша зона ответственности, пропускаем.
        exit 0
      fi
      if [ -n "$PARSED" ]; then
        CMD="$PARSED"
      else
        # jq отработал, но command пуст. Если сырой payload опасен — fail-CLOSED
        # (значит структура не та, что ожидаем, а команда выглядит деструктивной).
        if [ "$raw_is_danger" = "1" ]; then
          echo "⛔ STRIP-SCRIPT GUARD: не извлёк tool_input.command из stdin, но сырой payload похож на strip/clean/fix. Блокирую (fail-closed)." >&2
          echo "Payload (сырой): $STDIN_RAW" >&2
          echo "Bypass (если уверен): STRIP_FORCE=1" >&2
          exit 2
        fi
        # Команда реально пустая и не опасна — нечего проверять.
        exit 0
      fi
    else
      # jq отсутствует — обязательная зависимость для парса stdin недоступна.
      # Если payload пахнет strip/clean/fix — fail-CLOSED, иначе пропускаем.
      if [ "$raw_is_danger" = "1" ]; then
        echo "⛔ STRIP-SCRIPT GUARD: jq не установлен, не могу распарсить stdin, а payload похож на strip/clean/fix вызов. Блокирую (fail-closed)." >&2
        echo "Payload (сырой): $STDIN_RAW" >&2
        echo "Установите jq или используйте STRIP_FORCE=1 если уверены." >&2
        exit 2
      fi
      exit 0
    fi
  fi
fi

# Если после env+stdin команда так и не определена — проверять нечего.
[ -z "$CMD" ] && exit 0

# Совпадает ли с целевым паттерном?
# python ... (path)*strip*.py | *clean*.py | *fix_inline*.py | *fix_clean*.py
if echo "$CMD" | grep -qE "$DANGER_RE"; then
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
    # exit 2 — для PreToolUse это блокирующий код (stderr возвращается агенту).
    # Раньше был exit 1 (non-blocking) — усилено до fail-CLOSED.
    exit 2
  fi
fi

exit 0
