---
name: link-reclaim-broken-swap
description: "Битый линкбилдинг — найти у конкурента 4xx backlinks → предложить замену нашей страницей. 60-70% insert rate, самый дешёвый канал. Триггеры: 'broken backlink swap', 'reclaim links', 'broken link building', '404 backlinks', 'битые ссылки конкурентов', 'битый линкбилдинг', 'link reclamation', 'перехват ссылок', 'reclaim 404'."
argument-hint: "[client-slug] [competitor-domain]"
user-invocable: true
allowed-tools: Read Write Edit Bash WebSearch WebFetch Grep Glob
---

# Link Reclaim (Broken Swap)

Битый линкбилдинг через перехват 404 у конкурентов. Самый дешёвый и эффективный канал backlinks — insert rate 60-70% (vs 3-8% обычного outreach).

## Идея workflow

1. Конкурент клиента (`competitor.com`) когда-то имел страницу `/old-article` с входящими ссылками с разных сайтов.
2. Страница протухла → 404.
3. Сайты-доноры всё ещё ссылаются на 404. Им это **вредит SEO** — они заинтересованы починить.
4. Мы пишем: «У вас битая ссылка на `[url]`. У нас есть похожий материал: `[наш-url]`. Если уместно — рад замене».
5. Они меняют → клиент получает backlink с минимальным усилием.

## Proven tools (используем готовое, не велосипеды)

Per `~/.claude/rules/proven-tools-first.md`:

- **`linkchecker`** ([959 stars](https://github.com/linkchecker/linkchecker), PyPI) — кравлер для проверки ссылок, async, выдаёт CSV/JSON/SQL
- **`httpx`** (Python lib, ~13K stars) — async HTTP для batch-проверок 4xx
- **DataForSEO API** (через `seo-dataforseo` skill) — backlinks конкурента, есть Ahrefs/SEMrush data
- **keys.so API** — для российских конкурентов (токен в `tokens.json` если есть)
- **Common Crawl** — fallback бесплатный источник backlinks

Не пишем кастомный crawler — обёртки над этими тулами.

## Pre-check

```bash
# Конфиг клиента
Read clients/<client-slug>/config.yaml

# Обязательные поля:
# - site: наш сайт клиента
# - niche: для match similarity
# - competitors: [список доменов]
```

Если `competitors:` пуст — запросить у пользователя или сгенерить через WebSearch `"топ конкурентов <niche> <city>"`.

## WORKFLOW (5 шагов)

### Шаг 1. Fetch competitor backlinks

```bash
python3 scripts/fetch_competitor_backlinks.py \
  --competitor competitor.com \
  --output clients/<slug>/link-reclaim/<date>/competitor_backlinks.csv \
  --source dataforseo  # или keys-so / ahrefs / semrush
```

Источник по приоритету:
1. **DataForSEO** (если есть подписка) — самый полный
2. **keys.so** (для рунета) — токен в `tokens.json`
3. **Ahrefs/SEMrush** — если есть guest-доступ
4. **Common Crawl** fallback — bulk-API, медленнее

Output CSV: `url_from, url_to, anchor, dr, traffic, last_seen`

### Шаг 2. Filter URLs to check

```bash
# Фильтр: только страницы конкурента с >=2 backlinks (стоит проверять)
python3 scripts/filter_candidates.py \
  --input competitor_backlinks.csv \
  --min-backlinks 2 \
  --output candidates.csv
```

### Шаг 3. HTTP check 4xx

```bash
python3 scripts/check_4xx.py \
  --input candidates.csv \
  --concurrency 10 \
  --output broken_urls.csv
```

Filtered output: только URL'ы с 4xx/5xx ответом + список доноров.

### Шаг 4. Match local pages (для каждого 404)

```bash
python3 scripts/match_local_pages.py \
  --broken broken_urls.csv \
  --client-site https://client-site.ru \
  --method tfidf  # или embeddings / manual
  --output swap_suggestions.csv
```

Берёт title/анкор/path-slug от 404 → ищет страницу клиента с близкой темой:
- **TF-IDF similarity** между анкором и title-tags клиентских страниц
- **Slug similarity** (если 404 = `/implants/zubnye` → match `/uslugi/implantatsiya`)
- **Niche keyword overlap**

Если similarity < 0.3 → пометить `match: weak`, не предлагать.

### Шаг 5. Draft outreach

```bash
python3 scripts/draft_outreach.py \
  --swaps swap_suggestions.csv \
  --client-name "Стоматология Дентикс" \
  --client-contact "anton@artvision.pro" \
  --template templates/outreach-broken-swap.md \
  --output drafts/
```

Один .md файл на каждого донора с предзаполненным email/контактом.

## Tracking

После outreach — log в `~/.claude/logs/link-reclaim.log`:

```
2026-05-21 14:30 | client=dentix | donor=mednews.ru | broken=competitor.com/x | suggested=dentix.ru/y | status=sent
2026-05-25 09:15 | client=dentix | donor=mednews.ru | status=inserted
```

KPI:
- **Sent rate** — сколько писем отправлено / candidates
- **Insert rate** — сколько заменили / sent (норма 60-70%)
- **High-DR insert** — сколько DR>40 (для TG-нотификации)

## TG-нотификация

При найденной swap-opportunity high-DR (>40) — авто-нотификация в команду:

```bash
~/.claude/scripts/tg-send.sh team \
  "🔗 Link reclaim: найден DR47 донор для $CLIENT — $DONOR ссылается на 404 у $COMPETITOR. Кандидат на замену: $LOCAL_URL"
```

## Интеграция

- **С `linkbuilding` skill** — broken-swap = один из 4 каналов в общем плане линкбилдинга (каталоги / тематика / NAP / **broken-swap**)
- **С `outreach-emails` skill** — broken-swap письмо = 5-й тип шаблона (cold pitch / case study / data / event / **broken-fix**)
- **С `seo-dataforseo`** — для backlinks-данных через DataForSEO MCP
- **С `clients/<slug>/config.yaml`** — competitors list

## Структура output

```
clients/<slug>/link-reclaim/<YYYY-MM-DD>/
├── competitor_backlinks.csv      # raw из API
├── candidates.csv                # отфильтровано
├── broken_urls.csv               # 4xx подтверждены
├── swap_suggestions.csv          # с match'ем нашей страницы
└── drafts/
    ├── donor1.example.com.md
    ├── donor2.example.com.md
    └── ...
```

## Antipatterns

- ❌ Слать outreach БЕЗ ручного просмотра match (TF-IDF может промахнуться → выглядит спамом)
- ❌ Match слабый (<0.3) предлагать как «похожее» — портит репутацию агентства
- ❌ Слать с одного email массово — попадание в спам. Использовать персонализированный sender (Artvision team).
- ❌ Конкуренты-агрегаторы (yandex.ru/maps, 2gis) — у них нет 404, не считать
- ❌ Ссылки внутри клиентского же домена — не reclaim, это internal link audit

## Чек-лист готовности к запуску

- [ ] `clients/<slug>/config.yaml` существует
- [ ] `competitors:` заполнен (минимум 2-3 домена)
- [ ] `site:` URL подтверждён `curl -sI`
- [ ] DataForSEO/keys.so токены есть в `tokens.json` ИЛИ согласие на Common Crawl fallback
- [ ] Output папка `clients/<slug>/link-reclaim/` создана

## Прецеденты

TBD — наполнять по мере применения к клиентам.

## Связанные правила

- `~/.claude/rules/proven-tools-first.md` — использовать `linkchecker` + `httpx`, не велосипедить
- `~/.claude/rules/quality.md` — match similarity ручная проверка перед send
- `~/.claude/rules/security.md` — outreach в Artvision-стиле, без AI-маркеров

## Связанные скиллы

- `/linkbuilding` — общий план линкбилдинга
- `/outreach-emails` — шаблоны писем
- `/seo-backlinks` — анализ backlink-профиля
- `/seo-dataforseo` — DataForSEO MCP интеграция
