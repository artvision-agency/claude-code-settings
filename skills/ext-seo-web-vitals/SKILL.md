---
name: ext-seo-web-vitals
description: External Google Chrome web-vitals library (8.5K⭐ Apache-2.0). Official JS snippet for real-user Core Web Vitals (LCP, INP, CLS). Field data collection — НЕ lab data. Use when устанавливаем CWV-метрики на клиентский сайт для GA4/Метрики. Triggers — 'web vitals', 'cwv field', 'real user metrics', 'lcp inp cls', 'core web vitals js', 'ext-seo-web-vitals'.
---

# ext-seo-web-vitals — real-user CWV метрики

**Upstream:** github.com/artvision-agency/web-vitals ← GoogleChrome/web-vitals (8.5K⭐, Apache-2.0)
**Category:** SEO / CWV
**Use case:** JS snippet встроить в сайт клиента → собирать **field data** (real users), а не lab data PSI/Lighthouse.

## Lab vs Field — критическое различие

- **Lab data** (lhci, PSI, наш `/perf-bench`) — синтетический прогон в идеальных условиях
- **Field data** (web-vitals JS) — реальные пользователи, реальные устройства, реальная сеть
- Часто расхождение 20-40%. Google Search Console использует именно field data (CrUX)

## Когда вызывать

- Установить CWV-метрики на клиентский сайт (OTIDO, Творим, Blumart)
- Собрать field data → отправить в GA4/Я.Метрику
- Cross-check с lab data (расхождение signals проблему)
- A/B test: до/после optimization changes

## Как пользоваться

```bash
gh repo clone artvision-agency/web-vitals ~/forks/web-vitals
# Скопировать в сайт клиента (vanilla JS snippet):
```

```html
<script type="module">
  import {onCLS, onINP, onLCP} from 'https://unpkg.com/web-vitals@5?module';
  function sendToAnalytics(metric) {
    // отправка в GA4 / Я.Метрику / endpoint
    fetch('/api/vitals', {body: JSON.stringify(metric), method: 'POST'});
  }
  onCLS(sendToAnalytics);
  onINP(sendToAnalytics);
  onLCP(sendToAnalytics);
</script>
```

## A/B vs наш `/perf-bench` (lab)

- Установить на artvision.pro/blumart-orm-dashboard → 7 дней field data
- Сравнить с lab PSI score
- Метрика: расхождение % по LCP/INP/CLS
- Inform клиента: «лаба показывает X, real users Y — разница из-за Z»

## Связанные

- Lab tools: `/perf-bench` (наш), `@lhci/cli` (adopted)
- Research: `~/artvision-data/research/2026-05-20-agency-tools-discovery/01-seo-crawl.md`
