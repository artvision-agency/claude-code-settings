#!/bin/bash
# UserPromptSubmit hook — авто-поиск файлов клиента БЕЗ трат токенов LLM.
# Детектит запрос «найди файлы / где КП / последние файлы клиента X»,
# запускает Spotlight (mdfind) и инжектит готовые пути в контекст.
# inject-only (никогда не блокирует). Bypass: FIND_FILES_OFF=1
set -u
[[ "${FIND_FILES_OFF:-0}" == "1" ]] && exit 0

python3 "$HOME/.claude/hooks/prompt-find-client-files.py" 2>/dev/null || exit 0
