---
name: ext-an-matomo
description: External privacy-focused web analytics (matomo-org/matomo, 21K⭐ GPL-3.0). Self-hosted Google Analytics alternative. **Критично для NDA-клиентов** (Blumart 🔒) и медицинских клиник (152-ФЗ + 323-ФЗ compliance). Triggers — 'matomo', 'analytics self-host', 'аналитика без google', 'privacy analytics', 'ga4 альтернатива', '152 фз analytics', 'ext-an-matomo'.
---

# ext-an-matomo — privacy-first web analytics

**Upstream:** github.com/artvision-agency/matomo ← matomo-org/matomo (21K⭐, GPL-3.0 ⚠️)
**Category:** Analytics
**Use case:** Self-hosted alternative GA/Я.Метрика. Полный контроль data + GDPR/152-ФЗ compliance.

## ⚠️ GPL-3.0 — per-instance deploy

- ✅ OK: каждый client получает свой Matomo на нашем VPS
- ❌ NOT OK: модификации Matomo + продажа closed-source SaaS

## Когда вызывать (критично для нашего портфеля)

- **Blumart 🔒 NDA** — нельзя отправлять данные в Google Analytics
- **Медицинские клиники** (152-ФЗ + 323-ФЗ) — privacy compliance
- **OTIDO, Творим** — full data ownership как UPSELL feature
- Когда Я.Метрика недоступна (зарубежные клиенты — RicheList Европа/ОАЭ)

## Как пользоваться

```bash
gh repo clone artvision-agency/matomo ~/forks/matomo
cd ~/forks/matomo
# Docker compose:
docker compose up -d
# или официальный installer:
curl -L https://builds.matomo.org/matomo.zip -o matomo.zip
```

## Snippet на клиентский сайт

```html
<script>
var _paq = window._paq = window._paq || [];
_paq.push(['trackPageView']);
_paq.push(['enableLinkTracking']);
(function() {
  var u="https://matomo.artvision.pro/";
  _paq.push(['setTrackerUrl', u+'matomo.php']);
  _paq.push(['setSiteId', '1']); // unique per client
  var d=document, g=d.createElement('script'), s=d.getElementsByTagName('script')[0];
  g.async=true; g.src=u+'matomo.js'; s.parentNode.insertBefore(g,s);
})();
</script>
```

## A/B vs Google Analytics + Я.Метрика

- Метрика: data completeness, privacy compliance score, owned-data
- Кейс: blumart-orm-dashboard → 2 недели Matomo vs Я.Метрика → coverage diff

## Возможность upsell

Predict «Artvision Privacy Analytics» — для NDA/медицинских клиентов как премиум-add-on +20K/мес.

## Связанные

- Research: `~/artvision-data/research/2026-05-20-agency-tools-discovery/07-analytics-dashboards.md`
- PII compliance: `/ext-content-pii` (Wave 1)
