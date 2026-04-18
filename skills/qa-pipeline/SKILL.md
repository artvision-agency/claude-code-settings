---
name: qa-pipeline
description: Universal QA orchestrator. Runs unit → integration → e2e → security → stress for any project type (Telegram bot, web app, API, CLI, scraper). Detects project stack automatically, picks the right runner, gates deploy. Use when adding a new product or before release. Triggers — "прогнать pipeline", "qa audit", "full tests", "gate", "release check".
---

# QA Pipeline — универсальный оркестратор

## Что делает

Одна команда → полный прогон тестов + gate pass/fail.

```
Project → detect type → runner → unit → integration → e2e → security → stress → report
```

## Признанность стека (GitHub stars 2026-04-18)

Используются только инструменты с community traction. Никаких самодельных решений, если есть признанная либа.

| Категория | Инструмент | ⭐ Stars | Статус |
|-----------|-----------|--------:|--------|
| Python test runner | pytest | 12k | де-факто стандарт |
| Web E2E | Playwright | 86k | монополист |
| Python Playwright | playwright-python | 14.5k | официальный |
| Anti-detect scraping | SeleniumBase | 12.5k | UC mode |
| TG bot MTProto client | Telethon | 12k | монополист |
| TG bot framework #1 | python-telegram-bot | 29k | reference |
| TG bot framework #2 | aiogram | 5.7k | популярен в RU/СНГ |
| TG bot framework TS | grammY | 3.5k | TS выбор |
| Contract API | schemathesis | 2.5k | OpenAPI fuzz |
| Load API | k6 | 27k | OSS стандарт |
| JSON schema | jsonschema | 4.5k | Draft 2020-12 |
| Golden diff | deepdiff | 2.1k | общепринят |
| Fake TG API | tgmock | 4 | молодой, архитектурно правильный |
| Aiogram unit | aiogram_tests | 72 | заброшен 01-2024, fallback на моки |

## Автоопределение типа проекта

Скрипт `scripts/detect-project-type.sh` смотрит:

| Сигнал | Тип |
|--------|-----|
| `import telethon`, `import aiogram`, `python-telegram-bot` | telegram-bot-python |
| `grammy`, `grammyjs` в package.json | telegram-bot-typescript |
| `playwright`, `from playwright.sync_api` (и **не** бот) | web-scraper или web-app |
| `fastapi`, `flask`, `django`, `express` (API routes) | api |
| `next`, `vite`, `react`, `vue` | web-app |
| `argparse`, `click`, `typer` (главный вход = CLI) | cli |
| `airflow`, `dagster`, `prefect`, `pandas` ETL | data-pipeline |

Fallback: general-purpose Python → минимальный runner.

## Стандартный pipeline

Каждый runner запускает фазы в том же порядке. Gate = если любая P0 fail — остановиться.

| Фаза | P0/P1/P2 | Инструменты | Gate |
|------|:--------:|-------------|------|
| **Lint/format** | P0 | ruff / eslint | warnings OK, errors fail |
| **Type check** | P0 | mypy / tsc | errors fail |
| **Unit tests** | P0 | pytest / vitest | fail → gate close |
| **Coverage** | P0 | pytest-cov / v8 | <75% → warn, <50% → fail |
| **Security scan** | P0 | bandit / semgrep / npm audit | CRITICAL → fail |
| **Secret scan** | P0 | gitleaks / trufflehog | найдено → fail |
| **Dep audit** | P0 | pip-audit / npm audit | CRITICAL/HIGH → fail |
| **Integration** | P1 | pytest с моками (не реальная сеть) | fail → warn |
| **Contract tests** | P1 (API) | schemathesis | fail → warn |
| **E2E** | P1 | Playwright / Telethon | fail → warn, но блокирует release |
| **Accessibility** | P1 (web) | axe-core | violations → warn |
| **Visual regression** | P2 (web) | Playwright toHaveScreenshot | diff → warn |
| **Load / stress** | P2 | k6 / locust / asyncio concurrent | p95 > SLO → warn |
| **Anti-detect** | P2 (scraper) | SeleniumBase sannysoft | detected → warn |

## Runners

Детали по типу проекта:

- `runners/telegram-bot.md` — TG боты (Telethon e2e, MockedBot unit, FSM tests)
- `runners/web-app.md` — веб (Playwright + axe + Lighthouse + visual)
- `runners/api.md` — REST/GraphQL (schemathesis + k6 + auth flows)
- `runners/cli.md` — CLI tools (expect + golden files + exit codes)
- `runners/web-scraper.md` — скрейперы (schema validation + golden + anti-detect + freshness)

## Использование

### Полный прогон
```
/qa-pipeline <project-path>
```

### Быстрый smoke (только P0, <5 минут)
```
/qa-pipeline <project-path> --smoke
```

### Только конкретная фаза
```
/qa-pipeline <project-path> --phase unit
/qa-pipeline <project-path> --phase security
/qa-pipeline <project-path> --phase e2e
```

### С указанием типа (если auto-detect ошибается)
```
/qa-pipeline <project-path> --type telegram-bot-python
```

## Алгоритм

1. **Определить проект** — cwd или переданный путь
2. **Detect type** — запустить `scripts/detect-project-type.sh <path>`
3. **Загрузить runner** — `runners/<type>.md`
4. **Pre-checks** — venv/node_modules установлены? Если нет — `make install` или `pip install -r requirements-dev.txt`
5. **Запустить фазы** — P0 последовательно (stop on fail), P1+P2 параллельно
6. **Собрать артефакты:**
   - `qa-report-<timestamp>.md` — человекочитаемый
   - `qa-report-<timestamp>.json` — для CI
   - Coverage HTML — `htmlcov/`
   - Playwright traces — `test-results/`
7. **Gate:**
   - Все P0 pass → **PASS** → можно deploy
   - Любой P0 fail → **FAIL** → блокируем
   - P1/P2 fail → **WARN** → показать, деплой на усмотрение

## Интеграция с LaunchAgent/PM2

После успешного deploy запускать `--smoke`:

```bash
# В deploy-tvorims.sh после rsync + restart
/qa-pipeline /path/to/bot --smoke --bail
if [ $? -ne 0 ]; then
  echo "❌ Smoke failed — rolling back"
  git reset --hard HEAD~1
  pm2 restart bot
  exit 1
fi
```

Hook для LaunchAgent: `~/.claude/hooks/post-deploy-smoke.sh`.

## Gate критерии для production

Перед разрешением деплоя в production:

| Требование | Gate |
|------------|:----:|
| Unit tests present | ✅ |
| Coverage ≥ 75% | ✅ |
| No CRITICAL security findings | ✅ |
| No secrets committed | ✅ |
| E2E smoke path passes (1+ сценарий) | ✅ |
| Integration tests (API/DB) pass | ✅ |
| Runtime <5 минут на smoke | ✅ |

Если чего-то нет → **gate close** → сначала доводим, потом деплой.

## Знает про

- `~/.claude/templates/qa-starter/` — готовые scaffolds для стартa
- `bot-audit` skill — параллельный senior-ревью 3 агентами
- `bot-test-matrix` skill — генерация test cases из FSM
- `e2e-bot-testing` skill — Telethon runner для TG ботов

## НЕ делает

- Не деплоит сам — только проверяет
- Не правит код — только отчёт + gate
- Не создаёт новые тесты — использует существующие
- Для generation новых тестов → `bot-test-matrix` или agent

## Признаки того что pipeline надо обновить

- New language/framework появился (добавить runner)
- Industry tool сменился (обновить `SKILL.md` stars table)
- Security/compliance требование (добавить в P0)
- Частый false-positive в конкретной фазе (переквалифицировать P0→P1)

Такие изменения коммитить с обоснованием в `CHANGELOG.md` этого скилла.
