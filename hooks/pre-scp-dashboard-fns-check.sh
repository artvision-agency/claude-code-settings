#!/usr/bin/env bash
# pre-scp-dashboard-fns-check.sh — блокирует scp клиентских дашбордов с ФНС-mislabel
#
# Срабатывает: PreToolUse Bash на `scp ... clients/*/dashboard*.html` ИЛИ
#              `scp ... clients/*/director-cabinet*.html` ИЛИ
#              `scp ... presales/*/mirbir-simple*.html`
#
# Прецедент 2026-05-20:
#   Strict-аудит нашёл что на live MIRBIR кабинета были устаревшие данные ФНС 2024
#   и mislabel «net profit = EBITDA». Этот хук ловит mislabel и пропускает WARN.
#
# Bypass: FNS_CHECK_SKIP=1 scp ...

set -euo pipefail

# Парсим аргументы tool_input из stdin (hook contract)
JSON_INPUT=$(cat)

# Достаём command из tool_input
COMMAND=$(echo "$JSON_INPUT" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('tool_input', {}).get('command', ''))" 2>/dev/null || echo "")

# Не наш scp — пропускаем
if [[ ! "$COMMAND" =~ scp.*\.html ]]; then
    exit 0
fi

# Bypass
if [[ "${FNS_CHECK_SKIP:-}" == "1" ]]; then
    echo "[pre-scp-dashboard-fns-check] SKIP по FNS_CHECK_SKIP=1" >&2
    exit 0
fi

# Извлекаем path локального файла из scp команды (первый аргумент scp)
# scp PATH user@host:remote
FILE=$(echo "$COMMAND" | grep -oE '(/Users/antonk/|~/)[^ ]+\.html' | head -1 || true)
[ -z "$FILE" ] && exit 0
FILE="${FILE/#\~\//$HOME/}"

# Только дашборды клиентов / mirbir-simple
if [[ ! "$FILE" =~ (dashboard|director-cabinet|mirbir-simple|cabinet) ]]; then
    exit 0
fi
if [[ ! "$FILE" =~ (clients/|presales/) ]]; then
    exit 0
fi

[ -f "$FILE" ] || exit 0

SCRIPT="$HOME/.claude/scripts/factcheck-fns-freshness.py"
[ -x "$SCRIPT" ] || exit 0

# Запускаем — exit 2 = CRITICAL (блок), exit 1 = WARN (пропуск с сообщением)
OUTPUT=$(python3 "$SCRIPT" "$FILE" --json 2>/dev/null || true)

CRITICAL=$(echo "$OUTPUT" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('summary', {}).get('CRITICAL', 0))" 2>/dev/null || echo "0")
WARN=$(echo "$OUTPUT" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('summary', {}).get('WARN', 0))" 2>/dev/null || echo "0")

if [ "$CRITICAL" -gt 0 ]; then
    echo "" >&2
    echo "⛔ pre-scp-dashboard-fns-check: $CRITICAL CRITICAL findings" >&2
    echo "" >&2
    echo "Найдены mislabel метрики (например 'net profit = EBITDA') или другие фактологические ошибки." >&2
    echo "Запусти: python3 $SCRIPT $FILE" >&2
    echo "Bypass: FNS_CHECK_SKIP=1 scp ..." >&2
    echo "" >&2
    exit 1
fi

if [ "$WARN" -gt 5 ]; then
    echo "" >&2
    echo "⚠ pre-scp-dashboard-fns-check: $WARN WARN findings" >&2
    echo "Финансовые числа без явного года или URL источника." >&2
    echo "Проверь вручную: python3 $SCRIPT $FILE" >&2
    echo "(scp пропускается, но рекомендуется добавить URL list-org/rusprofile)" >&2
    echo "" >&2
fi

exit 0
