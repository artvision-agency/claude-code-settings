#!/usr/bin/env bash
# Одноразовое напоминание: опубликовать 2 части шортса V1 в канал.
# Ставится launchd-задачей pro.artvision.remind-video-publish на 2026-06-13 12:00 MSK.
# После отправки САМ выгружает и удаляет свою плашку (чтобы не повторялось ежегодно).
set -uo pipefail

BOT="$(python3 -c 'import json,os;t=json.load(open(os.path.expanduser("~/artvision-data/tokens.json")))["telegram"]["portal_bot"];print(t if isinstance(t,str) else t.get("token",""))')"
CHAT="161261562"
MSG="🔔 НАПОМИНАНИЕ (12:00) — публикация шортса V1 (CTR по позициям) в канал @artvisionagency

Решение: 2 ЧАСТИ. Перед публикацией (в сессии Claude — скажи «го видео»):
1. Перерезать на 2 части по ЧИСТОЙ границе фразы (прошлый рез 21.3с был в середине предложения — найти конец предложения по субтитрам/транскрипту).
2. Звук 48кГц — уже исправлено.
3. Прогнать scripts/tg_prepublish_check.sh каждую часть → PASS.
4. Показать тебе в личку на модерацию → твой ОК.
5. Только потом — публикация ботом в канал @artvisionagency + подписи.

Stories — позже, отдельно.
Файлы: ~/artvision-data/personal/social_clips/2026-05-12-research-video/output/"

curl -s -X POST "https://api.telegram.org/bot${BOT}/sendMessage" \
  --data-urlencode "chat_id=${CHAT}" \
  --data-urlencode "text=${MSG}" >/dev/null 2>&1

# самоликвидация (одноразовость)
PLIST="$HOME/Library/LaunchAgents/pro.artvision.remind-video-publish.plist"
launchctl unload "$PLIST" 2>/dev/null || true
rm -f "$PLIST" 2>/dev/null || true
exit 0
