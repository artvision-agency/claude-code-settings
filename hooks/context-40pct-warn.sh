#!/bin/bash
# UserPromptSubmit hook: напоминание о /compact focus при ~40%+ контекста
# Правило bulletproof 40% Rule: качество деградирует после 40%
# Источник: ~/.claude/rules/bulletproof-patterns.md + session-commands.md

set -uo pipefail

INPUT="$(cat 2>/dev/null || echo '{}')"
TRANSCRIPT=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('transcript_path',''))" 2>/dev/null || echo "")

[ -z "$TRANSCRIPT" ] && exit 0
[ ! -f "$TRANSCRIPT" ] && exit 0

SIZE=$(stat -f%z "$TRANSCRIPT" 2>/dev/null || stat -c%s "$TRANSCRIPT" 2>/dev/null || echo 0)

# Rough proxy: transcript ~1MB ≈ полный контекст 200K токенов
# 40% ≈ 400KB, 50% ≈ 500KB, 80% ≈ 800KB
THRESHOLD_40=400000
THRESHOLD_80=800000

# Dedupe per session — не спамим каждый turn
SID=$(basename "$TRANSCRIPT" .jsonl)
FLAG_40="/tmp/ctx40-warned-${SID}.flag"
FLAG_80="/tmp/ctx80-warned-${SID}.flag"

if [ "$SIZE" -gt "$THRESHOLD_80" ] && [ ! -f "$FLAG_80" ]; then
  touch "$FLAG_80"
  PCT=$((SIZE * 100 / 1000000))
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

if [ "$SIZE" -gt "$THRESHOLD_40" ] && [ ! -f "$FLAG_40" ]; then
  touch "$FLAG_40"
  PCT=$((SIZE * 100 / 1000000))
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
