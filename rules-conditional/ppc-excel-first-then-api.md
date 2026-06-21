---
name: ppc-excel-first-then-api
paths:
  - '**/ppc/**'
  - '**/ads/**'
  - '**/*direct*'
  - '**/*ppc*'
---

# PPC: сначала Excel/файлы → потом API (детерминированный порядок, token-diet)

> **Установлено:** 2026-06-21 (Антон). «Сначала с Excel отработать, потом JSON дёргать — чтобы не тратить много. Зафиксировать как workflow, детерминированно.»
> **Доказательство:** ОДИН дамп Ads из Я.Директ API = 522 KB ≈ 130K токенов в одном ответе, висит в контексте, переотправляется каждый turn = главный пожиратель токенов на PPC.
> **Связано:** `determinism-first-and-verify`, `ppc-show-as-ad-previews`, `cost-aware-alternatives-first`, `numbers-deterministic-meaning-llm`, `ppc-upload-always-off`, `TOKEN-DIET-FINDINGS.md`.

## Детерминированный порядок (HARD — не нарушать ради скорости)
**ФАЗА 1 — EXCEL/ФАЙЛЫ (БЕЗ API Яндекса).**
- Проверка настройки, заполнение шаблона, сверка по справке Директа (лимиты символов, группировка) — всё на уровне Excel-выгрузок (Commander export / master xlsx), НЕ дёргая API.
- Семантика, тексты, гео, структура РК — в файлах.
- Источник истины фазы 1 = Excel-файлы клиента (`clients/<slug>/ppc/*.xlsx`, commander-export), не API.

**ГЕЙТ — показать Антону → CONFIRM.**
- Заполненный шаблон/проверку показать Антону (deploy-URL). Только после явного одобрения → Фаза 2.

**ФАЗА 2 — API/JSON (ТОЛЬКО заливка + verify).**
- API Я.Директа дёргать ТОЛЬКО на финал: заливка кампаний (всегда OFF — `ppc-upload-always-off`) + cabinet-verify.
- ПРАВИЛА API чтобы не жечь:
  1. Ответ API → в ФАЙЛ (`clients/<slug>/ppc/data/*.json`), в чат — только СВОДКА (N РК/ключей/объявлений + статусы). НЕ печатать полный JSON в tool-результат.
  2. `FieldNames` минимум: `["Id","State","CampaignId"]`, не весь объект.
  3. `jq`-фильтр на клиенте: `jq '.result.Ads[]|{Id,State}'` — точечно, не весь дамп.
  4. cabinet-verify → summary («✅ 8 РК OFF, 0 тратящих»), дамп в файл.
  5. Читать файл точечно (grep/jq по полю), не держать весь JSON в контексте.

## Антипаттерны (то, что жгло)
- ❌ Дёргать GetCampaigns/GetAds/keywordbids на каждый чих в фазе исследования/заполнения (Фаза 1).
- ❌ Печатать полный JSON-ответ Я.Директа в чат (522KB-дамп = ~130K токенов, оседает в контексте).
- ❌ Запрашивать все поля объекта вместо FieldNames-минимума.
- ❌ Перейти к API (Фаза 2) до прохождения Excel-фазы и одобрения Антона.

## Кандидат-workflow (TBD, по запросу Антона — детерминированный скелет)
`.claude/workflows/ppc-setup.js`: phase('Excel-проверка') → phase('Заполнение шаблона') → gate(CONFIRM Антона) → phase('Заливка OFF') → phase('cabinet-verify summary'). Каждая фаза = свой шаг, API только в последних двух. Собрать в свежей сессии + `node --check` (determinism-first verify-гейт).

## Кандидат-хук (TBD, approve — blast-radius)
`pre-bash-ppc-api-gate.sh` (PreToolUse Bash): если вызов Я.Директ API (GetCampaigns/GetAds/keywordbids) И в сессии нет маркера прохождения Excel-фазы + CONFIRM → warn «PPC: сначала Excel-фаза + одобрение». Bypass `PPC_API_OK=1`. Не регистрировать без approve + тест.

## Sync
`~/.claude/rules-conditional/` → грузится только в PPC-папках (token-diet, не жрёт контекст вне PPC).
