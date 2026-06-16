#!/usr/bin/env bash
# start-tg-session-age.sh — SessionStart хук: warn если Telethon session expired.
#
# Прецедент 2026-05-20 (session 87d9412c): обе sessions были expired 12+ дней.
# Антон попросил "найди пароль в чате с андреем" — невозможно без активной session.
# Потеряли ~30 мин и токены на круги «попробуй telethon».
#
# Поведение: WARN в stdout (доп. контекст в стартовом меню), не блокирует.
#
# Bypass: TG_AGE_SKIP=1
set -euo pipefail

if [[ "${TG_AGE_SKIP:-0}" == "1" ]]; then
  exit 0
fi

SESSIONS=(
  "$HOME/artvision-data/.claude_temp_scripts/tg_userbot.session"
  "$HOME/artvision-data/telegram_session.session"
)

NOW=$(date +%s)
THRESHOLD_DAYS=7

# Маркер последней УСПЕШНОЙ telethon auth (touched скриптом tg-chat-export и др.)
AUTH_MARKER="$HOME/artvision-data/.claude_temp_scripts/.tg-auth-ok"

WARN_LINES=()

# Age check sessions
for SESSION in "${SESSIONS[@]}"; do
  if [[ ! -f "$SESSION" ]]; then
    continue
  fi
  MTIME=$(stat -f "%m" "$SESSION" 2>/dev/null || stat -c "%Y" "$SESSION" 2>/dev/null || echo 0)
  [[ "$MTIME" == "0" ]] && continue
  AGE_DAYS=$(( (NOW - MTIME) / 86400 ))
  if (( AGE_DAYS > THRESHOLD_DAYS )); then
    WARN_LINES+=("  ⚠️  $(basename "$SESSION") — mtime age ${AGE_DAYS}д (>$THRESHOLD_DAYS)")
  fi
done

# Auth marker check (file отдельный от session-файла)
if [[ -f "$AUTH_MARKER" ]]; then
  MTIME=$(stat -f "%m" "$AUTH_MARKER" 2>/dev/null || stat -c "%Y" "$AUTH_MARKER" 2>/dev/null || echo 0)
  AGE_DAYS=$(( (NOW - MTIME) / 86400 ))
  if (( AGE_DAYS > THRESHOLD_DAYS )); then
    WARN_LINES+=("  ⚠️  .tg-auth-ok — последний успешный auth был ${AGE_DAYS}д назад")
  fi
else
  # Маркера нет → ни разу не было успешной auth (или удалили) → предупредить
  WARN_LINES+=("  ⚠️  .tg-auth-ok маркер НЕ найден — telethon auth не подтверждалась")
fi

if (( ${#WARN_LINES[@]} == 0 )); then
  exit 0
fi

cat <<EOF
═══════════════════════════════════════════════════════════
  ⚠️  TELETHON SESSION EXPIRED (вероятно — не авторизована)
═══════════════════════════════════════════════════════════
${WARN_LINES[*]}

Re-auth требует ВВОДА КОДА из TG (Claude не может).
Если планируешь /tg-chat-export, поиск в чатах, мониторинг —
запусти прямо сейчас в терминале:

  cd ~/artvision-data && python3 -c "
  from telethon import TelegramClient; import json
  t = json.load(open('tokens.json'))['telegram']
  client = TelegramClient('.claude_temp_scripts/tg_userbot', int(t['api_id']), t['api_hash'])
  client.start()  # запросит phone+code
  print('OK', client.get_me().username)
  client.disconnect()
  "

Bypass: TG_AGE_SKIP=1
Прецедент: session 87d9412c, self-corrections.md #12
═══════════════════════════════════════════════════════════
EOF
exit 0
