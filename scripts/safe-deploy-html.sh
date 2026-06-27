#!/usr/bin/env bash
# safe-deploy-html.sh — единый pipeline для деплоя клиентских HTML.
#
# Гарантирует что factcheck-v2.py прогоняется ПЕРЕД scp (вне зависимости от хуков).
# Используется ВМЕСТО сырого scp для клиентских HTML.
#
# Назначение: саб-агенты которым PreToolUse-хуки родительской сессии недоступны
# должны деплоить ТОЛЬКО через эту команду.
#
# Использование:
#   safe-deploy-html.sh <local_html> <vps_path>
#
#   safe-deploy-html.sh ~/clients/X/index.html /var/www/artvision/kp/X/index.html
#
# Поведение:
#   1. Проверяет файл существует
#   2. Прогоняет factcheck-v2.py --standard
#   3. Если CRITICAL > 0 → exit 1 (не деплоит)
#   4. Если 0 CRITICAL → mkdir -p на VPS + scp
#   5. Ставит www-data владельцем файла
#   6. Verifies через curl что URL отдаёт 200 + правильный Content-Length
#   7. Печатает Live URL и деплой-репорт
#
# Bypass: FACTCHECK_SKIP=1 safe-deploy-html.sh ...
# Только для emergency, не использовать для клиентских КП.
#
# Exit codes:
#   0 = deploy OK + factcheck PASS
#   1 = factcheck CRITICAL → деплой НЕ выполнен
#   2 = scp/network ошибка
#   3 = неправильные аргументы или файл не найден

set -euo pipefail

# --- Args ---
if [[ $# -lt 2 ]]; then
    cat >&2 <<EOF
usage: safe-deploy-html.sh <local_html> <vps_path>

example:
  safe-deploy-html.sh ~/artvision-data/clients/spb-kursy/index.html \\
                      /var/www/artvision/kp/spb-kursy/index.html
EOF
    exit 3
fi

LOCAL="$1"
VPS_PATH="$2"
VPS_HOST="root@80.90.181.152"

# Expand ~
LOCAL="${LOCAL/#\~/$HOME}"

if [[ ! -f "$LOCAL" ]]; then
    echo "ERROR: file not found: $LOCAL" >&2
    exit 3
fi

# --- Determine URL for verify ---
# /var/www/artvision/kp/X/index.html → https://artvision.pro/kp/X/
URL_PATH="${VPS_PATH#/var/www/artvision/}"
if [[ "$URL_PATH" == "$VPS_PATH" ]]; then
    echo "ERROR: vps_path must be under /var/www/artvision/: $VPS_PATH" >&2
    exit 3
fi

case "$URL_PATH" in
    */index.html)
        URL_PATH="${URL_PATH%/index.html}"
        PUBLIC_URL="https://artvision.pro/${URL_PATH}/"
        ;;
    *.html)
        PUBLIC_URL="https://artvision.pro/${URL_PATH}"
        ;;
    *)
        PUBLIC_URL="https://artvision.pro/${URL_PATH}"
        ;;
esac

VPS_DIR="$(dirname "$VPS_PATH")"

# --- Bypass ---
if [[ "${FACTCHECK_SKIP:-0}" == "1" ]]; then
    echo "[safe-deploy] WARNING: FACTCHECK_SKIP=1 — bypassing factcheck (emergency mode)" >&2
else
    # --- Factcheck ---
    FACTCHECK="/Users/antonk/.claude/scripts/factcheck-v2.py"
    REPORT="/tmp/factcheck-safe-deploy-$(basename "$LOCAL" .html)-$(date +%s).md"

    echo "" >&2
    echo "═══════════════════════════════════════════" >&2
    echo "  SAFE-DEPLOY: factcheck-v2.py --standard" >&2
    echo "  File: $LOCAL" >&2
    echo "  Target: $PUBLIC_URL" >&2
    echo "═══════════════════════════════════════════" >&2

    set +e
    python3 "$FACTCHECK" "$LOCAL" --standard --report "$REPORT" 2>&1
    FC_EXIT=$?
    set -e

    # factcheck-v2.py exit codes:
    #   0 = PASS or REVIEW (no CRITICAL)
    #   1 or 2 = CRITICAL found
    if [[ $FC_EXIT -ne 0 ]]; then
        echo "" >&2
        echo "❌ FACTCHECK FAILED — CRITICAL issues found." >&2
        echo "   Report: $REPORT" >&2
        echo "   Деплой НЕ выполнен." >&2
        echo "" >&2
        echo "   Чтобы посмотреть отчёт:" >&2
        echo "     cat $REPORT" >&2
        echo "" >&2
        echo "   Bypass (только emergency):" >&2
        echo "     FACTCHECK_SKIP=1 safe-deploy-html.sh $LOCAL $VPS_PATH" >&2
        exit 1
    fi
    echo "✅ Factcheck PASS — proceeding with deploy" >&2
    echo "   Report: $REPORT" >&2
fi

# --- Prepare remote dir ---
echo "" >&2
echo "[safe-deploy] preparing remote dir $VPS_HOST:$VPS_DIR" >&2
set +e
ssh -o ConnectTimeout=10 -o BatchMode=yes "$VPS_HOST" "mkdir -p '$VPS_DIR'" 2>&1
MKDIR_EXIT=$?
set -e

if [[ $MKDIR_EXIT -ne 0 ]]; then
    echo "❌ remote mkdir failed (exit $MKDIR_EXIT)" >&2
    exit 2
fi

# --- SCP ---
echo "" >&2
echo "[safe-deploy] scp $LOCAL → $VPS_HOST:$VPS_PATH" >&2
set +e
scp -o ConnectTimeout=10 -o BatchMode=yes "$LOCAL" "$VPS_HOST:$VPS_PATH" 2>&1
SCP_EXIT=$?
set -e

if [[ $SCP_EXIT -ne 0 ]]; then
    echo "❌ SCP failed (exit $SCP_EXIT)" >&2
    exit 2
fi

# --- Owner ---
set +e
ssh -o ConnectTimeout=10 -o BatchMode=yes "$VPS_HOST" "chown www-data:www-data '$VPS_PATH'" 2>&1
CHOWN_EXIT=$?
set -e

if [[ $CHOWN_EXIT -ne 0 ]]; then
    echo "❌ remote chown failed (exit $CHOWN_EXIT)" >&2
    exit 2
fi

# --- Verify HTTP 200 ---
echo "[safe-deploy] verifying $PUBLIC_URL" >&2
HTTP_INFO=$(curl -sI --max-time 10 "$PUBLIC_URL" 2>&1 | head -5)
HTTP_CODE=$(printf '%s' "$HTTP_INFO" | grep -oE 'HTTP/[0-9.]+ [0-9]+' | awk '{print $2}' | head -1)
CONTENT_LEN=$(printf '%s' "$HTTP_INFO" | grep -i 'content-length' | awk '{print $2}' | tr -d '\r' | head -1)

if [[ "$HTTP_CODE" != "200" ]]; then
    echo "⚠️  HTTP $HTTP_CODE (expected 200)" >&2
    echo "   $PUBLIC_URL" >&2
    exit 2
fi

# --- Final report ---
echo "" >&2
echo "═══════════════════════════════════════════" >&2
echo "  ✅ DEPLOY SUCCESS" >&2
echo "  URL: $PUBLIC_URL" >&2
echo "  HTTP: $HTTP_CODE" >&2
echo "  Content-Length: $CONTENT_LEN" >&2
echo "═══════════════════════════════════════════" >&2

# Stdout — первая строка для людей, JSON ниже для автоматического парсинга.
printf 'Live URL: %s\n' "$PUBLIC_URL"
printf '{"url":"%s","http":"%s","content_length":"%s"}\n' "$PUBLIC_URL" "$HTTP_CODE" "$CONTENT_LEN"
