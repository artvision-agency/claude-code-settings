# Rules Relocation Map — context-diet (где теперь живут перенесённые правила)

> Создано 2026-06-11 (Антон approve, ветка context-diet-w1). Спека: `~/artvision-data/decisions/2026-06-11-context-diet-spec.md`.
> **Зачем:** правило перенесено из `rules/` (грузилось ВСЕГДА) в `rules-conditional/` (грузится хуком `inject-context-rules.sh` ТОЛЬКО при cwd/Edit в matching-папке).
> **«Не нашёл правило» → смотри сюда** (анти no-false-negative). Содержимое НЕ удалено, только переехало + получило `paths:` frontmatter.
> **Механизм:** `rules/*.md` (maxdepth-1) грузятся нативно всегда; подпапки и `rules-conditional/` — нет. Хук грузит conditional по совпадению cwd ИЛИ file_path при Edit/Write.

## Волна 1 — перенесено в `rules-conditional/` (2026-06-11)

| Правило | Триггер-папки (paths) | Было KB |
|---|---|---|
| shorts-pip-composition | personal/social_clips/**, clients/**/ads/**, *shorts*/*reels*/*video* | 17.1 |
| tg-video-publishing | personal/social_clips/**, clients/**/ads/**, *video*/*shorts* | 9.3 |
| ndfl-formulas | personal/finance/**, *ipoteka*/*savings*/*vklad* | 7.0 |
| calculator-real-estate-checks | *ipoteka*/*calculator*/*kvartir*, finance/** | 4.8 |
| signage-naruzhka-viz-workflow | clients/**/ideas/**, *signage*/*vyveska*/*naruzhk*/*billboard* | 6.2 |

**Снято с автозагрузки Волной 1: ~44 KB** (global rules 464→401 KB). Проверено: все 5 грузятся хуком при Edit в matching-папке (тесты пройдены).

## ⚠️ Что НЕ переносим (остаётся в rules/ всегда)
Поведенческие + срабатывающие по ТЕМЕ запроса без папочной привязки (хук матчит только cwd/file_path, не keyword):
- consilium-matrix, model-bakeoff (PROVENANCE HARD), prompt-elaboration, orchestration-method-selection, mindset-huang, cherny-tips, template-selection-map, site-clone-pipeline, rootcause-fix-template, self-corrections, core/security/session/git/quality/no-smoothing/antipatterns/asana-required-fields/agent-roster и пр. универсальные.

## Следующие волны (TODO, после verify в свежей сессии + push на 3 аккаунта)
- Волна 2 (project rules ~/artvision-data/.claude/rules/): PPC-playbook-set (anticrisis/ppc-metrika/ppc-launch — clients/**/ppc, clients/**/ads), dental-clinic-blueprint (clients/**med**), seo-presale-audit/seo-rank-loop/tfidf/topvisor-ops/semrush-ops (clients/**/seo/**), kp-* (presales/**, clients/**/kp).
- self-corrections.md (57K) — сжать до таблицы «ошибка→правило», детали в архив (ОТДЕЛЬНО, аккуратно).
- MEMORY.md индекс — сжать 1-строчными хуками.
- Хуки 161→~40 диспетчерами.

## Откат
`git checkout main` (ветка context-diet-w1 не смержена). Или `git mv rules-conditional/<file> rules/` + убрать frontmatter.

## Волна 2 — перенесено в `rules-conditional/` (2026-06-20, token-diet)

| Правило | Триггер-папки (paths) |
|---|---|
| figma-mcp-bulk-creative | design/**, *figma*, ads/** |
| designer-prompt-templates | design/**, *design* |
| site-clone-pipeline | *clone*, clients/** |
| moodboard-photographer-brief | *moodboard*, *photo*, clients/** |
| semrush-ops | **/seo/**, *semrush* |
| topvisor-ops | **/seo/**, *topvisor* |
| seo-presale-audit-workflow | **/seo/**, *audit* |
| bank-source-blocklist | **/finance/**, *vklad*, *savings* |
| finance-data-collection | **/finance/**, *vklad*, *savings* |
| welcome-vs-base-math | **/finance/**, *vklad* |
| ppc-show-as-ad-previews | **/ppc/**, **/ads/** |
| visual-overlays-faces-and-metro | **/ads/**, social_clips/** |

**Снято Волной 2: −63 KB** (rules/ 533→470 KB). Эффект — со следующего старта сессии.
