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

## Если сессия истекла

Telethon session: `~/.claude/state/telethon_session`

При ошибке авторизации:
1. Сообщить пользователю: "Telethon сессия истекла, нужен код из TG"
2. Запустить авторизацию с `client.start(phone='+79819139908')`
3. Попросить код у пользователя
4. Ввести через `code_callback`

## Когда использовать

- "покажи переписку с клиентом X"
- "что обсуждали в тг с Y"
- "экспорт чата"
- Перед созданием КП — проверить историю общения
- После встречи — найти договорённости в чате
