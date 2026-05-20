---
name: ext-content-pii
description: External PII detection/redaction (microsoft/presidio, 8.2K⭐ MIT). Detect names, phones, emails, addresses, passport numbers in text/docs. Critical для NDA-клиентов (Blumart 🔒) и медицинских (152-ФЗ + 323-ФЗ). Use перед публикацией отзывов, кейсов, отчётов где могут быть имена пациентов/клиентов. Triggers — 'pii', 'pii detect', 'pii redact', 'remove names', 'обезличить', 'удалить личные данные', '152 фз', 'медицинская анонимизация', 'nda compliance', 'ext-content-pii'.
---

# ext-content-pii — PII detection/redaction

**Upstream:** github.com/artvision-agency/presidio ← microsoft/presidio (8.2K⭐, MIT)
**Category:** Content / Compliance
**Use case:** detect+redact personal data (имена, телефоны, email, адреса, паспорта) — для 152-ФЗ, 323-ФЗ, NDA.

## Когда вызывать (КРИТИЧНО)

- Перед публикацией клиентских кейсов где есть имена врачей/пациентов
- Перед загрузкой отзывов Я.Карт/2ГИС в наши дашборды (там часто полные имена)
- Перед коммитом контакт-листов в публичные репо
- Audit `clients/*/context-log.md` и `meetings/*` на утечки персональных данных
- Blumart 🔒 — обработка ORM-отзывов с упоминанием реальных клиентов

## Как пользоваться

```bash
gh repo clone artvision-agency/presidio ~/forks/presidio
cd ~/forks/presidio && pip install presidio-analyzer presidio-anonymizer
python -m spacy download ru_core_news_lg  # русская языковая модель
```

```python
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

analyzer = AnalyzerEngine(supported_languages=["ru", "en"])
anonymizer = AnonymizerEngine()

text = "Иван Петров позвонил с +7-911-123-4567 по email ivan@example.ru"
results = analyzer.analyze(text=text, language="ru")
clean = anonymizer.anonymize(text=text, analyzer_results=results).text
# → "<PERSON> позвонил с <PHONE_NUMBER> по email <EMAIL_ADDRESS>"
```

## Workflow Artvision

1. Любой artifact на отправку клиенту проходит presidio scan
2. Если найдены PII в видимом тексте — STOP, обезличить или подтвердить разрешение клиента
3. Логи в `~/artvision-data/clients/<slug>/compliance/pii-scan-<date>.json`

## A/B vs ручной regex

- Метрика: recall (найденные PII) + precision (false positives)
- Кейс: Blumart 50 отзывов с именами клиентов → presidio vs наш regex
- Russian-specific: ФИО распознавание через spaCy ru-модель

## Связанные

- 152-ФЗ compliance: `~/artvision-data/clients/<medical>/compliance/`
- Research: `~/artvision-data/research/2026-05-20-agency-tools-discovery/02-content-nlp.md`
- NDA flag: см. clients-registry.md секция 🔒 NDA
