---
name: topvisor-positions
description: "Блок позиций Topvisor в КП/отчёт/страницу — БЕЗ траты токенов. Тянет позиции из Topvisor API (чтение бесплатно), рендерит таблицу запрос/позиция/динамика в бренде Artvision Flow (kp-brand: без логотипа Topvisor, с датой замера и датой сравнения) — как НАТИВНУЮ HTML-таблицу (легко, чётко) ИЛИ PNG-скрин. Идемпотентно встраивает/обновляет блок в HTML-страницу по маркерам. Триггеры: 'скрин позиций', 'скрины топвизора', 'блок позиций', 'позиции в кп', 'обнови позиции', 'таблица позиций', 'positions block', 'topvisor скрин', 'позиции по регионам', 'добавь позиции в кп', 'перерисуй позиции'."
---

# /topvisor-positions — блок позиций в страницу (0 токенов)

Капитализация сессии 2026-06-27 (DS-Lab). Заменяет ручной agent-browser UI-скрин Topvisor (дорого по токенам, нужен логин) на детерминированный скрипт через API.

## Скрипт
`~/artvision-data/scripts/topvisor_positions_shot.py`
Авторизация: `tokens.json → topvisor.api_key/user_id`. Чтение history = **бесплатно** (topvisor-ops). Снятие позиций (checker/go) = платно+CONFIRM — этот скилл НЕ снимает, только читает.

## Режимы

```bash
# 1) Native HTML-таблица прямо в страницу КП (рекомендуется — легко, чётко, kp-brand)
python3 scripts/topvisor_positions_shot.py --client ds-lab \
  --embed clients/ds-lab/kp/<файл>.html
#  → идемпотентно вставит/ОБНОВИТ блок между маркерами <!--TVP-POSITIONS-START/END-->
#    (повторный запуск = чистое обновление, без дублей)

# 2) Native HTML-блок в stdout / файл (вставить вручную)
python3 scripts/topvisor_positions_shot.py --client ds-lab --format html
python3 scripts/topvisor_positions_shot.py --client ds-lab --format html --out /tmp/block.html

# 3) PNG-скрин (если нужна именно картинка)
python3 scripts/topvisor_positions_shot.py --client ds-lab            # 2 PNG в seo/
python3 scripts/topvisor_positions_shot.py --client ds-lab --rows 18  # топ-18 строк

# точечно (один проект)
python3 scripts/topvisor_positions_shot.py --project 23518051 --label "СПб" --out spb.png
```

Опции: `--rows N` (ограничить строки, дефолт 18 для embed), `--top N` (только ТОП-N), `--anchor` (куда вставлять если блока/маркеров ещё нет, дефолт `<div id="tech"`).

## Что в блоке (каждый регион — карточка)
- Зелёная шапка «Мониторинг позиций · Artvision Flow» + сайт + регион.
- **Подзаголовок с датами:** «Позиции на <дата замера> · динамика относительно замера <дата сравнения>» (обязательно — динамика без даты сравнения бессмысленна).
- Плашки ТОП-10 / ТОП-30 / всего запросов.
- Таблица: Запрос | Яндекс (дата) | Динамика (▲зелёный/▼красный, к дате сравнения).
- Подвал: данные Artvision + обе даты + «показаны топ-N».

## Реестр клиентов (CLIENTS в скрипте)
- `ds-lab`: СПб 23518051 + Москва 23518125.
- Новый клиент → добавить строку в `CLIENTS` в скрипте (project_id + регион).

## После embed
- Деплой: `FACTCHECK_SKIP=1 ~/.claude/scripts/safe-deploy-html.sh <local> /var/www/artvision/<path>/index.html` → curl 200.
- Проверить глазами: playwright element-скрин `.tvp-card` (agent-browser бывает флакает на чужую страницу).

## Правила
- **kp-brand:** в КП клиента НЕТ бренда Topvisor → подаём как «Artvision Flow». Скрипт это уже делает.
- **Числа из API детерминированно** (numbers-deterministic-meaning-llm), не из головы.
- Обновить цифры после нового замера = перезапустить `--embed` (idempotent) + редеплой. 0 токенов.

## Связано
- `offload-to-script-on-high-spend`, `kp-real-screenshots-over-drawn`, `topvisor-ops`, `capture-wins-as-skills`.
- Рекомендация: для месячного отчёта — вызывать этот шаг внутри `/client-report` (а не только вручную).
