# Handover: автоматизация месячных отчётов (0 токенов) — ПРОДОЛЖИТЬ свежей сессией

**Дата:** 2026-06-27 20:30 · **Контекст:** ops/infra · **Сессия:** d4f3bc14 · **Статус:** дизайн готов, реализация next

## Цель
Свести построение месячных отчётов клиентам + доказательных блоков к ~0 токенов + правильная активация (cron). Общее для ВСЕХ клиентов.

## Что уже сделано (эта сессия)
- Скрипт `scripts/topvisor_positions_shot.py`: PNG + native HTML + idempotent `--embed` (маркеры TVP-POSITIONS). 0 токенов, числа из API, даты замера+сравнения.
- Скилл `/topvisor-positions` создан + зарегистрирован.
- Встроен шаг 2b в скилл `/client-report` (блок позиций в SEO-раздел, `--anchor '<!--SEO-POSITIONS-->'`). Smoke-тест idempotent PASS.
- Спека: `docs/automation-monthly-report-trigger-spec.md` (ЧИТАТЬ ПЕРВЫМ).

## Следующие шаги (по спеке, свежая сессия — НЕ Dumb Zone)
1. **Блок 2** каркас service-proof генератора (1 шаблон: Wordstat частотность ИЛИ PageSpeed) — копия паттерна topvisor_positions_shot, низкий риск.
2. **Блок 1** `scripts/monthly-report-scheduler.py` + тесты `--dry-run`/`--simulate-date` (3 кейса: месяц-старт строит / не тот день молчит / уже построено skip). БЕЗ регистрации LaunchAgent.
3. **LaunchAgent** `pro.artvision.monthly-report-scheduler` — только после 3/3 тестов + approve Антона (харнес 3 аккаунта).
4. Блок 3 (шаблон отчёта на маркерах) — по мере.

## Гачи
- Дата месяц-старта — из договора (`ops-contract-dates.yaml`/CONTRACT-DELIVERABLES), НЕ из головы. USmile=10-е.
- Авто-отправка клиенту ЗАПРЕЩЕНА (CONFIRM — человек). Авто-оплата снятия позиций ЗАПРЕЩЕНА.
- Суммы счёта НЕ в отчёт (finance-gate). Расход Директа БЕЗ НДС.
- cron не наследует shell env — тестировать `env -i`.
- Эталон отчёта: usmile-otchet (artvision.pro/usmile-otchet/).

## Связанные
- Спека: `docs/automation-monthly-report-trigger-spec.md`
- Скиллы: `/client-report`, `/topvisor-positions`
- Правила: project-tasks-single-source #7, offload-to-script-on-high-spend, enforcement-primitives, testing.md
- Предыдущий handover (ds-lab КП): clients/ds-lab/handover/HANDOVER-2026-06-27-1600-topvisor-shots-migration.md
