# Handover: SEO-аудит mitralab.ru + позиции (presale)

**Дата:** 2026-04-23 05:11
**Контекст:** presale (новый клиент, не в clients-registry)
**Сессия:** d9c94c22-d9e4-49a5-91dd-d3aaa74df735
**Статус:** в работе — техаудит готов, ждём 1 клик в Topvisor для съёма позиций

## 🎯 Цель сессии

SEO-аудит mitralab.ru (клиника базальной имплантации, Москва, Bitrix) по основным факторам + снять позиции 10-20 маркерных запросов в Яндекс/Москва.

## ✅ Что сделано

- `presales/mitralab/seo/audit-2026-04-23.md` — полный отчёт: 75/100 hybrid-audit, 0 critical / 5 medium, 9 секций (резюме, блокеры, среднее, ОК, структура, маркерные, статус позиций, план, источники)
- `reports/hybrid-audit.json` — сырые данные от `scripts/hybrid-seo-audit.py`
- **Topvisor:** создан проект **id 28063349** ("mitralab.ru — базальная имплантация"), залиты все 20 маркерных через `add/keywords_2/keywords/import`
- `sync/recaps/d9c94c22-...md` — recap заполнен (цель + deliverables + acceptance + log)

## 🧠 Решения и ПОЧЕМУ

| Решение | Альтернатива | Почему |
|---|---|---|
| Создал проект в Topvisor через API | Сразу через UI вручную | Чтобы автоматизировать заливку 20 ключей |
| Поисковик Yandex добавляем через UI | Через API (любой add/edit endpoint) | Topvisor v2 API НЕ имеет работающего endpoint для добавления searcher — пробовал 8 вариантов, все 1003 "undefined method". Документация (seo-research-methodology.md) подтверждает: только UI |
| Маркерные = 20 шт (ВЧ + СЧ + USP сайта) | 10 коротких ВЧ | USP-запросы ("без костной пластики", "all on 4", "при пародонтозе") = реальная коммерческая выдача клиники + покрывают синонимы (базальная = стратегическая) |
| Региона нет — берём 213 (Москва Desktop) | 213+1 (Москва+МО) | Сайт = клиника в Москве, USP "за 1-3 дня" = очный визит → МО в первой итерации не нужно |
| Storage = `presales/mitralab/` | `clients/mitralab/` | Клиента нет в clients-registry → presale (если станет клиентом — переедет) |
| НЕ запускал Playwright Yandex SERP | Скрейп напрямую | Curl на yandex.ru/search/ дал капчу. Playwright тоже рискует на 3-5/20 → лучше Topvisor через UI |

## ❌ Что НЕ сделано и почему

- **Позиции в Яндекс не сняты** — ждём 1 клик в Topvisor UI (добавить Yandex+Москва(213)+Desktop+depth 100). Без поисковика проверка не запускается
- **Wordstat частоты** — не собирал, чтобы не сжигать токены. Direct API v5 `HasSearchVolume` даёт только boolean, для чисел нужен Wordstat web scrape (не настроен)
- **PageSpeed/CWV** — нет PSI key в tokens. Можно через `https://pagespeed.web.dev/` ручным запросом
- **Я.Вебмастер/Метрика клиента** — нет доступов (это presale, прав на сайт ещё нет)

## 📚 Уроки

- **Topvisor v2 API ограничения:** проект создаётся (`add/projects_2/projects` + `url`), keywords заливаются (`add/keywords_2/keywords/import` + `keywords:[]`), но searchers/regions — ТОЛЬКО через UI. Endpoint `add/projects_2/searchers` и все вариации возвращают 1003. Записать в `knowledge/seo/rules.md` чтобы не тратить время в следующий раз
- **urllib + Topvisor SSL = таймауты на macOS**, curl работает мгновенно. Использовать subprocess+curl или requests, не urllib

## 🔜 Следующие шаги

1. **HIGH — ждёт Антона:** открыть https://topvisor.com/positions/?project_id=28063349 → `+ Поисковик` → Yandex / Москва (213) / Desktop / depth 100. Сказать «го» → следующий Claude снимет позиции через `get/positions_2/history` и допишет в `audit-2026-04-23.md`
2. **MEDIUM — после позиций:** клиенту/Антону презентовать отчёт + предложить услугу (это presale)
3. **LOW:** добавить mitralab в `clients-registry.md` если станет клиентом

## 🗺️ Карта файлов

```
artvision-data/
├── presales/mitralab/seo/
│   └── audit-2026-04-23.md    ← главный отчёт (9 секций)
├── reports/
│   ├── hybrid-audit.json      ← сырые данные
│   └── hybrid-audit-agent-prompt.md
└── sync/recaps/
    └── d9c94c22-d9e4-49a5-91dd-d3aaa74df735.md  ← заполнен

~/.claude_temp_scripts/
├── topvisor_mitralab.py       ← создание проекта (отработал)
├── topvisor_mitralab2.py      ← добавление keywords/searcher (urllib SSL fail)
├── topvisor_setup.sh          ← bash-версия (нашли что searcher endpoint не существует)
└── topvisor_check.py          ← попытка SERP-tasks через project_id=-1 (deprecated)
```

## ⚠️ Гачи

- **Topvisor project 28063349 уже создан** — НЕ создавать второй раз
- **20 keywords уже залиты** — НЕ перезаливать (топвизор всё равно дедуплицирует, но лишние счётчики)
- **Searcher = ТОЛЬКО UI** — даже не пытайся через API, потеря времени
- **mitralab.ru** работает на Bitrix → правки sitemap/schema/headers/cache через админку CMS, не через VPS клиента (доступа нет)
- Файлы в `presales/`, не в `clients/` — клиент ещё не подписан

## 🔗 Связанные ресурсы

- Topvisor проект: https://topvisor.com/positions/?project_id=28063349
- Сайт клиента: https://mitralab.ru/
- TG чат с клиентом: ⚠️ не указан, спросить Антона
- Asana задача: ⚠️ не создавалась (это инициатива Антона из чата, не задача)
