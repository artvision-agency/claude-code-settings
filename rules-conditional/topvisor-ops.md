---
name: topvisor-ops
paths:
  - '**/seo/**'
  - '**/*topvisor*'
---

# Topvisor — операции (консолидированный ops-гайд)

> Свод всех операций Topvisor что гоняем постоянно + грабли (за которые платили). Один файл вместо разбросанных memory.
> **Связано (детали):** `memory/feedback_topvisor_api_v2_quirks.md`, `feedback_topvisor_filter_safety.md` (сжёг 100₽ ДВАЖДЫ), `feedback_topvisor_ui_required_for_region.md`. Скрипты: `scripts/topvisor_multiregion.py`, `topvisor_serp.py`, `topvisor_validate_clusters.py`. Skill: `/topvisor-init`.

## API base
`POST https://api.topvisor.com/v2/json/<path>` · headers `{Content-type: application/json, User-Id: <user_id>, Authorization: bearer <api_key>}` · креды `tokens.json → topvisor {user_id, api_key}`.

## Операции (рецепты)

| Операция | path | ключевое (грабли) |
|----------|------|-------------------|
| Создать проект | `add/projects_2/projects` | параметр **`url=`** (НЕ `site=`); result строкой |
| Список проектов | `get/projects_2/projects` | `{show_searchers:1}` → проверить настроены ли регионы |
| Добавить конкурентов | `add/projects_2/competitors` | `urls[]` (без on=1) |
| Группы ключей | `get/keywords_2/groups` | вернёт id групп («Остальные» / создать) |
| **Добавить ключ** | `add/keywords_2/keywords` | **`to_id`=group_id + `name`=один ключ** (НЕ `group_id`, НЕ массив `keywords`!). Один вызов = один ключ. **БЕСПЛАТНО** |
| Список ключей | `get/keywords_2/keywords` | `{limit:10000, fields:["id","name"]}` |
| Удалить ключ | `del/keywords_2/keywords` | по `id` (не name) |
| **История позиций** | `get/positions_2/history` | **`regions_indexes` ОБЯЗАТЕЛЕН**, `count_dates` **max 31**. ЧТЕНИЕ истории — **БЕСПЛАТНО**. searchers=НЕТ → позиции никогда не снимались |
| **Снять позиции** | `edit/positions_2/checker/go` | **ПЛАТНО** — только EQUALS [один project_id]. Опасные фильтры (всё-кроме-списка / regex-% / любой-EXISTS / диапазон / пустой / id=0) = broadcast по ВСЕМ проектам → сжёг 100₽ ДВАЖДЫ. Hook `pre-bash-topvisor-guard.sh` блокирует. Только с ОК Антона |

## Жёсткие правила
1. **Позиции (снятие) — ПЛАТНО + CONFIRM Антона.** Чтение истории — бесплатно. Перед «Pending позиции» — проверить `get/projects_2/projects show_searchers:1`: searchers=НЕТ → не настроено (новый клиент), есть → тянуть `history` (бесплатно).
2. **Регионы/searchers настраиваются через UI** (`topvisor.com/positions/?project_id=X`), API v2 `add searcher` не даёт. НО если в defaults аккаунта регионы есть — подхватываются (см. api_v2_quirks).
3. **add keyword = `to_id`+`name` по одному.** Это #1 грабля (терял время дважды за сессию).
4. **Broadcast-фильтр при снятии позиций = деньги.** Только EQUALS single PID. Hook стоит — не глушить.
5. Новый клиент → `/topvisor-init` (читает queries.txt+competitors.txt+config.yaml, заводит за раз).
