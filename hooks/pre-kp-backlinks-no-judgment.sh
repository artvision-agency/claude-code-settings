#!/usr/bin/env bash
# Не оценивать качество ссылок (плохо/спам/PBN) без сверки с позициями конкурента
set -uo pipefail
[[ "${BACKLINKS_JUDGMENT_OK:-0}" == "1" ]] && exit 0
INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
[[ ! "$TOOL" =~ ^(Write|Edit)$ ]] && exit 0
[[ ! "$FILE" =~ presales/.+/kp/.+\.html$ ]] && exit 0
CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // .tool_input.new_string // empty' 2>/dev/null)
[[ -z "$CONTENT" ]] && exit 0
# Если в #backlinks есть оценочные слова "плохо/спам/арендный/мусорный" про конкурента
if echo "$CONTENT" | grep -qiE 'спам.?сигнал|арендн.{0,15}сигнал|мусорн.{0,15}ссылк|низкокачествен'; then
    if ! echo "$CONTENT" | grep -qiE 'топ-?[1-9]|занимает.*позиц|снимок позиций.*[0-9]{2}'; then
        echo "⚠️  WARN:  WARN: pre-kp-backlinks-no-judgment: оценка качества ссылок без позиций конкурента. Дешёвые ссылки могут работать (см. shkolamm ТОП-1). Bypass: BACKLINKS_JUDGMENT_OK=1" >&2
        exit 0  # warning-only mode (was blocking)
    fi
fi
exit 0
