
## Routed 2026-04-26 02:17
- [ ] **[routed]** **Entry point: @avportal_bot — handler любой ссылки** [client:internal] [result:bot-handler-deployed] [priority:high] [skill:aiogram-patterns] [assignee:claude] [due:2026-04-30] [blocked-by:Архитектура] — regex URL → INSERT link_inbox → reply с кнопками [📋 Asana / 🚀 Начать]

## Routed 2026-05-08 22:22
- [ ] **[routed]** **Scout follow-up: ADMIN_USER_IDS + bot entry-point** [product:scout] [priority:high] [assignee:anton+claude] [due:2026-05-10] [result:bot-live] — `scripts/scout_bot_handlers.py:ADMIN_USER_IDS = frozenset()` пустой. Нужны TG IDs Антона/Андрея из memory `accounts.md`. Решение: добавить в @avportal_bot или создать отдельный @scout_bot.

## Routed 2026-05-09 18:11
- [ ] **[routed]** **Telethon: outreach userbot Антона + throttle** [client:blumart] [priority:high] [assignee:claude] [result:tg-outreach-script+jsonl] [blocked-by:freelancers.csv] — userbot от личного TG Антона (НЕ @avportal_bot — у бота нет права писать первым в DM). Re-auth `tg_userbot.session` если expired (см. `self-corrections.md` #12). Throttle 5-8/час, рандомные паузы 7-15 мин. Логи в `tg-outreach.jsonl`. Dedup vs `already-contacted.csv`.

## Routed 2026-05-25 19:37
- [ ] **[routed]** **[infra] Разобрать рестарты VPS claude-worker** [priority:medium] [assignee:claude] [result:worker-stable] — claude-worker (pm2 на VPS) перезапускался 4×/ч 25.05, от него зависит AI-советник @avportal_bot. Алерты заглушены фильтром, причина не устранена. Проверить pm2 logs claude-worker. Сессия 85fca7e8.

## Routed 2026-06-11 03:02
- [ ] **[routed]** 🔴 **VPS 80.90.181.152: api.telegram.org НЕДОСТУПЕН (timeout, 2 замера 11.06 ~02:35 и 02:53)** [priority:high] [assignee:claude] [result:tg-connectivity-restored-or-workaround] — DNS резолвится (149.154.166.110), TCP/HTTPS timeout. Polling-боты на VPS не получают апдейты (pm2 online ≠ работает). Выяснить: блок хостера/RKN → решение (webhook через nginx / прокси). Связано: avportal-bot остановлен 09.06.
