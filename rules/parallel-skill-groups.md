# Parallel Skill Groups — авто-параллельный запуск overlap-скиллов

> **Установлено:** 2026-05-22 (сессия по запросу Антона).
> **Цель:** для классов задач где есть несколько overlap-скиллов (свои + скачанные с GitHub) — запускать 2-3 параллельно, потом консолидировать результаты в один с dedup.
> **Связано:** `consilium-matrix.md` (cons vs round_table vs swarm), `bulletproof-patterns.md` (challenge loop), `tool-adoption-proof.md`, `antipatterns.md` (5+ агентов на всякий случай — ЗАПРЕЩЕНО).

## Главный принцип

Когда задача попадает в один из 4 классов ниже — **автоматически** запускать 2-3 скилла параллельно (не один). После — консолидировать результаты:
- Dedup по ключу (URL+issue / file:line / finding-text)
- Severity-rank: CRITICAL > HIGH > MEDIUM > LOW
- Cross-confirmation: если 2+ скилла нашли одно и то же → +1 confidence
- Уникальные находки одного скилла остаются (разные подходы видят разное)
- Финальный артефакт — **единый** консолидированный отчёт с пометкой откуда (`[seo-audit+seo-master]`)

## 4 класса задач (v1, 2026-05-22)

### Класс 1: SEO-аудит

**Триггеры:** `seo аудит`, `seo audit`, `аудит сайта`, `проверь seo`, `технический seo`, `seo health`, `seo issues`, `оптимизация сайта`, `почему не ранжируется`, `seo expert`

**Скиллы (запускать 2-3):**
1. `/seo-audit` — full website crawl + parallel subagents (8 always + 7 conditional)
2. `/seo-master` — hybrid-seo-audit.py + meta-tags + keyword research
3. `/seo-technical` — crawlability, indexability, security, mobile, CWV
4. `/seo-factors-audit` — текстовые/коммерческие/поведенческие факторы
5. `/seo-cluster` — semantic topic clustering (опционально, если есть keyword list)

**Default тройка:** `/seo-audit` + `/seo-master` + `/seo-technical`
Для крупных клиентов (>50 страниц) добавлять `/seo-factors-audit`.

**Консолидация:**
- Ключ dedup: `URL + issue_type` (e.g., `/page-1 + missing-meta-description`)
- Severity: CRITICAL (broken canonical, no index) > HIGH (missing meta) > MID > LOW
- Уникальные подходы: `/seo-audit` смотрит crawl-wide, `/seo-master` ловит CWV, `/seo-technical` ловит robots/sitemap. Все 3 нужны.

### Класс 2: Фактчек / КП-аудит

**Триггеры:** `фактчек`, `factcheck`, `проверь кп`, `проверь факты`, `audit kp`, `проверь перед деплоем`, `validate html`, `kp audit`, `проверь страницу`

**Скиллы (запускать 2-3):**
1. `/factcheck` — 7 слоёв (структура, данные, кросс-ссылки, HTTP, консистентность, numeric, domain validators)
2. `/audit-kp` — специализированный аудит КП (если есть)
3. `strict-factchecker` агент — паранойя на каждое число
4. `/finance-factcheck` — если документ про деньги (ставки/инвестиции/ROI)

**Default тройка для обычных КП:** `/factcheck` + `strict-factchecker` agent + `/audit-kp`
**Для финансовых документов:** `/factcheck` + `/finance-factcheck` + `strict-factchecker`

**Консолидация:**
- Ключ dedup: `claim-text + source-url`
- Severity: CRITICAL (выдуманные числа/цитаты) > HIGH (UNCONFIRMED источник) > MID (несоответствие версий)
- Cross-confirmation: 2+ агента подтверждают «факт OK» → высокая уверенность. Один сомневается — оставить в WARN.
- VERDICT: PASS / REVIEW / FAILED. FAILED = не отправлять.

### Класс 3: Code review / security

**Триггеры:** `code review`, `ревью`, `security review`, `проверь код`, `code audit`, `проверка безопасности`, `quality audit`, `security audit`, `аудит кода`

**Скиллы (запускать 2-3):**
1. `/code-review` — лёгкое 1 проход для коммитов
2. `/code-audit` — параллельный аудит 4 агентами (security + quality + architecture + platform)
3. `/security-review` — XSS, injection, OWASP Top 10
4. `/security-scan` — статический скан
5. `/tdd` — проверка покрытия тестами

**Default тройка:** `/code-review` + `/security-review` + `/code-audit`
Для security-sensitive кода (auth, payments) — обязательно все 3.

**Консолидация:**
- Ключ dedup: `file:line + issue-type`
- Severity: CRITICAL (security vulns) > HIGH (bugs) > MID (quality) > LOW (style)
- Финальный артефакт: HTML-отчёт с разделами по типу проблем

### Класс 4: Research / market analysis

**Триггеры:** `исследование рынка`, `market research`, `анализ рынка`, `конкуренты`, `competitive analysis`, `TAM SAM SOM`, `competitor analysis`, `research`, `deep research`, `crag`

**Скиллы (запускать 2-3):**
1. `/market-research` — universal market research (TAM/SAM/SOM, конкуренты, monetization)
2. `/deep-research` — глубокое исследование с источниками
3. `/competitive-intel` — competitor intelligence
4. `/competitive-teardown` — детальный разбор конкурента
5. `/crag-research` — Corrective RAG с факчеком чисел

**Default тройка для market:** `/market-research` + `/competitive-intel` + `/crag-research`
**Для конкретного конкурента:** `/competitive-teardown` + `/deep-research` + `/crag-research`

**Консолидация:**
- Ключ dedup: `claim + source-url + date`
- Cross-confirmation: 2+ источника на каждое число (см. `finance-data-collection.md`)
- Конфликт данных → пометить «РАСХОЖДЕНИЕ: agent-A: X (src), agent-B: Y (src)»

## Когда НЕ применять (исключения)

- **Быстрый фикс <5 мин** (одна правка, опечатка) — overkill
- **Внутренние черновики** — экономия токенов
- **Уже один параллельный запуск был в этой сессии по этой задаче** — не дублировать
- **Пользователь явно указал один скилл** — уважать выбор («запусти только /seo-audit»)
- **Stage 1 (черновик)** — параллель на финальном прогоне перед deploy, не на каждой итерации

## Лимиты параллельности

| Параметр | Значение |
|----------|----------|
| Максимум скиллов параллельно | **3** (default) |
| Можно расширить до | 4-5 для критичных revenue-задач (КП клиенту >500K, security аудит prod) |
| Минимум скиллов в группе | 2 (иначе не параллель, а просто 1 скилл) |
| Cost cap | ~$1.5 на параллельный прогон (3 × ~$0.50) |

## Формат уведомления (auto-mode)

При срабатывании — **первая строка ответа**:

```
[PARALLEL: 3 skills — /seo-audit + /seo-master + /seo-technical, ~$1.20]
```

После прогона — финальный артефакт с пометкой:

```
## Источники анализа
- /seo-audit (повторный прогон 2026-05-22 14:30)
- /seo-master (полный аудит)
- /seo-technical (Lighthouse + crawl)

## Консолидированные находки (dedup)
| Severity | Issue | URL | Подтверждено |
| CRITICAL | Missing canonical | / | seo-audit + seo-master |
| HIGH | LCP 3.2s | /home | seo-master + seo-technical |
| ...
```

## Антипаттерны

- ❌ Запускать ВСЕ 5 скиллов класса «на всякий случай» — нарушение `antipatterns.md` («5+ агентов»)
- ❌ Параллель на каждой итерации правок (только на final pass)
- ❌ Параллель для one-off задач (мелкая правка опечатки)
- ❌ Игнорировать результат одного из скиллов при консолидации (каждый видит своё)
- ❌ Делать только intersection (∩) — нужен union (∪) с dedup
- ❌ Запускать когда пользователь явно указал «только X»

## Расширение

Новый класс задач — дописать сюда секцию с триггерами + default тройкой + правилом консолидации. После 3 успешных применений в реальных задачах — закрепить как стабильный.

## Прецеденты

- **2026-05-22 (создание):** Антон поднял проблему — недавно добавили 10 design/UX скиллов с GitHub (`reference_skills_adoption_2026-05-05.md`), часть overlap'ит со своими. Решение — для классов «аудит/оптимизация/research» запускать параллель + консолидировать. Stage 1 правила.

## Связанные

- `~/.claude/rules/consilium-matrix.md` — для стратегии/tool adoption (другой слой)
- `~/.claude/rules/antipatterns.md` — лимит 5+ агентов
- `~/.claude/rules/bulletproof-patterns.md` — challenge loop поверх результата
- `~/.claude/hooks/prompt-parallel-skills-detect.sh` — детектор класса задачи
- `~/.claude/scripts/parallel-skills-registry.json` — машино-читаемый registry для хука
