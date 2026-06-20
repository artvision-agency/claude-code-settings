# Token-diet — план снижения трат токенов

> Создан 2026-06-20. Запускать в СВЕЖЕЙ сессии (`/clear` → "выполни TOKEN-DIET-PLAN").
> Причина: правила (533K/136K токенов) + MCP-дубли грузятся в КАЖДЫЙ запрос.
> Эффект context-diet наступает со следующего старта (правила уже в текущем контексте).
> Делать ДЕТЕРМИНИРОВАННО, БЕЗ роя агентов (рой жжёт то, что экономим). Всё в ветке + откат.

## Замер ДО (2026-06-20)
- `~/.claude/rules/*.md` = 533 KB ≈ 136 000 токенов, 85 файлов
- За неделю +11 новых правил (~120 KB): auto-test-team, checks-by-validators, cost-aware,
  design-complexity, finisher-loop, source-consolidation, enforcement-primitives, codex-dev-lifecycle(20K)…
- MCP: 3× Asana (дубли), WordPress, Elementor, Pencil — сотни инструментов

## Шаг 1 — MCP чистка (мгновенный эффект, обратимо)
- Убрать дубли Asana → оставить ОДИН (`asana`), отключить `claude_ai_Asana`, `claude_ai_Asana_2`
- Отключить `wordpress` + `elementor-mcp` (не используются ежедневно; включать по запросу)
- Файлы: `~/.claude/settings.json` (enabledMcpjsonServers / permissions) + `.mcp.json`
- Проверка: `/mcp` показывает меньше серверов; Asana работает (1 шт)

## Шаг 2 — context-diet волна 2 (главный рычаг, −80-100K)
Перенести УЗКИЕ правила из `rules/` → `rules-conditional/` (грузятся хуком inject-context-rules.sh
ТОЛЬКО когда cwd/file_path матчит `paths:` frontmatter). Образец — волна 1 (15 файлов уже там).

Кандидаты (узкие, привязка к папке/типу — НЕ поведенческие):
| Правило | paths |
|---|---|
| figma-mcp-bulk-creative (9.7K) | `**/design/**`, `**/*figma*`, `**/ads/**` |
| designer-prompt-templates (5.2K) | `**/design/**`, `**/*design*` |
| site-clone-pipeline | `**/*clone*`, `clients/**` |
| moodboard-photographer-brief | `**/*moodboard*`, `**/*photo*`, `clients/**` |
| semrush-ops | `**/seo/**` |
| topvisor-ops | `**/seo/**` |
| seo-presale-audit-workflow | `**/seo/**` |
| bank-source-blocklist | `**/finance/**`, `**/*vklad*` |
| finance-data-collection | `**/finance/**`, `**/*vklad*` |
| welcome-vs-base-math | `**/finance/**` |
| ppc-show-as-ad-previews | `**/ppc/**`, `**/ads/**` |
| visual-overlays-faces-and-metro | `**/ads/**`, `**/social_clips/**` |

НЕ ТРОГАТЬ (поведенческие, нужны по теме запроса вне привязки к папке):
core, security, session, git, quality, no-smoothing, antipatterns, self-corrections,
agent-roster, consilium-matrix, orchestration-method-selection, prompt-elaboration,
mindset-huang, cherny-tips, enforcement-primitives, determinism-first, model-bakeoff,
document-list-format, no-false-negative, auto-specialist-routing, finisher-loop,
checks-by-validators, codex-dev-lifecycle, visual-content-not-just-ratio, image-edit-preserve-subjects,
project-work-plan-template (HARD-стандарт гантов), calculations-need-sources, finance-password-gate.

Процедура для каждого: prepend frontmatter (name+paths) → `git mv rules/X.md rules-conditional/X.md`
→ дописать строку в `rules/_RELOCATION-MAP.md`. Тест: Edit файла в matching-папке → хук грузит правило.

## Шаг 3 — сжать MEMORY.md (36→24 KB)
Индекс раздут (система ругается). Ужать длинные строки до <200 симв, детали — в topic-файлы.

## Шаг 4 — механизмы по запросу, не дефолтом
- `codex-dev-lifecycle` / `auto-test-team` / `checks-by-validators` — включать ОСОЗНАННО на тяжёлый
  код/проверку, НЕ на каждую правку. Снять формулировку "DEFAULT/обязательно для ВСЕХ" → "по триггеру/ставке".

## Замер ПОСЛЕ
`cat ~/.claude/rules/*.md | wc -c` — должно стать ~350-400 KB (было 533). Показать −KB числом.

## Откат
`git checkout main` (всё делать в ветке `token-diet`). MCP — вернуть профиль full.
