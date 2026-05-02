#!/usr/bin/env bash
# orm-pulse: установка LaunchAgent для cron-запусков
# macOS использует LaunchAgents (~/Library/LaunchAgents/) вместо crontab.
# Usage: ./install-cron.sh <client_slug> [hour] [minute]

set -euo pipefail

CLIENT="${1:?Usage: $0 <client_slug> [hour=9] [minute=0]}"
HOUR="${2:-9}"
MINUTE="${3:-0}"

LABEL="pro.artvision.orm-pulse.${CLIENT}"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
SCRIPT="$HOME/.claude/skills/orm-pulse/scripts/run.sh"
LOG_DIR="$HOME/.claude/logs"
mkdir -p "$LOG_DIR"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${SCRIPT}</string>
        <string>${CLIENT}</string>
        <string>full</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>${HOUR}</integer>
        <key>Minute</key>
        <integer>${MINUTE}</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>${LOG_DIR}/orm-pulse-${CLIENT}.log</string>
    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/orm-pulse-${CLIENT}.err.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin:/Library/Frameworks/Python.framework/Versions/3.14/bin</string>
        <key>HOME</key>
        <string>${HOME}</string>
    </dict>
</dict>
</plist>
EOF

# Перезагрузить если уже был
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"

echo "✅ LaunchAgent установлен: ${LABEL}"
echo "   Запуск ежедневно в ${HOUR}:${MINUTE}"
echo "   Логи: ${LOG_DIR}/orm-pulse-${CLIENT}.log"
echo "   Plist: ${PLIST}"
echo ""
echo "Проверить статус: launchctl list | grep orm-pulse"
echo "Запустить вручную: launchctl start ${LABEL}"
echo "Снять: launchctl unload ${PLIST}"
