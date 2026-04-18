# Штатное расписание агентов — автоматическая маршрутизация

> При получении задачи — определить тип → запустить нужного агента.
> НЕ спрашивать "какого агента запустить?" — определять самому по таблице.

## Маршрутизация по типу задачи

| Тип задачи | Ключевые слова | Agent subagent_type | Model |
|------------|---------------|---------------------|-------|
| Баланс, матмодель, симуляция | баланс, матмодель, damage, XP curve, retention | `data-analyst` | opus |
| Backend, API, WebSocket | сервер, API, endpoint, auth, rate limit, DB | `backend-developer` | opus |
| Frontend, Vue, UI | компонент, UI, анимация, Vue, CSS, layout | `vue-expert` | opus |
| Тесты, QA | тест, pytest, coverage, e2e, assert | `test-automator` | opus |
| Security, аудит безопасности | XSS, injection, auth bypass, DoS, OWASP | `security-engineer` | opus |
| Баги, дебаг | баг, ошибка, crash, stack trace, fix | `debugger` | opus |
| SEO, контент | SEO, ключевые, мета, title, h1, контент | `seo-analyzer` | opus |
| КП, presale | КП, коммерческое, предложение, клиент | `sales-engineer` | opus |
| Документы, договоры | договор, акт, НДА, docx, Google Docs | `technical-writer` | opus |
| DevOps, деплой | nginx, pm2, docker, deploy, VPS, SSL | `devops-engineer` | opus |
| Code review, рефакторинг | ревью, рефакторинг, clean code, debt | `code-reviewer` | opus |
| Архитектура, дизайн системы | архитектура, микросервис, schema, DDD | `backend-architect` | opus |
| Данные, парсинг, скрейпинг | парсинг, 2ГИС, скрейпинг, данные, CSV | `data-engineer` | opus |
| Платформы, SDK интеграция | Yandex Games, Telegram Mini App, CrazyGames | `fullstack-developer` | opus |
| Финансы, unit economics | ARPDAU, LTV, CAC, revenue, конверсия | `quant-analyst` | opus |

## Правила запуска

1. **1 задача** → 1 агент нужного типа
2. **2-3 задачи** → последовательно или параллельно (по зависимостям)
3. **4+ задач** → АВТОМАТИЧЕСКИЙ SWARM (параллельные агенты)
4. **Неясный тип** → `general-purpose` агент
5. **Кросс-тип** (баланс + тесты) → 2 агента разных типов

## Контекст для агентов (передавать ВСЕГДА)

Каждый агент получает в промпте:
- Путь к файлам проекта
- Текущий стек (из CLAUDE.md проекта)
- Что именно сделать (конкретная задача, не "посмотри")
- Формат результата (файл, отчёт, код)

## Пример

Задача: "100 тестов матмодели Card Duel"
→ Тип: тесты + баланс
→ Агенты: 7x `test-automator` (по категориям), каждый получает формулы из audit-report
→ Результат: `tests/test_damage.py`, `tests/test_haste.py`, ...
