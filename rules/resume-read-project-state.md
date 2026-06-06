# Resume клиента/проекта — читать ПАМЯТЬ проекта, не только handover

> **Установлено:** 2026-05-29 (Антон, сессия USmile ecb60472).
> **Прецедент:** на ресюме USmile прочитал только последний handover (тред вывески) → «не видел контекст» → начал дублировать уже сделанное (180 файлов проекта, офлайн/билборды/биржи давно проработаны). Антон: «почему ты не видишь контекста и всех документов по проекту?»
> **Связано:** `session.md`, `clients-pretask.md` (project), `kp-brand.md` Pre-Task, skill `handover`, `self-corrections.md`.

## Корень проблемы

**Handover однопоточный по дизайну** — каждая сессия пишет про СВОЙ тред. Цепочка handover'ов тонкая, ни один не содержит ВСЕГО проекта. Resume-хук показывает последний handover → легко принять его за «полный контекст». Это ошибка.

**Полнота состояния проекта — НЕ в handover, а в канонических файлах:**
- `clients/<slug>/context-log.md` — append-only лог ВСЕХ сессий (главный источник правды)
- `clients/<slug>/STATUS.md` — текущее состояние (если есть)
- `clients/<slug>/plan/task-plan*.md` или `plan/*PLAN*.md` — persistent план с чеклистами
- `clients/<slug>/WAITING-FROM-CLIENT.md` — что ждём от клиента (если есть)

## Правило (HARD)

Перед ЛЮБОЙ работой по клиенту/проекту после ресюме/clear/нового handover — **прочитать в порядке**:
1. `context-log.md` (весь лог сессий)
2. `STATUS.md` (если есть)
3. `plan/task-plan*.md` / `plan/*PLAN*.md` (если есть)
4. `WAITING-FROM-CLIENT.md` (если есть)
5. Только ПОТОМ — handover (он указатель на эти файлы, не замена).

**Перед созданием нового файла/документа** — `find clients/<slug> -name '*<тема>*'` + grep по теме. Если по теме уже есть файл — ДОПОЛНЯТЬ его, не плодить дубль.

## Handover-шаблон обязан содержать
В шапке handover — строка: **«Полное состояние → context-log.md + STATUS.md + task-plan.md (читать ПЕРВЫМ)»**. Handover синтезирует тред + ПОЧЕМУ + next steps, но НЕ претендует на полноту проекта.

## Антипаттерны
- ❌ Принять последний handover за полный контекст проекта
- ❌ Начать работу по клиенту не открыв context-log.md
- ❌ Создать новый файл-документ не проверив `find`/grep на существующий (дубль)
- ❌ «STATUS.md/task-plan нет → создам новый план» без проверки что плана реально нет

## Кандидат-хук (TBD, ждёт approve — меняет харнес)
`resume-project-state-reminder.sh` (SessionStart source=resume/clear ИЛИ UserPromptSubmit при первом упоминании клиента) — если cwd/prompt указывает на `clients/<slug>/` и в transcript нет Read для `context-log.md` → инжект напоминания «прочитай context-log+STATUS перед работой». Bypass `PROJECT_STATE_OK=1`.

## Прецедент
- **2026-05-29 USmile:** дубль `offline-ads-master.md` создан поверх существующих `MASTER-offline-placement.md` + `billboards-inventory-full.md` (30КБ). Удалён. Причина — не прочитал context-log + не сделал find по теме. Правило установлено.
