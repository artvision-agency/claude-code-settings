#!/usr/bin/env bash
# start-time-context.sh — SessionStart hook.
# Инжектит в additionalContext: текущее время + день недели + классификация
# (утро/день/вечер/ночь, будни/выходной), чтобы Claude корректно реагировал
# на «спать», «утро», «обед», «13:15», «вечер пятницы» и т.п.
#
# Прецедент: 2026-05-04 — Антон попросил "сделай чтобы обновлять статус времени
# у себя в голове прии каждом налчаее сесс если ты не знаешь что день что ночь".
# По умолчанию Claude видит только currentDate (без часа), не различает день/ночь.
set -uo pipefail

H=$(date +%H)
HUMAN=$(date '+%H:%M %Z, %A %d.%m.%Y')
DOW=$(date +%u)  # 1=Mon ... 7=Sun

if   [ "$H" -ge 5 ]  && [ "$H" -lt 12 ]; then PART="утро (5-12)"
elif [ "$H" -ge 12 ] && [ "$H" -lt 17 ]; then PART="день (12-17)"
elif [ "$H" -ge 17 ] && [ "$H" -lt 22 ]; then PART="вечер (17-22)"
else                                            PART="ночь (22-5)"
fi

if [ "$DOW" -ge 6 ]; then DAYTYPE="выходной"; else DAYTYPE="будни"; fi

CTX="🕐 Сейчас: ${HUMAN} — ${PART}, ${DAYTYPE}. Используй для решений 'спать/работать/ждать встречи' и интерпретации 'утром', 'вечером', 'к обеду'."

jq -nc --arg ctx "$CTX" '{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$ctx}}'
