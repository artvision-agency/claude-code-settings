---
name: tg-chat-export
description: "Экспорт переписки из Telegram через Telethon. Поиск чатов, экспорт истории в таблицу/файл. Триггеры: чат тг, переписка тг, экспорт чата, tg chat, телетон, покажи переписку, диалог с клиентом тг, история чата"
---

# TG Chat Export — экспорт переписки из Telegram

## Что делает

Через Telethon (MTProto userbot) читает полную историю любого чата Telegram и выдаёт в формате таблицы.

## Скрипт

`~/.claude/scripts/tg-chat-export.py`

## Алгоритм

### 1. Определить чат

Если клиент указан — искать ID в известных чатах:

| Клиент | Chat ID | Тип |
|--------|---------|-----|
| Esenina (группа) | -5134497082 | Group |
| Esenina (личка) | 954855520 | User |

Если ID неизвестен:
```bash
python3 ~/.claude/scripts/tg-chat-export.py --search "имя клиента"
```

### 2. Экспортировать

```bash
# Все сообщения (до 500)
python3 ~/.claude/scripts/tg-chat-export.py --chat-id <ID> -o /tmp/tg-export.md

# С фильтром по дате
python3 ~/.claude/scripts/tg-chat-export.py --chat-id <ID> --since 2026-03-01 -o /tmp/tg-export.md

# Больше сообщений
python3 ~/.claude/scripts/tg-chat-export.py --chat-id <ID> --limit 2000 -o /tmp/tg-export.md
```

### 3. Показать пользователю

- Если < 50 сообщений — вывести таблицу прямо в чат
- Если > 50 — сохранить в `clients/<client>/tg-chat-<name>-<date>.md` и показать сводку

### 4. Список всех диалогов

```bash
python3 ~/.claude/scripts/tg-chat-export.py --list
```

## ДЕТЕРМИНИРОВАННЫЙ RE-AUTH (обязательная пред-проверка ЛЮБОГО TG-чтения)

> Делать ВСЕГДА перед чтением TG (этот шаг = детерминированный гейт воркфлоу, не «вспомню»).
> Канон-сессия: `~/artvision-data/.claude_temp_scripts/tg_userbot`. Креды + телефон: `tokens.json['telegram']` (api_id 35195969, **phone +79110861888** — сохранён). Скрипт: `scripts/tg-signin-relay.py`.

**Шаги (Claude гонит сам, пользователь даёт ТОЛЬКО код):**
```bash
# 1. Проверка
SEO_MASTER_FORCE=1 python3 ~/artvision-data/scripts/tg-signin-relay.py check
#    AUTH @user → сессия жива, читать сразу (шаг «Экспортировать»)
#    NOT_AUTH → re-auth ниже
# 2. Отправить код (телефон из tokens.json, НЕ выводить из памяти — это unblock'ает классификатор)
SEO_MASTER_FORCE=1 python3 ~/artvision-data/scripts/tg-signin-relay.py send +79110861888
#    OK код отправлен → код прилетел Антону в TG
# 3. Антон ДИКТУЕТ 5 цифр в чат → Claude:
SEO_MASTER_FORCE=1 python3 ~/artvision-data/scripts/tg-signin-relay.py signin <КОД> [2fa_pass]
#    OK авторизован → сессия жива. BAD_CODE/EXPIRED → повторить send. NEED_2FA → запросить пароль.
```
Маркеры парсить: `AUTH @user / NOT_AUTH / OK код отправлен / OK авторизован / BAD_CODE / EXPIRED / NEED_2FA`.

**Разделение труда (правило Антона 2026-06-09):** Claude делает ВСЁ (check/send/signin/чтение). Пользователь — только диктует код (Telegram физически шлёт код только владельцу — единственное что Claude не может получить сам). НЕ гонять пользователя в терминал — `tg-reauth.sh` интерактивный устарел для Claude-сессий, использовать relay.

⚠️ Старый путь (`~/.claude/state/telethon_session` + ручной `client.start`) — НЕ использовать. Канон = relay + сессия `tg_userbot` + телефон из tokens.

## Когда использовать

- "покажи переписку с клиентом X"
- "что обсуждали в тг с Y"
- "экспорт чата"
- Перед созданием КП — проверить историю общения
- После встречи — найти договорённости в чате
