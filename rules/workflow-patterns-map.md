# Workflow Patterns Map — 6 паттернов Dynamic Workflows → классы задач Артвижн

> **Установлено:** 2026-06-05 (Антон). Источник: Habr 1043002 «Dynamic Workflows in Claude Code» — Claude Opus сам пишет JS-обвязку, оркеструющую субагентов с изолированными контекстами. Решает 3 болезни одного контекста: агентская лень, self-bias при верификации, смещение цели после компакции.
> **Это СЛОВАРЬ паттернов + маршрут**, НЕ дубль. Реализация и лимиты — в связанных правилах:
> `orchestration-method-selection.md` (main vs Workflow vs рой vs Conductor — что когда, надёжность), `parallel-skill-groups.md` (overlap-скиллы по классам), `consilium-matrix.md` (cons/round_table/рой/codex/gemini), `parallel-task-orchestration.md` (рой сеньоров), `prompt-elaboration.md` (ось 4 — выбор паттерна).

## 6 паттернов (vocabulary)

| Паттерн | Суть | Наши классы задач | Чем делаем |
|---------|------|-------------------|------------|
| **1. Classify-and-act** | агент-классификатор → маршрут к разным агентам по типу | роутинг входящей задачи, `/combine` очередь, agent-roster, маршрутизация КП по типу проекта (kp-workflow-family) | main + agent-roster.md |
| **2. Fan-out-and-synthesize** | дробим на N шагов → агент на каждый (чистый контекст) → барьер-синтез | SEO-аудит по разделам §1-§6, КП по блокам, research по источникам, семантика по кластерам, ревью N файлов/лендингов | `Workflow` pipeline/parallel ИЛИ main по разделам |
| **3. Adversarial verification** | на каждый результат — отдельный верификатор по РУБРИКЕ, цель опровергнуть | factcheck чисел, strict-factchecker, quality-gate КП, проверка claim'ов аудита, code-review | `/factcheck`+strict, round_table, Workflow verify-стадия |
| **4. Generate-and-filter** | генерим набор → фильтр по рубрике → dedup → только лучшее проверенное | семантика/кластеры (generate→volume-gate→SERP-overlap), креативы РСЯ, идеи заголовков/УТП, доноры линкбилдинга | main + tfidf-clustering / ad-creative |
| **5. Tournament** | N агентов решают по-разному → судья попарно → победитель | варианты дизайна/нейминга, A/B-концепты КП, model-bakeoff (image/video/LLM), выбор стратегии | model-bakeoff.md, Workflow judge-панель |
| **6. Loop-until-done** | цикл до условия остановки (нет новых находок / нет ошибок), не фикс число | ORM-сбор отзывов, bug-hunt, аудит «до исчерпания», накопление до цели (10 находок) | `/loop` + Workflow loop-until-dry |

## Правила применения

1. **Выбор паттерна — ось 4 разворачивания** (`prompt-elaboration.md`). Сложная задача → назвать паттерн в строке `[РАЗВЁРТКА:...]`.
2. **Рубрика обязательна** для паттернов 3/4/5 (Habr). Без критериев верификатор/судья/фильтр слепой → мусор. Рубрику беру из канон-spec (_compliance-checklist, seo-audit-spec, severity-шкала).
3. **Бюджет явно** для тяжёлых (Habr: «используй 10k токенов»; наш лимит — 3-4 агента, antipatterns.md). Workflow поддерживает `budget` (turn-target).
4. **Метод оркестрации ≠ паттерн.** Паттерн = ЧТО (структура работы). Метод = ЧЕМ (main / `Workflow` tool / Agent-рой / Conductor-LITE). Выбор метода — `orchestration-method-selection.md`. ⚠️ **Субагенты падают 403/socket → main-процесс или Conductor-LITE**, паттерн остаётся тот же (fan-out делаю последовательно в main). Не долбить падающий рой.
5. **`ultracode` / `Workflow` tool** — только при явном opt-in Антона (keyword `ultracode`, «используй воркфлоу», «рой», именованный workflow). Иначе — main-процесс по паттерну. Workflow жжёт токены (десятки агентов) → не инферить без запроса.
6. **Combine с `/goal` + `/loop`** для повторяемых (триаж, research, верификация, мониторинг) — Habr.

## Связь с уже существующим (не дублировать)

- **Класс-маппинг скиллов** (SEO/factcheck/code-review/research/paid-ads, default-тройки, консолидация dedup) → `parallel-skill-groups.md`. Здесь — только паттерн-словарь поверх.
- **LLM-консилиум** (cons / round_table / codex / gemini — другие семейства моделей) → `consilium-matrix.md`. Это слой «другое мнение», паттерн 3 (adversarial) другим семейством.
- **Рой сеньоров + граф зависимостей** → `parallel-task-orchestration.md`.
- **Надёжность методов + Conductor-LITE** → `orchestration-method-selection.md`.

## Антипаттерны

- ❌ Паттерн 3/4/5 без рубрики (слепая верификация/фильтр/судья).
- ❌ Запускать `Workflow`/рой без opt-in Антона (десятки агентов, жжёт токены).
- ❌ Долбить падающий рой (403) вместо переключения на main по тому же паттерну.
- ❌ 5+ агентов «на всякий» (лимит 3-4, antipatterns).
- ❌ Дублировать сюда класс-маппинг из parallel-skill-groups — ссылаться.

## Sync
`~/.claude/rules/` (claude-code-settings → 3 аккаунта).
