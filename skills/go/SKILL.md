---
name: go
description: Утреннее интервью-меню для Антона. Показывает goal-dashboard клиентов (BluMart/Творим/Madwave и др., у кого есть goals.yaml), топ-5 просроченных висяков из qa-watchdog + 5 overdue из TODO. После — меню 3 действий (a) дожимаем висяки / (b) запускаем /combine на overdue / (c) новая задача через интервью. Триггеры — '/go', 'утро', 'старт сессии', 'утреннее меню'. ВНИМАНИЕ — НЕ путать с «го/go» (короткое подтверждение «делай» → /combine). Используется автоматически из bootstrap-LaunchAgent при login Mac (через 60 сек после открытия iTerm).
user-invocable: true
---

# /go — утренний дашборд + интервью-меню

Задача скилла: за 30 секунд показать Антону полную картину утра — **цели клиентов с pace-контролем + проактивные вопросы по висякам**, и сразу дать выбор куда идти.

## Что выводит (3 блока + меню)

### Блок 1 — Goals dashboard (клиентские цели с измеримым темпом)

```bash
python3 ~/artvision-data/scripts/goals-progress.py
```

Показывает строки вида:
```
🔴 blumart: ORM публикации Q2 2026 (март-май)
  Факт 46 / план pro-rata 124 / цель 165 к дедлайну (18 дн)
  Темп 0.62/день · нужно 6.61/день · gap -78
  На модерации: 24 (могут добавиться)
  ⚠️  qcomment_budget: пополнить qcomment до 500+
```

Источник цифр: `clients/*/goals.yaml`. Если у клиента нет goals.yaml — он не в дашборде (норма для presale-клиентов).

### Блок 2 — qc-questions (висяки от qa-watchdog)

```bash
python3 ~/artvision-data/scripts/qa-watchdog.py
```

Выводит топ-5 просроченных задач и незакрытых acceptance из recaps. Для каждой — короткий вопрос «дожимаем / откладываем / закрываем?»

### Блок 3 — Overdue из TODO (только если qa-watchdog их не подсветил)

```bash
grep -rE "\[due:\d{4}-\d{2}-\d{2}\]" ~/artvision-data/TODO.md ~/artvision-data/presale/TODO.md ~/artvision-data/products/TODO.md 2>/dev/null \
  | python3 -c "import sys, re; from datetime import date; t=date.today(); rows=[]; [rows.append((m.group(1), l.strip())) for l in sys.stdin for m in [re.search(r'\[due:(\d{4}-\d{2}-\d{2})\]', l)] if m and date.fromisoformat(m.group(1)) < t]; rows.sort(key=lambda x: x[0]); [print(f'  {r[0]} → {r[1][:130]}') for r in rows[:5]]"
```

### Меню (3 действия)

```
═══════════════════════════════════════════
  Что делаем?

  a) ДОЖИМАЕМ ВИСЯКИ — интерактивно по каждому из топ-5 qc-questions
  b) КОМБАЙН OVERDUE — /combine для просроченных задач
  c) НОВАЯ ЗАДАЧА — интервью

  Цифра/буква, или текст задачи
═══════════════════════════════════════════
```

## Логика обработки выбора

- **`a` / «дожимаем»** — пройтись по qc-questions.jsonl топ-5, для каждой спросить короткий ответ (one-liner). Закрывать/обновлять в TODO/Asana по ответу.
- **`b` / «комбайн»** — вызвать Skill combine (с приоритетом overdue first)
- **`c` / «новая задача» / любой текст** — запустить интервью по `~/.claude/rules/session.md` (уточнить для кого, результат, срочность → разбить на atomic → в очередь)

## Когда вызывается автоматически

LaunchAgent `pro.artvision.bootstrap` при login Mac открывает iTerm → `cd ~/artvision-data && claude` → через 60 сек автопечать `/go` (если Антон не отменил Ctrl+C).

## Связанные файлы

- `~/artvision-data/scripts/goals-progress.py` — pace calculator
- `~/artvision-data/scripts/qa-watchdog.py` — сканер висяков
- `~/artvision-data/clients/<slug>/goals.yaml` — определение целей клиента
- `~/artvision-data/sync/goals-status.json` — JSON-output для других скриптов
- `~/artvision-data/sync/qc-questions.jsonl` — вопросы для интервью
- `~/.claude/rules/session.md` — общий протокол интервью и меню
- `~/Library/LaunchAgents/pro.artvision.bootstrap.plist` — RunAtLoad обёртка

## Расширение

Чтобы добавить нового клиента в goals dashboard — создать `clients/<slug>/goals.yaml` по образцу `clients/blumart/goals.yaml`. Скрипт `goals-progress.py` автоматически подхватит.

Следующие кандидаты на goals.yaml:
- **tvorimsovershenstvo** (Творим): SEO позиции — цель X ключей в топ-10 к дате Y
- **madwave**: бюджет Директ освоено — цель X к дате
- **ant-partners**: SEO позиции
- **otido**: SEO + Директ конверсии
