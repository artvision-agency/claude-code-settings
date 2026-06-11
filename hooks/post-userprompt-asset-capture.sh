#!/bin/bash
# UserPromptSubmit hook: детектит URL медиа/доступы в prompt пользователя
# и инжектит system-reminder с императивом WRITE-FIRST в clients/<slug>/assets/.
# См. ~/.claude/rules/asset-capture-no-loss.md

set -euo pipefail

# Читаем stdin JSON
INPUT=$(cat)
PROMPT=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('prompt',''))" 2>/dev/null || echo "")
CWD=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('cwd','/Users/antonk'))" 2>/dev/null || echo "/Users/antonk")
SESSION_ID=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('session_id','unknown'))" 2>/dev/null || echo "unknown")

[ -z "$PROMPT" ] && exit 0

# === ДЕТЕКТОР АКТИВОВ ===
# Паттерны URL медиа/галерей/доступов
ASSET_PATTERNS='(https?://[^[:space:]"'\''<>]*\.(jpg|jpeg|png|webp|gif|svg|mp4|mov|webm|pdf|psd|ai|fig|sketch)|https?://[^[:space:]"'\''<>]*(wfolio|drive\.google\.com/file|dropbox\.com|disk\.yandex|cloud\.mail\.ru|behance\.net|figma\.com/file|tildacdn|i\.wfolio|wetransfer|sendspace)|https?://[^[:space:]"'\''<>]*(\.tilda|/upload/|/uploads/|/media/|/images/|/photos/))'

# Паттерны доступов (логин/пароль/API)
ACCESS_PATTERNS='(login:|логин:|пароль:|password:|api[_-]?key|secret|token:|access[_-]?key|client[_-]?secret)'

# Паттерны реквизитов
REQUISITES_PATTERNS='(ИНН[[:space:]]?[0-9]{10,12}|ОГРН[[:space:]]?[0-9]{13,15}|КПП[[:space:]]?[0-9]{9}|р/с[[:space:]]?[0-9]{20})'

HAS_ASSET=$(echo "$PROMPT" | grep -iE "$ASSET_PATTERNS" 2>/dev/null | head -3 || echo "")
HAS_ACCESS=$(echo "$PROMPT" | grep -iE "$ACCESS_PATTERNS" 2>/dev/null | head -3 || echo "")
HAS_REQ=$(echo "$PROMPT" | grep -iE "$REQUISITES_PATTERNS" 2>/dev/null | head -3 || echo "")

# Если ничего не найдено — exit
if [ -z "$HAS_ASSET" ] && [ -z "$HAS_ACCESS" ] && [ -z "$HAS_REQ" ]; then
  exit 0
fi

# === ОПРЕДЕЛИТЬ SERVICE NAME (ALLCAPS в prompt — это глобальный сервис, не клиент) ===
# Прецедент 2026-05-20 (session 87d9412c): пароль TOPVISOR ошибочно привязался к
# kamey (последний клиент сессии). Сначала проверяем — может это сервис, а не клиент.
SERVICE_NAME=""
KNOWN_SERVICES="TOPVISOR|YANDEX|GOOGLE|GITHUB|DIRECT|METRIKA|WEBMASTER|WORDSTAT|SBIS|SABY|TILDA|TIMEWEB|HOSTLAND|VERCEL|SUPABASE|OPENROUTER|GROQ|DEEPSEEK|HUGGINGFACE|YOUTUBE|TELEGRAM|SLACK|ASANA|KWORK|ZENNO|QCOMMENT|TURBOTEXT|VLPCO|REGRU|VPS|CLOUDFLARE|MAILGUN|TWILIO|STRIPE|NPM"
# Ищем ALLCAPS service-name отдельно (с границами слов)
SERVICE_NAME=$(echo "$PROMPT" | grep -oE "\\b($KNOWN_SERVICES)\\b" | head -1 || echo "")

# === ОПРЕДЕЛИТЬ CLIENT SLUG (если это НЕ сервис) ===
CLIENT_SLUG=""
if [ -z "$SERVICE_NAME" ]; then
  # 1. Из cwd: /Users/antonk/artvision-data/clients/<slug>/...
  if [[ "$CWD" =~ /clients/([^/]+) ]]; then
    CLIENT_SLUG="${BASH_REMATCH[1]}"
  fi

  # 2. Из последнего упоминания в session jsonl (если cwd не дал slug)
  if [ -z "$CLIENT_SLUG" ]; then
    SESSION_FILE="/Users/antonk/.claude/projects/-Users-antonk/${SESSION_ID}.jsonl"
    if [ -f "$SESSION_FILE" ]; then
      # Ищем последние 50 строк, грепаем clients/<slug>
      CLIENT_SLUG=$(tail -50 "$SESSION_FILE" 2>/dev/null | grep -oE 'clients/[a-z0-9_-]+' | tail -1 | sed 's|clients/||' || echo "")
    fi
  fi
fi

# === ВЕТКА: сервисный пароль/credential → tokens.json ===
if [ -n "$SERVICE_NAME" ] && [ -n "$HAS_ACCESS" ]; then
  SERVICE_LOWER=$(echo "$SERVICE_NAME" | tr '[:upper:]' '[:lower:]')
  cat <<EOF
[ASSET-CAPTURE SERVICE CREDENTIAL] Антон передал доступ к сервису \`${SERVICE_NAME}\` (не клиент).

ДЕЙСТВИЕ (WRITE-FIRST):
1. ПЕРВЫМ tool call — Edit \`~/artvision-data/tokens.json\` секция \`${SERVICE_LOWER}\`
   - Добавить login + password + дату + кто передал + назначение
   - Шаблон полей: см. существующие секции (kwork, zenno_club, vps)
2. tokens.json в .gitignore — не пушится, но синхронизируется через ~/.claude/scripts/sync-memory.sh
3. НЕ записывать в clients/<slug>/access.md — это глобальный сервис, не клиентский

Прецедент: session 87d9412c — пароль TOPVISOR ошибочно привязался к kamey.
EOF
  exit 0
fi

# Если slug не определён — инжектим generic warning
if [ -z "$CLIENT_SLUG" ]; then
  TYPES=""
  [ -n "$HAS_ASSET" ] && TYPES="${TYPES}URL медиа, "
  [ -n "$HAS_ACCESS" ] && TYPES="${TYPES}доступы, "
  [ -n "$HAS_REQ" ] && TYPES="${TYPES}реквизиты, "
  TYPES="${TYPES%, }"

  cat <<EOF
[ASSET-CAPTURE WARNING] В prompt детектирован: ${TYPES}.
Client slug не определён (cwd не в clients/<slug>/, в сессии нет упоминаний).

ДЕЙСТВИЕ: если этот актив относится к клиенту — спроси «к какому клиенту?» И ПЕРВЫМ tool call сделай Write в \`clients/<slug>/assets/external-urls.yaml\` ПЕРЕД ответом в чат.
Правило: ~/.claude/rules/asset-capture-no-loss.md (WRITE-FIRST).
EOF
  exit 0
fi

# === ЛОГ PENDING (для Stop-hook проверки) ===
PENDING_DIR="/Users/antonk/artvision-data/clients/${CLIENT_SLUG}/assets"
mkdir -p "$PENDING_DIR" 2>/dev/null || true
PENDING_FILE="${PENDING_DIR}/external-urls-pending.md"

{
  echo ""
  echo "## $(date '+%Y-%m-%d %H:%M:%S') session=$SESSION_ID"
  [ -n "$HAS_ASSET" ] && echo "**URL медиа:** $HAS_ASSET"
  [ -n "$HAS_ACCESS" ] && echo "**Доступ:** $(echo "$HAS_ACCESS" | head -c 100)..."
  [ -n "$HAS_REQ" ] && echo "**Реквизит:** $HAS_REQ"
  echo "Prompt excerpt: $(echo "$PROMPT" | head -c 200)..."
} >> "$PENDING_FILE" 2>/dev/null || true

# === ИНЖЕКТ В STDOUT (становится контекстом prompt) ===
TYPES=""
[ -n "$HAS_ASSET" ] && TYPES="${TYPES}URL медиа, "
[ -n "$HAS_ACCESS" ] && TYPES="${TYPES}доступы, "
[ -n "$HAS_REQ" ] && TYPES="${TYPES}реквизиты, "
TYPES="${TYPES%, }"

cat <<EOF
[ASSET-CAPTURE REQUIRED] Антон передал: ${TYPES} для клиента \`${CLIENT_SLUG}\`.

ДЕЙСТВИЕ (WRITE-FIRST правило, см. ~/.claude/rules/asset-capture-no-loss.md):
1. ПЕРВЫМ tool call сделай Write/Edit в \`clients/${CLIENT_SLUG}/assets/external-urls.yaml\` (для URL медиа) или \`access.md\` (для доступов) или \`config.yaml\` (для реквизитов)
2. ТОЛЬКО ПОТОМ отвечай в чат

Если файла нет — создай по шаблону из ~/.claude/templates/client-assets-external-urls.yaml
Pending-лог: $PENDING_FILE
EOF

exit 0
