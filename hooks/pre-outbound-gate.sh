#!/bin/bash
# PreToolUse(Bash): блокирует отправку наружу клиенту без ACK Антона.
# Триггеры: curl к клиентским доменам, scp на клиентские VPS, mailx/sendmail,
#           telegram bot send_message к клиентским chat_id.
# ACK: файл /tmp/.claude_outbound_ack (создаётся Антоном) или ключевое слово --ack-anton в команде.

INPUT=$(cat)
CMD=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null)

[ -z "$CMD" ] && exit 0

# ACK-байпас
if echo "$CMD" | grep -q -- '--ack-anton'; then
  exit 0
fi
if [ -f /tmp/.claude_outbound_ack ]; then
  # one-shot: потребить файл
  rm -f /tmp/.claude_outbound_ack
  exit 0
fi

# Паттерны исходящих действий к клиентам
OUTBOUND=0
REASON=""

# scp/rsync на клиентские VPS (кроме наших)
if echo "$CMD" | grep -qE '\b(scp|rsync)\b'; then
  if echo "$CMD" | grep -qvE '80\.90\.181\.152|147\.45\.232\.226|localhost|127\.0\.0\.1'; then
    if echo "$CMD" | grep -qE '@[a-zA-Z0-9.-]+:'; then
      OUTBOUND=1
      REASON="scp/rsync к внешнему хосту"
    fi
  fi
fi

# Email отправка
if echo "$CMD" | grep -qE '\b(mail|mailx|sendmail|msmtp)\b.*@'; then
  OUTBOUND=1
  REASON="email отправка"
fi

# TG bot sendMessage / WebFetch POST к api.telegram.org с клиентским chat_id
# (группа команды — не блокируем)
TEAM_CHAT_IDS="-1001234567890"  # заглушка — реальные team chat_id можно добавить
if echo "$CMD" | grep -qE 'api\.telegram\.org/bot[^/]+/sendMessage'; then
  # Если не указан team chat — считаем outbound
  OUTBOUND=1
  REASON="Telegram sendMessage"
fi

# gh pr create / gh issue create к публичным репо клиента — не трогаем пока

if [ "$OUTBOUND" -eq 1 ]; then
  cat <<EOF
🛑 OUTBOUND-GATE: обнаружена попытка отправки наружу клиенту.
Причина: $REASON
Команда: $(echo "$CMD" | head -c 200)

Перед отправкой:
  1. Покажи Антону контент (deploy на ревью-URL ОК).
  2. Получи ACK → одно из:
     • touch /tmp/.claude_outbound_ack  (one-shot байпас)
     • добавь --ack-anton в команду
EOF
  exit 2
fi

exit 0
