---
name: pagespeed-block
description: "Блок скорости загрузки (PageSpeed) в КП/отчёт/страницу — БЕЗ траты токенов. Тянет метрики Google PageSpeed Insights (LCP/CLS/TBT/score + INP из CrUX), рендерит карточку Mobile+Desktop с цветом по порогам в бренде Artvision как native HTML, идемпотентно встраивает по маркерам. Триггеры: 'блок скорости', 'скорость в кп', 'pagespeed блок', 'core web vitals блок', 'lcp cls', 'скорость загрузки', 'pagespeed block', 'speed block'."
---

# /pagespeed-block — блок скорости загрузки (0 токенов)

Семья «service-proof» (как `/topvisor-positions`, `/wordstat-block`). Скрипт `~/artvision-data/scripts/pagespeed_proof_block.py`.

## Команды
```bash
python3 scripts/pagespeed_proof_block.py --url https://ds-lab.ru --embed <page>.html --anchor '<!--PAGESPEED-->'
python3 scripts/pagespeed_proof_block.py --client ds-lab --format html --out block.html
python3 scripts/pagespeed_proof_block.py --fixture data.json --out block.html   # тест без API
```

## Что делает
- PSI v5 (lab Lighthouse + field CrUX), Mobile + Desktop: LCP, CLS, TBT, Performance-score, INP (поле).
- Цвет по порогам: LCP ≤2.5с/CLS ≤0.1/TBT ≤200мс/score ≥90 = зелёный; хуже = жёлтый/красный.
- Native HTML, маркеры `<!--PAGESPEED-START/END-->`, idempotent embed, raw-кэш `clients/<slug>/proof/pagespeed-<date>.json`.
- Footnote: нормы метрик + «лаб-замер PSI, реальные польз. INP из CrUX где доступно».

## ⚠️ Лимит PSI
- Анонимный PSI = **HTTP 429 при частых запросах**. Для надёжных live-замеров — ключ `env PSI_API_KEY` (Google Cloud → PageSpeed Insights API, бесплатный tier).
- Без ключа: код отрабатывает gracefully (WARN → карточка «Нет данных»), но цифры не получит при 429.

## Правила
- kp-brand: бренд Artvision, источник Google PageSpeed раскрыт честно (общедоступный инструмент).
- Числа из API детерминированно (calculations-need-sources: источник+дата).
- Тесты: `python3 scripts/tests/test_pagespeed_proof_block.py` (render/embed/guards/extract, без live).

## Связано
`/topvisor-positions`, `/wordstat-block` (образцы), `/client-report` (встроить шагом), спека `docs/automation-monthly-report-trigger-spec.md` Блок 2.
