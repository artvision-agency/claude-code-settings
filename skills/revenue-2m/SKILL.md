---
name: revenue-2m
description: "Revenue milestone tracker: 2,000,000 RUB/month ($22,200 USD). Dashboard with current revenue, gap analysis, concrete actions to close the gap. Triggers: '2mln', '2 million', '2 миллиона', 'цель 2м', 'milestone 2m', 'revenue 2m'"
argument-hint: "[action: dashboard|plan|update]"
---

# /revenue-2m — Milestone: 2,000,000 RUB/month (~$22,200 USD/month)

## TARGET

| Metric | RUB | USD (~90 RUB/$) |
|--------|-----|------------------|
| Monthly target | 2,000,000 | $22,200 |
| Annual target | 24,000,000 | $266,400 |
| Weekly run-rate | 500,000 | $5,550 |

## STEP 1: Load Current State

```bash
# Read revenue data
cat ~/.claude/projects/-Users-antonk/memory/revenue-goal.md

# Read client list
cat /Users/antonk/artvision-data/schedule/reports-invoices.json 2>/dev/null || echo "No invoice schedule"

# Check Asana for revenue-related tasks
# asana_cli.py tasks --open
```

## STEP 2: Calculate Dashboard

Build and display this table:

```
============================================
  REVENUE MILESTONE: 2M RUB ($22.2K USD)
============================================

CURRENT REVENUE:
| Source          | RUB/month | USD/month | Status    |
|-----------------|-----------|-----------|-----------|
| Client A        | XXX,XXX   | $X,XXX   | Paying    |
| Client B        | XXX,XXX   | $X,XXX   | Paying    |
| ...             |           |           |           |
|-----------------|-----------|-----------|-----------|
| TOTAL CONFIRMED | XXX,XXX   | $X,XXX   | XX% of 2M |
| TOTAL PIPELINE  | XXX,XXX   | $X,XXX   | XX% of 2M |

GAP TO 2M:
| Metric    | RUB       | USD     |
|-----------|-----------|---------|
| Target    | 2,000,000 | $22,200 |
| Confirmed | XXX,XXX   | $X,XXX  |
| GAP       | X,XXX,XXX | $XX,XXX |

PROGRESS: [████████░░░░░░░░] XX%
```

## STEP 3: Gap Closing Actions

Rank ALL possible revenue actions by:
1. **Speed** — how fast can it generate revenue (days/weeks/months)
2. **Size** — how much RUB/month it adds
3. **Probability** — likelihood of closing (%)
4. **Expected Value** = Size x Probability

### Action Categories:

**A. Upsell existing clients** (fastest, highest probability)
- Additional services to paying clients
- Price increases for underpriced contracts
- New service lines (PPC, content, AI)

**B. Reactivate paused clients** (fast, medium probability)
- Clients on pause (VLPCo, etc.)
- Clients with debt (Extru, etc.)

**C. Close pipeline** (medium speed, variable probability)
- Active negotiations (Atribeaute, etc.)
- Warm leads

**D. New client acquisition** (slower, lower probability)
- Inbound from SEO/content
- Outbound presale
- Referrals

**E. Product revenue** (variable)
- AIvision services
- Dental-Experts partnership
- Richelist crypto
- Music production

### Output format:

```
TOP 5 ACTIONS TO CLOSE THE GAP:

| # | Action | +RUB/mo | +USD/mo | Time | Prob | EV RUB |
|---|--------|---------|---------|------|------|--------|
| 1 | ...    | XXX,XXX | $X,XXX  | Xw   | XX%  | XX,XXX |
| 2 | ...    | XXX,XXX | $X,XXX  | Xw   | XX%  | XX,XXX |
| 3 | ...    | XXX,XXX | $X,XXX  | Xw   | XX%  | XX,XXX |
| 4 | ...    | XXX,XXX | $X,XXX  | Xw   | XX%  | XX,XXX |
| 5 | ...    | XXX,XXX | $X,XXX  | Xw   | XX%  | XX,XXX |

TOTAL EV: +XXX,XXX RUB ($X,XXX USD)
IF ALL CLOSE: XXX,XXX + GAP coverage = XX%
```

## STEP 4: Create Asana Tasks

For each action with EV > 50,000 RUB:
- Create Asana task with deadline
- Assign to Andrey or Anton
- Tag: revenue, milestone-2m

## STEP 5: Update Memory

Update `~/.claude/projects/-Users-antonk/memory/revenue-goal.md` with:
- New confirmed total
- Updated client statuses
- Next review date

## STEP 6: Proactive Revenue Monitoring

Claude MUST create these cron tasks at session start:

```
CronCreate: every 4 hours
Prompt: "Revenue check — прочитай revenue-goal.md, проверь:
1. Есть ли незакрытые счета (просроченные)?
2. Есть ли горячие лиды без КП?
3. Есть ли клиенты которым можно допродать услугу?
4. Есть ли готовые продукты без лендинга/публикации?
Если есть хоть один пункт — напомни Антону конкретное действие."
```

### Revenue triggers (при ЛЮБОМ упоминании в сессии):
- Новый клиент / лид / запрос → сразу оценить чек + создать задачу КП
- Готовая страница / продукт → сразу спросить "куда распространяем?"
- Завершённая задача клиенту → сразу спросить "можно допродать?"
- Конец месяца → напомнить про счета ВСЕМ клиентам

## STEP 7: Distribution Research

При каждом запуске скилла — WebSearch по:
1. "SEO агентство привлечение клиентов каналы 2026" — новые каналы
2. "B2B lead generation digital agency" — международные практики
3. Проверить конкурентов из competitor-analysis.md — что нового

Результат: 3 конкретных идеи для распространения с оценкой стоимости и ROI.

## RULES

1. ALL amounts shown in BOTH RUB and USD
2. USD rate: use current (~90 RUB/$), note the rate used
3. Be REALISTIC about probabilities — no inflated numbers
4. Focus on actions Claude can EXECUTE (KP, content, audit), not just suggest
5. Cross-reference with Asana — don't create duplicate tasks
6. Run this at least weekly (suggest in /weekly-check)
7. **PROACTIVE:** не ждать запроса — напоминать о revenue-действиях каждые 4 часа через cron
8. **ASK QUESTIONS:** если не хватает данных для оценки — задать 10-30 вопросов сразу, одним блоком

## TABOO: AI/Neural Networks in Public Materials

**АБСОЛЮТНЫЙ ЗАПРЕТ** упоминать AI, нейросети, Claude, GPT, машинное обучение в:
- КП для клиентов
- Страницах услуг
- Публичных материалах (vc.ru, Habr, соцсети)
- Отчётах клиентам
- Лендингах продуктов

**Что вместо этого:**
- "Авторская методология" вместо "AI-генерация"
- "Аналитическая система" вместо "нейросеть"
- "Экспертный анализ" вместо "машинное обучение"
- "Автоматизированный аудит" вместо "AI-аудит"
- Показывать РЕЗУЛЬТАТ, не инструмент

**Исключение:** AIvision — сам продукт про AI, но позиционирование: "мы делаем вас видимым для AI", НЕ "мы используем AI для работы"
