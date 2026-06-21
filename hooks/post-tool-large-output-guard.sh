#!/usr/bin/env bash
# post-tool-large-output-guard.sh
# PostToolUse(Bash): warn если tool-результат >100KB осел в контексте.
# Правило: large-tool-output-to-file.md (token-diet 2026-06-21, Антон).
# Детализацию НЕ терять — полный ответ в файл по каналам, в контекст индекс+сводку.
# Warn-only (не блокирует — пост-фактум). Bypass: LARGE_OUTPUT_OK=1
set -uo pipefail

[ "${LARGE_OUTPUT_OK:-0}" = "1" ] && exit 0

input=$(cat 2>/dev/null || true)
size=${#input}
THRESH=${LARGE_OUTPUT_THRESHOLD:-100000}   # ~100KB ≈ ~25K токенов

if [ "$size" -gt "$THRESH" ]; then
  kb=$((size / 1024))
  msg="[large-output] tool-результат ~${kb}KB попал в контекст (порог $((THRESH/1024))KB). Правило large-tool-output-to-file: сохрани ПОЛНЫЙ ответ в файл (по каналам/источникам, 100% детализации), в контекст верни только индекс+сводку, детали доставай из файла точечно (jq/grep/awk). Детализацию НЕ терять — данные перемещаются в файл, не сокращаются. Это съедает токены каждый turn пока висит в контексте."
  # экранируем кавычки/переводы для JSON
  esc=$(printf '%s' "$msg" | sed 's/\\/\\\\/g; s/"/\\"/g')
  printf '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"%s"}}\n' "$esc"
fi
exit 0
