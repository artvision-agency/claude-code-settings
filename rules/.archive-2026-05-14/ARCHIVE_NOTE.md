# Archive 2026-05-14 — мёртвые rules

Архивированы правила с 0 упоминаний за последние 20 сессий (по grep по .jsonl logs).

Причина: 37% стартового контекста rules был мёртвым грузом (ECC дефолтные template-правила
для TypeScript/web/python которых мы не пишем активно).

**Освобождено:** 1526 строк стартового контекста.

Файлы:
contact-from-event.md
ecc-agents.md
ecc-code-review.md
ecc-coding-style.md
ecc-development-workflow.md
ecc-git-workflow.md
ecc-hooks.md
ecc-patterns.md
ecc-performance.md
ecc-security.md
ecc-testing.md
ecc-typescript-coding-style.md
ecc-typescript-hooks.md
ecc-typescript-patterns.md
ecc-typescript-security.md
ecc-typescript-testing.md
ecc-web-coding-style.md
ecc-web-design-quality.md
ecc-web-hooks.md
ecc-web-patterns.md
ecc-web-performance.md
ecc-web-security.md
ecc-web-testing.md
task-plan-required.md

Восстановление: `mv ~/.claude/rules/.archive-2026-05-14/<file> ~/.claude/rules/`

Метод аудита:
- ls -t ~/.claude/projects/-Users-antonk/*.jsonl | head -20
- для каждого rule: grep -l <stem> по этим 20 сессиям
- если 0 совпадений → кандидат на архив

Прецедент: AUTOLOADING session 2026-05-14 ночь, после жалоб Антона на медленный Claude.
