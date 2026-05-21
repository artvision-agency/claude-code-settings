---
name: ext-mkt-mautic
description: External Marketing Automation (mautic/mautic, 9.7K⭐ GPL/commercial). Email campaigns, drip sequences, lead scoring, landing pages. У нас пишутся письма скиллами /email-sequence /outreach-emails — но не отправляются системно. Mautic закрывает дыру отправки. Triggers — 'mautic', 'email automation', 'drip campaign', 'email рассылка', 'nurture sequence', 'welcome series', 'ext-mkt-mautic'.
---

# ext-mkt-mautic — email automation

**Upstream:** github.com/artvision-agency/mautic ← mautic/mautic (9.7K⭐, GPL ⚠️)
**Category:** Marketing
**Use case:** marketing automation — email + landing pages + lead scoring + drip campaigns

## Дыра в нашем стеке (которую закрывает Mautic)

| Что у нас | Mautic |
|-----------|--------|
| `/email-sequence` пишет письма | Отправляет, отслеживает open/click |
| `/outreach-emails` шаблоны | Sequencing + auto-followup |
| Mail merge вручную | Personalisation + A/B subject lines |

## Когда вызывать

- Welcome-sequence для Madwave eLama leads (10 контактов после переноса аккаунта)
- Drip-кампания для Творим клиентов (контент-обновления)
- Re-engagement для VLPco / Atribeaute (бывшие клиенты)
- Cold outreach Wave 2 pipeline: gmaps → Django-CRM → Mautic → conversion

## Как пользоваться

```bash
gh repo clone artvision-agency/mautic ~/forks/mautic
cd ~/forks/mautic
# Docker compose + setup wizard
docker compose up -d
# UI на localhost:8080
```

## A/B vs текущее (вручную)

- Метрика: open rate, click rate, response rate, time-to-send
- Кейс: pilot 20 cold leads через Mautic vs 20 manual → 7 days metrics

## Связанные

- Pipeline: `/ext-mkt-gmaps` → `/ext-mkt-crm-django` → `/ext-mkt-mautic`
- Research: `~/artvision-data/research/2026-05-20-agency-tools-discovery/03-marketing-automation.md`
