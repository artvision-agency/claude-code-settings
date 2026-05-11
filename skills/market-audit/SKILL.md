---
name: market-audit
description: 5 параллельных subagents для маркетингового аудита сайта (РФ-адаптация). Content+Conversion+Technical+Competitive+Strategy. Scoring 0-100 + HTML report. Триггеры — market audit, маркетинг аудит, /market-audit, пилотный аудит, аудит сайта клиента, marketing audit, comprehensive audit.
---

# Market Audit — оркестратор 5 параллельных аудитов (РФ)

Полный маркетинговый аудит сайта через 5 параллельных subagents.
Каждый — свой домен (content/conversion/technical/competitive/strategy), своя scoring rubric 0-100, своя секция в финальном HTML report.

**РФ-адаптация zubair-trabzada/ai-marketing-claude:** Я.Метрика вместо GA, Я.Карты+2GIS вместо Google Maps, ВК+Дзен+Habr вместо Twitter+Reddit, Топвизор+Wordstat вместо SEMrush, llms.txt для GEO.

## Когда применять

| Триггер | Описание |
|---|---|
| Presale recon | Перед звонком новому клиенту — за 4-6 мин полная картина |
| Квартальный check | Аудит активных клиентов раз в квартал |
| Drop в трафике/конверсии | Диагностика после падения метрик |
| Pre-КП discovery | Сбор фактов до начала /presale-kp |
| Конкурент-bench | Сравнение клиент vs топ-3 конкурента (с флагом `--competitive-deep`) |

**НЕ применять:** для simple landing-only (1 страница) — нет смысла в 5 subagents. Для одного бренда продаваемого товара — `/cro` достаточно.

---

## Inputs

```yaml
url: https://artvision.pro              # обязательно
brand_name: Artvision                   # опционально, иначе из <title>
region: msk                              # опционально, для locale-context: msk|spb|kazan|...
industry_hint: medical|saas|ecom|...    # опционально, ускоряет детект
output_dir: ~/artvision-data/clients/<slug>/seo/  # по умолчанию
```

Если клиент медицинский — обязательно подгружать `lr_id` из `~/.claude/rules/medical-kp.md` для Topvisor-checks.

---

## Pipeline (3 фазы)

### Фаза 1 — Discovery (1-2 мин)

ДО запуска subagents:

1. **WebFetch homepage** → сохранить `<title>`, `<h1>`, meta description, главный CTA
2. **WebFetch до 5 ключевых страниц** — /price, /about, /services|/products, /blog, /contacts (если найдены через regex по homepage)
3. **Детект business type** по сигналам:
   - **Medical/B2B** — лицензии, ФИО врачей, «запись», «филиал», ИНН
   - **SaaS/Software** — «попробовать бесплатно», pricing tiers, API docs, login
   - **E-commerce** — корзина, каталог, отзывы товаров, доставка
   - **Agency/Services** — кейсы, портфолио, «работа с нами», testimonials
   - **Local Business** — адрес, телефон, часы работы, карта Я.Карт
   - **Marketplace** — две стороны, листинги, рейтинги исполнителей
4. **Region detection** — телефонный код (+7 495 = МСК lr=213, +7 812 = СПб lr=2, +7 843 = Казань lr=43)
5. **Page map** — список URL + title + role для каждого subagent

### Фаза 2 — Parallel analysis (3-5 мин — самая длинная фаза)

Запустить 5 Task tool calls **параллельно** (в одном assistant message, не последовательно):

```
Task 1: subagent_type=general-purpose, prompt = "Ты — content auditor. URL=<url>, brand=<brand>, business_type=<type>. Rubric: <загружен из references/scoring-rubric.md секция Content>. Проанализируй: TF-IDF главной, content gap vs top-3 (по поиску), AI writing detection (commas, em-dashes, jargon density), tone-of-voice consistency, blog quality. Verify фактчек URL через WebFetch. Output: JSON {"score": 0-100, "findings": [...], "recommendations": [...], "evidence_urls": [...]}"

Task 2: subagent_type=general-purpose, prompt = "Ты — conversion auditor. ... CTA effectiveness, form friction (полей >5 = -10), popup timing, mobile CTA visibility, trust signals near CTA, pricing page (если есть), signup flow ..."

Task 3: subagent_type=general-purpose, prompt = "Ты — technical auditor. ... Core Web Vitals (PSI mobile+desktop), schema markup, robots.txt+sitemap.xml+llms.txt, mobile viewport, CSP+HTTPS, alt-tags, internal linking depth ...

ВАЖНО — для analytics + schema detection ВСЕГДА использовать robust-детектор:
```python
import sys; sys.path.insert(0, '/Users/antonk/.claude/skills/market-audit/scripts')
from analytics_detector import detect_analytics_robust, count_schema_types
analytics = detect_analytics_robust(html)   # 3-source: plain_js/base64/noscript/preconnect
schema = count_schema_types(html)            # BeautifulSoup-based, видит @graph nested types
```
Confidence: high (3+ sources) / medium (2) / low (1) — ВСЕГДА указывать в finding.
Простой grep `ym(NNN,` падает на WP+LiteSpeed/Autoptimize (33% false positive — prev session pilot 2026-05-11). Использовать `detect_analytics_robust` обязательно."

Task 4: subagent_type=general-purpose, prompt = "Ты — competitive auditor. ... Найди топ-3 конкурента (Яндекс СПб/МСК top-10 по основному запросу), сравни backlink profile (если данных нет — на основе ИКС/возраст), content depth, pricing positioning. Используй WebSearch + WebFetch ..."

Task 5: subagent_type=general-purpose, prompt = "Ты — strategy auditor. ... Позиционирование (1-line value prop), ICP detection (кому продаётся, явные сигналы), recipient-personalization (3 тезиса под топ-роль), ToV match audience, trust signals (about, team, ИНН, лицензии), growth loops ..."
```

**Каждый subagent получает:**
1. URL клиента + brand + business_type + region
2. Свою секцию scoring rubric из `references/scoring-rubric.md`
3. Инструкцию вывода: строгий JSON `{"score": 0-100, "findings": [...], "recommendations": [...], "evidence_urls": [...]}`
4. Доступ к WebFetch/WebSearch (через `general-purpose` тип)

**Если subagent падает / timeout >5 мин** — пометить `partial: true` в финальном отчёте, остальные 4 идут как есть.

### Фаза 3 — Synthesis (1-2 мин)

1. Собрать 5 JSON outputs
2. Compute composite score (взвешенное среднее):
   ```
   Marketing Score = (
       Content      * 0.25 +
       Conversion   * 0.20 +
       Technical    * 0.20 +
       Competitive  * 0.15 +
       Strategy     * 0.20
   )
   ```
3. Grade interpretation:
   - 85-100 = A (Excellent)
   - 70-84 = B (Good)
   - 55-69 = C (Average)
   - 40-54 = D (Below average)
   - 0-39 = F (Critical)
4. Aggregate recommendations → классифицировать:
   - **Quick wins** (<1 неделя, low effort)
   - **Strategic** (1-4 недели, medium effort)
   - **Long-term** (1-3 месяца, high effort)
5. Render HTML report через шаблон ниже

---

## Output

### Primary: HTML report

Путь: `<output_dir>/market-audit-<slug>-YYYY-MM-DD.html`

По умолчанию для клиентов: `~/artvision-data/clients/<slug>/seo/market-audit-<date>.html`
Для пилотов / своего сайта: `~/artvision-data-orchestrator-week1/scripts/orchestrator/_pilot/market-audit-<slug>-<date>.html`

Структура HTML:

```html
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <title>Market Audit — {brand} — {date}</title>
  <style>
    /* Простой clean стиль. НЕ КП-template. Стандартный sans-serif, таблицы. */
    body { font-family: -apple-system, system-ui, sans-serif; max-width: 1200px; margin: 2em auto; padding: 0 1em; color: #222; }
    h1 { border-bottom: 3px solid #2c3e88; padding-bottom: 0.3em; }
    h2 { margin-top: 2em; color: #2c3e88; }
    table { border-collapse: collapse; width: 100%; margin: 1em 0; }
    th, td { border: 1px solid #ddd; padding: 0.5em 0.8em; text-align: left; }
    th { background: #f5f6fa; }
    .score-A { color: #15803d; font-weight: 700; }
    .score-B { color: #84cc16; }
    .score-C { color: #d97706; }
    .score-D { color: #ea580c; }
    .score-F { color: #dc2626; font-weight: 700; }
    .bar { display: inline-block; height: 8px; background: #2c3e88; border-radius: 2px; vertical-align: middle; }
    .section { background: #fafbfc; padding: 1em; border-left: 4px solid #2c3e88; margin: 1em 0; }
    code { background: #f0f2f5; padding: 0.1em 0.4em; border-radius: 3px; }
  </style>
</head>
<body>
  <h1>Market Audit — {brand}</h1>
  <p><strong>URL:</strong> <a href="{url}">{url}</a> · <strong>Дата:</strong> {date} · <strong>Тип бизнеса:</strong> {industry} · <strong>Регион:</strong> {region}</p>

  <h2>Итоговая оценка: <span class="score-{grade}">{score}/100 ({grade})</span></h2>

  <h2>Score Breakdown</h2>
  <table>
    <thead><tr><th>Категория</th><th>Score</th><th>Вес</th><th>Взвешено</th><th>Ключевая находка</th></tr></thead>
    <tbody>
      {rows: one per subagent}
    </tbody>
  </table>

  <h2>Quick Wins (на этой неделе)</h2>
  <ol>{quick_wins as li}</ol>

  <h2>Strategic Recommendations (этот месяц)</h2>
  <ol>{strategic as li}</ol>

  <h2>Long-Term Initiatives (квартал)</h2>
  <ol>{long_term as li}</ol>

  <h2>Detailed Findings by Category</h2>
  {for each subagent: <div class="section"><h3>{name}</h3><p>Score: {score}/100</p><ul>{findings}</ul><h4>Recommendations</h4><ul>{recs}</ul></div>}

  <p><em>Generated by /market-audit · Artvision orchestrator week1</em></p>
</body>
</html>
```

### Secondary: stdout summary

```
═══════════════════════════════════════════
  Market Audit — {brand} ({url})
═══════════════════════════════════════════
  Marketing Score: {score}/100 (Grade: {grade})

  Content & Messaging:     {XX}/100  ████████░░
  Conversion Optimization: {XX}/100  ██████░░░░
  Technical & SEO:         {XX}/100  ███████░░░
  Competitive Positioning: {XX}/100  █████░░░░░
  Strategy & Growth:       {XX}/100  ██████░░░░

  Top 3 Quick Wins:
    1. ...
    2. ...
    3. ...

  Report: {html_path}
  Wall-clock: {N}m {M}s
═══════════════════════════════════════════
```

---

## Rules & integration

- **Запрет AI-маркеров в публичных отчётах** (`security.md`): не «AI-аудит», не «нейросеть», не «GPT»/«Claude». Заменять на «авторская методология»/«экспертная аналитика».
- **Factcheck перед HTML** (`quality.md`): все URL в evidence_urls проверяются `curl -sI` → 200. Findings без evidence_urls = UNCONFIRMED, не показываются в публичной версии.
- **Recipient-personalization** (`recipient-personalization.md`): strategy subagent выдаёт 3 тезиса под top-role.
- **Industry-aware rubric**: medical = строже на trust signals/licenses, SaaS = строже на pricing/funnel, e-com = строже на reviews/cart.
- **No-smoothing** (`no-smoothing.md`): если subagent не нашёл данных — пишет «нет данных», не «возможно есть».

---

## Anti-patterns

| ❌ | ✅ |
|---|---|
| Запустить 5 subagents последовательно | ОДИН message с 5 Task calls = параллельно |
| Передать subagent весь rubric | Только свою секцию (token budget) |
| Грузить общий output в LLM-маркеры | Чистый clean HTML без emoji/жаргона |
| Оценивать medical как SaaS | Industry-detection в Фазе 1 — обязательно |
| Финал без factcheck evidence_urls | Все URL проверять `curl -sI` |

---

## Cross-skill

После /market-audit логично:
- `/presale-kp` — если планируется КП
- `/cro` — фокус на conversion findings
- `/seo-master` — углубление technical секции
- `/cons` — стратсессия по findings

## Pilot reference

Первый pilot: artvision.pro (2026-05-11) — see `~/artvision-data-orchestrator-week1/scripts/orchestrator/_pilot/market-audit-artvision-pro-2026-05-11.html`.
