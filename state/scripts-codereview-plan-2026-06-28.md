# План: Codex код-ревью скриптов (сегодня, 38 файлов) → фикс → re-verify → durability

> Установлено 2026-06-28. Цель: Codex подтверждает корректность скриптов, написанных сегодня, фиксим находки, делаем так чтобы работало в будущем (verify-gate + тесты + регистрация). Идём ПОСТУПАТЕЛЬНО по фазам.

## Scope
38 скриптов, тронутых сегодня (выбор Антона: «сегодняшние 38»). Месяц (1449) отложен — слишком много шума.

## Фазы (поступательно)

- [ ] **Ф0. Ревью (идёт)** — 4 Codex-агента параллельно:
  - Батч1 инфра (.claude/scripts + artvision-data/scripts root + tests) — agent ac7ab04a1dd58db15
  - Батч2 usmile+deploy — agent a109085041a8fb617
  - Батч3 ppc/manual_strategy — agent a647113cbdbbc974c
  - + ревью kislovodsk-safety-digest.py (отдельный Codex, раунд 1) — agent abbcea0f2213fa28b
- [ ] **Ф1. Консолидация** (task #2) — единый severity-список, dedup, приоритет (прод-деплой/секреты/числа наверх).
- [ ] **Ф2. Починка P0/P1** (task #3) — переписать код по находкам. Делать в ЧИСТОМ контексте (compact/handover — сейчас Dumb Zone).
- [ ] **Ф3. Codex re-verify** (task #4) — повторная проверка изменённых файлов, вердикт.
- [ ] **Ф4. Durability** (task #5) — py_compile/bash -n гейты, мини-тесты критичных, регистрация в реестре, краткая дока.

## Особые риск-точки
- deploy_docyurov_landing.sh, run-seo-pipeline.sh — прод-деплой (бэкап? подтверждение? идемпотентность?)
- build_money_prices.py, metrika_direct_expenses.py, service_value_model.py, clinic_pricing.py, direct_auction_bid_coverage.py — деньги/числа (детерминированно кодом?)
- collect_* (Wordstat/Директ/Метрика/Вебмастер) — токены не хардкод, обработка ошибок API
- kislovodsk-safety-digest.py — токен из tokens.json, shell-инъекция в TG-текст
- Найдено: portal_bot мёртв (401) — чинить токен отдельно (затрагивает всю TG-инфру).

## Связанные правила
script-tool-lifecycle, determinism-first-and-verify, numbers-deterministic-meaning-llm, codex-dev-lifecycle, finisher-loop.
