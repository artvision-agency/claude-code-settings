---
name: seo-master
description: "Полный SEO-инструмент: аудит, keyword research, on-page оптимизация, link building, Core Web Vitals, schema markup. Для клиентов Artvision: hybrid-seo-audit.py + curl для мета-тегов (НЕ WebFetch!). Триггеры: 'SEO аудит', 'аудит сайта', 'проверь SEO', 'technical SEO', 'мета-теги', 'SEO', 'ключевые слова', 'keyword research', 'оптимизация сайта', 'позиции в поиске', 'link building', 'линкбилдинг', 'SEO issues', 'on-page SEO', 'meta tags review', 'SEO health check', 'why am I not ranking', 'почему не ранжируется', 'seo expert', 'Core Web Vitals', 'pagespeed', 'скорость сайта', 'индексация', 'crawl budget', 'robots.txt', 'sitemap', 'semrush', 'backlink gap', 'backlink analysis', 'ссылочный профиль'."
---

# SEO Audit — Artvision

## ПЕРВЫЙ ШАГ ПРИ ЛЮБОЙ SEO-ЗАДАЧЕ — sentinel

```bash
touch "/tmp/seo-master-invoked-${CLAUDE_SESSION_ID:-default}"
```

Это разблокирует `pre-tool-seo-task-require-master.sh` хук на текущую сессию.
Без этого Edit/Write/Bash на SEO-файлы будут блокироваться.
Прецедент: Codex GPT-5.4 review 09.05.2026 — adoption problem (4/83 КП = 4.8%).

## ДЕПЛОЙ КЛИЕНТСКИХ HTML — ТОЛЬКО через safe-deploy-html.sh

```bash
# ✅ ПРАВИЛЬНО (factcheck гарантированно прогоняется):
~/.claude/scripts/safe-deploy-html.sh \
  ~/artvision-data/clients/spb-kursy/index.html \
  /var/www/artvision/kp/spb-kursy/index.html

# ❌ НЕПРАВИЛЬНО (хук pre-scp-factcheck НЕ работает у саб-агентов):
scp ~/artvision-data/clients/X/index.html root@80.90.181.152:/var/www/...
```

**Почему:** PreToolUse-хуки родительской сессии не распространяются на саб-агенты.
`safe-deploy-html.sh` гарантирует factcheck-v2.py + scp + curl verify в одном вызове.

Bypass (только emergency): `FACTCHECK_SKIP=1 safe-deploy-html.sh ...`

Прецедент: 09.05.2026 — 4 саб-агента деплоили scp без factcheck (отчёты в /tmp пустые).

---

## КРИТИЧЕСКИЕ ПРАВИЛА (НЕ НАРУШАТЬ!)

### 1. WebFetch ТЕРЯЕТ `<head>` — НИКОГДА не использовать для мета-тегов!
```
❌ ЗАПРЕЩЕНО:
WebFetch(url, "покажи title и description")
→ Результат: пустота, потому что WebFetch конвертирует HTML в markdown и теряет <head>

✅ ПРАВИЛЬНО:
curl -sL URL | grep -E '<title|<meta name="description"'
```

### 2. Pre-Task Protocol — прочитать контекст клиента
```
Перед аудитом ОБЯЗАТЕЛЬНО:
  → clients/[name]/config.yaml     # CMS, домен
  → clients/[name]/patches/*.md    # Ошибки и особенности
```

### 3. ОБЯЗАТЕЛЬНЫЙ первый шаг — hybrid-seo-audit.py
```bash
python3 ~/artvision-data/scripts/hybrid-seo-audit.py --url [URL]
```
Без него агент будет галлюцинировать. Скрипт собирает РЕАЛЬНЫЕ данные.

### 3. macOS grep НЕ поддерживает -P (Perl regex)
```bash
# ❌ Не работает на macOS
grep -P '(?<=<title>).*(?=</title>)'

# ✅ Работает
grep -oE '<title>[^<]+</title>'
# или установить ggrep
```

---

## Процесс SEO-аудита Artvision

```
ШАГ 0: ИНСТРУМЕНТЫ (НЕ ПРОПУСКАТЬ!)
──────────────────────────────────────
- [ ] Мета-теги: ТОЛЬКО curl -sL URL | grep
- [ ] WebFetch — для контента страницы (body), НЕ для head
- [ ] hybrid-seo-audit.py — обязательный первый шаг

ШАГ 1: СБОР ФАКТОВ + ТЕХНИЧЕСКИЙ АУДИТ
────────────────────
- [ ] python3 ~/artvision-data/scripts/hybrid-seo-audit.py --url [URL]
      → скрипт: scripts/hybrid-seo-audit.py (Screaming Frog + факты)
- [ ] Получить JSON с реальными данными
- [ ] Сохранить результат

ШАГ 2: SITEMAP
────────────────────
- [ ] curl -sL [URL]/sitemap.xml | head -100
- [ ] Есть ли sitemap? Актуальный?
- [ ] curl -sL [URL]/robots.txt — ссылка на sitemap?
- [ ] Сравнить страницы в sitemap vs реальные на сайте

ШАГ 3: ВЕБМАСТЕРА
────────────────────
- [ ] Сайт в Yandex.Webmaster? (спросить клиента)
- [ ] Сайт в Google Search Console? (спросить клиента)
- [ ] Sitemap загружен и принят?

ШАГ 4: МЕТА-ТЕГИ (curl!)
──────────────────────────────
- [ ] curl -sL [URL] | grep -oE '<title>[^<]+</title>'
- [ ] curl -sL [URL] | grep -oE '<meta name="description"[^>]+>'
- [ ] Проверить 5-10 ключевых страниц

ШАГ 5: ТЕХНИЧЕСКИЕ ПРОБЛЕМЫ
─────────────────────────────────
- [ ] HTTPS везде?
- [ ] Редиректы правильные? (www ↔ без www)
- [ ] Скорость загрузки (PageSpeed Insights)
- [ ] Мобильная версия

ШАГ 6: АНАЛИЗ КОНКУРЕНТОВ
──────────────────────────────
- [ ] Топ страниц конкурентов:
      → скрипт: scripts/semrush_top_pages.py --domain competitor.ru --limit 50
- [ ] Backlink Gap — доноры конкурентов, которых нет у нас:
      → скрипт: scripts/semrush_backlink_gap.py --domain site.ru --competitors "c1.ru,c2.ru"

ШАГ 7: ПРОВЕРКА ДОНОРОВ
──────────────────────────────
- [ ] Пакетная проверка ИКС/DR найденных доноров:
      → скрипт: scripts/check_ics_dr.py --input donors.md --output results.md
- [ ] Отсеять доноров с ИКС < 10 или DR < 5

ШАГ 8: ОТЧЁТ
────────────────────
Приоритеты:
- 🔴 КРИТИЧНО (блокирует индексацию)
- 🟡 ВАЖНО (влияет на ранжирование)
- 🟢 ЖЕЛАТЕЛЬНО (улучшит)

Сохранить в: clients/[name]/seo/audit_YYYY-MM-DD.md
```

---

## Semrush API Integration

Ключ: `tokens.json → semrush` (проверить: `python3 -c "import json; print(json.load(open('/Users/antonk/artvision-data/tokens.json'))['semrush'])"`)

### Автоматическое использование при:
- **Keyword Research:** `semrush domain organic` → органические ключи конкурентов
- **Backlink Analysis:** `semrush backlinks` → ссылочный профиль
- **Backlink Gap:** `semrush backlink gap` → доноры конкурентов, которых нет у нас
- **Domain Overview:** `semrush domain overview` → трафик, ключи, позиции

### Скрипт:
```bash
python3 ~/artvision-data/scripts/semrush-api.py --domain example.com --report organic
python3 ~/artvision-data/scripts/semrush-api.py --domain example.com --report backlinks
python3 ~/artvision-data/scripts/semrush-api.py --domains "site1.com,site2.com" --report backlink-gap
```

### Когда вызывать:
- При SEO-аудите (ШАГ 1) — domain overview + `scripts/hybrid-seo-audit.py`
- При keyword research — organic keywords
- При анализе конкурентов (ШАГ 6) — `scripts/semrush_top_pages.py`
- При backlink analysis (ШАГ 6) — `scripts/semrush_backlink_gap.py`
- При проверке доноров (ШАГ 7) — `scripts/check_ics_dr.py`
- При линкбилдинге → перенаправлять на `/parasitic-seo` или `/outreach-emails`

---

## Команды для аудита

### Мета-теги (ТОЛЬКО curl!)
```bash
# Title
curl -sL "https://example.com" | grep -oE '<title>[^<]+</title>'

# Description
curl -sL "https://example.com" | grep -oE '<meta name="description"[^>]+>'

# Canonical
curl -sL "https://example.com" | grep -oE '<link rel="canonical"[^>]+>'

# OG теги
curl -sL "https://example.com" | grep -oE '<meta property="og:[^"]*"[^>]+>'

# Все мета-теги
curl -sL "https://example.com" | grep -E '<title|<meta|<link rel="canonical"' | head -20
```

### Sitemap
```bash
# Проверить наличие
curl -sI "https://example.com/sitemap.xml" | head -5

# Содержимое
curl -sL "https://example.com/sitemap.xml" | head -50

# Количество URL
curl -sL "https://example.com/sitemap.xml" | grep -c '<loc>'
```

### Robots.txt
```bash
curl -sL "https://example.com/robots.txt"
```

### hybrid-seo-audit.py
```bash
# Один сайт
python3 ~/artvision-data/scripts/hybrid-seo-audit.py --url https://example.com

# Все клиенты
python3 ~/artvision-data/scripts/hybrid-seo-audit.py --all
```

---

## Формат отчёта

```markdown
# SEO-аудит: [Название клиента]

**Дата:** YYYY-MM-DD
**Сайт:** https://example.com
**Аудитор:** Claude + hybrid-seo-audit.py

## Резюме
- Общая оценка: X/10
- Критичных проблем: N
- Важных: N
- Желательных: N

## 🔴 КРИТИЧНЫЕ проблемы

### 1. [Проблема]
- **Что:** описание
- **Где:** URL или место
- **Влияние:** как влияет на SEO
- **Решение:** конкретные шаги

## 🟡 ВАЖНЫЕ проблемы
...

## 🟢 РЕКОМЕНДАЦИИ
...

## Технические данные
- Title: [есть/нет, длина]
- Description: [есть/нет, длина]
- Sitemap: [URL, кол-во страниц]
- Robots.txt: [есть/нет]
- HTTPS: [да/нет]
- Скорость: [PageSpeed score]
```

---

## Частые ошибки (НЕ ПОВТОРЯТЬ!)

| Ошибка | Последствие | Правильно |
|--------|-------------|-----------|
| WebFetch для мета-тегов | "title пустой" (ложь) | curl -sL URL \| grep |
| Аудит без hybrid-seo-audit.py | Галлюцинации | Сначала скрипт |
| grep -P на macOS | Команда падает | grep -E или ggrep |
| Забыть sitemap | Пропустить проблему индексации | Всегда проверять |

---

You are an expert in search engine optimization. Your goal is to identify SEO issues and provide actionable recommendations to improve organic search performance.

## Initial Assessment

Before auditing, understand:

1. **Site Context**
   - What type of site? (SaaS, e-commerce, blog, etc.)
   - What's the primary business goal for SEO?
   - What keywords/topics are priorities?

2. **Current State**
   - Any known issues or concerns?
   - Current organic traffic level?
   - Recent changes or migrations?

3. **Scope**
   - Full site audit or specific pages?
   - Technical + on-page, or one focus area?
   - Access to Search Console / analytics?

---

## Audit Framework

### Priority Order
1. **Crawlability & Indexation** (can Google find and index it?)
2. **Technical Foundations** (is the site fast and functional?)
3. **On-Page Optimization** (is content optimized?)
4. **Content Quality** (does it deserve to rank?)
5. **Authority & Links** (does it have credibility?)

---

## Technical SEO Audit

### Crawlability

**Robots.txt**
- Check for unintentional blocks
- Verify important pages allowed
- Check sitemap reference

**XML Sitemap**
- Exists and accessible
- Submitted to Search Console
- Contains only canonical, indexable URLs
- Updated regularly
- Proper formatting

**Site Architecture**
- Important pages within 3 clicks of homepage
- Logical hierarchy
- Internal linking structure
- No orphan pages

**Crawl Budget Issues** (for large sites)
- Parameterized URLs under control
- Faceted navigation handled properly
- Infinite scroll with pagination fallback
- Session IDs not in URLs

### Indexation

**Index Status**
- site:domain.com check
- Search Console coverage report
- Compare indexed vs. expected

**Indexation Issues**
- Noindex tags on important pages
- Canonicals pointing wrong direction
- Redirect chains/loops
- Soft 404s
- Duplicate content without canonicals

**Canonicalization**
- All pages have canonical tags
- Self-referencing canonicals on unique pages
- HTTP → HTTPS canonicals
- www vs. non-www consistency
- Trailing slash consistency

### Site Speed & Core Web Vitals

**Core Web Vitals**
- LCP (Largest Contentful Paint): < 2.5s
- INP (Interaction to Next Paint): < 200ms
- CLS (Cumulative Layout Shift): < 0.1

**Speed Factors**
- Server response time (TTFB)
- Image optimization
- JavaScript execution
- CSS delivery
- Caching headers
- CDN usage
- Font loading

**Tools**
- PageSpeed Insights
- WebPageTest
- Chrome DevTools
- Search Console Core Web Vitals report

### Mobile-Friendliness

- Responsive design (not separate m. site)
- Tap target sizes
- Viewport configured
- No horizontal scroll
- Same content as desktop
- Mobile-first indexing readiness

### Security & HTTPS

- HTTPS across entire site
- Valid SSL certificate
- No mixed content
- HTTP → HTTPS redirects
- HSTS header (bonus)

### URL Structure

- Readable, descriptive URLs
- Keywords in URLs where natural
- Consistent structure
- No unnecessary parameters
- Lowercase and hyphen-separated

---

## On-Page SEO Audit

### Title Tags

**Check for:**
- Unique titles for each page
- Primary keyword near beginning
- 50-60 characters (visible in SERP)
- Compelling and click-worthy
- Brand name placement (end, usually)

**Common issues:**
- Duplicate titles
- Too long (truncated)
- Too short (wasted opportunity)
- Keyword stuffing
- Missing entirely

### Meta Descriptions

**Check for:**
- Unique descriptions per page
- 150-160 characters
- Includes primary keyword
- Clear value proposition
- Call to action

**Common issues:**
- Duplicate descriptions
- Auto-generated garbage
- Too long/short
- No compelling reason to click

### Heading Structure

**Check for:**
- One H1 per page
- H1 contains primary keyword
- Logical hierarchy (H1 → H2 → H3)
- Headings describe content
- Not just for styling

**Common issues:**
- Multiple H1s
- Skip levels (H1 → H3)
- Headings used for styling only
- No H1 on page

### Content Optimization

**Primary Page Content**
- Keyword in first 100 words
- Related keywords naturally used
- Sufficient depth/length for topic
- Answers search intent
- Better than competitors

**Thin Content Issues**
- Pages with little unique content
- Tag/category pages with no value
- Doorway pages
- Duplicate or near-duplicate content

### Image Optimization

**Check for:**
- Descriptive file names
- Alt text on all images
- Alt text describes image
- Compressed file sizes
- Modern formats (WebP)
- Lazy loading implemented
- Responsive images

### Internal Linking

**Check for:**
- Important pages well-linked
- Descriptive anchor text
- Logical link relationships
- No broken internal links
- Reasonable link count per page

**Common issues:**
- Orphan pages (no internal links)
- Over-optimized anchor text
- Important pages buried
- Excessive footer/sidebar links

### Keyword Targeting

**Per Page**
- Clear primary keyword target
- Title, H1, URL aligned
- Content satisfies search intent
- Not competing with other pages (cannibalization)

**Site-Wide**
- Keyword mapping document
- No major gaps in coverage
- No keyword cannibalization
- Logical topical clusters

---

## Content Quality Assessment

### E-E-A-T Signals

**Experience**
- First-hand experience demonstrated
- Original insights/data
- Real examples and case studies

**Expertise**
- Author credentials visible
- Accurate, detailed information
- Properly sourced claims

**Authoritativeness**
- Recognized in the space
- Cited by others
- Industry credentials

**Trustworthiness**
- Accurate information
- Transparent about business
- Contact information available
- Privacy policy, terms
- Secure site (HTTPS)

### Content Depth

- Comprehensive coverage of topic
- Answers follow-up questions
- Better than top-ranking competitors
- Updated and current

### User Engagement Signals

- Time on page
- Bounce rate in context
- Pages per session
- Return visits

---

## Common Issues by Site Type

### SaaS/Product Sites
- Product pages lack content depth
- Blog not integrated with product pages
- Missing comparison/alternative pages
- Feature pages thin on content
- No glossary/educational content

### E-commerce
- Thin category pages
- Duplicate product descriptions
- Missing product schema
- Faceted navigation creating duplicates
- Out-of-stock pages mishandled

### Content/Blog Sites
- Outdated content not refreshed
- Keyword cannibalization
- No topical clustering
- Poor internal linking
- Missing author pages

### Local Business
- Inconsistent NAP
- Missing local schema
- No Google Business Profile optimization
- Missing location pages
- No local content

---

## Output Format

### Audit Report Structure

**Executive Summary**
- Overall health assessment
- Top 3-5 priority issues
- Quick wins identified

**Technical SEO Findings**
For each issue:
- **Issue**: What's wrong
- **Impact**: SEO impact (High/Medium/Low)
- **Evidence**: How you found it
- **Fix**: Specific recommendation
- **Priority**: 1-5 or High/Medium/Low

**On-Page SEO Findings**
Same format as above

**Content Findings**
Same format as above

**Prioritized Action Plan**
1. Critical fixes (blocking indexation/ranking)
2. High-impact improvements
3. Quick wins (easy, immediate benefit)
4. Long-term recommendations

---

## Доступные скрипты (вызывать из workflow)

| Скрипт | Назначение | Пример вызова |
|--------|-----------|---------------|
| `scripts/semrush_backlink_gap.py` | Backlink Gap через Playwright + SEMrush | `python3 scripts/semrush_backlink_gap.py --domain site.ru --competitors "c1.ru,c2.ru"` |
| `scripts/semrush_top_pages.py` | Топ страниц конкурентов из SEMrush | `python3 scripts/semrush_top_pages.py --domain competitor.ru --limit 50` |
| `scripts/check_ics_dr.py` | Пакетная проверка ИКС/DR через be1.ru | `python3 scripts/check_ics_dr.py --input donors.md --output results.md` |
| `scripts/hybrid-seo-audit.py` | Технический SEO-аудит (Screaming Frog + факты) | `python3 scripts/hybrid-seo-audit.py --url site.ru` |

---

## Tools Referenced

**Free Tools**
- Google Search Console (essential)
- Google PageSpeed Insights
- Bing Webmaster Tools
- Rich Results Test
- Mobile-Friendly Test
- Schema Validator

**Paid Tools** (if available)
- Screaming Frog
- Ahrefs / Semrush
- Sitebulb
- ContentKing

---

## Questions to Ask

If you need more context:
1. What pages/keywords matter most?
2. Do you have Search Console access?
3. Any recent changes or migrations?
4. Who are your top organic competitors?
5. What's your current organic traffic baseline?

---

## Keyword Research Process

1. **Seed keywords:** Core topics клиента
2. **Expansion:** Related terms, questions (Wordstat, Keys.so)
3. **Analysis:** Volume, difficulty, intent
4. **Mapping:** Keywords → pages (1 страница = 1 основной кластер)
5. **Prioritization:** Opportunity scoring (высокая частота + низкая конкуренция)

### Search Intent Types — определяется ПО ВЫДАЧЕ, не по словам в запросе

**КЛЮЧЕВОЕ ПРАВИЛО (Антон 09.05.2026):**
Интент = **что Яндекс/Google показывает в ТОП-10**, а не что написано в запросе.
Маркеры в запросе («цена», «купить», «лучшие») — подсказка, **не определение**.

| Intent | Определение по SERP (ТОП-10) | Что юзер делает на странице |
|--------|------------------------------|------------------------------|
| **Коммерческий** | **80-90% ТОП-10 = страницы услуг / товаров / категорий товаров** | Читает что это, характеристики, цена → заказывает/покупает |
| **Информационный** | 80-90% ТОП-10 = статьи / гайды / Wikipedia / медэнциклопедии / справочники | Узнаёт информацию, не покупает |
| **Транзакционный** | ТОП-10 = карточки товаров / формы заказа / прямые offers | Готов оплатить прямо сейчас |
| **Навигационный** | ТОП-1 = конкретный бренд / сайт / приложение | Ищет конкретный ресурс |
| **Смешанный** | ТОП-10 = mix статей и услуг (50/50) | Сложный кейс — отдельная посадочная или две |

**Примеры (КАК ПРОВЕРИТЬ интент):**
- «курсы массажа спб» — без слова «цена», но ТОП-10 = школы с программами+ценами+формой записи → **коммерческий**
- «что такое массаж» — ТОП-10 = Wikipedia, медпорталы, статьи → **информационный**
- «лучшие SEO инструменты» — ТОП-10 = обзоры, рейтинги, сравнения статей → **информационный** (НЕ коммерческий!)
- «купить массажный стол» — ТОП-10 = карточки товаров → **транзакционный**
- «ahrefs вход» — ТОП-1 = ahrefs.com → **навигационный**

**Как применять при сборе семантики:**
1. Собрать список запросов по теме клиента (Wordstat, ключи конкурентов)
2. **Для каждого** — снять SERP ТОП-10 (Topvisor / Playwright / WebSearch)
3. Классифицировать по типу страниц в ТОП-10
4. **На одной посадочной = только запросы одного интента.** Смешивать = терять позиции
5. Запросы с разным интентом одного корня = РАЗНЫЕ страницы:
   - «массаж» (комм SERP) → услуга
   - «что такое массаж» (инфо SERP) → статья в блоге → перелинковка на услугу

Для spb-kursy.ru пример (массаж):
- **комм** (ТОП-10 = школы): курсы массажа спб, обучение массажу спб, школа массажа спб, курсы медицинского массажа спб, диплом массажиста спб
- **инфо** (ТОП-10 = статьи): как стать массажистом, виды массажа, профстандарт массажиста, что нужно для работы массажистом
- **транз** (ТОП-10 = формы): записаться на курсы массажа, оплатить обучение массажу, поступить на массажиста спб
- **нав** (ТОП-1 = конкретный бренд): «{бренд школы} официальный сайт» — для presale не критично

---

## Off-Page SEO / Link Building

- Digital PR и упоминания бренда
- Guest posting на тематических ресурсах
- Партнёрские ссылки
- Анализ бэклинков конкурентов (Ahrefs/Semrush)
- Посевы и крауд-маркетинг

### Ключевые метрики

| Метрика | Инструмент |
|---------|-----------|
| Organic traffic | GA4 / Метрика |
| Keyword rankings | Topvisor / Keys.so |
| Domain Rating | Ahrefs |
| Core Web Vitals | Search Console |
| Backlinks | Ahrefs / Semrush |
| CTR | Search Console |

---

## Related Skills

- **programmatic-seo**: For building SEO pages at scale
- **schema-markup**: For implementing structured data
- **page-cro**: For optimizing pages for conversion (not just ranking)
- **analytics-tracking**: For measuring SEO performance
- **parasitic-seo** — для линкбилдинга через площадки (НЕ seo-master)
- **content-writer** — для создания контента
- **outreach-emails** — для outreach-писем

---

## SEO-правила DrMax + Шакин (обновлено 2026-03-08)

### Robots.txt (10 правил)
- Файл СТРОГО в корне (`/robots.txt`), только нижний регистр, UTF-8, HTTP 200
- Максимум 1024 директив, максимум 500 КБ
- Каждый запрещённый путь — отдельная строка `Disallow`
- `Host:` для Яндекса без `http://` и без слеша в конце
- `Sitemap:` объявлять явно с полным URL
- Пагинация: НЕ закрывать через robots.txt — использовать `<meta name="robots" content="noindex, follow">`
- JS и CSS файлы НЕ закрывать от индексации (нужны краулеру для рендеринга)
- Создавать отдельные секции User-agent для Google и Яндекс
- Google: побеждает самая длинная совпадающая директива
- Яндекс: Allow приоритетнее Disallow при равной длине

### Sitemap.xml (8 правил)
- Максимум 50 000 URL на файл, максимум 50 МБ несжатый
- Оптимальный размер: до 10 000 URL на файл (лучше индексируется)
- `<lastmod>` — использовать и обновлять при реальных изменениях
- `<priority>` и `<changefreq>` — поисковики игнорируют, удалить для уменьшения размера
- Включать ТОЛЬКО канонические URL с HTTP-статусом 200
- НЕ включать: страницы с noindex, закрытые robots.txt, 404, редиректы
- Генерировать динамически, не раз в месяц вручную
- Sitemap НЕ заменяет внутреннюю перелинковку — только дополняет краулинг

### Core Web Vitals (пороги)
- LCP: до 2.5 сек (хорошо), 2.5–4.0 (улучшить), >4.0 (плохо)
- CLS: до 0.1 (хорошо), 0.1–0.25 (улучшить), >0.25 (плохо)
- INP: до 200 мс (хорошо), 200–500 мс (улучшить)
- Каждая дополнительная секунда загрузки = -20% конверсии
- Ориентир: не быстрее всех, а быстрее лидеров ТОПа по нише
- Сайты без CWV теряют ~3.7% видимости; выполняющие — +1%
- HTTPS + HTTP/2 — обязательное условие
- CSS — во внешние файлы, не inline (для кешируемости)

### Мобильная версия (7 пунктов)
- >50% запросов с мобильных — Mobile First приоритет
- 70% органической выдачи различается между десктопом и мобайлом
- На мобайле: скрывать второстепенный контент в табы/аккордеоны
- Меню мобайл = идентично десктоп по структуре
- Отключить авто-прокрутку слайдеров на мобайле
- Минимальный размер шрифта основного текста: 15px
- Сравнивать отказы/время/глубину для мобайл vs десктоп — находить проблемы

### SSL, редиректы, дубли
- HTTPS обязателен — без него пометка "ненадёжный"
- Редиректы: максимум 2 перехода (301→301→финал = 2 hop max)
- Canonical на все дублирующиеся страницы
- Пагинация: `noindex, follow`
- Страницы категорий: excerpt вместо полного текста
- URL: статические (`/slug/`), не динамические (`?id=123`), до 4–5 сегментов

### Структурированные данные (Schema.org / JSON-LD)
- JSON-LD предпочтителен (размещать в header или footer)
- Данные в разметке ОБЯЗАТЕЛЬНО должны отображаться на странице визуально — иначе санкции
- Для локального бизнеса: конкретный тип (Dentist, Attorney, Physician), не общий LocalBusiness
- Обязательные поля NAP: Name, Address, Phone
- Рекомендованные: часы работы, lat/long, email, URL, логотип, соцсети
- Для YMYL: MedicalCondition, MedicalTherapy, HowTo, ClaimReview
- Для авторов: Person/Author + reviewedBy
- Валидировать через Google Rich Results Test и Яндекс валидатор перед деплоем

### Текстовые факторы (Title, H1, мета, LSI)
- Title первые 52 символа: 1–2 полных предложения по 4U (Useful, Urgent, Unique, Ultra-specific)
- Title 53+ символы: ключи второго приоритета, в конце — бренд через тире
- Google может перезаписывать Title — фокус на H1, анкоры, качество контента
- Meta Description: 120–133 символа, USP + транзакционные маркеры, НЕ набивать ключами
- H1: один на страницу, содержит главный ключ, НЕ дублирует Title
- H2: минимум 5 секций, заголовки иерархичны (не пропускать уровни)
- LSI-термины: 5–6 экземпляров на 1 000 слов
- ВЧ-слова: максимум 10–15 на 1 000 слов
- НЕ ставить `<b>`/`<strong>` на ключевые слова — риск -50 позиций (воспринимается как спам)
- Для визуального выделения ключей — использовать CSS-стили, не HTML-теги

### CTR и сниппеты (пороги)
- Отличный CTR: 15%+ | Средний: 7–8% | Плохой: 1–2%
- Каждый +3% CTR ≈ +1 позиция в выдаче (Moz, подтверждено Шакиным 2026-04)
- Title для CTR: 4U в первых 52 символах, общая длина в коде 200+ символов
- Meta Description для CTR: USP + маркеры ("бесплатно", "доставка", "гарантия", "цена")
- Пороги аудита: малый сайт от 100 показов/мес, крупный от 1 000 показов/мес
- После обновления: дата модификации + GSC/Вебмастер переиндексация + мониторинг CTR еженедельно

### Snippet CTR boost (продвинутые приёмы)
- **Graphic emoji** — Google вырезает большинство. Перед использованием проверять в SERP через Pixel Tools (serp.pixel-tools.com) или ручной поиск: `купить X 🎁` — если эмодзи виден в выдаче, то можно использовать
- **ASCII/текстовые emoji** — Google НЕ вырезает: `(´･ω･`)`, `[◉_◉]`. Нишевый приём, НЕ для B2B-серьёзных тематик. Подходит для развлекательных/молодёжных ниш
- **Word-triggers словарь** — копить по тематикам свои триггеры повышающие CTR. Примеры: RU — "со скидкой", "официальный", "за 1 день", "без предоплаты" | EN — "you can't get cheaper", "#1 rated", "limited time"
- **Автоанализ сниппетов конкурентов** — периодически сверять title/description топ-10 по ключевым запросам (Screaming Frog custom extraction + сравнение с нашим текущим snippet). Выдаёт какие триггеры работают в нише

### Аудит технических ошибок (пайплайн)
- Битые внутренние ссылки: Screaming Frog, устранять сразу
- Цепочки редиректов: максимум 2 перехода
- Дубли мета-тегов: каждый title и description уникальный
- Страницы без мета-тегов: заполнить все
- Orphaned pages: добавить внутренние ссылки или удалить
- Аудит бэклинков: раз в квартал (Semrush, Ahrefs), токсичные — Google Disavow

### Внутренняя перелинковка (семантический кокон)
- Трёхуровневая иерархия: мать (ВЧ) → дочерние (расширяют тему) → внучатые (узкая тема)
- Минимум 3 лексических вариации анкора для каждой ссылки
- Контекст вокруг ссылки: 15 слов с каждой стороны, 2–4 предложения в абзаце
- SILO: внутри кластера ссылаются свободно, между кластерами — только при семантической связи
- Все страницы доступны с главной в не более 3 кликов
- Блок "Похожие материалы" в конце каждой статьи

### TF-IDF анализ посадочных страниц (ОБЯЗАТЕЛЬНО при аудите контента)

**Цель:** сравнить терминологический профиль нашей страницы vs ТОП-20 конкурентов в Яндекс И Google.

#### Методология
```
1. Определить primary keyword для каждой посадочной
2. Собрать ТОП-20 из Google (WebSearch) + ТОП-20 из Яндекс (Topvisor API или WebFetch yandex.ru/search/?text=...&lr=213)
3. WebFetch контент 10-15 конкурентов (из обоих ПС)
4. Извлечь текст (strip HTML, удалить nav/footer/scripts)
5. Tokenize: биграммы + триграммы (не только юниграммы!)
6. Рассчитать TF-IDF для каждого терма на каждой странице
7. Сравнить наш профиль vs среднее конкурентов
```

#### Классификация термов
| Статус | Определение | Действие |
|--------|------------|----------|
| **MISSING** | TF-IDF >0.01 у конкурентов, отсутствует у нас | Добавить в контент |
| **UNDERUSED** | Наш TF-IDF < 50% от среднего конкурентов | Увеличить частоту |
| **OVERUSED** | Наш TF-IDF > 200% от среднего | Разбавить синонимами |
| **UNIQUE** | Есть только у нас | Сохранить (дифференциация) |

#### Hard/Soft кластеризация запросов
- **Hard кластер:** пересечение ТОП-10 в SERP ≥3 URL → ОДИН кластер → ОДНА посадочная
- **Soft кластер:** пересечение 1-2 URL → разные кластеры, но связаны перелинковкой
- **Проверка:** для каждого запроса кластера — сравнить SERP. Если выдача кардинально отличается → отдельная страница
- Маркерные ключи с разным интентом (коммерческий vs инфо) = РАЗНЫЕ кластеры даже при одном корне

#### Поисковые системы (обязательно ОБЕ)
- **Google:** WebSearch → TOP-20
- **Яндекс:** Topvisor API (positions_2/history) или WebFetch yandex.ru/search/?text={query}&lr={region}
- Сравнивать профили отдельно: что важно в Яндекс может не совпадать с Google
- Финальные рекомендации = пересечение важных термов из обоих ПС

#### Формат отчёта TF-IDF
```markdown
## [URL] — [Primary Keyword]

### Яндекс TOP-20 анализ
| Терм | Наш TF-IDF | Средний конкурентов | Gap | Приоритет |

### Google TOP-20 анализ
| Терм | Наш TF-IDF | Средний конкурентов | Gap | Приоритет |

### Пересечение (оба ПС)
| Терм | Важность Яндекс | Важность Google | Действие |

### Hard clustering check
- SERP overlap: [X из 10 URL совпадают между запросами кластера]
- Вердикт: [одна посадочная / разделить]
```

#### Автоматизация
```bash
# Python скрипт для TF-IDF (сохранить в scripts/)
python3 ~/artvision-data/scripts/tfidf-landing-audit.py --url [URL] --keyword "[keyword]" --top 20
```

#### Передача ссылочных весов (Link Equity Flow)
После TF-IDF — проверить внутреннюю перелинковку:
1. Crawl всех страниц → граф ссылок
2. PageRank distribution (damping=0.85, 20 итераций)
3. Выявить: orphan pages, dead ends, weight leaks, перекос на главную
4. Анкорный анализ: keyword-rich vs generic ("подробнее")
5. Рекомендации: конкретные ссылки (откуда → куда → с каким анкором)
