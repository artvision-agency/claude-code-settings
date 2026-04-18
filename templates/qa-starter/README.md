# QA Starter Templates

Готовые testing-стартеры для типовых проектов Artvision. Скопировал
папку → `make install && make test` — коверов пройдены, CI зелёный.

Все данные о звёздах/статусах — GitHub actuals на **2026-04-18**.

## Какой template для чего

| Template | Когда применять | Основные тулы |
|----------|-----------------|---------------|
| `python/` | Любой Python-проект (либа, CLI, worker) | pytest, coverage, mypy, ruff, pre-commit |
| `typescript/` | Node/Bun либа, CLI, backend | vitest, tsc --strict, eslint, prettier |
| `api/` | REST API (Python/Node) — contract + smoke | schemathesis / dredd, openapi-spec |
| `web-app/` | Frontend (React/Vue/Svelte) + E2E | playwright-pytest или playwright-test |
| `web-scraper/` | Скрейперы, парсеры, ETL на HTML | playwright + seleniumbase + jsonschema + deepdiff |
| `telegram-bot-python/` | TG-боты на python-telegram-bot / aiogram | pytest + telethon E2E + stress + tgmock + aiogram_tests |

**Можно комбинировать.** API + scraping worker в одном репо →
`cp python/. ./; cp api/. ./; cp web-scraper/. ./`.

## Матрица признанности инструментов (source: GitHub stars 2026-04-18)

| Tool | Stars | Verdict |
|------|------:|---------|
| `pytest` | 12k | Must-have Python (де-факто стандарт) |
| `vitest` | 13.8k | Must-have TypeScript (быстрее jest, ESM native) |
| `jest` | 44.5k | Валидно для legacy Node, для нового — vitest |
| `playwright` | 86k | Must-have E2E веб (Microsoft, supersedes cypress на нашем стеке) |
| `pytest-playwright` | 543 | Official MS плагин — для Python E2E |
| `playwright-test` | — | Официальный Node test runner Playwright |
| `SeleniumBase` | 12.5k | Лучшее в 2026 для anti-detect скрейпинга, UC mode |
| `selenium` | 31k | Legacy, уступает Playwright по DX, но всё ещё живой |
| `telethon` | 10.6k | Userbot для TG E2E — единственная рабочая опция для MTProto |
| `tgmock` | ~4 | Молодой, fake TG Bot API HTTP server. Архитектурно правильный, но ранняя стадия |
| `aiogram_tests` | ~72 | Единственная «признанная» unit-тест-либа для aiogram. **Заброшен с 2024-01** — использовать с fallback |
| `jsonschema` | 4.5k | Стандарт индустрии для Python (Draft 2020-12) |
| `deepdiff` | 2.1k | Diff для golden-files, понятный pretty output |
| `schemathesis` | 2.4k | Property-based тесты OpenAPI — обязательно в `api/` |
| `httpx` | 14.1k | Async HTTP client, де-факто заменил `requests` |
| `ruff` | 38.6k | Линт + формат Python, в 100x быстрее black+flake8 |
| `mypy` | 19.3k | Type-checker Python, эталон |
| `beautifulsoup4` | — | HTML parsing, живой и быстрый с lxml |
| `tenacity` | 6.7k | Retry-декоратор, де-факто стандарт в Python |

## Общие принципы всех templates

1. **Pinned upper-bound** версии (`<2`, `<3`) — защита от случайных major bumps.
2. **`pre-commit`** с ruff/eslint — линт до CI, не после.
3. **`Makefile`** как унифицированный entrypoint — `make install`, `make test`, `make test-fast`.
4. **Markers в pytest.ini** — `integration`, `slow`, `stealth` — чтобы CI умел fast lane.
5. **Golden files** для всего что структурированно — регрессии ловятся точечно.
6. **Schema validation** для всего что пересекает границу процесса (API, scrape, LLM output).

## Связь с Artvision rules

- `~/.claude/rules/quality-gates.md` — обязательные проверки перед деплоем.
- `~/.claude/rules/core.md` — `set -euo pipefail` в shell-скриптах, factcheck-v2 перед scp.
- `/Users/antonk/.claude/skills/python-testing-patterns` — skill для нового кода.
- `/Users/antonk/.claude/skills/javascript-testing-patterns` — то же для JS/TS.
