#!/bin/sh
# Одноразовое напоминание о встрече с Ярмолинским 12.06 10:45.
# Срабатывает только в день встречи, потом выгружает себя.
TARGET="2026-06-12"
TODAY=$(date '+%Y-%m-%d')
[ "$TODAY" != "$TARGET" ] && exit 0
NOTIFY_FORCE=1 "$HOME/.claude/scripts/tg-send.sh" anton "⏰ Напоминание: сегодня в 10:45 встреча с Ярмолинским (USmile) на метро Московская. (Asana 1215636253760181)"
# выгрузить себя после срабатывания
launchctl unload "$HOME/Library/LaunchAgents/pro.artvision.remind-yarmolinsky.plist" 2>/dev/null
rm -f "$HOME/Library/LaunchAgents/pro.artvision.remind-yarmolinsky.plist" "$HOME/.claude/scripts/remind-yarmolinsky.sh"
