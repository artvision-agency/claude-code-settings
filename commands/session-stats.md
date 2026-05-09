# /session-stats — Аудит инструментов сессии

Анализирует **текущую** (или указанную) сессию Claude Code: показывает что было реально использовано (агенты, скиллы, скрипты), что доступно но не вызвано, где Claude взял базовые настройки вместо запрошенных скиллов.

## Что делать

```bash
python3 ~/.claude/scripts/audit-session-tools.py
```

(без аргумента берётся самая свежая сессия из `~/.claude/projects/-Users-antonk/`)

С указанным sessionId:

```bash
python3 ~/.claude/scripts/audit-session-tools.py 9fdfb27e-ebf5-4d1f-8859-d5e3fcc88e24
```

## Формат вывода

```
========================================================================
  SESSION TOOLS AUDIT — <sessionId>
========================================================================

📋 Цель: <из recap>
🔢 Всего tool_use: N

✅ ИСПОЛЬЗОВАНО
Subagent-агенты (N вызовов):
  • general-purpose ×8
  • frontend-developer ×3
  ...

Skills (N вызовов):
  • superpowers:brainstorming ×1
  • cons ×1

CLI / scripts:
  • curl ×15
  • scp ×10
  • playwright(py) ×12
  ...

❌ НЕ ИСПОЛЬЗОВАНО (релевантные skills, M из 211):
  • design-extract
  • ui-ux-pro-max
  • brand-guidelines
  • factcheck
  ...

📊 Покрытие:
  • Skills: 2/211 (1%)
  • Agents: 8/199
  • Scripts: 0/106
```

## Когда запускать

- В конце сессии перед `/sync-sessions`
- При завершении любой большой задачи — для самоаудита
- При жалобе пользователя «почему не использовал X» — диагностика
- Stop-hook `stop-skill-audit.sh` вызывает автоматически
