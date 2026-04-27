# Handover: Artvision Ads Stack — рисёрч + форк PPC-инструментов

**Дата:** 2026-04-27 21:30
**Контекст:** products
**Сессия:** 1ddd65f4-8e15-4853-a5cf-cf4923f95f57 (без имени)
**Статус:** в работе (рисёрч+форки сделаны, smoke-test впереди)

## 🎯 Цель сессии

Найти senior AI-агентов по контекстной рекламе (Я.Директ / Google Ads / VK Ads) + GitHub-репо для форка под Artvision. Цель — занять опенсорс-нишу VK Ads (пустая) + усилить Direkt-Radar + recurring revenue через PPC-абонентки.

## ✅ Что сделано

- **Рисёрч 4 параллельных агента (~18 мин):** sub-agents.directory + GitHub Yandex / Google / VK / multi-platform
- **Финальный отчёт + топ-3 для форка** — выдан в чате (есть в transcript)
- **Форки на GitHub `justtrance-web` + локальный клон в `~/artvision-forks/`:**
  - `Silverov/yandex-direct-skill` (12★, MIT, Shell) — Claude Code Skill, 55 проверок Я.Директ, A-F grading, RU benchmarks
  - `SvechaPVL/yandex-mcp` (14★, MIT, Python) — MCP-сервер с 128 tools (Direct 80 + Metrika 43 + Wordstat 5)
  - `AgriciDaniel/claude-ads` (3548★, MIT, Python) — 7 ad-платформ × 250+ checks, parallel agents, AI creatives, PDF
- **TODO добавлен:** `~/artvision-data/products/TODO.md` секция **"Artvision Ads Stack"** с 10 follow-up задачами (3 done × форки + 7 doing)
- **Recap заполнен:** `~/artvision-data/sync/recaps/1ddd65f4-...md`
- **Commit:** `feat(products): Artvision Ads Stack — 3 фокс PPC-инструментов` (aa1f75d7e на ветке `feat/ops-crm-v1`)

## 🧠 Решения и ПОЧЕМУ

| Решение | Альтернатива | Почему |
|---------|--------------|--------|
| Форкнуть Silverov yandex-direct-skill (12★) — основной кандидат | tapi-yandex-direct (62★ Python) | Tapi мёртв с 2022. Silverov активный (Feb 2026), MIT, и архитектурно совпадает со стеком `~/.claude/skills/` |
| Взять SvechaPVL yandex-mcp как комплемент к skill | yandex-direct-for-all (Codex plugin) | Codex plugin привязан к ChatGPT-Codex, а MCP — нативный для Claude Code. 128 tools против фрагментарного покрытия |
| Форкнуть claude-ads (3.5K★) даже без поддержки Yandex/VK | Не брать — мы Я.Директ | Архитектура parallel agents + 250+ checks = donor-паттерн для расширения Silverov на Я.Директ. Плюс as-is для глобал-клиентов |
| Локация форков `~/artvision-forks/` (вне artvision-data) | `~/artvision-data/forks/` (внутри репо) | Чтобы не было submodule-конфликтов: nested git внутри git вызывает путаницу |
| VK Ads — писать с нуля, не форкать | Форкать `python273/vk_api` (1367★, общий VK API) | Опенсорса по VK Ads нет (последний живой 2018). Чистый рынок → шанс стать первым стандартом РУ |
| Не форкать `cohnen/mcp-google-ads` (570★) | Форкать как 4-й | Дублирует claude-ads функционал для Google. Подключим **as-is через `claude mcp add`** при необходимости |

## ❌ Что НЕ сделано

- **Smoke-test #2 (yandex-mcp) на реальном Я.Директ токене** — отложено: контекст 51% перед запуском, делаем в новой сессии
- **Изучение SKILL.md Silverov** — не открывал, в TODO с дедлайном 04.05
- **VK Ads Skill с нуля** — стратегическая задача, дедлайн 15.06
- **Решение про Telegram-канал AI-агентств** — Антон не упоминал, но есть в trends memory (можно отдельно вернуться)

## 📚 Уроки (новое знание)

- **Опенсорс PPC-инструментов сильно сегментирован по бюджету:** Google Ads — топ 3.5K★, Yandex — 62★, VK — пусто. Прямая корреляция с покупательной способностью рынка → возможность для РУ-игрока занять Я.Директ + VK
- **MCP vs Skill — комплементарны, не конкурируют:** Skill = аудит/стратегия/HTML-отчёт, MCP = операционка через Claude в чате. Связка обеих → полный PPC-цикл
- **Sub-agents.directory не покрывает marketing/ads** — там только dev-стек (React/Python/Postgres). Для PPC искать **только по GitHub topics**
- Сохранить в `feedback_ppc_opensource_landscape_2026.md`: записать карту репо + инсайт «VK ниша пустая»

## 🔜 Следующие шаги (приоритет)

0. **🎯 ТОП-ПРИОРИТЕТ — First real case: Грелка-Гуделка** (новая задача из этой же сессии, ровно после форков). Ресторан СПб, бюджет 70K (контекст+таргет), доступы Я.Директ + Метрика + VK уже в `clients/grelka-gudelka/access.md`, КП v1 отправлен, senior-review есть. Шаги:
   - Read `~/artvision-forks/yandex-direct-skill/SKILL.md` — понять формат API-токена и endpoints
   - Прописать `yandex.direct.grelka` в `~/artvision-data/tokens.json` (ключ + OAuth flow если нужно)
   - Запустить аудит через #1 → `clients/grelka-gudelka/presale/audit/direct-audit-2026-05-01.md`
   - `claude mcp add yandex-mcp ~/artvision-forks/yandex-mcp` + smoke-test
   - Усилить КП v2 через позиционирование **Artvision Direkt-Radar**
   - **NB:** claude-ads (Google/Meta) НЕ применимо — РФ-локалка, Google заблокирован для РФ-рекламодателей с 2022, Meta тоже. Только Я.Директ + VK Ads (последнее — руками или ждём Artvision VK Ads Skill 15.06)
   - **Дедлайн:** 2026-05-01

1. **HIGH (стартовать в новой сессии):** Smoke-test `~/artvision-forks/yandex-mcp` через `claude mcp add` на тестовом токене (предложение: OTIDO как у наш платящий клиент с Я.Директ РСЯ). Проверить: 128 tools работают? Какие auth-проблемы? Дедлайн 04.05
2. **HIGH:** Read `~/artvision-forks/yandex-direct-skill/SKILL.md` + написать gap-analysis (что покрывает / что нужно докрутить). Дедлайн 04.05
3. **HIGH:** Доработка #1 v1 — multi-account routing (skill переключается между токенами клиентов из tokens.json). Дедлайн 10.05
4. **MEDIUM:** Локализовать claude-ads → "Artvision Ads Audit" (правило `security.md`: убрать "AI/Claude" из публичных названий). Интегрировать в `presale-kp` skill. Дедлайн 17-24.05
5. **MEDIUM:** Стартовать **VK Ads Skill с нуля** по архитектуре Silverov+claude-ads. Дедлайн 15.06
6. **LOW:** Round-table проверка через `mcp__llm-consilium__round_table` стратегии форк vs build (правило `tool-adoption-proof.md`)

## 🗺️ Карта файлов

```
~/artvision-forks/                                        ← новая директория
├── yandex-direct-skill/   ← Silverov fork (Claude Skill)
├── yandex-mcp/            ← SvechaPVL fork (MCP 128 tools)
└── claude-ads/            ← AgriciDaniel fork (multi-platform)

~/artvision-data/
├── products/TODO.md       ← секция "Artvision Ads Stack" (новая, 10 задач)
└── sync/recaps/1ddd65f4-...md   ← recap этой сессии (заполнен)

GitHub: github.com/justtrance-web/{yandex-direct-skill, yandex-mcp, claude-ads}
```

## ⚠️ Гачи

- **Проверить tokens.json на Я.Директ** перед smoke-test — какие клиенты там есть? Артвижн ведёт несколько (`yandex.direct, 3 аккаунта` из rules/yandex-api.md). OTIDO упомянут в clients-registry как "SEO, Директ (РСЯ)" — но это не значит что у нас есть API-токен
- **`~/artvision-forks/` НЕ под git** — это просто рабочая локация. Доработки делать через PR в форки на github.com/justtrance-web/...
- **claude-ads в форке имеет dependabot ветки** (pillow, playwright, reportlab, requests) — игнорировать или мерджить через GH UI
- **Я.Директ для РФ-клиентов работает**, но Google Ads с марта 2022 заблокирован для РФ-рекламодателей. claude-ads — только для глобал-клиентов Artvision (релоканты, западные SaaS, B2B export)
- **Правило `security.md`:** в любых публичных описаниях продуктов **никаких "AI/Claude/нейросети"** — только "Авторская методология", "Аналитическая система"
- Пред-условие #1 доработки: сначала прочитать SKILL.md Silverov — не дублировать что у него уже есть

## 🔗 Связанные ресурсы

- **Recap сессии:** `~/artvision-data/sync/recaps/1ddd65f4-8e15-4853-a5cf-cf4923f95f57.md`
- **Commit:** `aa1f75d7e` на `feat/ops-crm-v1` (artvision-data)
- **GitHub forks:**
  - https://github.com/justtrance-web/yandex-direct-skill
  - https://github.com/justtrance-web/yandex-mcp
  - https://github.com/justtrance-web/claude-ads
- **Источники топ-3 (originals):**
  - https://github.com/Silverov/yandex-direct-skill
  - https://github.com/SvechaPVL/yandex-mcp
  - https://github.com/AgriciDaniel/claude-ads
- **Полный отчёт рисёрча:** в transcript этой сессии (4 task-notification result-блока: aa606eef..., a64756395..., a41d5d90b..., accb832dc...)
- **Связанный продукт:** Direkt-Radar (Artvision Scout) в `products/ROADMAP-2026-Q1.md` + секция в `products/TODO.md`
