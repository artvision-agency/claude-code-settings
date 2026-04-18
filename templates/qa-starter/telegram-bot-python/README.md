# QA Starter — Telegram Bot (Python)

Расширяет `python/` template + Telethon E2E + stress test.

## Применение

```bash
# 1. Применить базовый python/ template
cp -r ~/.claude/templates/qa-starter/python/. ./
# 2. Наложить telegram-bot-python/ (добавляет tests/e2e + tests/stress)
cp -r ~/.claude/templates/qa-starter/telegram-bot-python/. ./
# 3. Зависимости
pip install -r requirements-dev.txt
pip install telethon PyYAML
# 4. Настроить tokens.json или env vars (см. tests/e2e/README.md)
```

## Что добавляется поверх python/

```
tests/
├── e2e/
│   ├── runner.py                   # Telethon-based runner (~200 строк)
│   ├── scenarios/
│   │   └── _template.yaml          # шаблон сценария
│   └── README.md                   # setup: api_id, api_hash, session
└── stress/
    └── test_concurrent.py          # 10 параллельных юзеров, p50/p95/p99
```

## E2E: запуск

```bash
# Настроить (см. tests/e2e/README.md):
export TG_API_ID=... TG_API_HASH=... TG_SESSION=.tg_session TG_BOT_USERNAME=@bot
# Первый раз — создать session-файл (разовый логин):
python -c "from telethon import TelegramClient; import os; \
  TelegramClient(os.environ['TG_SESSION'], int(os.environ['TG_API_ID']), os.environ['TG_API_HASH']).start()"

# Прогнать сценарии:
python tests/e2e/runner.py tests/e2e/scenarios/
```

## Stress: запуск

Нужен пул session-файлов (по одному на виртуального юзера):

```bash
export TG_STRESS_SESSIONS=./sessions/   # папка с N *.session
export TG_STRESS_USERS=10
export TG_STRESS_ITERATIONS=5
export TG_STRESS_COMMAND="/start"

pytest tests/stress/test_concurrent.py -s --run-integration
```

Вывод: `p50=0.85s p95=1.92s p99=2.40s`. SLO-ассерты в тесте — подстрой под своего бота.

## Безопасность session-файлов

- НЕ коммитить session в git:
  ```gitignore
  *.session
  *.session-journal
  .tg_*_session*
  sessions/
  ```
- В CI — секреты через GitHub Actions `secrets.*`, session-файл в encrypted artifact.
- Userbot-аккаунт отдельный (не основной TG Антона).

## Изоляция бота

E2E-прогон гонит бот в dev-инстансе:
- отдельный токен (`@my_bot_dev`),
- отдельная БД,
- отдельный webhook/polling процесс.

Иначе прод-пользователи получат странные уведомления.

## Fast integration tests with tgmock (опционально)

`tgmock` — fake Telegram Bot API HTTP-сервер локально. Бот ходит на
`http://localhost:port/bot<token>/...` вместо `api.telegram.org`. Быстрее
Telethon-E2E (не нужен userbot, нет сетевой задержки) но ловит только
bot-level логику — не видит реальных edge cases TG API.

**Репо:** https://github.com/azdaev/tgmock (архитектурно правильный подход,
проект молодой, ~4⭐ на 2026-04-18).

**На pypi пакета нет** (проверено 2026-04-18) — установка из исходников:

```bash
pip install "git+https://github.com/azdaev/tgmock.git#egg=tgmock"
# или форкнуть в Artvision и pin на commit
```

**Пример fixture + теста (pytest):**

```python
# tests/integration/test_bot_with_tgmock.py
import pytest
import subprocess, time, os, signal
from contextlib import contextmanager

@contextmanager
def tgmock_server(port=8081):
    proc = subprocess.Popen(
        ["tgmock", "--port", str(port)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    time.sleep(0.5)
    try:
        yield f"http://localhost:{port}"
    finally:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=5)

@pytest.fixture
def fake_tg():
    with tgmock_server() as url:
        yield url

def test_start_command(fake_tg, monkeypatch):
    # Заставить бота ходить на fake-сервер вместо api.telegram.org
    monkeypatch.setenv("TELEGRAM_API_URL", fake_tg)
    from myapp.bot import handle_start
    result = handle_start(update={"message": {"text": "/start", "chat": {"id": 1}}})
    assert "Привет" in result["text"]
```

**Когда выбирать tgmock vs Telethon-E2E:**

| Нужно | tgmock | Telethon (tests/e2e/) |
|-------|:------:|:---------------------:|
| Unit-level logic handlers | ✅ | ❌ избыточно |
| Keyboard/callback routing | ✅ | ✅ |
| Реальный rate-limit / FloodWait | ❌ | ✅ |
| Userbot в групповом чате | ❌ | ✅ |
| CI без секретов TG | ✅ | ❌ нужен session |

## Опционально: aiogram_tests для aiogram 3.x

Чистые unit-тесты handlers без сети через `MockedBot` +
`MessageHandlerTester`. Полезно для быстрых regression-проверок FSM и
middleware.

```bash
pip install "aiogram-tests<2"  # актуальная 1.0.3 на 2026-04-18
```

**Предупреждение:** апстрим (github.com/OCCASS/aiogram_tests, ~72⭐) **не
обновлялся с января 2024**. Для aiogram 3.5+ могут быть несовместимости —
тестировать с fallback на ручные `AsyncMock`. В CI пин версии + lock-файл.

**Пример теста `/start`:**

```python
# tests/unit/test_handlers_aiogram.py
import pytest
from aiogram_tests import MockedBot
from aiogram_tests.handler import MessageHandler
from aiogram_tests.types.dataset import MESSAGE

from myapp.handlers import start_handler  # aiogram 3.x handler

@pytest.mark.asyncio
async def test_start_returns_greeting():
    request = MessageHandler(start_handler, state=None)
    calls = await request.query(message=MESSAGE.as_object(text="/start"))
    answer = calls.send_message.fetchone()
    assert "Привет" in answer.text
```

**Связка с ручными моками (fallback):** если `aiogram_tests` ломается на
вашей версии aiogram — используйте `AsyncMock(spec=Bot)` из `python/`
template (унаследовано от python-telegram-bot testing patterns).

## Матрица инструментов

| Инструмент | Слой | Скорость | Реализм | Когда |
|------------|------|:--------:|:-------:|-------|
| `AsyncMock` (ручной) | unit | 🟢🟢🟢 | 🔴 | Pure handler logic |
| `aiogram_tests` | unit | 🟢🟢🟢 | 🟡 | aiogram FSM/middleware |
| `tgmock` | integration | 🟢🟢 | 🟡🟡 | Routing + keyboard flows |
| Telethon (`tests/e2e/`) | e2e | 🟢 | 🟢🟢🟢 | Pre-release smoke, real API |
| Stress (`tests/stress/`) | load | — | 🟢🟢 | SLO p50/p95/p99 |
