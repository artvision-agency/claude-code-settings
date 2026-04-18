#!/bin/bash
# One-shot reminder в TG team chat 17:00 2026-04-17 — итоги ночной сессии Ops CRM v1
set -euo pipefail

MSG="🕔 17:00 — итоги ночной сессии 2026-04-17 (Ops CRM v1)

✅ СДЕЛАНО (branch feat/ops-crm-v1, не мерджено):
• Андрей: пакет 8 задач (msg_id=6688) — пришли дедлайны?
• План Ops CRM v1: docs/plans/2026-04-15-ops-crm-upgrade.md
• Батч 1: миграция+schema+parser (363→393 task, soft-delete, audit)
• Батч 2: Asana sync (111 задач) + REST API (21 pytest)
• Батч 3: frontend create/edit/delete/filters (16 acceptance)
• Батч 4: SSE+move+tests (87 pytest green, manual 10/10) + LaunchAgent cron 15min

⚠️ БЛОКЕРЫ (нужны Антон):
1. Cardwell emails: Adsgram + GameAnalytics + CrazyGames (Gmail MCP expired → /mcp)
2. OTIDO UTM #1: запросить у клиента админку @OtidoGroup боту
3. Миграция почт artvision.pro: app-passwords в Yandex 360
4. Fix pre-outbound-gate.sh: добавить -4273200821 в TEAM_CHAT_IDS
5. Андрей: ответ с дедлайнами по 8 задачам?

🎯 РЕВЬЮ Ops CRM:
cd ~/artvision-data/dashboards
python3 engine/server.py &
open http://127.0.0.1:5055/ops-crm.html

Если ОК → merge feat/ops-crm-v1 → main"

# Через TG team chat
curl -s -X POST "https://api.telegram.org/bot8399522625:AAGeVvP1WeyijXTcRByiynPOXncBFUwLKQ4/sendMessage" \
    -H "Content-Type: application/json" \
    --data-binary @<(python3 -c "import json,sys; print(json.dumps({'chat_id':'-4273200821','text':sys.argv[1]}))" "$MSG") \
    > /tmp/reminder-1700-result.json

# Удалить себя из crontab после выполнения
crontab -l 2>/dev/null | grep -v "reminder-1700-2026-04-17.sh" | crontab -
# и удалить скрипт
rm -f "$0"
