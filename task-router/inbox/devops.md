
## Routed 2026-04-17 11:03
- [ ] **[routed]** **Skill `remote-scheduler` — TG-бот /remind + REST API на VPS** [product:internal] [priority:medium] [skill:python-developer] — универсальный планировщик: команда `/remind 18:00 текст` или curl на VPS API → cron на VPS → TG напоминание. Цель: задача → planned → notification → человек открывает Claude → продолжает работу. Пример паттерна: ночная сессия 17.04, перенос reminder-1700 на VPS вручную (5 мин). Универсал — 2-3ч (бот команды + jsonl очередь + cron-проверка минутно)
