---
name: revenue-5m
description: "Revenue milestone tracker: 5,000,000 RUB/month ($55,500 USD). Strategic planning for scaling beyond 2M. Product revenue, team scaling, market expansion. Triggers: '5mln', '5 million', '5 миллионов', 'цель 5м', 'milestone 5m', 'revenue 5m'"
argument-hint: "[action: dashboard|strategy|roadmap]"
---

# /revenue-5m — Milestone: 5,000,000 RUB/month (~$55,500 USD/month)

## TARGET

| Metric | RUB | USD (~90 RUB/$) |
|--------|-----|------------------|
| Monthly target | 5,000,000 | $55,500 |
| Annual target | 60,000,000 | $666,000 |
| Weekly run-rate | 1,250,000 | $13,875 |

## PREREQUISITE

First run `/revenue-2m` to get current baseline. 5M planning builds on top of 2M milestone.

## STEP 1: Revenue Architecture

5M/month CANNOT come from agency services alone. Required mix:

```
============================================
  REVENUE MILESTONE: 5M RUB ($55.5K USD)
============================================

REVENUE MIX TARGET:
| Stream           | RUB/month   | USD/month | % of 5M | Type        |
|------------------|-------------|-----------|---------|-------------|
| Agency clients   | 2,000,000   | $22,200   | 40%     | Service     |
| Products (SaaS)  | 1,500,000   | $16,650   | 30%     | Recurring   |
| Partnerships     | 1,000,000   | $11,100   | 20%     | Revenue share|
| Passive/other    | 500,000     | $5,550    | 10%     | Passive     |
|------------------|-------------|-----------|---------|-------------|
| TOTAL            | 5,000,000   | $55,500   | 100%    |             |
```

## STEP 2: Load Current State + 2M Progress

```bash
cat ~/.claude/projects/-Users-antonk/memory/revenue-goal.md
```

Display:
```
CURRENT vs 5M:
| Metric    | RUB       | USD     |
|-----------|-----------|---------|
| Target    | 5,000,000 | $55,500 |
| Confirmed | XXX,XXX   | $X,XXX  |
| GAP       | X,XXX,XXX | $XX,XXX |

PROGRESS: [███░░░░░░░░░░░░░] XX%
```

## STEP 3: Strategic Pillars Analysis

### Pillar 1: Agency Scale (target: 2M RUB / $22.2K)
- Current client base revenue
- Upsell potential per client
- New client acquisition capacity
- Average check optimization
- **Bottleneck:** team capacity (Anton + Andrey + Claude)
- **Solution:** hire/outsource + automation

### Pillar 2: Product Revenue (target: 1.5M RUB / $16.7K)

Evaluate each product:

| Product | Stage | MRR potential | Time to revenue | Investment |
|---------|-------|---------------|-----------------|------------|
| AIvision | MVP | 300-500K | 3-6 months | Low |
| Lead Auction | Idea | 200-400K | 6-12 months | Medium |
| Direct Radar | Idea | 100-200K | 3-6 months | Low |
| SEO Pipeline | Internal | 100-300K | 1-3 months | Low |
| Sales Psych | Idea | 200-500K | 6-12 months | Medium |

For each product, calculate:
- **Unit economics:** price x customers needed = target
- **CAC:** how to acquire customers
- **Payback period**

### Pillar 3: Partnerships (target: 1M RUB / $11.1K)

| Partnership | Model | Potential | Status |
|-------------|-------|-----------|--------|
| Dental-Experts | Revenue share | 300-500K | Active |
| Richelist | Equity/share | Variable | Active |
| White-label SEO | Reseller | 200-400K | Not started |
| Referral network | Commission | 100-200K | Not started |

### Pillar 4: Passive Income (target: 500K RUB / $5.5K)

| Source | Potential | Status |
|--------|-----------|--------|
| Music (Suno) | 50-100K | Active |
| Course/education | 100-200K | Not started |
| Templates/tools | 50-100K | Not started |
| Affiliate | 50-100K | Not started |

## STEP 4: Roadmap to 5M

Build quarterly roadmap:

```
Q1 2026 (current): Baseline → 2M foundation
Q2 2026: 2M confirmed + first product revenue
Q3 2026: 2.5-3M (products scaling)
Q4 2026: 3.5-4M (partnerships + products)
Q1 2027: 5M target
```

For each quarter, specify:
- Revenue target (RUB + USD)
- Key actions (max 5)
- Hiring needs
- Investment needed

## STEP 5: Weekly Tracking Table

```
WEEK OF [date]:
| Stream      | Target  | Actual  | Delta   | Trend |
|-------------|---------|---------|---------|-------|
| Agency      | 500K/w  | XXX     | +/-XXX  | ^/v/= |
| Products    | 375K/w  | XXX     | +/-XXX  | ^/v/= |
| Partners    | 250K/w  | XXX     | +/-XXX  | ^/v/= |
| Passive     | 125K/w  | XXX     | +/-XXX  | ^/v/= |
|-------------|---------|---------|---------|-------|
| TOTAL       | 1,250K  | XXX     | +/-XXX  | ^/v/= |
```

## STEP 6: Blockers & Dependencies

Identify and list:
1. **Team capacity** — what can't be done with current team
2. **Capital needs** — what requires upfront investment
3. **Technical debt** — what slows down product development
4. **Market risks** — competition, regulation, economy

## STEP 7: Update Strategy Files

- Update `revenue-goal.md` with 5M roadmap
- Create/update `products/ROADMAP-2026-Q1.md`
- Create Asana milestones for each quarterly target

## STEP 8: Distribution Channels Research

At each skill run, research and rank distribution channels:

### For Agency (Pillar 1):
- Referrals from existing clients (cost: 0, conversion: high)
- SEO on artvision.pro (cost: time, conversion: medium)
- vc.ru / Habr case studies (cost: time, conversion: medium)
- Cold outreach via email/TG (cost: low, conversion: low)
- Partnerships with web studios (cost: revenue share, conversion: medium)

### For Products (Pillar 2):
- Upsell to existing agency clients (cost: 0, highest probability)
- Landing page + SEO (cost: time)
- Product Hunt / directories (cost: time, good for international)
- Free tool strategy → paid conversion
- Content marketing (without mentioning AI internals!)

### For Partnerships (Pillar 3):
- Industry events / conferences
- Professional communities (TG groups, forums)
- White-label agreements

**Always evaluate:** cost, time to result, expected ROI, scalability.

## RULES

1. ALL amounts in BOTH RUB and USD (note exchange rate used)
2. 5M is IMPOSSIBLE with agency alone — always include product/partnership pillars
3. Be brutally honest about timelines — no wishful thinking
4. Each pillar must have at least 2 concrete next actions
5. Review quarterly, adjust based on actuals
6. Cross-reference with `/revenue-2m` — 2M is prerequisite
7. Focus on LEVERAGE — what generates revenue without proportional time investment
8. **PROACTIVE:** suggest revenue actions even when not asked
9. **ASK QUESTIONS:** if data is missing, ask 10-30 questions in one block

## TABOO: AI/Neural Networks in Public Materials

**ABSOLUTE BAN** on mentioning AI, neural networks, Claude, GPT, ML in:
- Client proposals (KP)
- Service pages
- Public materials (vc.ru, Habr, social media)
- Client reports
- Product landing pages

**Instead use:**
- "Proprietary methodology" not "AI-generation"
- "Analytical system" not "neural network"
- "Expert analysis" not "machine learning"
- "Automated audit" not "AI-audit"
- Show RESULTS, not tools

**Exception:** AIvision — the product is about AI visibility, but positioning is "we make YOU visible to AI", NOT "we use AI to do our work"
