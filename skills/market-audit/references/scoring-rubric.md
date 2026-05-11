# Scoring Rubric — 5 категорий × 5 score-bands

Каждый subagent получает СВОЮ секцию (не весь файл — экономия токенов).

Score range — 0-100. Бэнды: 0-20 Critical, 21-40 Poor, 41-60 OK, 61-80 Good, 81-100 Excellent.

---

## 1. Content (вес 0.25)

Что оценивает: качество главной + блога, копирайтинг, AI-detection, tone-of-voice, TF-IDF, гэп против top-3 конкурентов.

| Score | Band | Критерии (должно быть выполнено большинство) |
|---|---|---|
| **0-20** | Critical | Главная без чёткого УТП, lorem ipsum / явный auto-translation. Headline = generic «Добро пожаловать». Нет блога ИЛИ блог копипаст без авторов. AI-маркеры (em-dash density >5/1000w, «давайте углубимся»/«важно отметить»). Жаргон без объяснений. Текст из GPT-3.5-templates («в эпоху цифровизации»). |
| **21-40** | Poor | УТП есть, но размыто («лучшее качество»). Блог есть, но 1-2 поста за квартал. Headline не проходит 5-секундный тест. TF-IDF главной — не покрывает core keywords (синонимы только). Тон неровный (где «вы», где «вас»). |
| **41-60** | OK | УТП конкретное, измеримое («снижаем CAC на 30%»). Блог 1-2 поста/мес, тематика релевантна. Headline проходит 5-секундный тест. Tone-of-voice консистентен на главной + 1-2 ключевых страницах. AI-detection не срабатывает. |
| **61-80** | Good | УТП с числами + доказательством (case study рядом). Блог 4+ поста/мес, авторы named. Headline + sub-headline пара (value + proof). TF-IDF — топ-50% по нише. ToV единый на всех страницах. Контент-кластеры (silo) видны. |
| **81-100** | Excellent | УТП — категория-defining («the first X to do Y»). Блог 8+ постов/мес, signature voice. Headline с конкретным числом/именем/контекстом («Снизили CAC PandaCaffe с 4000 до 1200 ₽»). TF-IDF — топ-10% по нише. ToV не путается с конкурентом (можно узнать без логотипа). Темат. кластеры покрывают buyer journey TOFU+MOFU+BOFU. |

**Evidence что собирать:** URL homepage, URL 5 ключевых страниц, выборка из 3-5 блогпостов с датами, scoring по TF-IDF (через keys.so/wordstat — если доступ есть, иначе manual), AI-detection через regex (em-dash count, jargon count).

---

## 2. Conversion (вес 0.20)

Что оценивает: CTA, формы, popup, mobile UX, signup/checkout flow, paywall (если применимо), pricing page.

| Score | Band | Критерии |
|---|---|---|
| **0-20** | Critical | CTA отсутствует ИЛИ generic («Узнать больше»). Форма >10 полей. Нет mobile-version (или горизонтальный scroll). Нет trust signals рядом с CTA. Popup срабатывает сразу при заходе (без exit-intent). Signup flow — несколько страниц без progress indicator. |
| **21-40** | Poor | CTA есть, но визуально не выделен (тот же цвет что body). Форма 6-10 полей, нет inline validation. Mobile есть, но touch targets <44px. Trust signals только в footer. Popup есть, exit-intent или scroll-based, но timing aggressive. |
| **41-60** | OK | CTA выделен (контраст + действие-глагол). Форма 4-5 полей. Mobile — viewport meta + responsive grid. Trust signals рядом с form (отзывы / гарантия / лого клиентов). Popup умеренный (40% scroll или 30s). Pricing page есть (если применимо). |
| **61-80** | Good | CTA-иерархия: primary (контрастный) + secondary (outline) + ghost. Форма 2-3 поля + progressive disclosure. Mobile — sticky CTA bar внизу. Trust signals = case studies с измеримыми числами. Popup с явной value-prop (lead-magnet). Pricing — 3 tier с anchoring + FAQ. |
| **81-100** | Excellent | CTA контекстный (меняется по странице, релевантно её роли). Форма 1-2 поля + inline validation + autofill. Mobile = native-feel (swipe, bottom-sheet). Trust signals = numbered proof (NPS, retention rate, growth). Popup исключительно по поведению (не на scroll-bot). Pricing page = психология (anchor, decoy, social proof per tier). Signup flow = 1 step, magic link. |

**Evidence:** scroll-recording sample (если есть Я.Метрика), скриншот CTA-block desktop+mobile (Playwright), форма HTML markup, popup trigger logic (DevTools), pricing page URL, signup landing URL.

---

## 3. Technical (вес 0.20)

Что оценивает: Core Web Vitals, schema markup, robots.txt + sitemap.xml + llms.txt, mobile-friendly, security headers, internal linking, image optimization.

| Score | Band | Критерии |
|---|---|---|
| **0-20** | Critical | LCP >4s, CLS >0.25, INP >500ms. Нет robots.txt ИЛИ блочит crawlers. Нет sitemap.xml. Schema = 0. Mobile fails Lighthouse (viewport missing). HTTP вместо HTTPS, или mixed content. TTFB >2s. Картинки несжатые JPG >500KB каждая, без alt. |
| **21-40** | Poor | LCP 2.5-4s, CLS 0.1-0.25, INP 200-500ms. robots.txt есть, sitemap есть, но устаревший (>6 мес). Schema = только Organization (без Product/Service/FAQ/Breadcrumbs). Mobile passes, но touch issues. HTTPS есть, но HTTP2 нет. TTFB 600ms-2s. WebP частично. |
| **41-60** | OK | LCP 1.5-2.5s, CLS <0.1, INP <200ms. robots+sitemap корректные, обновлены. Schema = Organization + Product/Service. Mobile-friendly pass. HTTPS + HSTS. TTFB 200-600ms. WebP+AVIF на главной. alt-tags >80%. |
| **61-80** | Good | LCP <1.5s, CLS <0.05. Schema = Organization + Service + FAQ + Breadcrumbs. Полный llms.txt. CSP headers, HSTS + preload. TTFB <200ms (CDN активен). Все картинки WebP/AVIF, lazy-loading. Internal linking — orphan pages = 0 (по SF crawl). |
| **81-100** | Excellent | Core Web Vitals all green на mobile+desktop. Schema = полный набор (LocalBusiness/MedicalBusiness где применимо, Review, AggregateRating, HowTo). llms.txt с полным content map для AI crawlers. Все security headers (CSP nonce, X-Frame-Options DENY, Referrer-Policy strict-origin). TTFB <100ms. Edge caching + Brotli. Internal linking структурирован по silo / topic-cluster pattern. Schema.org валидируется через validator.schema.org без warnings. |

**Evidence:** PSI mobile+desktop URL + score, `curl -sI {url}` для headers, `curl {url}/robots.txt`, `curl {url}/sitemap.xml`, `curl {url}/llms.txt`, schema-markup-validator output, Lighthouse JSON.

**РФ-специфика:** добавить проверку Я.Метрика установлена (search for `mc.yandex.ru/metrika`), Я.Вебмастер verified (search `yandex-verification` meta), 2GIS API если local business.

---

## 4. Competitive (вес 0.15)

Что оценивает: позиционирование vs top-3 конкурентов в Яндекс (СПб/МСК), backlink gap, content gap, pricing positioning.

| Score | Band | Критерии |
|---|---|---|
| **0-20** | Critical | Топ-3 конкурента не определены (нет SERP analysis). Брендовая видимость нулевая (поиск по бренду — нет среди первых 10 не своих ссылок). ИКС <10, у конкурентов >50. Pricing — самый высокий без обоснования. Content depth = 1/10 vs конкуренты (например 5 статей vs 50). |
| **21-40** | Poor | Конкуренты есть, но клиент проигрывает по ИКС/возрасту в 5-10x. Брендовый поиск = клиент на 5-10 позиции. Pricing — выше конкурентов без явного differentiation. Кейсов <3 у клиента, у топ-3 >10. |
| **41-60** | OK | Клиент видим в топ-10 по основному запросу (среди топ-3 + 7 конкурентов). ИКС в пределах 30-200% от средней по нише. Pricing в pricing-range competitor-средние. Брендовый поиск = клиент #1. 5-10 кейсов. |
| **61-80** | Good | Клиент в топ-5 по основному кластерному запросу. ИКС выше среднего по нише. Pricing — обоснованная premium-позиция (есть value-proof) ИЛИ обоснованная low-cost-позиция (volume play). Comparison/«vs» pages есть для топ-2 конкурентов. 15-30 кейсов с проверяемыми метриками. |
| **81-100** | Excellent | Клиент в топ-3 по 3+ основным кластерам. ИКС в топ-10% ниши. Pricing = либо premium-leader (NPS подтверждает), либо category-creator (свой pricing model). «Alternatives to {konkurent}» pages — у клиента есть, у топ-3 нет. 50+ кейсов с фото/именами/числами/датами. Брендовая ASCII-видимость в Яндекс и Google = #1 по всей семантике. |

**Evidence:** Топ-10 Яндекс СПб/МСК по основному запросу (через keys.so / wordstat / manual SERP), ИКС всех 4 доменов (через `pr-cy.ru/{domain}/`), backlink count (через keys.so если доступ, иначе approximation), pricing pages всех 4 (screenshots), wayback machine first-snapshot date для возраста.

**Критерий «прямой конкурент»** (из `presale-recon-standard.md`): сумма ≥70 по 5 сигналам (product overlap 35, SERP overlap 25, region 15, ICP 15, размер 10). Иначе — «частично/смежный».

---

## 5. Strategy (вес 0.20)

Что оценивает: позиционирование (1-line value prop), ICP detection, recipient-personalization, ToV match, trust signals (about, team, ИНН/лицензии), growth loops, retention signals.

| Score | Band | Критерии |
|---|---|---|
| **0-20** | Critical | Нет value prop ИЛИ generic («лучшие в своём деле»). Нет «о компании»/«team». Нет ИНН/реквизитов в footer. ICP не определён (одна страница для всех). Нет growth loops (нет реферальной программы, нет email-capture). Нет retention signals (нет email-newsletter, нет loyalty). |
| **21-40** | Poor | Value prop есть, generic. About есть, но нет team/photo. ИНН есть, но только мелким шрифтом. ICP смутный (упоминается «для бизнеса»). Email-capture есть, но без incentive. Нет community/loyalty. |
| **41-60** | OK | Value prop конкретный (1 строка, проходит «но почему именно вы»). About + team с именами. ИНН + лицензии в footer + /about. ICP явно очерчен (1-3 segments названы). Email-capture с lead-magnet. Retention = email-newsletter или ежемес. отчёт клиенту. |
| **61-80** | Good | Value prop = категория («первый X для Y»). About = founder story + team + values. Trust signals = ИНН + лицензии + дипломы + награды. ICP = 1-2 segments + явные buyer persona на сайте (под кого strona/CTA). Recipient-personalization = role selector ИЛИ страницы под role. Growth loops = реферальная (с условиями) + content-loop (UGC). Retention = community (TG/Discord) + email + loyalty pricing. |
| **81-100** | Excellent | Value prop = category-defining (свой term, не competitor's). Founder POV в каждом post. About = mission + manifesto + history. Trust signals = ИНН + лицензии + сертификации индустрии + named media coverage + customer logos. ICP = 1 segment razor-sharp (Pat Flynn rule: «I serve X who want Y»). Recipient-personalization = dynamic role selector + personalized headlines. Growth loops = 3+ работающих (referral, UGC, partner, content-led). Retention = эксклюзивный community + loyalty tiers + customer council. ToV unmistakable (можно distinguish без logo). |

**Evidence:** /about URL, /team URL (если есть), footer screenshot (ИНН/лицензии), email-capture form, любая growth-related страница (referral/affiliate/partner), retention сигналы (newsletter subscribe count если виден, community link).

**Industry-specific:** medical обязательно — лицензия Росздравнадзора + сайт лицензии + дипломы врачей. SaaS — SOC2 / GDPR / security page. E-com — возврат + доставка + поддержка contact.

---

## Composite Marketing Score

```
Total = Content*0.25 + Conversion*0.20 + Technical*0.20 + Competitive*0.15 + Strategy*0.20
```

### Grade interpretation

| Range | Grade | Что значит для клиента |
|---|---|---|
| 85-100 | **A** | Excellent — minor optimizations. Можно фокусировать ресурсы на новые каналы / расширение. |
| 70-84 | **B** | Good — есть конкретные точки роста (3-5 quick wins + 1-2 strategic). |
| 55-69 | **C** | Average — серьёзные пробелы. Strategic + long-term инициативы обязательны. |
| 40-54 | **D** | Below average — нужен major overhaul. Перестраивать фундамент (positioning + tech + conversion). |
| 0-39 | **F** | Critical — фундаментальные проблемы. Без переделки маркетинговой стратегии трафик/конверсия не вырастут. |

---

## Per-subagent JSON output schema

```json
{
  "section": "content|conversion|technical|competitive|strategy",
  "score": 0-100,
  "band": "Critical|Poor|OK|Good|Excellent",
  "findings": [
    {"severity": "critical|high|medium|low", "what": "...", "where": "https://...", "evidence": "..."}
  ],
  "recommendations": [
    {"effort": "quick_win|strategic|long_term", "what": "...", "impact": "high|medium|low", "timeline": "1 week|1 month|1 quarter"}
  ],
  "evidence_urls": ["https://...", "..."],
  "partial": false,
  "notes": "Если не хватило данных — здесь, не в findings"
}
```

`evidence_urls` обязателен — иначе findings помечаются UNCONFIRMED и в публичный отчёт не идут.
