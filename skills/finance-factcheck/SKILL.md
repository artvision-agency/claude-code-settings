---
name: finance-factcheck
description: "Strict factcheck финансового документа (КП, дашборд, аналитика со ставками банков, ОФЗ, БПИФ, НДФЛ). 7 слоёв проверки: HTML структура → ассеты HTTP → кросс-ссылки → консистентность → numeric facts (Layer 5) → domain validators (Layer 6) → strict adversarial (Layer 7). Триггеры: 'факчек финдокумента', 'проверь ставки', 'finance factcheck', 'факчек банки', 'проверь финрасчёт'."
---

# /finance-factcheck — 7-слойный факчек финансового документа

## Что делает

Расширенный фактчек для документов со ставками, налогами, инвестиционными инструментами. Не общий factcheck, а специализированный — поймает welcome-математику, ловушки НДФЛ-льготы, устаревшие YTM ОФЗ.

## Использование

```
/finance-factcheck <file.html|file.md> [--strict] [--rerun-stale]
```

Параметры:
- `<file>` — путь к документу
- `--strict` — обязательный Layer 7 (adversarial subagent)
- `--rerun-stale` — повторный WebFetch на все URL независимо (даже подтверждённые)

## 7 слоёв проверки

### Layer 1-4 (наследует общий /factcheck)

1. **Структура** — HTML, мета, теги
2. **Ассеты** — HTTP HEAD на img/audio/video
3. **Кросс-ссылки** — config.yaml, context-log
4. **Консистентность** — placeholder, дубли

### Layer 5 — Numeric facts (НОВЫЙ)

`factcheck-numeric.py`:
- Извлекает все числовые утверждения (% годовых, ₽, даты)
- Для каждого ищет URL-источник в радиусе 200 символов
- Если URL есть — повторный WebFetch → grep на число
- Если число расходится >0.5 п.п. → MISMATCH
- Если URL нет → NO-URL (в strict режиме — FAIL)

### Layer 6 — Domain validators (НОВЫЙ)

Финансовые специфичные проверки:

**Welcome-математика:**
- Если документ содержит расчёт за период дольше welcome-периода
- Должна быть формула с разбивкой (welcome × N мес + базовая × (срок − N) мес)
- Если нет — MISMATCH «welcome-математика нарушена»

**НДФЛ-льгота 2026:**
- Если документ упоминает НДФЛ на проценты
- Льгота должна быть **160 000 ₽** (не 145К, не 210К — поймано в session 9f7e1adc)
- Если другое число — MISMATCH

**ОФЗ YTM свежесть:**
- Если в документе ОФЗ с указанной YTM
- Свежесть < 7 дней (плавает с торгами)
- Если старше — STALE, рекомендация перепроверить moex.com

**АСВ-лимит:**
- Если сумма > 1.4М в одном банке
- Должно быть предупреждение «остаток вне страховки»
- Если нет предупреждения — WARN

**Заблокированные источники:**
- Если документ ссылается на офсайты из blocklist (sberbank.ru, alfabank.ru/make-money, mkb.ru, vbr.ru)
- Должна быть пометка «через агрегатор»
- Если ссылка как primary source — WARN

### Layer 7 — Strict adversarial subagent (опц)

`Agent(subagent_type=strict-factchecker)` параллельно:
- Презумпция лжи на каждое число
- Независимая повторная сверка через WebFetch
- Возвращает Verdict: BLOCK / CONDITIONAL / PASS

## Алгоритм

1. Прочитать файл и определить тип (HTML/MD)
2. Если есть `config.yaml` рядом — подгрузить как source
3. Запустить Layer 1-4 (factcheck-v2.py --standard)
4. Запустить Layer 5 (factcheck-numeric.py)
5. Запустить Layer 6 (встроенные домен-валидаторы)
6. Если `--strict` или путь матчит `personal/finance/*` / `clients/*/kp/*` / `presales/*/kp/*` → Layer 7
7. Свести отчёт + Verdict
8. Если CRITICAL — BLOCK deploy

## Маршрутизация Verdict

| Verdict | Действие |
|---------|----------|
| ✅ PASS | Деплой разрешён |
| ⚠️ CONDITIONAL | Можно деплоить с дисклеймерами (добавить блок «свежесть данных», «UNCONFIRMED отметки») |
| ❌ BLOCK | Деплой запрещён, исправить ошибки |

## Авто-trigger

Хук `pre-finance-deploy.sh` (PreToolUse Bash) автоматически запускает Layer 5 для:
- `personal/finance/*` → scp на VPS
- `personal/ipoteka/*` → scp
- `/preview/savings-*`, `/preview/finance-*`, `/preview/calculator-*` → scp

Хук `pre-scp-factcheck.sh` (расширен) — для всех клиентских и финансовых документов.

## Связанные

- `~/.claude/skills/factcheck/SKILL.md` — общий factcheck (Layer 1-4)
- `~/.claude/scripts/factcheck-numeric.py` — Layer 5
- `~/.claude/agents/strict-factchecker.md` — Layer 7
- `~/.claude/rules/finance-data-collection.md`
- `~/.claude/rules/welcome-vs-base-math.md`
- `~/.claude/rules/ndfl-formulas-2026.md`
- `~/.claude/rules/bank-source-blocklist.md`

## Прецедент

Session 9f7e1adc — финансовая HTML v1.0 содержала 6 CRITICAL ошибок не пойманных Layer 1-4. Strict-агент + numeric проверка → v3.3 final.
