---
name: savings-rates
description: "Параметризованный ресерч ставок РФ-банков (накопит. счета + срочные вклады + ОФЗ + БПИФ) на N млн ₽ на M месяцев. Запускает рой 5-8 senior-research агентов с WebFetch на офсайты + агрегаторы + macro (ЦБ, АСВ, НДФЛ). Результат — HTML с CONFIRMED/UNCONFIRMED маркировкой и расчётом N сценариев. Триггеры: 'куда положить', 'вклады', 'накопит счета', 'savings rates', 'банковские ставки', 'разместить N млн', 'savings research'."
---

# /savings-rates — ресерч ставок РФ-банков

## Что делает

Полный pipeline исследования банковских ставок в РФ под конкретную задачу размещения денег. Запускает рой агентов параллельно, агрегирует данные, факчекает, рассчитывает сценарии, генерирует HTML.

## Использование

```
/savings-rates --amount 3000000 --term 6mo [--risk low|mid|high] [--flexibility low|mid|high]
```

Параметры:
- `--amount` — сумма в ₽ (например 1000000, 3000000)
- `--term` — срок (3mo, 6mo, 12mo)
- `--risk` — толерантность к риску (по умолчанию mid)
- `--flexibility` — нужна ли гибкость движений (по умолчанию mid)

Если параметры не заданы — спросить у пользователя через `AskUserQuestion`.

## Pipeline (7 шагов)

### 1. Прочитать baseline и правила (5 сек)
- `~/.claude/projects/-Users-antonk/memory/reference_russian_banks_baseline_*.md` — последний снапшот
- `~/.claude/rules/finance-data-collection.md` — стандарт сбора
- `~/.claude/rules/welcome-vs-base-math.md` — обязательная разбивка периодов
- `~/.claude/rules/ndfl-formulas-2026.md` — формула льготы
- `~/.claude/rules/bank-source-blocklist.md` — какие сайты не fetch'аются

### 2. Запустить рой 5-8 senior-research агентов параллельно (3-5 мин)

Группы:
- **Топ-5 крупных банков** (Сбер, ВТБ, Альфа, Газпром, Т-Банк) — накопит. счета
- **Средние банки** (МКБ, Совкомбанк, Росбанк, ПСБ, Уралсиб, ОТП, Хоум, ДОМ.РФ) — накопит. счета
- **Цифровые/маркетплейс** (Озон, Яндекс, WB, МТС, Точка, Авангард) — накопит. счета
- **Срочные вклады** — 10+ банков
- **Macro + альтернативы** (ЦБ ставка, АСВ, ОФЗ, БПИФ LQDT/SBMM/AKMM)

Каждому агенту:
- WebFetch на офсайт банка (если не в blocklist)
- Альтернатива: banki.ru, finuslugi.ru, bankinform.ru, 1000bankov.ru
- Минимум 2 источника на каждое число
- Маркер CONFIRMED / UNCONFIRMED / NO-DATA
- Указать дату и время проверки

### 3. Strict factcheck первичных данных (3-5 мин)

`Agent(subagent_type=strict-factchecker)` с GLOBAL OVERRIDE на запись .md отчёта.

Презумпция лжи: каждое число → независимая повторная проверка через WebFetch.

### 4. Round_table кросс-валидация (1-2 мин)

```
mcp__llm-consilium__round_table(
    models='llama,qwen3,hermes-405b,gpt-oss-groq',
    prompt='...рекомендация сценариев...'
)
```

4 free Groq + 1-2 OR модели (если баланс есть). Если 3+ модели подтверждают — solid.

### 5. Расчёт N сценариев (1 мин)

Применять правила:
- `welcome-vs-base-math.md` — раздельно welcome + базовая на остаток срока
- `ndfl-formulas-2026.md` — льгота 160К на 2026 (или новая если архив ЦБ изменился)
- АСВ — обязательно учесть лимит 1.4М

Сценарии (по умолчанию 4-5):
- **A** — простой 1-2 банка
- **B** — гибрид АСВ × 2-3 банка
- **C** — фикс-вклады с условиями
- **D** — ОФЗ + БПИФ (без банковской мороки)
- **E** — Yandex Сейв (если Плюс)

### 6. Генерация HTML

Структура:
- TLDR с Топ-3 сценариями
- TOC
- Macro-контекст (ЦБ, АСВ, НДФЛ)
- Таблицы накопит. счетов / вкладов / альтернатив
- Топ-кандидаты карточками
- Расчёт N сценариев
- Чёрный список (избегать)
- «Дочекать руками» (что Антон проверяет в приложениях)
- Методология

Стиль: `~/artvision-data/personal/finance/savings-19052026/index.html` как template.

### 7. Деплой и факчек

```
scp <html> root@80.90.181.152:/var/www/artvision/preview/savings-<date>/index.html
```

Хук `pre-scp-factcheck.sh` + `pre-finance-deploy.sh` сработают автоматически.

После деплоя — curl-check + X-Robots-Tag noindex.

## Результаты

- **Live URL** первой строкой ответа (правило feedback_deploy_url_first)
- HTML на VPS + локально в `personal/finance/savings-<date>/`
- Все факчек-отчёты в той же папке (`factcheck-*.md`, `check-*.md`)
- Обновление memory: `reference_russian_banks_baseline_<date>.md`

## Когда вызывать

- «Куда положить N млн на M мес»
- «Сравни ставки банков»
- «Что выгоднее — вклад или ОФЗ»
- «savings research»

## Связанные скиллы

- `/finance-factcheck` — для проверки готового документа
- `/portfolio-calc` — для расчёта без полного ресерча
- `/factcheck` — общий, не финансовый

## Связанные правила и memory

- `~/.claude/rules/finance-data-collection.md`
- `~/.claude/rules/welcome-vs-base-math.md`
- `~/.claude/rules/ndfl-formulas-2026.md`
- `~/.claude/rules/bank-source-blocklist.md`
- `~/.claude/projects/-Users-antonk/memory/reference_russian_banks_baseline_*.md`
- `~/.claude/projects/-Users-antonk/memory/feedback_savings_3M_scenarios.md`
- `~/.claude/projects/-Users-antonk/memory/feedback_welcome_math_in_finance_consilium.md`
- `~/.claude/projects/-Users-antonk/memory/feedback_accrual_base_min_vs_daily.md`

## Прецедент

Session 9f7e1adc (19.05.2026): 3M на 6 мес. Полный pipeline отработан вручную, результат — `personal/finance/savings-19052026/index.html`. Этот скилл — каноническая reusable версия того pipeline.
