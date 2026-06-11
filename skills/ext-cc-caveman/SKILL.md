---
name: ext-cc-caveman
description: External Claude Code skill (JuliusBrussee/caveman, 62K⭐ MIT). Cuts ~65% tokens by simplifying language patterns. Use when user asks to save tokens, run long sessions efficiently, or benchmark token cost. Triggers — 'caveman', 'токен экономия', 'token saver', 'снизь токены', 'cut tokens', 'shrink prompt', 'ext-cc-caveman'.
---

# ext-cc-caveman — token saver

**Upstream:** github.com/artvision-agency/caveman ← JuliusBrussee/caveman (62K⭐, MIT, 2026-05-20)
**Category:** Claude Code ecosystem
**Use case:** snover Claude Max биллинга — режет до 65% токенов через language simplification

## Когда вызывать

- Long sessions где token-cost растёт
- Перед запуском дорогого Agent/swarm на много шагов
- Benchmark: вместе с `/ext-meta-bench` чтобы измерить экономию

## Как пользоваться

1. Если форк ещё не клонирован локально:
   ```bash
   gh repo clone artvision-agency/caveman ~/forks/caveman
   ```
2. Применить к промпту или диалогу — следовать инструкциям upstream README
3. Записать результат A/B в `~/artvision-data/benchmarks/cc-caveman-<date>.md`

## A/B vs обычные Claude сессии

- Метрика: токены IN+OUT на одну задачу
- Кейс: одна `/cons <client>` сессия с caveman и без
- Где смотреть: `~/.claude/logs/cost-2026-05.log`

## Связанные

- Реестр: `~/artvision-data/.claude/rules/external-tools-catalog.md`
- Research: `~/artvision-data/research/2026-05-20-agency-tools-discovery/05-claude-code-ecosystem.md`
- Decision: `~/artvision-data/decisions/2026-05-20-external-tools-adoption.md`
