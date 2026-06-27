# Handover: service-proof генераторы (0 токенов) — 3 готовы, остаток свежей сессией

**Дата:** 2026-06-27 22:00 · **Контекст:** ops/infra · **Сессия:** d4f3bc14 · **Статус:** Блок 2 на 3/4, Блок 1 не начат

> Читать ПЕРВЫМ: docs/automation-monthly-report-trigger-spec.md (ДЕДУП + СЦЕНАРИЙ Codex).
> Процесс (Антон): Codex ревьюит → согласие → реализую → Codex проверяет → круг до DoD. Агент Codex: codex:codex-rescue.

## ГОТОВО (закоммичено + запушено, скиллы на всех аккаунтах)
| Генератор | Скилл | Статус | Тесты |
|-----------|-------|--------|-------|
| Topvisor позиции | /topvisor-positions | ✅ | smoke |
| Wordstat частотность | /wordstat-block | ✅ Codex-approved v1 | 5/5 |
| PageSpeed скорость | /pagespeed-block | ✅ Codex-approved v1 | 8/8 |
- Все: PNG/native HTML + idempotent `--embed` по маркерам, raw-кэш clients/<slug>/proof/, бренд Artvision (kp-brand), числа из API, честные подписи.
- topvisor встроен в /client-report (шаг 2b).
- Скрипты: scripts/{topvisor_positions_shot,wordstat_proof_block,pagespeed_proof_block}.py + scripts/tests/test_*.py.

## ОСТАЛОСЬ (свежая сессия, тем же Codex-циклом)
1. **SERP-конкуренты генератор** (Блок 2, 4-й) — по образцу wordstat/pagespeed. Источник: Cloud Search SERP (есть в нашем стеке) — кто в ТОП-10 по ключам vs клиент. Изолированный, безопасный.
2. **Блок 1 — расширить client_scheduler** (НЕ новый файл!): action_generate_report со старого plan_fact_report.py на новый /client-report пайплайн. ⚠️ ЖИВОЙ scheduler (invoice/payment/overdue ежедневно, LaunchAgent ops-unified-check). Codex-порядок: СНАЧАЛА тесты фиксируют текущее поведение (scripts/tests/test_client_scheduler.py), ПОТОМ backward-compat правка (report_type: client_report; helper scripts/ppc/run-client-report-pipeline.py; пер-шаговые таймауты; --force --action report сейчас→report_reminder, учесть). Поля в schedule/reports-invoices.json (report_day, report_type, direct_login, site, review_deploy_path, hardcheck_url, positions_anchor, topvisor_client, notify.report_ready, enabled). LaunchAgent НЕ трогать.

## ГАЧИ
- PageSpeed: анонимный PSI = 429 (диагностика). Live КП нужен env PSI_API_KEY (Google Cloud, бесплатный tier) — ИНФРА-задача добыть ключ. Без данных → exit 2.
- Wordstat: блок = «связанный спрос по теме» (SearchedWith+SearchedAlso), не сид-частотность — честно подписано + footnote. --login для детерминизма при мультилогине.
- Блок 1 — самое опасное: НЕ делать на деградации контекста (>50%). Тесты ПЕРВЫМИ.
- Codex иногда добавляет ложный session-footer (competitor pricing / SEO planning) — игнорировать, это его read-only sandbox.

## Связанные
- Спека: docs/automation-monthly-report-trigger-spec.md
- Скиллы: /client-report, /topvisor-positions, /wordstat-block, /pagespeed-block
- Правила: project-tasks-single-source #7, offload-to-script-on-high-spend, enforcement-primitives, codex-dev-lifecycle, testing.md
- Предыдущие handover: HANDOVER-2026-06-27-2030-report-automation.md, clients/ds-lab/handover/HANDOVER-2026-06-27-1600-*.md
