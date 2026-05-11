# KP Review Scoring Rubric — 7 dimensions, 0-100 each

> Используется в `/presale-kp-parallel`. Каждый subagent получает СВОЮ секцию (не весь файл) + 00-scope.md + инструкцию JSON output.

## Шкала (общая)

| Band | Score | Описание |
|---|---|---|
| **A** | 85-100 | Готово к отправке. Никаких CRITICAL, мелкие nit-ы только. |
| **B** | 70-84 | Можно отправить с мелкими правками. Рекомендации, не блок. |
| **C** | 55-69 | Нужна переработка. HIGH issues. |
| **D** | 40-54 | Серьёзные проблемы. Нельзя отправлять. |
| **F** | 0-39 | КП непригоден. Переделывать целиком. |

`blocker: true` ВСЕГДА если есть finding с `severity: "critical"`. Score-band не отменяет blocker.

---

## 1. Factcheck (вес 0.25)

**Что проверяем:** все числовые утверждения в КП имеют 2+ источника, не выдуманы.

| Score | Критерий |
|---|---|
| 100 | Все числа CONFIRMED через 2+ источников. Источники указаны рядом. |
| 85 | 1-2 числа UNCONFIRMED, помечены явно. Остальные с источниками. |
| 70 | 3-5 чисел UNCONFIRMED без явной метки. Нет WRONG. |
| 55 | 1 число WRONG (опровергнуто) или 6+ UNCONFIRMED. |
| 40 | 2+ числа WRONG. CRITICAL. |
| 0 | КП построено на выдуманных данных. CRITICAL. |

**CRITICAL триггеры:**
- Любое число с WRONG статусом
- Выручка клиента / ИНН / ФИО — без источника rusprofile/checko/ФНС
- Конкурент с фейковым названием (нет такой компании в SERP)

**HIGH:**
- 3+ числа UNCONFIRMED
- Дата публикации без источника (важно для свежести данных)

**Sources whitelist:**
- rusprofile.ru, checko.ru, list-org.com (юрлица)
- ФНС API (выручка)
- WebSearch с указанием query
- Прямой сайт клиента / конкурента (с датой curl)
- Topvisor / Direct API (если применимо)

---

## 2. Brand-alignment (вес 0.10)

**Что проверяем:** КП соответствует фирменному стилю клиента (цвета, шрифты, тон).

| Score | Критерий |
|---|---|
| 100 | Primary + secondary цвета совпадают с config.yaml клиента ±5% (HSL). Шрифт правильный. Тон официальный/неофициальный совпадает с сайтом. |
| 85 | Primary совпадает, secondary немного отличается. Шрифт правильный. |
| 70 | Primary совпадает, secondary не совпадает или отсутствует. |
| 55 | Primary не совпадает, но в той же гамме (warm/cool). |
| 40 | Primary не совпадает, другая гамма. |
| 0 | Дизайн другого клиента (template-overflow). CRITICAL. |

**CRITICAL триггеры:**
- Primary цвет другого клиента в видимом тексте (template-overflow из spb-kursy → cosmetology-kursy, прецедент 11.05.2026)
- Логотип / название другого клиента в видимом тексте

**HIGH:**
- Primary цвет не соответствует config.yaml.brand_palette
- Шрифт не из config.yaml.font_family

**Source of truth:** `clients/<slug>/config.yaml` → `design.palette` + `design.font` + WebFetch `curl https://<client_site>`.

---

## 3. Pricing (вес 0.15)

**Что проверяем:** тарифы соответствуют выручке клиента (0.5-1.5% от годовой).

| Score | Критерий |
|---|---|
| 100 | 3 тарифа (Старт/Рост/Масштаб), каждый в диапазоне 0.5-1.5% годовой выручки. Логичная градация ×1.3-1.7. |
| 85 | 3 тарифа, цены в диапазоне, градация неровная. |
| 70 | 3 тарифа, 1 цена выходит за 1.5% (overpriced) или ниже 0.5% (underpriced). |
| 55 | 2 тарифа вместо 3 или цены сильно за пределами диапазона. |
| 40 | 1 тариф или нет привязки к выручке клиента. |
| 0 | Цены явно выдуманы / нет реквизитов / не указана годовая ставка. CRITICAL. |

**CRITICAL триггеры:**
- Цена выходит за 0.3-3% годовой выручки (слишком дёшево или дорого, прецедент УГН 105/155/220К для 196.6 млн выручки)
- Цены без указания «в месяц» / «единоразово»
- Нет 3 уровней (стандарт для seo-кп)

**HIGH:**
- 1 тариф out-of-range 0.5-1.5%
- Нет привязки тарифа к scope (что входит)

**Medical mode (если `industry: medical`):**
- 1 филиал → диапазон 105/135/175K (из `medical-kp.md`)
- 2+ филиала → базовая × 1.5
- ВСЕГДА учитывать оборот (даже если 1 филиал)

**Source of truth:** counterparty-check → выручка ФНС → формула 0.5-1.5%. Согласование с Антоном ДО отправки.

---

## 4. SEO baseline (вес 0.15)

**Что проверяем:** что в КП написано про текущее состояние клиента (что есть/нет) совпадает с реальностью.

| Score | Критерий |
|---|---|
| 100 | Все findings про сайт клиента подтверждены real-world curl/Playwright. Использует `analytics_detector.py` для robust detection. |
| 85 | 1-2 finding с medium confidence, остальные high. |
| 70 | 3+ findings low confidence (grep на минифицированном HTML). |
| 55 | 1 fake-finding (КП говорит «нет Метрики», а она есть). |
| 40 | 2+ fake-findings или ложное утверждение про robots/sitemap. |
| 0 | Большинство findings про сайт ложные. CRITICAL. |

**CRITICAL триггеры:**
- «Метрика не подключена» когда она base64 в LiteSpeed (прецедент artvision.pro pilot)
- «Schema markup отсутствует» когда есть 5+ типов (использовать `count_schema_types`)
- «robots.txt блокирует индексацию» когда `Disallow: /` отсутствует
- «sitemap.xml не найден» когда `curl -sI` даёт 200

**HIGH:**
- 3+ findings без confidence-уровня
- «Mobile не оптимизирован» без скриншота Playwright 375 viewport

**Source of truth:**
```python
import sys; sys.path.insert(0, '/Users/antonk/.claude/skills/market-audit/scripts')
from analytics_detector import detect_analytics_robust, count_schema_types
# Real-world проверка ДО утверждения в КП
```

---

## 5. Competitive (вес 0.10)

**Что проверяем:** 3 «прямых конкурента» в КП реально прямые (≥70 score по 5-балльной системе).

| Score | Критерий |
|---|---|
| 100 | 3 конкурента имеют ≥70 score (product 35 + SERP 25 + region 15 + ICP 15 + size 10). С Topvisor SERP-снимком ≥3 ключей. |
| 85 | 3 конкурента ≥70, но без Topvisor SERP-снимка (только название + сайт). |
| 70 | 2 из 3 ≥70, 1 = 50-69 (помечен «частично прямой»). |
| 55 | 1 из 3 ≥70, остальные смежные ниши. |
| 40 | Все 3 < 70 (смежные ниши выданные за прямых). |
| 0 | Конкуренты выдуманы / не существуют. CRITICAL. |

**CRITICAL триггеры:**
- Конкурент с фейковым названием (`«Лор-Альянс»`-style прецедент)
- Конкурент в другом регионе без overlap по target geo
- Конкурент — наш собственный клиент (конфликт интересов)

**HIGH:**
- 2+ конкурента в смежной нише выданы за прямых
- Нет SERP-снимка (только название)

**Source of truth:** `presale-recon-standard.md` 5-балльная система. Topvisor SERP API через `topvisor.api_token` (см. `feedback_topvisor_filter_safety.md` про EQUALS filter).

---

## 6. Copy (вес 0.15)

**Что проверяем:** русскоязычная редактура + recipient-персонализация + ban-list.

| Score | Критерий |
|---|---|
| 100 | 3 тезиса под роль получателя на первом экране. Tone-of-voice адекватен роли. Нет ban-words. Нет жаргона без перевода. |
| 85 | 3 тезиса есть, но 1 не специфичен для роли. Нет ban-words. |
| 70 | 3 тезиса размытые / generic. Нет ban-words. |
| 55 | Нет 3 тезисов. Tone neutral. Нет ban-words. |
| 40 | 1-2 ban-words (Topvisor / SEMrush / Ahrefs в видимом тексте). |
| 0 | AI / нейросети / Claude / GPT упоминания в видимом тексте. CRITICAL. |

**CRITICAL триггеры (ban-list):**
- AI / нейросеть / нейронка / Claude / GPT / ML / LLM в видимом тексте (security.md ТАБУ)
- Topvisor / SEMrush / Ahrefs / DataForSEO / Keys.so (используем Artvision LinkForge / Flow / Scout / Radar)
- UNCONFIRMED / CONFIRMED / WRONG / curl / WebFetch / snippet — внутренние маркеры
- artvision.pro упоминания в кп клиенту (не наш сайт продвигаем)
- Жаргон без перевода для Антона (см. `feedback_no_jargon_for_anton.md`: hero/CTA/landing/stack/mockup/component)

**HIGH:**
- Нет 3 тезисов под `target_recipient_role`
- Tone не соответствует роли (для CEO технические детали без cifr, для CMO размытые «улучшим SEO»)
- 1-2 предложения с em-dash и parallel structure («не X, а Y» больше 3 раз) — AI writing signal

**Source of truth:**
- `recipient-personalization.md` (3 тезиса × роль)
- `kp-brand.md` (бренд-список + ban-list)
- `security.md` (AI ТАБУ)
- `feedback_no_jargon_for_anton.md`
- `feedback_no_internal_markers_in_client_docs.md`

---

## 7. Visual + Mobile (вес 0.10)

**Что проверяем:** HTML рендерится корректно на 3 breakpoints, ассеты загружаются, нет h-scroll.

| Score | Критерий |
|---|---|
| 100 | Playwright скриншоты 375/768/1440 чистые. H-scroll = 0 на mobile. Все `<img src>` дают HTTP 200. LCP < 2.5s. |
| 85 | Скриншоты чистые. 1-2 картинки lazy-load (норма). LCP 2.5-3s. |
| 70 | 1 битый ассет (404). Mobile h-scroll = 0. |
| 55 | 2-3 битых ассета или 1 секция переполнена на mobile. |
| 40 | Mobile h-scroll > 0 (boxes выходят за viewport). |
| 0 | КП не рендерится / JS errors blocking. CRITICAL. |

**CRITICAL триггеры:**
- Mobile h-scroll > 0 на любом viewport <768px (прецедент: spb-kursy v1, fix через `[class*="pc-"] { max-width: 100vw !important; }`)
- Hero image 404 (виден broken-image icon)
- JS error блокирует interactive (`onclick` не работает)
- TH count ≠ TD count в любой таблице (broken layout)

**HIGH:**
- 1-2 картинки 404 ниже fold (некритично, но клиент заметит при скролле)
- LCP > 4s (slow first paint)
- Нет mobile-fix CSS (`@media (max-width: 768px)`)

**Source of truth:** Playwright скриншоты в `.kp-review/screenshots/{375,768,1440}.png`. Каждый ассет проверяется `curl -sI` на HTTP 200.

---

## JSON output schema (для всех 7 subagents)

```json
{
  "dimension": "factcheck|brand|pricing|seo|competitive|copy|visual",
  "score": 0-100,
  "blocker": true|false,
  "findings": [
    {
      "severity": "critical|high|medium|low",
      "what": "Описание проблемы (1 предложение)",
      "where": "kp_path:section_id или kp_path:line_NN",
      "evidence": "Ссылка / curl output / скриншот / URL источника",
      "fix": "Конкретный fix (что заменить и на что)"
    }
  ],
  "recommendations": [
    {
      "priority": "P0|P1|P2|P3",
      "what": "Что сделать",
      "effort": "small|medium|large",
      "impact": "high|medium|low"
    }
  ],
  "evidence_urls": ["https://..."],
  "partial": false,
  "notes": ""
}
```

`blocker: true` СТАВИТ subagent если есть хоть один `severity: "critical"` finding. Финальный VERDICT = OR всех blocker'ов.
