---
name: ext-mkt-crm-django
description: External multi-tenant CRM (MicroPyramid/Django-CRM, 2.3K⭐ MIT). Django REST + SvelteKit, self-hosted, **multi-tenant** = можем давать клиентам как product (+30-50K/мес × 5 клиентов). Triggers — 'crm', 'crm для клиента', 'lead management', 'crm дашборд', 'multi-tenant crm', 'django-crm', 'ext-mkt-crm-django'.
---

# ext-mkt-crm-django — multi-tenant CRM

**Upstream:** github.com/artvision-agency/Django-CRM ← MicroPyramid/Django-CRM (2.3K⭐, MIT ✅)
**Category:** Marketing / CRM
**Use case:** open-source self-hosted CRM, **multi-tenant** — каждый клиент получает свой instance. Можем продавать как продукт.

## Зачем именно multi-tenant

- 5 клиентов × 30-50K/мес «Творим CRM» = +150-250K MRR
- Self-host на нашем VPS = низкая cost
- MIT лицензия = коммерческое использование без ограничений

## Когда вызывать

- Внутренний CRM Artvision (presale-pipeline 377 задач — Asana не справляется)
- Клиентский CRM (Творим, OTIDO, Атрибьюти давно говорят «нужна CRM»)
- Lead capture + nurture sequences
- Multi-tenant deployment для отдельных клиентских instances

## Как пользоваться

```bash
gh repo clone artvision-agency/Django-CRM ~/forks/django-crm
cd ~/forks/django-crm
# Backend (Django REST):
pip install -r requirements.txt
python manage.py migrate && python manage.py runserver
# Frontend (SvelteKit) — отдельный пакет
```

## A/B vs Asana

- Метрика: time-to-close (presale), lead loss rate, custom-field flexibility
- Кейс: мигрировать presale-pipeline (mirbir, grelka-gudelka, dental-experts) в Django-CRM → 2 недели

## Стратегическая идея — Wave 2 unlock

Если успешно мигрируем presale → можем **продавать клиентам**: «Творим CRM», «OTIDO CRM» как Artvision-product. +30-50K/мес × 5 = новый поток к 2M.

## Связанные

- Research: `~/artvision-data/research/2026-05-20-agency-tools-discovery/03-marketing-automation.md`
