---
name: bot-fix
description: "Быстрый фикс бага в TG-боте на VPS: диагностика из логов, патч, синтаксис, рестарт, тест. Безопасный workflow с бэкапами."
argument-hint: "[описание бага или 'логи']"
user-invocable: true
allowed-tools: Read Write Edit Bash Glob Grep
---

# /bot-fix — Быстрый фикс бота на VPS

Триггеры: `исправь бот`, `бот сломался`, `fix bot`, `баг в боте`, `бот не работает`

## WORKFLOW

### Шаг 1: Диагностика (30 сек)

```bash
# Определить VPS и сервис
ssh root@<VPS> "systemctl list-units --type=service | grep -i bot"
ssh root@<VPS> "journalctl -u <service> --no-pager -n 30 --since '1 hour ago' | grep -i 'error\|exception\|traceback'"
```

**Из логов извлечь:**
- Файл + строка ошибки
- Тип: NameError, KeyError, AttributeError, ImportError, TypeError
- Контекст: какая функция, какой input вызвал

### Шаг 2: Бэкап (ОБЯЗАТЕЛЬНО)

```bash
ssh root@<VPS> "cp <file>.py <file>.py.bak"
```

### Шаг 3: Патч

**Правила патчинга на VPS:**
- НЕ использовать `sed` для многострочных замен (ломается на Ubuntu)
- Использовать Python heredoc:
```bash
ssh root@<VPS> << 'PYEOF'
python3 << 'PY'
with open("/path/to/file.py", "r") as f:
    content = f.read()
content = content.replace("old_code", "new_code")
with open("/path/to/file.py", "w") as f:
    f.write(content)
print("PATCHED OK")
PY
PYEOF
```

**Типичные фиксы TG-ботов:**
| Баг | Фикс |
|-----|------|
| `name 'X' is not defined` | Добавить параметр в функцию + передать при вызове |
| `'NoneType' has no attribute` | Guard: `if X is not None:` или fallback |
| Blocking `await send_email()` | `asyncio.create_task()` вместо `await` |
| Double call finish/cleanup | Guard: `if user_id not in sessions: return` |
| Source tracking `==` vs prefix | `source.startswith("prefix")` |
| 152-ФЗ consent bypass | Consent gate на ВСЕ entry points (deep links, QR) |
| `409 Conflict: terminated by setWebhook request` (grammY/polling) | `curl .../deleteWebhook?drop_pending_updates=true` + `pm2 restart` |
| `AI Advisor DM failed: 400: chat not found` | Битый ADMIN_ID — `getChat` для каждого ID, убрать/заменить битый в `.env` |
| `pending_update_count` растёт | Polling отвалился — проверить webhook, рестарт |

### Для @avportal_bot специфика (vps-bot/bot.js на 80.90.181.152)

См. полный чеклист: `~/.claude/projects/-Users-antonk/memory/reference_avportal_bot_runtime.md` → раздел "Диагностический чеклист".

Основные точки проверки:
1. `ssh cmd "pm2 describe avportal-bot"` — uptime/restarts
2. `getWebhookInfo` — если url != "" → вебхук мешает
3. `getChat` для каждого ADMIN_IDS → найти битые ID
4. `grep 'ai_advisor_sent'` в pm2 logs — есть ли успешные Advisor-нотификации

### Шаг 4: Проверка синтаксиса (ОБЯЗАТЕЛЬНО перед рестартом)

```bash
ssh root@<VPS> "python3 -c \"import py_compile; py_compile.compile('<file>', doraise=True); print('OK')\""
```

### Шаг 5: Рестарт + проверка

```bash
ssh root@<VPS> "systemctl restart <service> && sleep 2 && systemctl status <service> --no-pager | head -15"
ssh root@<VPS> "journalctl -u <service> --no-pager -n 5"
```

**Проверить:**
- `Active: active (running)` — бот запустился
- Нет `ERROR`/`CRITICAL` в логах
- Версия в логе совпадает с ожидаемой

### Шаг 6: Функциональный тест

**Email:** отправить тестовое письмо через Python на VPS, проверить mail.log
**Webhook:** curl к endpoint, проверить ответ
**TG:** дать ссылку пользователю для ручного теста

### АНТИПАТТЕРНЫ

- НЕ деплоить без бэкапа
- НЕ перезапускать без проверки синтаксиса
- НЕ предлагать деплой когда просят проверку
- НЕ патчить sed-ом многострочные блоки на Ubuntu
- НЕ блокировать UX пользователя await-ом на I/O (email, HTTP)
