#!/bin/bash
# UserPromptSubmit hook: напоминание о /compact focus при ~40%+ контекста
# Правило bulletproof 40% Rule: качество деградирует после 40%
# Источник: ~/.claude/rules/bulletproof-patterns.md + session-commands.md

set -uo pipefail

INPUT="$(cat 2>/dev/null || echo '{}')"
TRANSCRIPT=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('transcript_path',''))" 2>/dev/null || echo "")

[ -z "$TRANSCRIPT" ] && exit 0
[ ! -f "$TRANSCRIPT" ] && exit 0

SID=$(basename "$TRANSCRIPT" .jsonl)

# РЕАЛЬНЫЙ процент контекста.
# Источник правды #1: statusline пишет context_window.used_percentage в /tmp/claude-ctx-<SID>.pct
#   (то же число, что видит пользователь внизу панели).
# Fallback #2: считаем реальные токены контекста из usage последнего сообщения транскрипта
#   (input + cache_read + cache_creation) ÷ окно модели. НЕ по размеру файла —
#   .jsonl это append-only лог всей истории, а не живое окно (прецедент: файл 1.08МБ ≈ 49% реально).
PCT=$(cat "/tmp/claude-ctx-${SID}.pct" 2>/dev/null)

if ! [[ "$PCT" =~ ^[0-9]+$ ]]; then
  PCT=$(tac "$TRANSCRIPT" 2>/dev/null | python3 -c "
import sys, json
WINDOW = 1000000  # Opus 4.8 [1m] / current default; даёт under-warn если окно меньше (безопаснее over-warn)
for line in sys.stdin:
    try: d = json.loads(line)
    except: continue
    u = (d.get('message') or {}).get('usage')
    if u:
        tot = u.get('input_tokens',0) + u.get('cache_read_input_tokens',0) + u.get('cache_creation_input_tokens',0)
        print(int(tot * 100 / WINDOW)); break
else:
    print(0)
" 2>/dev/null)
fi

[[ "$PCT" =~ ^[0-9]+$ ]] || PCT=0

THRESHOLD_40=40
THRESHOLD_80=80

# Dedupe per session — не спамим каждый turn
FLAG_40="/tmp/ctx40-warned-${SID}.flag"
FLAG_80="/tmp/ctx80-warned-${SID}.flag"

if [ "$PCT" -gt "$THRESHOLD_80" ] && [ ! -f "$FLAG_80" ]; then
  touch "$FLAG_80"
  cat <<EOF
═══════════════════════════════════════════
🚨 CONTEXT ~${PCT}% — КРИТИЧНО (>80%)
═══════════════════════════════════════════
/compact на 80% теряет критичное. Лучше:
  1. handover skill → /clear
  2. НЕ /compact — сразу /clear
  3. Resume через git handover.md
═══════════════════════════════════════════
EOF
  exit 0
fi

if [ "$PCT" -gt "$THRESHOLD_40" ] && [ ! -f "$FLAG_40" ]; then
  touch "$FLAG_40"
  cat <<EOF
═══════════════════════════════════════════
⚠️  CONTEXT ~${PCT}% — ПРОЙДЕН ПОРОГ 40% ("Dumb Zone")
═══════════════════════════════════════════
Правило bulletproof: качество деградирует после 40%.
Рекомендую перед следующей крупной задачей:
  /compact focus on <текущая задача>
  или handover skill → /clear
Не откладывать до 80% — там /compact уже теряет важное.
═══════════════════════════════════════════
EOF
fi

exit 0
