#!/bin/bash
# PostToolUse(Bash): после scp КП на наш VPS — авто-strict L2 в фоне.
# Триггер: команда содержит scp + /var/www/artvision/kp/<slug>/ + root@80.90.181.152
# Действие: spawn subagent strict-factchecker через Claude SDK headless (--bare)
# Результат: запись в /tmp/auto-strict/{slug}-{date}.md + если BLOCK → TG alert
#
# Установлено: 2026-05-05 после 3 итераций strict L2 на 14 wave-2 КП AdvertMed
# (всего ~$15 в токенах, поймано 8 BLOCK + 6 CONDITIONAL — прибыль очевидна).

INPUT=$(cat)
CMD=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null)

[ -z "$CMD" ] && exit 0

# Триггер только на scp кп-страниц на наш VPS
echo "$CMD" | grep -qE '\bscp\b.*root@80\.90\.181\.152.*/var/www/artvision/kp/' || exit 0

# Извлекаем slug из пути scp
SLUG=$(echo "$CMD" | grep -oE '/var/www/artvision/kp/[a-z0-9-]+' | head -1 | sed 's|/var/www/artvision/kp/||')
[ -z "$SLUG" ] && exit 0

# Skip если этот slug уже проверялся в последние 30 минут (избегаем рекурсии при v2/v3 итерациях)
LOCK_FILE="/tmp/auto-strict-lock-${SLUG}"
if [ -f "$LOCK_FILE" ]; then
  AGE=$(($(date +%s) - $(stat -f%m "$LOCK_FILE" 2>/dev/null || echo 0)))
  if [ "$AGE" -lt 1800 ]; then
    exit 0  # silent skip
  fi
fi
touch "$LOCK_FILE"

URL="https://artvision.pro/kp/${SLUG}/"
LOG_DIR="$HOME/artvision-data/clients/_factcheck-history"
mkdir -p "$LOG_DIR"
DATE=$(date +%Y-%m-%d_%H%M)
REPORT="$LOG_DIR/${SLUG}-${DATE}.md"

# Лог о запуске (Claude видит это в stderr хука)
echo "[post-kp-deploy-factcheck] Auto-strict L2 spawned for $SLUG → $URL" >&2
echo "[post-kp-deploy-factcheck] Report → $REPORT" >&2

# Spawn в фоне через nohup + claude --bare (headless SDK)
# Промпт: лаконичный, ≤500 слов, verdict BLOCK/CONDITIONAL/PASS
nohup bash -c "
PROMPT='Strict factcheck Layer 2 на $URL. Презумпция лжи на каждое число. Проверь через WebFetch: phone, address, year_founded, branches соответствуют сайту клиники. Wordstat-блок релевантен нише. ТОП-3 конкурентов реально в выдаче региона. Числа имеют источник + дату. Verdict: BLOCK / CONDITIONAL / PASS + список конкретных проблем. Финал ≤ 500 слов.'
echo \"# Auto strict-factcheck — \$(date +%Y-%m-%dT%H:%M:%S%z)\" > '$REPORT'
echo '' >> '$REPORT'
echo '**URL:** $URL' >> '$REPORT'
echo '**Slug:** $SLUG' >> '$REPORT'
echo '' >> '$REPORT'
claude --bare -p \"\$PROMPT\" >> '$REPORT' 2>&1 || echo '[FAIL] claude --bare exited \$?' >> '$REPORT'
# Если в отчёте есть BLOCK — TG alert
if grep -qiE '^[*]*[Vv]erdict[*: ]+(BLOCK|❌)' '$REPORT' || grep -qE '\\bBLOCK\\b' '$REPORT'; then
  python3 -c \"
import sys, json, urllib.request, urllib.parse
try:
  with open('$HOME/artvision-data/tokens.json') as f:
    t = json.load(f)
  bot = t.get('telegram_bots',{}).get('avportal_bot',{}).get('token','')
  chat = t.get('telegram_chats',{}).get('antonk_dm','')
  if bot and chat:
    msg = '🚨 Auto strict-L2 BLOCK: $URL\\\\nReport: $REPORT'
    url = f'https://api.telegram.org/bot{bot}/sendMessage'
    data = urllib.parse.urlencode({'chat_id': chat, 'text': msg}).encode()
    urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=8)
except Exception as e:
  print(f'tg-alert-fail: {e}', file=sys.stderr)
\"
fi
" > /dev/null 2>&1 &

exit 0
