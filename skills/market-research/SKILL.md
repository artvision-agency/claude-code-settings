---
name: market-research
description: >-
  Universal market research for any product, business, or game.
  Auto-detects type (SaaS, mobile app, game, local business, e-commerce, service).
  Competitor factcheck, country microplans (messengers, marketplaces, payments),
  TAM/SAM/SOM, monetization models, free/paid promotion channels, launch timeline,
  demographic analysis. Generates visual HTML report with CSS charts (no JS).
  Triggers: 'market research', 'исследование рынка', 'анализ рынка',
  'competitor analysis', 'конкуренты', 'TAM SAM SOM', 'market size',
  'размер рынка', 'game analytics', 'игровая аналитика', 'CPI',
  'product research', 'go-to-market research', 'GTM research',
  'business analysis', 'аналитика продукта', 'рыночный анализ'
user-invocable: true
disable-model-invocation: false
allowed-tools: Read Write Edit Bash Grep Glob Agent WebSearch WebFetch
metadata:
  author: artvision
  version: "2.0"
  category: market-research
---

# Market Research

Generate comprehensive market research for ANY product type.
Output: self-contained HTML with dark theme, CSS-only charts, tooltips, print styles.

## Step 0: Detect Product Type

Analyze user input and classify:

| Type | Indicators | Special Sections |
|------|-----------|-----------------|
| **Game** | game, play, level, PvP, multiplayer | CPI, platform costs, game stores, streaming |
| **SaaS** | app, platform, subscription, B2B | MRR/ARR, churn, CAC/LTV, integrations |
| **Mobile App** | app, iOS, Android, download | ASO, CPI, store optimization, retention |
| **Local Business** | clinic, restaurant, salon, city | Local SEO, maps, reviews, foot traffic |
| **E-commerce** | shop, store, products, delivery | AOV, ROAS, marketplace fees, logistics |
| **Service/Agency** | consulting, agency, outsource | Lead gen, sales cycle, proposal win rate |

Adapt ALL sections below to the detected type. If unclear, ASK.

## Input

User provides:
- Product name and concept
- Optional: target countries, budget, monetization

If not provided, ASK:
1. Product name + 1-sentence description
2. What makes it unique (vs alternatives)
3. Target market (countries/segments)
4. Budget range (0 / low / medium / high)

## Workflow

### Phase 1: Competitive Intelligence

Launch research agent(s) to find competitors:

**For Games:**
- Direct (same genre+mechanics), Adjacent (same genre), Platform (same store)
- Check Steam, App Store, Google Play, itch.io, TG Mini Apps
- Uniqueness Matrix: 4-6 elements, score 0/1 per competitor

**For SaaS/Apps:**
- Direct (same problem), Indirect (different approach), Substitutes
- Check G2, Capterra, ProductHunt, AlternativeTo, TrustPilot
- Feature Matrix: core features comparison table

**For Local Business:**
- Local competitors (same city/area)
- Check Yandex Maps, 2GIS, Google Maps reviews
- Service/price comparison table

**For E-commerce:**
- Same niche marketplaces + independent stores
- Check pricing, delivery, reviews, USP
- Price positioning matrix

### Phase 2: Market Sizing (TAM/SAM/SOM)

| Metric | What | How to Research |
|--------|------|----------------|
| TAM | Total addressable market | Global market reports, Statista |
| SAM | Serviceable addressable | Geographic + segment filter |
| SOM | Serviceable obtainable | Realistic year 1-2 capture |

Include:
- Market size ($B) with YoY growth
- Segment breakdown (by platform/channel/geography)
- Google Trends for key terms
- Seasonal patterns

### Phase 3: Demographics / ICP

**For B2C (games, apps, e-commerce):**
- Age distribution with spending brackets
- Gender, geography, device
- Core vs casual ratio

**For B2B (SaaS, services):**
- ICP: company size, industry, role, budget
- Decision maker vs user persona
- Sales cycle length

### Phase 4: Country Microplans

For EACH target country document:

| Data | Why |
|------|-----|
| Top 5 messengers + MAU | Community channels |
| App stores / marketplaces + share | Distribution |
| Payment methods + adoption % | Conversion |
| Language(s) | Localization |
| CPI/CAC range | Budget |
| Cultural notes | Positioning |
| Local platforms | Extra reach |

**CRITICAL rules:**
- Use LOCAL messengers (Zalo for Vietnam, BiP for Turkey, KakaoTalk for Korea)
- Include local payment methods (PIX for Brazil, UPI for India, Kaspi for KZ)
- Include local app stores (RuStore for Russia, ONE Store for Korea)
- Include local gaming/shopping platforms where applicable

**Tier system:**
- Tier 1: Home market (lowest risk, start here)
- Tier 2: High volume + low cost markets
- Tier 3: High ARPU + high cost markets (enter after validation)

### Phase 5: Competitor Factcheck

VERIFY all claims on actual platforms:
- Visit store pages, read real reviews
- Check last update date (abandoned?)
- Note download counts / revenue estimates
- Build factcheck matrix with scores

### Phase 6: Promotion Channels

**Free (0 cost) — rank by potential:**

| Channel Type | For Games | For SaaS | For Local |
|-------------|-----------|----------|-----------|
| Social media | TikTok clips | LinkedIn posts | Instagram/VK |
| Communities | Reddit, Discord | Indie Hackers, HN | Local groups |
| Content | Devlogs, streams | Blog, case studies | Reviews, UGC |
| Referral | Challenge links | Invite bonuses | Word of mouth |
| Platforms | CrazyGames, Poki | ProductHunt, G2 | Yandex Maps, 2GIS |
| SEO | App Store SEO | Blog SEO | Local SEO |

**Paid channels** with costs per channel and country.

### Phase 7: Monetization / Revenue Model

**For Games:** Battle Pass, cosmetics, ads, tournaments
**For SaaS:** Freemium tiers, usage-based, enterprise
**For E-commerce:** Margins, AOV, repeat rate
**For Services:** Hourly/project/retainer, upsell paths

Revenue projections at 3 growth stages with both USD and RUB.

### Phase 8: Launch Plan

7-day (or 30-day for SaaS) launch timeline:
- Daily actions, channels, budget
- KPIs per day/week
- Go/no-go criteria

## Output: HTML Report

Self-contained HTML, dark theme (#0f0f23), CSS-only charts.

### Required Visual Elements:
- **Stat cards** — 4 key metrics at top
- **Horizontal bars** — CPI, market sizes, feature comparison
- **Vertical bars** — revenue projections, costs, seasonal
- **Donut chart** (conic-gradient) — revenue mix / market share
- **Timeline** — launch plan with budget per step
- **Country cards** — flag + tier badge + 3 sections (messengers, stores, payments)
- **Channel cards** — MAX/HIGH/MED badges for free channels
- **Factcheck matrix** — competitors table with highlight column
- **Pain cards** — competitor weaknesses

### Tooltips:
`[data-tip]` on ALL data headers. CSS `::after` on hover shows explanation.
Add note at top: "Hover headers for explanations"

### Design tokens:
```css
Background: #0f0f23 | Cards: #1a1a3e | Border: #2a2a5a
Red: #e94560 | Green: #28a745/#5bff7f | Blue: #0d6efd/#6cb4ff
Yellow: #ffc107 | Text: #e0e0e0 | Muted: #888
Font: 'Segoe UI', system-ui, sans-serif
```

### Sections (adapt numbering to type):
```
01 Executive Summary (stat cards + key insight)
02 Competitor Factcheck (matrix + blue ocean/feature gap)
03 Market Size & Trends (TAM/SAM/SOM + charts)
04 Demographics / ICP
05 Country Microplans (if international)
06 Competitor Weaknesses (pain cards)
07 Free Promotion Channels (ranked)
08 Paid Channels + CPI/CAC
09 Payments & Distribution
10 Monetization / Revenue Model (donut + projections)
11 Launch Plan (timeline)
12 Growth Roadmap / Portfolio
```

## Deployment

1. Save: `products/<name>/market-research-<date>.html`
2. Deploy: `scp ... root@80.90.181.152:/var/www/artvision/<name>/`
3. Notify: TG message to team chat with link + summary

## Quality Checklist

- [ ] All competitor claims verified on actual platforms
- [ ] Country messengers/payments are LOCAL
- [ ] Revenue projections in both USD and RUB
- [ ] All chart bars have correct relative heights
- [ ] Tooltips on every data block
- [ ] Print styles work (@media print)
- [ ] File is self-contained (no CDN, no external JS/CSS)
- [ ] Deployed and TG notified
