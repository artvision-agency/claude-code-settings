#!/bin/bash
# session-continue-pin.sh — ЧЕРНОВИК (v0.1, НЕ зарегистрирован в settings.json).
#
# СТАТУС: ждёт approve Антона + тест 3 кейса (3 пин-сработки / 3 пропуска / bypass).
# НЕ РЕГИСТРИРОВАТЬ в ~/.claude/settings.json без явного approve — SessionStart-хук
# срабатывает КАЖДУЮ сессию на 3 аккаунтах (blast-radius, кривой ломает старт).
#
# Назначение (БОЛЬ Антона — спека 2026-06-20 «бесшовное продолжение сессии»):
#   После /clear свежая сессия ДРЕЙФУЕТ в комбайн/меню и теряет тему до-clear сессии.
#   Этот хук при старте сессии (source=clear|resume) проверяет: есть ли свежий маркер
#   активного autopilot (/tmp/autopilot-active-<slug>)? Если да — инжектит system-reminder:
#   «продолжи ЭТУ тему по STATUS.md, НЕ показывай меню-комбайн». Подавляет дрейф.
#
# Контракт SessionStart-хука (code.claude.com/docs/en/hooks):
#   - stdin: JSON c полем "source" (startup|resume|clear|compact) и др.
#   - stdout (exit 0): печатаем текст → попадает в контекст сессии как additionalContext.
#   - inject-only: НИКОГДА не exit!=0 на старте (сломает запуск сессии). Только инжект.
#
# Bypass: AUTOPILOT_PIN_OFF=1 — полностью отключает (обычный старт без пина).

set -uo pipefail

# --- bypass ---
if [ "${AUTOPILOT_PIN_OFF:-0}" = "1" ]; then
  exit 0
fi

# --- прочитать source из stdin JSON (best-effort, без падения) ---
INPUT="$(cat 2>/dev/null || true)"
SOURCE="$(printf '%s' "$INPUT" | python3 -c 'import sys,json
try:
    print(json.load(sys.stdin).get("source",""))
except Exception:
    print("")' 2>/dev/null || echo "")"

# Пин нужен на продолжении сессии, не на чистом первом старте.
case "$SOURCE" in
  clear|resume|compact) ;;
  *) exit 0 ;;
esac

# --- найти свежий маркер активного autopilot ---
# Маркер пишет skill autopilot: /tmp/autopilot-active-<slug>
# Формат (key=value построчно): slug=, status_path=, theme=, ts=
# «Свежий» = mtime моложе 12 часов (иначе считаем темой брошенной).
MAX_AGE_SEC=43200   # 12h
NOW="$(date +%s)"
PIN=""
for f in /tmp/autopilot-active-* ; do
  [ -e "$f" ] || continue
  mtime="$(stat -f %m "$f" 2>/dev/null || stat -c %Y "$f" 2>/dev/null || echo 0)"
  age=$(( NOW - mtime ))
  if [ "$age" -lt "$MAX_AGE_SEC" ]; then
    PIN="$f"
    break
  fi
done

[ -n "$PIN" ] || exit 0   # нет активного autopilot → обычный старт

# --- извлечь поля маркера ---
get() { sed -n "s/^$1=//p" "$PIN" 2>/dev/null | head -1; }
SLUG="$(get slug)"
STATUS_PATH="$(get status_path)"
THEME="$(get theme)"

if [ -z "${SLUG:-}" ]; then
  exit 0
fi
[ -n "${STATUS_PATH:-}" ] || STATUS_PATH="clients/$SLUG/STATUS.md"
[ -n "${THEME:-}" ] || THEME="см. STATUS.md"

# --- инжект напоминания (additionalContext) ---
cat <<EOF
[AUTOPILOT-CONTINUE] Активна autopilot-тема по проекту «${SLUG}».
ТЕМА: ${THEME}
Действия БЕЗ дрейфа в комбайн/меню:
  1. НЕ показывай меню перекрёстка / не запускай /go / /combine.
  2. Прочитай ПЕРВЫМ: ${STATUS_PATH} + clients/${SLUG}/context-log.md (resume-read-project-state).
  3. Re-create Task-tool задачи из секции ОЧЕРЕДЬ STATUS (каждый [ ] -> TaskCreate; [x]/[lock] пропустить).
  4. Сверь [x] с фактом (git log / campaigns.get State) — расхождение -> верни в [ ] (explicit-approval-tracking).
  5. Продолжи верхний [ ] из ОЧЕРЕДИ. Money-scope (whitelist/blacklist) — из STATUS, blacklist -> Ждёт-Антона, CONFIRM.
Маркер: ${PIN} (снять — rm, когда очередь пуста или всё в Ждёт-Антона). Bypass хука: AUTOPILOT_PIN_OFF=1.
EOF

exit 0
