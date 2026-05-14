#!/bin/bash
# eco-reminder-1800.sh — one-shot reminder для сессии ECO 04.05.2026 18:00 МСК
# Самоудаляется после первого запуска (plist + script).
set -euo pipefail

PLIST="$HOME/Library/LaunchAgents/pro.artvision.eco-reminder-1800.plist"
SCRIPT="$HOME/.claude/scripts/eco-reminder-1800.sh"

MSG="🔔 18:00 — выполнение задач очереди.

Asana: https://app.asana.com/1/860693669973770/project/1212305892582815/task/1214481285140598

19 pending в TaskList, top high:
• #2 HH scope-extension app #20952 (5 мин dev.hh.ru/admin)
• #4 HH-Recruiter бот (blocked-by #2)
• #8 @luxmarket_bot подписки
• #13 Roman Mebel пингануть
• #16 Бароян .docx отправка
• #19 Flow Spec-detector (in_progress)

Recap: ~/artvision-data/sync/recaps/9cb4a154-3712-422b-bc18-17d6d5bd91fe.md"

"$HOME/.claude/scripts/tg-send.sh" anton "$MSG" || true

# Self-cleanup (через 5 сек чтобы launchd успел захватить exit)
(sleep 5 && launchctl unload "$PLIST" 2>/dev/null && rm -f "$PLIST" "$SCRIPT") &
exit 0
