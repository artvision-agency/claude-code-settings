---
name: wordstat-block
description: "Блок частотности спроса (Wordstat) в КП/отчёт/страницу — БЕЗ траты токенов. Тянет РЕАЛЬНЫЕ показы/мес из Wordstat (Direct API v4 CreateNewWordstatReport), рендерит таблицу запрос/показов-в-мес в бренде Artvision как native HTML, идемпотентно встраивает по маркерам. Триггеры: 'блок частотности', 'частотность в кп', 'wordstat блок', 'показы в месяц', 'спрос wordstat', 'добавь частотность', 'wordstat block', 'frequency block'."
---

# /wordstat-block — блок частотности спроса (0 токенов)

Семья «service-proof» генераторов (как `/topvisor-positions`). Скрипт `~/artvision-data/scripts/wordstat_proof_block.py`.

## Команды
```bash
# native HTML в страницу (idempotent, по маркерам WORDSTAT)
python3 scripts/wordstat_proof_block.py --keys clients/<slug>/seo/queries-spb-current.txt \
  --region спб --embed <page>.html --anchor '<!--WORDSTAT-->'
# из реестра CLIENTS
python3 scripts/wordstat_proof_block.py --client ds-lab --region спб --format html --out block.html
# тест без API (fixture)
python3 scripts/wordstat_proof_block.py --fixture data.json --region спб --out block.html
```
Опции: `--rows N` (топ-N, деф 20), `--region` (спб/москва/россия/id).

## Что делает
- Реальные показы/мес из Wordstat (НЕ HasSearchVolume-булево; reuse `products/seo-pipeline/core/wordstat_v4_collector.py`).
- Кэш raw JSON → `clients/<slug>/proof/wordstat-<date>.json` (large-tool-output-to-file).
- Native HTML: шапка Artvision, плашки (кол-во запросов + сумма показов), таблица запрос/показов, источник+дата+регион. Маркеры `<!--WORDSTAT-START/END-->`.
- Idempotent embed (повторный = 1 пара маркеров, без дублей).

## Правила
- kp-brand: бренд Artvision, источник Wordstat раскрыт как «данные Wordstat» (это не сторонний платный инструмент-конкурент — частотность общедоступна).
- Числа из API детерминированно, не выдуманы (calculations-need-sources: источник+дата+регион).
- Авторизация: env `YANDEX_OAUTH_TOKEN` > явный `--login <логин>` > первый `tokens.json → yandex.direct.<login>.token` (с WARN). При мультилогине **указывай `--login` для детерминизма**.
- Блок «связанный спрос по теме» (SearchedWith+SearchedAlso), НЕ частотность самих сид-фраз — подписи честные + footnote «показы по связанным формулировкам, не уникальные пользователи/не прогноз лидов».
- Тесты: `python3 scripts/tests/test_wordstat_proof_block.py` (render/embed/guards, без live API).

## Связано
`/topvisor-positions` (образец паттерна), `/client-report` (встроить шагом), `offline-to-script-on-high-spend`, спека `docs/automation-monthly-report-trigger-spec.md` Блок 2.
