---
name: ext-ops-midday
description: External invoicing + time tracking + finance overview (midday-ai/midday, 14K⭐ AGPL-3.0). Closes huge gap — у нас нет нормального invoicing/time tracking, всё в Excel + Сбис. Use for revenue tracking, billing 3+ clients, time-by-client reports, financial overview към 2M-цели. Triggers — 'midday', 'invoicing', 'выставить счёт', 'time tracking', 'учёт времени', 'finance overview', 'фин обзор', 'ext-ops-midday'.
---

# ext-ops-midday — invoicing + time + finance

**Upstream:** github.com/artvision-agency/midday ← midday-ai/midday (14K⭐, AGPL-3.0 ⚠️)
**Category:** Agency Ops
**Use case:** invoicing + time tracking + file reconciliation + financial overview — закрывает дыру у Artvision (сейчас Excel + Сбис).

## ⚠️ AGPL — только self-host per-instance

- ✅ OK: self-host на нашем VPS для internal-use Artvision
- ❌ NOT OK: продавать клиентам как white-label SaaS (требует commercial license)

## Когда вызывать

- Invoice клиенту (OTIDO 210K, Творим 150K, Madwave 120K, и т.д.)
- Учёт времени Андрей/Стас по конкретному клиенту
- Месячный финансовый обзор → сравнение с целью 2M MRR
- Reconciliation банка (Сбер расчётник + Esenina разовые)

## Как пользоваться

```bash
gh repo clone artvision-agency/midday ~/forks/midday
cd ~/forks/midday && bun install
# Self-host: docker compose up
# Затем UI на localhost:3000
```

## A/B vs текущая система

- vs Excel + Сбис ЭДО
- Метрика: время на invoice (мин), error rate, recoverable receivables
- Кейс: 1 мес billing для 3 клиентов через Midday → diff

## Связанные

- Catalog: `~/artvision-data/.claude/rules/external-tools-catalog.md`
- Research: `~/artvision-data/research/2026-05-20-agency-tools-discovery/04-agency-ops.md`
