---
name: weekly-maintenance
description: "Еженедельное техобслуживание: проверка хуков, скриптов, агентов, конфигов на ошибки и оптимизация. Триггеры: 'maintenance', 'техобслуживание', 'ТО агента', 'weekly maintenance', 'проверь настройки'"
---

# Weekly Maintenance — Техобслуживание агента

## Цель
Раз в неделю агент проходится по всей инфраструктуре, находит и исправляет проблемы.

## Чек-лист проверок

### 1. Хуки (~/.claude/hooks/)
```bash
# Проверить что все хуки executable
ls -la ~/.claude/hooks/*.sh
# Тестировать каждый
for hook in ~/.claude/hooks/*.sh; do bash -n "$hook" && echo "OK: $hook" || echo "FAIL: $hook"; done
```
- Все ли хуки executable?
- Нет ли синтаксических ошибок?
- Актуальны ли пути в хуках?

### 2. Скиллы (~/.claude/skills/)
```bash
# Количество скиллов
ls -d ~/.claude/skills/*/SKILL.md | wc -l
# Проверить YAML frontmatter
for skill in ~/.claude/skills/*/SKILL.md; do head -5 "$skill"; echo "---"; done
```
- Все ли скиллы имеют корректный frontmatter?
- Нет ли дублей или конфликтов имён?
- Актуальны ли описания и триггеры?

### 3. Агенты (~/.claude/agents/)
```bash
ls ~/.claude/agents/*.md | wc -l
```
- Все ли агенты загружаются без ошибок?
- Нет ли устаревших промптов?

### 4. Скрипты (~/.claude/scripts/)
```bash
for script in ~/.claude/scripts/*.sh; do bash -n "$script" && echo "OK: $script" || echo "FAIL: $script"; done
for script in ~/.claude/scripts/*.py; do python3 -c "import py_compile; py_compile.compile('$script', doraise=True)" && echo "OK: $script" || echo "FAIL: $script"; done
```

### 5. Cron-задачи
```bash
crontab -l
```
- Все ли задачи актуальны?
- Нет ли конфликтов по расписанию?
- Логи пишутся?

### 6. LaunchAgents
```bash
ls ~/Library/LaunchAgents/ | grep -v com.apple
```
- Все ли загружены?
- Нет ли ошибок? (`launchctl list | grep claude`)

### 7. VPS (91.107.122.157)
```bash
ssh -i ~/.ssh/vps_artvision root@91.107.122.157 'uptime && pm2 list && crontab -l && df -h / && free -h'
```
- Сервисы работают?
- Диск не забит?
- Память в норме?

### 8. Git-репозитории
```bash
for repo in ~/artvision-data ~/artvision-tg-bot ~/devops-agent; do
  echo "=== $repo ==="
  cd "$repo"
  git status --short
  git log --oneline -1
  echo ""
done
```
- Нет ли незакоммиченных изменений?
- Всё ли запушено?

### 9. Токены и API
```bash
python3 ~/devops-agent/monitors/token_monitor.py --validate 2>/dev/null
```
- Все ли токены валидны?
- Нет ли просроченных?

### 10. CLAUDE.md
- Прочитать ~/.claude/CLAUDE.md
- Нет ли устаревших правил?
- Нет ли противоречий?
- Размер в пределах нормы?

## Формат отчёта

```markdown
# Maintenance Report: DD.MM.YYYY

## Состояние системы: ✅ OK / ⚠️ ISSUES / ❌ CRITICAL

| Компонент | Статус | Проблемы | Действия |
|-----------|--------|----------|----------|
| Хуки | ✅ | — | — |
| Скиллы | ⚠️ | 2 без frontmatter | Исправлено |
| VPS | ✅ | — | — |
| Git | ⚠️ | 3 непушнутых коммита | Запушено |
| Токены | ❌ | Groq expired | Обновлено |

## Автоматически исправлено
- ...

## Требует ручного вмешательства
- ...
```

## Действия после проверки
1. Автоматически исправлять мелкие проблемы (chmod, git push, syntax)
2. Показать отчёт пользователю
3. Для серьёзных проблем — спросить подтверждение перед исправлением
4. Git commit отчёт в artvision-data/reports/maintenance/

## Расписание
- **Когда:** Воскресенье вечером (после self-review)
- **Автозапуск:** LaunchAgent `com.claude.weekly-maintenance`
