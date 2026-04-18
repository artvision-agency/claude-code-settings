---
name: timeweb-support
description: "Отправка тикета в поддержку Timeweb Cloud через Telegram @twcsupport (Telethon MTProto). Триггеры: timeweb, тикет, поддержка timeweb, timeweb support, запрос в тп, обращение timeweb, тех поддержка, тикет тп"
---

# Timeweb Support — тикет в поддержку через Telegram

## Почему Telegram, а не панель

Веб-панель Timeweb Cloud защищена reCAPTCHA — Playwright не может отправить тикет.
Рабочий метод: отправка напрямую в @twcsupport через Telethon (MTProto userbot).

## Конфигурация

| Параметр | Значение |
|----------|----------|
| API_ID | 35195969 |
| API_HASH | 576ad787126be6f43f28df1a1279aa4a |
| Session | `/Users/antonk/.telegram_session` (файл `.telegram_session.session`) |
| Получатель | `@twcsupport` |
| Аккаунт Timeweb | sr951557 / justtrance@gmail.com |
| Копии тикетов | `/Users/antonk/artvision-data/docs/support/` |

## Данные сервера (из tokens.json)

Перед отправкой прочитать `tokens.json` ключи `timeweb_cloud` и `vps`:

```bash
python3 -c "
import json
d = json.load(open('/Users/antonk/artvision-data/tokens.json'))
tw = d['timeweb_cloud']
vps = tw['vps']
print(f'ID: {vps[\"id\"]}')
print(f'Name: {vps[\"name\"]}')
print(f'IP: {vps[\"ip\"]}')
print(f'Specs: {vps[\"specs\"]}')
print(f'Login: {tw[\"login\"]}')
print(f'Owner: {tw[\"owner\"]}')
"
```

## Алгоритм выполнения

### 1. Собрать информацию для тикета

Получить от пользователя (или сгенерировать из контекста):
- **Тема** (subject) — краткая, 1 строка
- **Описание проблемы** — подробно, с датами/логами
- **Запрашиваемые действия** — что именно просим от поддержки

Если пользователь дал короткое описание — Claude дополняет:
- Собрать логи с VPS (`ssh root@80.90.181.152 "last reboot --time-format iso | head -10"`)
- Проверить uptime (`ssh root@80.90.181.152 "uptime"`)
- Проверить нагрузку (`ssh root@80.90.181.152 "free -h && df -h / && cat /proc/loadavg"`)

### 2. Сформировать сообщение

Формат сообщения (профессиональный, на русском):

```
Тема: {subject}

Добрый день,

Аккаунт: sr951557
Сервер: {vps.id} / {vps.name} ({vps.ip})
Тариф: {vps.specs}

{описание проблемы}

Прошу:
{список запрашиваемых действий, нумерованный}

С уважением,
Антон Камеристый
Artvision Agency
```

### 3. Отправить через Telethon

Создать и запустить скрипт:

```bash
python3 << 'PYEOF'
import asyncio
from telethon import TelegramClient

API_ID = 35195969
API_HASH = "576ad787126be6f43f28df1a1279aa4a"
SESSION = "/Users/antonk/.telegram_session"

MESSAGE = """Тема: {subject}

Добрый день,

Аккаунт: sr951557
Сервер: {vps_id} / {vps_name} ({vps_ip})
Тариф: {vps_specs}

{description}

Прошу:
{actions}

С уважением,
Антон Камеристый
Artvision Agency"""

async def main():
    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.start()

    entity = await client.get_entity("twcsupport")
    result = await client.send_message(entity, MESSAGE)

    print(f"OK: message_id={result.id}, date={result.date}")

    await client.disconnect()

asyncio.run(main())
PYEOF
```

**ВАЖНО:**
- Подставить реальные значения в MESSAGE (не оставлять плейсхолдеры)
- Session файл: `/Users/antonk/.telegram_session` (Telethon добавит `.session` автоматически)
- Если ошибка авторизации — сообщить пользователю, запросить код из TG

### 4. Сохранить копию тикета

Сохранить в `/Users/antonk/artvision-data/docs/support/timeweb-ticket-{YYYY-MM-DD}.md`:

```markdown
# Запрос в техподдержку Timeweb Cloud

**Дата:** {дата}
**Сервер:** {vps.id} / {vps.name} ({vps.ip})
**Тариф:** {vps.specs}
**TG message_id:** {result.id}
**Статус:** отправлено

---

## Текст обращения

{полный текст сообщения}
```

Если файл с такой датой уже существует — добавить суффикс `-2`, `-3` и т.д.

### 5. Залогировать для follow-up

Вывести пользователю:
```
Тикет отправлен в @twcsupport
Message ID: {id}
Дата: {date}
Копия: docs/support/timeweb-ticket-{date}.md

Для проверки ответа: python3 ~/.claude/scripts/tg-chat-export.py --search "twcsupport"
```

## Follow-up (проверка ответа)

Для проверки ответа от поддержки использовать скилл `tg-chat-export`:

```bash
python3 ~/.claude/scripts/tg-chat-export.py --search "twcsupport"
# или по ID чата после первого экспорта:
python3 ~/.claude/scripts/tg-chat-export.py --chat-id <ID> --since {дата тикета} -o /tmp/twc-reply.md
```

## Если сессия Telethon истекла

1. Сообщить пользователю: "Telethon сессия истекла, нужен код из TG"
2. Запустить:
```python
client = TelegramClient(SESSION, API_ID, API_HASH)
await client.start(phone='+79819139908')
```
3. Попросить код у пользователя
4. После авторизации повторить отправку

## Безопасность

- **CONFIRM-уровень:** показать текст сообщения пользователю ПЕРЕД отправкой
- Не отправлять пароли/токены в текст тикета
- Не упоминать Claude/AI в тексте обращения

## Примеры использования

- "тикет в timeweb — сервер перезагружается"
- "напиши в поддержку timeweb что VPS лагает"
- "timeweb support — просим компенсацию за даунтайм"
- "обращение в тп — не работает IPv6"
