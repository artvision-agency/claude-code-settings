#!/usr/bin/env bash
# pre-kp-brand-extract-check.sh — PreToolUse hook
# Блокирует Write/Edit в `presales/<slug>/kp/*.html` если в сессии НЕ было
# WebFetch / curl на домен клиента (slug) — это означает что дизайн-система
# не извлекалась перед созданием КП.
#
# Bypass: BRAND_EXTRACT_OK=1
#
# Прецедент: 11.05.2026 cosmetology-kursy КП получил наследованный
# CAMEO стиль spb-kursy потому что rebuild упал и я не извлёк палитру.
# Antоn: «ПОЧЕМУ ТЫ САМ НЕ ПОНИМАЕШЬ ЧТО ТАК НАДО?»

set -uo pipefail

[[ "${BRAND_EXTRACT_OK:-0}" == "1" ]] && exit 0

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)

[[ ! "$TOOL_NAME" =~ ^(Write|Edit)$ ]] && exit 0
[[ -z "$SESSION_ID" ]] && exit 0

FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
[[ -z "$FILE" ]] && exit 0

# Только КП файлы клиентов
if ! echo "$FILE" | grep -qE 'presales/([^/]+)/kp/.*\.html$'; then
    exit 0
fi

SLUG=$(echo "$FILE" | sed -E 's|.*presales/([^/]+)/kp/.*|\1|')
[[ -z "$SLUG" ]] && exit 0

# Проверить config.yaml клиента — есть ли domain
CONFIG="/Users/antonk/artvision-data/clients/$SLUG/config.yaml"
DOMAIN=""
[[ -f "$CONFIG" ]] && DOMAIN=$(grep -E '^(domain|site|url):' "$CONFIG" 2>/dev/null | head -1 | sed -E 's|.*: *||; s|https?://||; s|/$||' | tr -d '"' || true)

# Если не нашли — пробуем guess по slug
[[ -z "$DOMAIN" ]] && DOMAIN="${SLUG}.ru"

TRANSCRIPT="$HOME/.claude/projects/-Users-antonk/${SESSION_ID}.jsonl"
[[ ! -f "$TRANSCRIPT" ]] && exit 0

# Ищем WebFetch / curl / urllib.request на домен в сессии
if grep -qE "(WebFetch|curl[^|]*|urllib\.request)[^\"']*\"?https?://$DOMAIN" "$TRANSCRIPT" 2>/dev/null; then
    exit 0  # Дизайн-система извлекалась — ОК
fi

# Также OK если файл уже существует (Edit к существующему КП — не первая генерация)
if [[ "$TOOL_NAME" == "Edit" ]] && [[ -f "$FILE" ]] && [[ $(wc -c <"$FILE") -gt 50000 ]]; then
    exit 0
fi

cat <<EOF
⛔ pre-kp-brand-extract-check: ЗАБЛОКИРОВАНО

Создаёшь КП для клиента <$SLUG> (домен: $DOMAIN), но в сессии нет
WebFetch / curl на этот домен — значит дизайн-система НЕ извлечена.

ПОЧЕМУ ВАЖНО: КП с дефолтной палитрой шаблона = ловушка.
Прецедент 11.05.2026: cosmetology-kursy получил navy+gold от spb-kursy
вместо лавандовой #9D8FD8 (своей). Антон поймал руками.

ДЕЙСТВИЕ:
  curl -sL https://$DOMAIN | grep -oE '#[0-9a-fA-F]{6}' | sort -u
  curl -sL https://$DOMAIN | grep -oE 'font-family:[^;]+' | sort -u
  # ИЛИ WebFetch https://$DOMAIN

После — повтори Write/Edit, хук разблокируется.

Bypass: BRAND_EXTRACT_OK=1 (если правда не нужно — например, КП на черновик)
EOF
exit 2
