---
name: domain-intel
description: |
  Универсальный инструмент работы с доменами и архивами для команды Artvision.
  Покрывает 3 группы задач:

  1. **Wayback Machine** — история контента (диф снапшотов конкурента, восстановление страниц клиента,
     presale-аудит «как сайт менялся за 5 лет», поиск удалённого контента).
  2. **Whois / DNS / возраст домена** — кто владел, когда зареган, на каком хостинге, MX/NS, истекает.
     Для presale, due diligence, фактчека юрлица.
  3. **Поиск истекающих/освобождающихся доменов** — expired.ru, expireddomains.net, reg.ru аукцион,
     webnames.ru/deleted, xpire.ru. Для PBN-стратегии и поиска брендового домена под клиента.

  Триггеры:
    вебархив, web archive, wayback, archive.org, снапшот, snapshot, диф снапшотов,
    восстановить страницу, восстановить сайт, история сайта, история домена, исчезла страница,
    domain history, site history, что было на сайте,
    whois, возраст домена, кто владелец, когда зареган,
    дроп домен, expired domain, истекающий домен, освобождается, аукцион доменов,
    expired.ru, expireddomains.net, reg.ru аукцион, webnames, xpire, telderi.

  Не путать с `/pbn-domains` (продажа PBN-пакетов клиенту, деплой сетки) — этот скилл шире и без
  «продажной» логики. `/pbn-domains` будет звать наши функции под капотом.
---

# domain-intel — работа с доменами и архивами

## Команды

```
domain-intel history <domain>                  # все снапшоты Wayback
domain-intel diff <url> <date1> <date2>        # diff title/H1/meta между датами
domain-intel restore <url> [--full-site]       # скачать страницу/сайт из архива
domain-intel save <url>                        # отправить в Wayback (Save Page Now)
domain-intel whois <domain>                    # RDAP-запрос: кто, когда, до каких пор
domain-intel intel <domain>                    # комплексный отчёт (history + whois + DNS + возраст)
domain-intel expired-search [filters]          # поиск истекающих доменов на 5 площадках
domain-intel bulk <yaml-file>                  # обход списка доменов → CSV
domain-intel monitor <yaml-file>               # cron-режим: алерт в TG если что-то изменилось
```

Запуск: `~/.claude/skills/domain-intel/.venv/bin/python ~/.claude/skills/domain-intel/scripts/domain_intel.py <команда>`

## Зависимости (Python 3.14, venv)

| Библиотека | Зачем | Лицензия |
|---|---|---|
| `waybackpack` (3.2K ⭐) | CDX API + downloader снапшотов | MIT |
| `savepagenow` (192 ⭐) | Save Page Now API | MIT |
| `cdx-toolkit` (204 ⭐) | низкоуровневый CDX для bulk | Apache-2.0 |
| `python-whois` | парсинг whois | MIT |
| `beautifulsoup4` | DOM-diff title/H1/meta | MIT |
| `requests` | HTTP с retry/back-off | Apache-2.0 |
| `playwright` | скрейпинг expired.ru / expireddomains.net | Apache-2.0 |
| `pyyaml` | bulk-конфиги клиентов | MIT |

## Use cases (Artvision)

### Presale-аудит (использует `intel`)
Антон получил лид. Запрос: `domain-intel intel example.ru` → отчёт:
- Возраст 8 лет, регистратор reg.ru, владелец «Иванов И.И.» с 2018 года
- В Wayback 247 снапшотов, активные обновления 2018-2024, потом тишина
- Хостинг: Beget с 2020, IP не менялся
- Текущий статус: домен жив, expires 2026-08-12

→ Антон знает: сайт настоящий, бренд старый, после 2024 запустение → возможно нужен SEO-перезапуск.

### Конкурентный аудит (использует `diff`)
SEO-стратег спрашивает: «что конкурент изменил на главной за полгода?»
`domain-intel diff https://competitor.ru 2026-01-01 2026-05-08`
→ таблица: title, H1, meta, изменённые блоки HTML.

### Восстановление страницы клиента (использует `restore`)
Клиент мигрировал CMS, потерял 50 SEO-страниц. Wayback видит их.
`domain-intel restore https://client.ru/uslugi --full-site` → папка с HTML, картинками, CSS.

### Поиск домена под нового клиента (использует `expired-search`)
Партнёр просит: «нужен .ru домен с возрастом 5+ лет про стоматологию, до 5К ₽».
`domain-intel expired-search --niche=stomatology --tld=ru --min-age=5 --max-price=5000`
→ парсинг expired.ru + xpire.ru + expireddomains.net → таблица кандидатов с историей и бэклинками.

### Мониторинг конкурентов (использует `monitor`)
Cron раз в неделю проверяет 30 конкурентских URL. Если изменился прайс/H1/контакты → TG-алерт команде.
`domain-intel monitor clients/<name>/competitors.yaml`

## Источники данных

| Источник | Что даёт | API/Scraping | Аккаунт |
|---|---|---|---|
| **archive.org Wayback** | История HTML | Free CDX API, ~10 req/s | не нужен |
| **archive.today** | Замороженные снимки | Только manual / `archiveis` lib | не нужен |
| **RDAP** (rdap.org, IANA) | Whois с 2018 | Free JSON API | не нужен |
| **dig / системный DNS** | Текущий DNS | CLI | не нужен |
| **expired.ru** | RU-аукцион | Playwright scraping | у Антона есть |
| **expireddomains.net** | Международные дропы с фильтрами | Playwright scraping | бесплатная регистрация |
| **xpire.ru** | RU дропы с DR/бэклинками | Playwright scraping | у Антона есть |
| **reg.ru/domain/new/rereg** | RU освобождающиеся | Playwright scraping | не нужен |
| **webnames.ru/domains/deleted** | RU удалённые | Playwright scraping | не нужен |

## Важные ограничения

- **Rate limits Archive.org:** ~10 req/s, IP-блок при burst → встроенный retry с back-off
- **Cloudflare-сайты блокируют прямой fetch** → fallback на Playwright
- **Snapshots могут исчезать** → для критичных клиентов хранить локальные WARC в `clients/<name>/archive/`
- **Fair use для аудита и восстановления клиенту OK**, но публичная перепубликация чужого контента — нет
- **expired.ru/xpire.ru** — авторизация Playwright через сохранённую сессию, см. `~/artvision-data/.claude_temp_scripts/playwright-profile/`
- **expireddomains.net** — бесплатная регистрация с email, лимит ~50 запросов/час

## Связь с другими скиллами

- `/pbn-domains` — узкий PBN-фокус (КП клиенту, продажа сетки). Зовёт наш `expired-search` и `restore`
- `/presale-kp` — preflight-аудит вызывает `intel <domain-клиента>`
- `/seo-master` — для SEO-аудита может использовать `history` + `diff` для понимания «что менялось»
- `/factcheck` — проверка возраста бренда vs whois домена
- `/counterparty-check` — проверка ИНН клиента + сравнение даты регистрации юрлица с whois домена
- `/new-client` — preflight-аудит при онбординге

## Прецедент

Создан 2026-05-08 после round_table (3 модели) + 3 параллельных senior-агента. Round_table рекомендовал
форк ArchiveBox/pywb — verifier-агенты с реальным `gh api` показали что эти проекты не в реальном топе
по активности/лицензии/стеку. Финальный выбор: тонкая обёртка над `waybackpack` + `savepagenow` +
`cdx_toolkit` + наш Playwright-парсер для expired-площадок.

Полный research: `sync/recaps/8dff9bf9-5ea7-42f8-bd38-7394182df9c9.md`.
