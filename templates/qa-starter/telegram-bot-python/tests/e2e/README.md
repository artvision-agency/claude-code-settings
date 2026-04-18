# E2E: Telegram Bot via Telethon

End-to-end сценарии, которые дрессируют реального бота от лица реального аккаунта (userbot через Telethon / MTProto).

## Setup

### 1. Получить api_id и api_hash

https://my.telegram.org → API development tools → создать приложение.

### 2. Создать session-файл

Разово залогиниться в userbot-аккаунт (НЕ в аккаунт разработчика — лучше отдельный TG-аккаунт для тестов):

```bash
python -c "
from telethon import TelegramClient
import os
c = TelegramClient(
    os.environ['TG_SESSION'],
    int(os.environ['TG_API_ID']),
    os.environ['TG_API_HASH'],
)
with c:
    me = c.loop.run_until_complete(c.get_me())
    print(f'logged in as {me.username or me.phone}')
"
```

После успешного логина файл `$TG_SESSION` создастся автоматически.

### 3. Env vars

Если используешь tokens.json в проекте Antonа:

```bash
export TG_API_ID=$(python3 -c "import json;print(json.load(open('tokens.json'))['telegram_api']['api_id'])")
export TG_API_HASH=$(python3 -c "import json;print(json.load(open('tokens.json'))['telegram_api']['api_hash'])")
export TG_SESSION=.tg_e2e_session
export TG_BOT_USERNAME=@my_bot
```

Или через `.env`:

```
TG_API_ID=12345
TG_API_HASH=abcdef...
TG_SESSION=.tg_e2e_session
TG_BOT_USERNAME=@my_bot
```

## Запуск

```bash
python tests/e2e/runner.py tests/e2e/scenarios/
# или конкретный:
python tests/e2e/runner.py tests/e2e/scenarios/flow_basic.yaml
```

Exit code `0` = всё прошло, `1` = хотя бы один fail.

## Формат сценария

См. `scenarios/_template.yaml`. Поддерживаемые шаги:

| Step | Значение |
|------|----------|
| `send_command` | строка `/cmd` |
| `send_text` | произвольный текст |
| `click_button` | подпись кнопки reply-keyboard |
| `click_callback` | подпись кнопки inline-keyboard |
| `assert_contains` | подстрока в ответе |
| `assert_matches` | regex в ответе |
| `assert_keyboard` | список подписей кнопок, должны все присутствовать |
| `sleep` | секунды (float) |

## Best practices

- Отдельный TG-аккаунт для E2E (не основной и не бот-аккаунт).
- Session-файл не коммитить в git — добавить `.tg_*_session*` в `.gitignore`.
- В CI использовать секреты (`TG_API_ID`, `TG_API_HASH`) + session-файл из artifact/cache.
- Между прогонами очищать диалог с ботом — реальный user может накапливать истории состояний.
- Бот должен быть в отдельном dev-инстансе (отдельный токен + отдельная БД), чтобы E2E не мешали проду.

## Troubleshooting

- `AuthKeyError` → session истёк, залогиниться заново.
- `FloodWaitError: N seconds` → TG rate limit, не запускай чаще раза в пару минут.
- Шаг `click_callback` падает с `message has no buttons` → предыдущий assert-шаг не прошёл (бот не прислал клавиатуру) либо кнопка называется иначе.
