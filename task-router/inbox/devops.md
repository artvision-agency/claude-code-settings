
## Routed 2026-04-21 15:15
- [ ] **[routed]** LaunchAgent `pro.artvision.content-factory` — cron 1/будни 10:00 МСК [priority:medium] [assignee:claude] [due:2026-04-28] [blocked-by:7 approved]

## Routed 2026-04-26 02:47
- [ ] **[routed]** **Переименовать `products/karta-topov/` → `products/flow/regions/` + обновить деплой-путь VPS** [product:flow] [result:repo-rename+vps-redeploy] [priority:medium] [assignee:claude] [due:2026-05-03] — решение Антона 25.04 (handover §7)

## Routed 2026-05-02 19:06
- [ ] **[routed]** **Проверить Colyseus endpoints на VPS:3001** [priority:medium] [assignee:claude] [result:live-endpoint-confirmed] — TCP открыт, HTTP корня молчит. Проверить /matchmake/, /colyseus/. Если сервис мёртв — рестарт docker

## Routed 2026-05-02 19:36
- [ ] **[routed]** **ssh VPS — проверить Colyseus docker (rebuild?)** [priority:medium] [assignee:claude] [skill:devops-engineer] [result:colyseus-alive-or-rebuilt] — TCP 3001 открыт, HTTP `/matchmake/` и `/colyseus/` HTTP=000. docker ps + logs + rebuild при необходимости
