---
name: seo-tools-routing
description: SEO-инструменты — маршрутизация по задаче
paths:
  - 'clients/*/seo/**'
  - 'clients/*/presale/**'
  - 'presales/**'
always: false
size_tokens: 1342
---

# SEO-инструменты — маршрутизация по задаче

> **Установлено:** 2026-05-11 после инцидента «закопался в DataForSEO повторно когда у нас есть SEMrush».
> **Цель:** жёстко зафиксировать какой инструмент берём для какой SEO-задачи. Не путаться между альтернативами.

## Жёсткая таблица «задача → инструмент»

| Задача | Инструмент | Источник в `tokens.json` | Альтернатива |
|--------|-----------|--------------------------|--------------|
| **Backlinks / ссылочный профиль** | **SEMrush** | `tokens.json → semrush` (UI логин/пароль) | DataForSEO Backlinks API — ТОЛЬКО если SEMrush недоступен/исчерпан |
| Позиции в Я.СПб (или другом регионе) | **Topvisor** | `tokens.json → topvisor.api_token` | Direct API не даёт позиций |
| Частотность ключей (широкая) | Я.Direct `hasSearchVolume` v5 + `ForecastNew` v4 | `yandex.direct.<account>.token` | Wordstat API — broken (v4 error 93) |
| Частотность точная `"!фраза"` | Wordstat UI через Playwright | persistent profile `/tmp/yandex-wordstat-profile` | API v1 403, API v4 error 93 |
| Прогноз трафика / CPC | Я.Direct ForecastNew | те же токены | — |
| Скорость / Lighthouse mobile | Google PSI v5 | `youtube.api_key` (GCP key, работает для PSI) | DataForSEO On-Page есть, но платно |
| Технический crawl (битые ссылки, дубли) | Screaming Frog CLI (`sf`) | локально установлен | Custom crawler bs4 — для до 50 URL |
| Parse главной (Schema, alt, H1, canonical) | curl + BeautifulSoup | — | `parse_html.py` или skill `seo-master` |
| Sitemap / robots / llms.txt | curl | — | — |
| Я.Метрика (трафик клиента) | Y.Metrika API | `yandex.metrika.token` | — после старта работ |
| Я.Вебмастер (импрешены, CTR) | Y.Webmaster API | `yandex.webmaster.token` | — после получения owner-verification от клиента |
| Я.СПб SERP snapshot для AI Overview | Topvisor SERP API | `topvisor.api_token` | curl Я.СПб → captcha, не работает |
| GEO-аудит (AI ответы по бренду) | skill `/geo-audit` (geo_audit.py) | внутренний | — |
| TF-IDF / семантический gap | skill `/content-writer` или `tfidf-clustering` | внутренний | — |

## Запрет на использование

| Инструмент | Когда **НЕ** брать |
|------------|---------------------|
| **DataForSEO Backlinks** | Если SEMrush доступен — DataForSEO ТОЛЬКО как fallback, не дефолт |
| **Ahrefs** | Не наш инструмент, нет аккаунта |
| **Serpstat** | Не наш инструмент, нет аккаунта |
| **Я.Вебмастер для не-клиента** | Только owner-verified сайты — не пытаться через API |
| **Wordstat API v1** | 403 Forbidden со всеми токенами — нет approval. Не пытаться. |

## Workflow по задаче «собрать ссылочный профиль клиента»

```
1. Проверить tokens.json → semrush — UI логин/пароль есть?
2. Playwright UI → https://www.semrush.com/login/ → решить captcha
3. Открыть Backlinks Overview для каждого домена
4. Извлечь: Authority Score, Referring Domains, Backlinks, Dofollow %
5. JSON → clients/<slug>/seo/<date>/backlinks/semrush-<domain>.json
6. Применить в КП новой секцией #backlinks
7. В тексте КП использовать «Artvision LinkForge» (наш бренд для ссылочного — kp-brand.md)
```

**НЕ** запускать DataForSEO Backlinks как первый выбор. Только если SEMrush login заблокирован капчей >2 раз ИЛИ free-квота исчерпана.

## Прецедент

**2026-05-11 (сессия c4f36879):**
- Я предложил DataForSEO для backlinks (16:35).
- Антон поправил: «беклинки мы берем с семраш» (16:38).
- Я спросил: «где в инструкциях пробел?» — пробел реальный, в `rules/` SEMrush не упоминался.
- Решение: этот файл `seo-tools-routing.md` — жёсткая маршрутизация.

## Связь с другими правилами

- `kp-brand.md` — брендирование инструментов (SEMrush в КП клиента = «Artvision LinkForge»)
- `medical-kp.md` — расширенный список для мед-клиентов
- `quality.md` — SEO-gates (свежесть данных, factcheck)
- `presale-recon-standard.md` — обязательная разведка
- `feedback_no_internal_markers_in_client_docs.md` — не упоминать имена инструментов в КП клиенту
