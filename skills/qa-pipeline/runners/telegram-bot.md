# Runner — Telegram Bot (Python/TypeScript)

## Применимо к
- Python + aiogram / python-telegram-bot / pyrogram / telethon
- TypeScript + grammY / telegraf

## Фазы (в порядке, P0 сверху)

### P0 — Must pass

1. **Lint**
   - Python: `ruff check .`
   - TS: `eslint . --ext .ts`

2. **Type check**
   - Python: `mypy <main_module>.py`
   - TS: `tsc --noEmit`

3. **Unit tests**
   - Python: `pytest tests/unit/ -v`
   - TS: `vitest run tests/unit/`
   - Требуется: handlers, FSM states, commands, callback parsing, guards

4. **Coverage ≥ 75%**
   - Python: `pytest --cov --cov-fail-under=75`
   - TS: `vitest run --coverage`

5. **Security**
   - Python: `bandit -r . -x tests/`
   - TS: `npm audit --production`

6. **Secret scan**
   - `gitleaks detect --no-git` или `trufflehog filesystem .`

7. **Dep audit**
   - Python: `pip-audit`
   - TS: `npm audit --audit-level=high`

### P1 — Важно но не блокирующе

8. **Integration (fake TG API)**
   - Если есть `tgmock` setup — прогнать
   - Альтернатива: `aiogram_tests` MockedBot
   - Проверяет: dispatcher routing, handler chain, middleware

9. **E2E через Telethon userbot**
   - `tests/e2e/runner.py` или `e2e_full_flow.py`
   - Нужна валидная Telethon session (`~/.claude/state/telethon_session.session`)
   - API_ID/HASH из `tokens.json` → `telegram.api_id`/`api_hash`
   - Rate limit: минимум 3 сек между сценариями

10. **FSM state machine tests**
    - Каждое состояние → вход/выход/fallback
    - Transitions coverage (генерится через `bot-test-matrix` skill)

### P2 — Nice to have

11. **Stress test**
    - 10-50 concurrent users через asyncio
    - Замер p50/p95/p99 latency
    - Template: `qa-starter/telegram-bot-python/tests/stress/test_concurrent.py`

12. **Error budget**
    - Rate limit handling (FloodWaitError)
    - Network resilience (ServerDisconnectedError reconnect)

## Специфика Telegram

### Что обязательно тестировать
- **Race conditions в callbacks** — двойной клик, отмена в процессе
- **XSS в email/TG-уведомлениях** — пользовательский ввод не исполняется
- **Auth bypass в admin commands** — проверка `user_id in admins`
- **FSM reset** — `/start` в любом состоянии сбрасывает корректно
- **Persistence** — бот переживает рестарт (Pickle/Redis)
- **Idempotency** — двойной webhook не создаёт дубликат

### Известные "ловушки"
- `query.answer()` перед чтением `user_data` — race
- `asyncio.create_task` без ссылки — orphan + GC warning
- `user_data` без TTL — копится навсегда
- Бот без healthcheck = 129 рестартов за 3 дня и никто не узнает (инцидент tvorims 2026-03-14)

### Live test rate limits
- **Минимум 3 сек** между сценариями в одной сессии
- Если FloodWaitError — уважать `err.seconds` + 1 сек
- Не флудить production бот — max 20-30 сценариев в прогон

## Инструменты (признанность)

| Что | Инструмент | Stars | Комментарий |
|-----|-----------|------:|-------------|
| Unit frameworks | aiogram_tests | 72 | Заброшен 2024, использовать с fallback |
| Fake TG API | tgmock | 4 | Молодой, git-only |
| Userbot client | Telethon | 12k | Монополист |
| Mocking helpers | pytest-mock, AsyncMock | n/a | Стандарт |

## Артефакты после прогона

- `tests/e2e/results/report_<timestamp>.json`
- `tests/e2e/results/last_full_run.txt`
- `htmlcov/index.html`
- `bandit-report.json`

## Gate критерии

**PASS** (можно деплоить):
- Все P0 зелёные
- Coverage ≥ 75%
- 0 CRITICAL security
- E2E happy path (/start → Q → answer → result) зелёный

**FAIL** (блок):
- Любой P0 красный
- Secret в коде
- Auth bypass в тестах
- Race condition reproducible

## Применение к продуктам (примеры)

| Продукт | Тип | Покрытие | Gap |
|---------|-----|----------|-----|
| es-ru-translator | aiogram + gTTS + Telethon STT | 96% unit + 12 e2e | — ready |
| tvorim-opros-bot | python-telegram-bot | 1751 строк тестов, 18 e2e | production-grade |
| voxrate-bot | aiogram | 37% coverage, 20/31 pass | gap: 27h работы |
| tvorim survey-bot | aiogram + Playwright scraper | 145 тестов, 131 pass | gap: scraper tests (7h) |
