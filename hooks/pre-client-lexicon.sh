#!/bin/bash
# PreToolUse(Edit/Write): lexicon-lint для файлов в clients/, presale/, kp/
# CRITICAL → блокирует (exit 2), WARN → предупреждает (exit 0)

INPUT=$(cat)

TOOL=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null)
FILE_PATH=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null)

[ -z "$FILE_PATH" ] && exit 0

# Только клиентские/КП/presale файлы
case "$FILE_PATH" in
  */clients/*|*/presale/*|*/kp/*) ;;
  *) exit 0 ;;
esac

# Bypass для внутренних служебных файлов клиента (CLAUDE.md, README.md в корне clients/<name>/)
# Эти файлы — для агента, не для клиента. Лексикон-правила «AI запрещено в публичных» к ним не применяются.
case "$FILE_PATH" in
  */clients/*/CLAUDE.md|*/clients/*/README.md|*/clients/*/context-log.md|*/clients/*/lexicon.yaml)
    exit 0 ;;
esac

# Явный bypass через env (для исключительных случаев — например, .ai-методология в названии скрипта)
if [ "${LEXICON_INTERNAL_OK:-0}" = "1" ]; then
  echo "⚠️  LEXICON_INTERNAL_OK=1 — пропуск проверки для $FILE_PATH" >&2
  exit 0
fi

# Только текстовые форматы
case "$FILE_PATH" in
  *.html|*.md|*.txt|*.yaml|*.yml|*.json) ;;
  *) exit 0 ;;
esac

# Извлекаем новое содержимое (Write.content или Edit.new_string)
CONTENT=$(echo "$INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin).get('tool_input', {})
print(d.get('content') or d.get('new_string') or '', end='')
" 2>/dev/null)

[ -z "$CONTENT" ] && exit 0

# Запускаем линтер
OUT=$(echo "$CONTENT" | python3 ~/.claude/scripts/lexicon-lint.py --content - --path "$FILE_PATH" 2>&1)
CODE=$?

if [ -n "$OUT" ]; then
  echo "$OUT"
fi

# exit 2 → блок с сообщением Claude
exit $CODE
