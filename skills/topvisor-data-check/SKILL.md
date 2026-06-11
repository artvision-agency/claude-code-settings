---
name: topvisor-data-check
description: Проверка какие данные реально есть в Topvisor-проекте ПЕРЕД тем как писать «Pending позиции» или гадать. Бесплатное чтение — настроены ли регионы (searchers), есть ли история съёмов, сколько ключей. Не запускает платный съём. Триггеры — topvisor data check, проверь топвизор проект, есть ли позиции в топвизоре, topvisor-data-check, что есть в топвизоре, история позиций топвизор, searchers топвизор.
---

# Topvisor data-check (бесплатное чтение)

> Чтобы не врать «Pending позиции» не проверив, и не запускать зря платный съём. Детали API — `~/.claude/rules/topvisor-ops.md`.

## Вызов
`/topvisor-data-check <project_id>` (или slug → найти project_id в config/handover)

## Что проверяет (всё БЕСПЛАТНО, без съёма)
1. **Регионы настроены?** `get/projects_2/projects {show_searchers:1, filters:[id IN [pid]]}` → `searchers=НЕТ` значит позиции НИКОГДА не снимались (новый клиент). Есть → шаг 2.
2. **История съёмов:** `get/positions_2/history {project_id, regions_indexes:[...], count_dates:31}` (count_dates max 31, regions_indexes ОБЯЗАТЕЛЕН). Вернёт даты → данные есть, тянуть.
3. **Ядро:** `get/keywords_2/keywords {limit:10000, fields:[id,name]}` → сколько ключей, по группам.

## Вердикт (что писать в §3 аудита)
- searchers=НЕТ → «Позиции не настроены — новый клиент, съёмов не было. Настройка региона через UI + платный съём (с ОК Антона)».
- searchers есть + история есть → тянуть реальные позиции (бесплатно), §3 заполнить.
- searchers есть, истории нет → «настроено, но не снято — запустить съём (платно, ОК)».

## НЕ делать
- ❌ Писать «Pending» не вызвав этот check.
- ❌ Запускать платный съём (`checker/go`) без явного ОК Антона — broadcast-фильтр сжёг 100₽ дважды (`topvisor-ops.md` + hook `pre-bash-topvisor-guard.sh`).
