---
name: presale-kp-parallel
description: Параллельный аудит КП клиента 7 subagents (Opus-only) перед отправкой. Factcheck + Brand + Pricing + SEO baseline + Competitive + Copy + Lexicon + Visual. Сводный HTML-отчёт + VERDICT блокер если есть CRITICAL. Триггеры — presale kp parallel, аудит кп параллельно, проверь кп перед отправкой, kp review, kp audit, kp parallel.
---

# /presale-kp-parallel — параллельный аудит КП клиенту

Запускает **7 параллельных Opus-subagents** для аудита готового КП по 7 измерениям, синтезирует результаты в Decision Report, блокирует отправку клиенту если есть CRITICAL.

Адаптировано из `github.com/wshobson/agents/plugins/comprehensive-review` (Opus-only, без cross-plugin зависимостей).

## Когда применять

| Триггер | Описание |
|---|---|
| КП собран, нужна проверка перед отправкой клиенту | После `/presale-kp` — финальный gate перед scp |
| КП правился (v2, v3) — проверить что fix не сломал другие места | Re-audit после правок |
| КП копировался по шаблону другого клиента — проверить полноту переноса | Аналог `kp-visual-diff`, но шире (не только визуал) |
| Перед отправкой клиенту на согласование | Обязательный gate (recall: 49 CRITICAL за месяц без аудита) |

**НЕ применять:**
- Для внутренних КП-черновиков (`_drafts/`) — это перед отправкой клиенту
- Для одностраничных рекламных лендингов — слишком тяжёлый pipeline, используй `/factcheck`

---

## Inputs

```yaml
kp_path: clients/<slug>/presale/kp/<file>.html  # обязательно
client_slug: <slug>                              # обязательно (читаем config.yaml)
client_site: https://...                         # из config.yaml.site
client_revenue_rub: NNNN                         # из counterparty-check / rusprofile
target_recipient_role: ceo|cmo|director|secretary|operational  # для recipient-personalization
reference_kp: clients/<other>/presale/kp/<file>.html  # опционально для diff
strict_mode: false                                # если true — блок на любой HIGH, не только CRITICAL
```

Автодетект из `clients/<slug>/config.yaml`:
- `brand_palette` (primary + secondary цвета)
- `font_family`
- `industry` (medical / b2b / e-commerce / agency / local)
- `regions[]` (для Topvisor + lr_id)
- `tariffs[]` — если уже зашиты

---

## Pipeline (3 фазы, ~6-8 минут)

### Фаза 1 — Discovery (1-2 мин)

ДО запуска subagents:

1. **Read** `config.yaml` клиента → palette, font, industry, regions, tariffs
2. **Read** `kp_path` → распарсить HTML через BeautifulSoup, извлечь:
   - все `<h1>`, `<h2>` → структура секций
   - все числовые утверждения (`\d+[\s\xa0]*(%|руб|RUB|₽|тыс|млн|год)`) → list для factcheck
   - inline CSS цвета (`#[a-fA-F0-9]{6}`) → сверка с config.yaml
   - все ссылки `href=` → list для HTTP HEAD проверки
3. **WebFetch** на 3 ключевые страницы клиента (`/`, `/contacts`, `/about`) — для brand alignment проверки
4. **counterparty-check** (если `client_revenue_rub` не указан) — попытка извлечь выручку из rusprofile/checko

Output: `.kp-review/00-scope.md` с разобранной структурой + extracted facts.

### Фаза 2 — Parallel audit (3-5 мин)

Запустить **7 Task tool calls в одном assistant message** (параллельно):

```python
# Все subagent_type = "general-purpose" (Opus, без Sonnet/Haiku)
# Каждый получает свою секцию scoring rubric из references/scoring-rubric.md
# Output формат: строгий JSON {section, score 0-100, findings[], recommendations[], blocker: bool}
```

**Task 1 — factcheck:** проверка всех числовых утверждений из 00-scope.md против 2+ источников (rusprofile, ФНС, WebSearch). CRITICAL если число без источника / WRONG. Использует skill `factcheck` методологию.

**Task 2 — brand-alignment:** сверка palette + font + tone-of-voice КП с сайтом клиента. `curl` сайта клиента, extract primary/secondary цвета, сравнить с inline CSS в КП. CRITICAL если основной цвет КП не из палитры клиента.

**Task 3 — pricing:** проверка тарифов против `client_revenue_rub × 0.5-1.5%` правила (см. `feedback_pricing_by_revenue.md`). Для медицины — расширенная сетка `medical-kp.md` 105/135/175K (1 филиал) или ×1.5 (2+). CRITICAL если цена выходит за разумный диапазон.

**Task 4 — seo-baseline:** что у клиента **есть** vs что **нет** в плане SEO (Topvisor позиции, Schema, sitemap, robots, llms.txt, мета-теги). Используется `analytics_detector.py` из market-audit для robust detection. CRITICAL если КП обещает «индексация» а robots.txt уже её разрешает (т.е. fake-finding).

**Task 5 — competitive:** проверка 3 прямых конкурентов из КП по 5-балльной системе (`presale-recon-standard.md`: product overlap 35 + SERP overlap 25 + region 15 + ICP 15 + size 10 ≥ 70 = прямой). CRITICAL если кто-то из 3 — смежная ниша, не прямой.

**Task 6 — copy:** русскоязычная редактура + рекипиент-персонализация. Проверка: нет «AI/нейросети/Claude/GPT» (security.md ТАБУ), есть 3 тезиса под `target_recipient_role` (recipient-personalization.md), нет жаргона без перевода для Антона (feedback_no_jargon_for_anton.md). CRITICAL если упоминания AI / Topvisor / SEMrush в видимом тексте.

**Task 7 — visual + mobile:** Playwright screenshot 3 breakpoints (375/768/1440), проверка h-scroll = 0 на mobile, проверка что все картинки загружаются (HTTP 200 на каждый `<img src>`), wow-анимации не ломают LCP. CRITICAL если mobile h-scroll или ассет 404.

**Каждый subagent получает:**
1. Содержимое `00-scope.md` (extracted facts)
2. Свою секцию rubric (`references/scoring-rubric.md`)
3. Доступ к Bash/WebFetch/Read для проверок
4. Инструкцию: строгий JSON output с `blocker: true|false`

**Если subagent падает / timeout >6 мин** — пометить `partial: true`, не блокер.

### Фаза 3 — Synthesis (1-2 мин)

1. Собрать 7 JSON outputs в `.kp-review/01-findings.json`
2. Compute composite score (взвешенное среднее):
   ```
   KP Score = (
       factcheck       * 0.25 +   # самый важный — числа клиента
       brand           * 0.10 +
       pricing         * 0.15 +
       seo_baseline    * 0.15 +
       competitive     * 0.10 +
       copy            * 0.15 +
       visual          * 0.10
   )
   ```
3. **VERDICT:**
   - Любой `blocker: true` → **❌ BLOCKED** — не отправлять клиенту
   - `strict_mode: true` + любой `score < 70` → **❌ BLOCKED**
   - Score ≥ 85 → **✅ APPROVED** — можно отправлять
   - Score 70-84 → **⚠️ REVIEW** — мелкие правки рекомендованы, не блокер
   - Score < 70 → **🔴 REWORK** — серьёзные правки нужны
4. Render HTML report в `.kp-review/02-final-report.html` (тот же шаблон что в `/market-audit`, цветовая раскладка по severity)
5. Output stdout summary + VERDICT в одну строку

---

## Output

### Primary: HTML report

Путь: `clients/<slug>/presale/kp/.kp-review/02-final-report.html`

Структура:
```html
<!DOCTYPE html>
<html lang="ru">
<head>
  <title>KP Review — {client} — {date}</title>
  <style>/* CAMEO-style, по нашему дизайн-стандарту */</style>
</head>
<body>
  <h1>KP Review — {client}</h1>
  <div class="verdict verdict-{approved|review|blocked}">VERDICT: {verdict_text}</div>

  <h2>Итоговая оценка: {score}/100</h2>
  <h2>Score Breakdown</h2>
  <table><!-- 7 dimensions × score × top finding --></table>

  <h2>BLOCKERS (P0 — fix перед отправкой)</h2>
  <ol><!-- blocker findings --></ol>

  <h2>Recommendations</h2>
  <ol><!-- по приоритету --></ol>

  <h2>Detailed Findings by Dimension</h2>
  <!-- 7 секций --->
</body>
</html>
```

### Secondary: stdout

```
═══════════════════════════════════════════
  KP Review — {client} ({kp_path})
═══════════════════════════════════════════
  Score: 78/100   VERDICT: ⚠️ REVIEW

  Factcheck:    85/100   ✓ blockers: 0
  Brand:        72/100   ⚠ palette mismatch
  Pricing:      90/100   ✓ blockers: 0
  SEO baseline: 65/100   ⚠ 2 fake-findings
  Competitive:  80/100   ✓ blockers: 0
  Copy:         70/100   ⚠ jargon без перевода
  Visual:       85/100   ✓ blockers: 0

  Top 3 recommendations:
    1. [brand] Сменить #2c3e88 на #614ce1 (palette клиента)
    2. [copy] Заменить "stack" на "набор инструментов" (Антон)
    3. [seo] Убрать «настроим индексацию» — robots.txt уже разрешает

  Report: clients/{slug}/presale/kp/.kp-review/02-final-report.html
  Wall-clock: 6m 23s
═══════════════════════════════════════════
```

---

## Принципы реализации

### 1. Только Opus, без Sonnet/Haiku

Все subagent calls — `subagent_type: "general-purpose"` (наследует Opus per core.md). НЕ указывать `model:` в Task tool. Если правило core.md изменится — править ОДНУ строку правила, не SKILL.

### 2. Параллель в одном assistant message

```python
# Правильно — все 7 Task в одном message:
[Task(...), Task(...), Task(...), Task(...), Task(...), Task(...), Task(...)]

# Неправильно — последовательно:
result1 = Task(...)
result2 = Task(...)  # ждёт result1
```

Это даёт ~6-8 минут wall-clock вместо 35-45 минут sequential.

### 3. Strict JSON output от каждого subagent

Subagent prompt заканчивается строгим schema:
```json
{
  "dimension": "factcheck",
  "score": 0-100,
  "blocker": true|false,
  "findings": [{"severity": "critical|high|medium|low", "what": "...", "where": "kp_path:line", "evidence": "...", "fix": "..."}],
  "recommendations": [{"priority": "P0|P1|P2", "what": "...", "effort": "small|medium|large"}],
  "partial": false,
  "notes": ""
}
```

### 4. Стейт файл для resume

`.kp-review/state.json` — если процесс прерван (compaction / network), можно вернуться:
```json
{
  "kp_path": "...",
  "client_slug": "...",
  "current_phase": 2,
  "completed_dimensions": ["factcheck", "brand", "pricing"],
  "started_at": "..."
}
```

При повторном запуске `/presale-kp-parallel` — проверить state.json и предложить resume.

### 5. Verdict-блокер интегрируется в hook

После генерации `02-final-report.html` — обновить `clients/<slug>/presale/kp/.kp-verdict.json`:
```json
{"verdict": "BLOCKED|REVIEW|APPROVED", "score": 78, "blockers": 2, "timestamp": "..."}
```

Хук `pre-scp-factcheck.sh` (уже существует) расширяется проверкой `.kp-verdict.json` — если `verdict == BLOCKED` → блокирует scp.

---

## Adoption notes

Источник pattern: `github.com/wshobson/agents/plugins/comprehensive-review/commands/full-review.md` (MIT).

Что взято:
- Orchestrator-workers pattern (5 phases → 3 phases для КП)
- State file для resume
- Phase checkpoint pattern
- JSON output schema от каждого subagent
- Consolidated report генерация

Что отброшено:
- `subagent_type: "architect-review"` / `"security-auditor"` (cross-plugin зависимости — у нас только `general-purpose`)
- Frontend/backend framework detection (не нужно для КП)
- CI/CD review phase (КП не деплоится в CI)
- 5 фаз → 3 (КП проще чем код-аудит)

Что добавлено:
- 7 КП-специфичных measurement dimensions (factcheck/brand/pricing/seo/competitive/copy/visual)
- Интеграция с `analytics_detector.py` (W2-T2)
- `recipient-personalization` rule (3 тезиса под роль)
- Pricing validation против `client_revenue_rub × 0.5-1.5%`
- Medical-mode (расширенные dimensions из `medical-kp.md`)
- Verdict-блокер для `pre-scp-factcheck.sh` hook

---

## Связанные skills и правила

- `presale-kp` — генерация КП (этот skill — gate ПЕРЕД отправкой результата)
- `factcheck` — низкоуровневая методология фактчекинга, использует Task 1
- `kp-visual-diff` — попарный визуальный diff (более узкая задача, может вызываться из Task 7)
- `medical-kp.md` — расширенный rubric для медицинских клиентов
- `kp-brand.md` — что **нельзя** в видимом тексте (Topvisor/SEMrush/Ahrefs/AI), используется Task 6
- `feedback_pricing_by_revenue.md` — формула цен 0.5-1.5%, используется Task 3
- `feedback_no_internal_markers_in_client_docs.md` — UNCONFIRMED/curl/CONFIRMED ban, используется Task 6
- `recipient-personalization.md` — 3 тезиса под роль, используется Task 6
- `presale-recon-standard.md` — 5-балльная система прямых конкурентов, используется Task 5
- Hook `pre-scp-factcheck.sh` — расширяется для чтения `.kp-verdict.json`
- Hook `pre-kp-bred-block.sh` — продолжает работать перед Write/Edit (сейчас работает)

## Acceptance criteria для самого skill

- [ ] SKILL.md описывает 7 dimensions + 3 фазы
- [ ] `references/scoring-rubric.md` — критерии 0-100 per dimension
- [ ] Smoke test на любом готовом КП (например `presales/spb-kursy/kp/spb-kursy_kp_v3.html`) проходит без exception
- [ ] Output JSON parsing работает (test с mock data)
- [ ] HTML report генерируется корректно
- [ ] Total wall-clock < 10 минут на КП размером ~50 KB
