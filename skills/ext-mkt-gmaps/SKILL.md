---
name: ext-mkt-gmaps
description: External Google Maps scraper для B2B leadgen (omkarcloud/google-maps-scraper, 2.7K⭐ MIT). Extracts 50+ data points per business: email, phone, website, reviews, hours. Triggers — 'google maps scrape', 'gmaps leadgen', 'b2b leads', 'scrape gmb', 'businesses extraction', 'ext-mkt-gmaps'.
---

# ext-mkt-gmaps — Google Maps leadgen

**Upstream:** github.com/artvision-agency/google-maps-scraper ← omkarcloud/google-maps-scraper (2.7K⭐, MIT ✅)
**Category:** Marketing / Leadgen
**Use case:** B2B lead extraction из Google Maps — 50+ data points per business.

## Когда вызывать

- Scrape стоматологии СПб → outreach Mautic (Wave 2 → А/Б pipeline)
- Масштабирование Грелка-Гудёлка модели на новые ниши
- Конкурент-research через GMB (рейтинги, кол-во отзывов, контакты)
- Зарубежные проекты (RicheList Европа/ОАЭ) где Я.Карты пусто

## Как пользоваться

```bash
gh repo clone artvision-agency/google-maps-scraper ~/forks/gmaps-scraper
cd ~/forks/gmaps-scraper && pip install -r requirements.txt
# Пример:
python main.py --query "стоматология Санкт-Петербург" --max 50 --output stomas-spb.csv
```

## A/B vs наш Я.Карты ZenoMate

- Я.Карты — Россия (DJB2-хэш, через ORM Command Center)
- Google Maps — зарубежные рынки + western-Russian audience
- Метрика: leads per hour, contact data completeness

## Pipeline integration

`/ext-mkt-gmaps` → CSV → `/ext-mkt-crm-django` (Wave 2) → outreach `/ext-mkt-mautic` (Wave 2) = **полный leadgen pipeline**

## Связанные

- Research: `~/artvision-data/research/2026-05-20-agency-tools-discovery/03-marketing-automation.md`
