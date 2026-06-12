---
name: workflows-map
description: Инвентарь всех named workflows (.claude/workflows/*.js) + детект broken-роутинга combine (corridor → несуществующий .js) + workflow без сопроводительного правила + дубли. Ловит рассинхрон при росте до 20+ воркфлоу. Внутренний ч/б табличный формат. Триггеры — карта воркфлоу, инвентарь workflows, workflows map, проверь роутинг combine, broken corridor, аудит воркфлоу, рассинхрон combine, сверка коридоров.
---

# workflows-map — карта named workflows + сверка роутинга combine

> Захвачено из работы Fable 5 (сессия 3017d7eb, workflows-mapper поймал broken corridor combine) · упаковано Opus 4.8 2026-06-12 · `capture-wins-as-skills`.
> Связано: `internal-docs-plain-tables.md` (формат — ч/б таблицы), `orchestration-method-selection.md`, combine.js (CORRIDOR_MAP), `/weekly-check` (фаза).

## Когда применять
- Периодически (фаза `/weekly-check`) — при 20+ workflows копятся дубли/broken-роутинг/gap-доки.
- После добавления/удаления named workflow — сверить, что combine.js CORRIDOR_MAP не указывает на несуществующий `.js`.
- Триггеры выше. Прецедент: combine `linkbuilding`/`local-seo` → несуществующие .js → EXEC throw (исправлено 2026-06-12).

## Что делает (детерминированно)
1. **Инвентарь** `~/artvision-data/.claude/workflows/*.js` — таблица [workflow · meta.name · meta.description · есть ли rule-док].
2. **Сверка CORRIDOR_MAP combine.js ↔ файлы** — каждый `corridor:'X'` → существует ли `X.js`? (`manual` = спец, без файла). Несуществующий → 🔴 BROKEN (EXEC throw при боевом прогоне).
3. **Gap-доки** — workflow без упоминания в правилах (`grep <name> ~/.claude/rules ~/artvision-data/.claude/rules`).
4. Вывод — ч/б таблица (правило internal-docs-plain-tables: без графики/бренда — это внутренний документ).

## Скрипт
`audit_workflows.py` — инвентарь + сверка CORRIDOR_MAP↔файлы + broken-флаги. Запускать в weekly-check. Exit≠0 если есть broken corridor (для CI/алёрта).

## Антипаттерны
- ❌ Добавить corridor в combine.js без создания `<corridor>.js` (EXEC throw) — этот скилл ловит.
- ❌ Оформлять карту в клиентском бренд-дизайне (это внутренний документ — ч/б таблицы).
- ❌ Удалить workflow, не сняв его из CORRIDOR_MAP combine.
