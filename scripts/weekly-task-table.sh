#!/bin/bash
set -euo pipefail

# Еженедельная таблица задач — генерация + отправка в TG
# Запуск: понедельник 09:00 через LaunchAgent

BOT_TOKEN=$(python3 -c "import json; t=json.load(open('$HOME/artvision-data/tokens.json')); print(t['telegram']['portal_bot']['token'])")
GROUP_CHAT="-4273200821"

# Даты текущей недели (Пн–Пт)
MON=$(date -v-$(($(date +%u)-1))d +%Y-%m-%d 2>/dev/null || date -d "last monday" +%Y-%m-%d)
FRI=$(date -v-$(($(date +%u)-5))d +%Y-%m-%d 2>/dev/null || date -d "next friday" +%Y-%m-%d)

echo "Generating weekly table: $MON — $FRI"

# Запускаем Claude для генерации таблицы
# (Claude читает Asana через MCP и формирует таблицу)
claude --print "Сгенерируй еженедельную таблицу задач из Asana на неделю $MON — $FRI.
Формат из processes/weekly-task-table.md.
Все исполнители: Андрей (boss@artvision.pro, GID 11616861546187), Антон (antoniokmr, GID 1212367692929434).
Отправь результат в TG группу $GROUP_CHAT.
Если есть перегруз (>7 задач/день) — добавь ⚠️ алерт.
Просроченные задачи — в отдельном блоке 🔴." 2>/dev/null

echo "Done: $(date)"
