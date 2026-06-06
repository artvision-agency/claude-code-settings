# Реестр покрытия задач инструкциями (rule/skill/SOP)

> Установлено: 2026-05-30 (Антон: «по каким задачам нет инструкций — пропишем, для всех проектов, чтобы я знал что ты/сеньоры поступаете как я думаю»).
> Цель: у КАЖДОГО повторяющегося типа задач есть документированная инструкция → предсказуемость.
> ⚠️ Статусы GAP — КАНДИДАТЫ (проверить grep по rules/+skills/+memory ПЕРЕД тем как писать — правило no-false-negative). Полный аудит — чистая сессия.
> Связано: project-work-plan-template, resume-read-project-state, agent-roster, parallel-skill-groups, deploy-report-template.

## Метод аудита (как заполнять, в чистой сессии)
1. Для каждого task-type: grep по `~/.claude/rules/` + `artvision-data/.claude/rules/` + `~/.claude/skills/*/SKILL.md` + `memory/`.
2. Найдено → статус ✅ COVERED (указать файл). Частично → 🟡 PARTIAL. Не найдено нигде → ❌ GAP (написать инструкцию).
3. Чем закрывать GAP: повторяющийся процесс с шагами → **skill**; принцип/запрет/стандарт → **rule**; чеклист операции → **SOP в rule**.

## Реестр (v1, 2026-05-30 — статусы проверить)

### Клиентские документы
- КП/presale — ✅ presale-kp + kp-brand
- Страница/лендинг — ✅ page-review + html-clients
- SEO-аудит — ✅ seo-master/seo-audit + factcheck
- Договор/акт/НДА — ✅ legal-docs + doc-manager
- **Месячный отчёт клиенту** — ❌ GAP? (есть клиенты на ретейнере OTIDO/Творим — стандартного шаблона отчёта не вижу) → проверить, вероятно нужен skill `/client-monthly-report`
- Презентация/слайды — 🟡 meeting-prep (проверить покрытие)

### SEO
- Семантика/кластеризация — ✅ tfidf-clustering + seo-cluster
- Контент/ТЗ — ✅ content-writer
- Линкбилдинг — ✅ linkbuilding + pbn-domains
- Парасайтинг — ✅ parasitic-seo
- Локальное/NAP/каталоги — 🟡 local-seo + asana NAP-правило (проверить полноту SOP регистрации)
- Миграция домена — ✅ seo-domain-diff
- Позиции/Topvisor — ✅ topvisor-init

### PPC / реклама
- Стратегия PPC — ✅ paid-ads
- Ретаргетинг — ✅ retargeting-setup
- Креативы РСЯ — ✅ ad-creative + yandex-direct-creatives + banner-stretch
- Завод в eLama (агентский) — ✅ elama-onboard (NEW 30.05)
- CRM→Я.Аудитории — ✅ crm-export-to-yandex-audiences (task #3, в работе)
- Аналитика кампаний — ✅ campaign-analytics
- **Перенос существующего кабинета Директа в eLama** — ❌ GAP (был у Madwave, не задокументирован) → SOP в elama-onboard или отдельный
- **Настройка Я.Метрики у клиента (цели/события/электронная коммерция)** — 🟡 analytics-tracking (проверить: есть ли SOP именно для клиента)

### ORM / репутация
- ORM-конвейер — ✅ orm-pulse
- **Сбор/заказ отзывов (биржи)** — 🟡 (qcomment/turbotext в memory, SOP?) → проверить

### Онбординг / доступы
- Новый клиент — ✅ new-client + client-init format
- **Запрос доступов у клиента (стандартный список+письмо)** — 🟡 (letters/ есть у USmile) → возможно skill `/access-request`
- **Приёмка/хранение доступов клиента** — 🟡 access.md + asset-capture (проверить SOP)

### Видео / контент-площадки
- Shorts/Reels — ✅ shorts-pip-composition
- Видеокружки клиенту — ✅ video-circles-pipeline
- Контент-план соцсети — ✅ smm-strategist + content-cadence

### Процесс / мета
- Handover — ✅ handover + resume-read-project-state (NEW)
- План работ проекта + визуал — ✅ project-work-plan-template (NEW)
- Recap — ✅ session.md
- Фактчек перед deploy — ✅ factcheck + deploy-report-template
- Параллельный рой/скиллы — ✅ parallel-task-orchestration + parallel-skill-groups
- Выбор агента — ✅ agent-roster

### Финансы / биллинг
- Сбор фин.данных — ✅ finance-data-collection
- Счета/проливы — ✅ finance-ops
- **Recurring биллинг клиента (ежемесячный счёт+акт)** — ❌ GAP? → проверить (billing_reminder.py есть, но SOP?)

### Жизненный цикл клиента
- **Реактивация ушедшего клиента** — ❌ GAP (Atribeaute/VLPco/Divinapp в реактивации, единого SOP нет) → skill/rule
- **Кризис/инцидент на сайте клиента (упал/взлом/выпал из индекса)** — ❌ GAP → SOP
- **Передача проекта другому исполнителю команды** — ❌ GAP? → проверить

## Топ-кандидаты GAP для написания (приоритет, после grep-проверки)
1. Месячный отчёт клиенту (ретейнер) — высокий (касается всех платящих)
2. Реактивация ушедшего клиента — высокий (3 клиента в реактивации)
3. Запрос/приёмка доступов (стандартное письмо+чеклист) — средний
4. Перенос кабинета Директа в eLama — средний (для eLama-клиентов)
5. Кризис на сайте клиента — средний
6. Recurring биллинг (счёт+акт ежемесячно) — средний

## Антипаттерны
- ❌ Заявить «нет инструкции по X» без grep по 4 источникам (rules×2 + skills + memory) — ложный пробел
- ❌ Писать дубль-инструкцию когда уже есть (find/grep перед созданием)
- ❌ Оставить GAP без владельца/срока — каждый подтверждённый GAP → задача
