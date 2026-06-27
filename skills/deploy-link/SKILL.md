---
name: deploy-link
description: Найти deploy-URL артефакта клиента (КП/калькулятор/анализ/дашборд/отчёт/матрица) по реестрам DEPLOY-LINKS.md — выдаёт живую ссылку первой строкой с проверкой HTTP 200, без ручного grep. Триггеры — 'дай ссылку на', 'где ссылка', 'найди ссылку', 'deploy-link', 'ссылка на калькулятор', 'ссылка на кп', 'ссылка на дашборд', 'ссылка на матрицу', 'где лежит <артефакт>'.
---

# deploy-link — быстрый поиск deploy-ссылки артефакта клиента

Правило: `~/.claude/rules/client-deliverables-registry.md`. Источник — `clients/<slug>/DEPLOY-LINKS.md`.

## Запуск
```bash
~/.claude/scripts/find-deploy-link.sh <slug> [тема]    # в реестре клиента
~/.claude/scripts/find-deploy-link.sh --all <тема>     # по всем клиентам
~/.claude/scripts/find-deploy-link.sh <тема>           # slug не папка → по всем
```

## Что делает
1. Грепает `DEPLOY-LINKS.md` (клиента или всех) по теме.
2. Достаёт `https://artvision.pro/...` ссылки + подпись артефакта.
3. Проверяет HTTP 200 на каждую (✅/⚠️код).
4. Выводит URL **первой строкой** (правило `feedback_deploy_url_first`), ниже — список с метками.

## Когда применять
На запрос «дай/найди/где ссылку на <КП/калькулятор/анализ/дашборд/отчёт/матрица> по <клиент>» — вызвать вместо ручного поиска. Если артефакта нет в реестре — найти (grep по `clients/<slug>/` + git) → curl 200 → **дописать в `DEPLOY-LINKS.md`** (капитализация, чтобы дальше находилось мгновенно).

## Пример
```
$ find-deploy-link.sh tvorim-sovershenstvo калькул
https://artvision.pro/kp/dental-calculator/
  ✅ [tvorim-sovershenstvo] Калькулятор стоимости стоматологических услуг — ...
  ✅ [tvorim-sovershenstvo] Анализ цен соседних клиник (матрица-калькулятор) — ...
```
