#!/bin/bash
# PostToolUse (Edit/Write): определяет КАКОЙ скилл нужен по контексту изменения
# Не запускает сам — выдаёт рекомендацию Claude, который вызовет Skill tool

FILE_PATH="${CLAUDE_FILE_PATH:-$1}"

if [ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ]; then
  exit 0
fi

# === Контекст: что за файл? ===
IS_BOT=false
IS_HTML=false
IS_PRODUCT=false

echo "$FILE_PATH" | grep -q "tg-bot\|survey-bot\|bot\.py\|handlers\|fsm\|middleware" && IS_BOT=true
echo "$FILE_PATH" | grep -q "\.html$" && IS_HTML=true
echo "$FILE_PATH" | grep -q "products/" && IS_PRODUCT=true

EXT="${FILE_PATH##*.}"

# === Счётчик изменений по типу (за сессию) ===
SESSION_DIR="/tmp/claude_skill_triggers"
mkdir -p "$SESSION_DIR"

# Трекаем изменённые файлы
echo "$FILE_PATH" >> "$SESSION_DIR/changed_files.log"
TOTAL_CHANGES=$(wc -l < "$SESSION_DIR/changed_files.log" 2>/dev/null | tr -d ' ')
BOT_CHANGES=$(grep -c "tg-bot\|bot\.py\|handlers\|fsm" "$SESSION_DIR/changed_files.log" 2>/dev/null || echo "0")
CODE_CHANGES=$(grep -c "\.\(py\|js\|ts\)$" "$SESSION_DIR/changed_files.log" 2>/dev/null || echo "0")

TRIGGER=""

# === Триггеры по порогам ===

# Бот: 3+ файлов бота изменено → bot-audit
if [ "$BOT_CHANGES" -ge 3 ] && [ ! -f "$SESSION_DIR/triggered_bot_audit" ]; then
  TRIGGER="🤖 [SKILL-TRIGGER: /bot-audit] 3+ файлов бота изменено ($BOT_CHANGES). Запусти полный аудит бота."
  touch "$SESSION_DIR/triggered_bot_audit"
fi

# Код: 5+ кодовых файлов → code-review
if [ "$CODE_CHANGES" -ge 5 ] && [ ! -f "$SESSION_DIR/triggered_code_review" ]; then
  TRIGGER="📝 [SKILL-TRIGGER: /code-review] 5+ кодовых файлов изменено ($CODE_CHANGES). Пора code review."
  touch "$SESSION_DIR/triggered_code_review"
fi

# Код: 10+ кодовых файлов → code-audit (глубокий)
if [ "$CODE_CHANGES" -ge 10 ] && [ ! -f "$SESSION_DIR/triggered_code_audit" ]; then
  TRIGGER="🔍 [SKILL-TRIGGER: /code-audit] 10+ файлов ($CODE_CHANGES). Нужен полный аудит: security + quality + architecture."
  touch "$SESSION_DIR/triggered_code_audit"
fi

# Любые 15+ изменений → verification-loop
if [ "$TOTAL_CHANGES" -ge 15 ] && [ ! -f "$SESSION_DIR/triggered_verification" ]; then
  TRIGGER="✅ [SKILL-TRIGGER: /verification-loop] 15+ изменений в сессии. Обязательная верификация перед завершением."
  touch "$SESSION_DIR/triggered_verification"
fi

if [ -n "$TRIGGER" ]; then
  echo "$TRIGGER"
fi

exit 0
