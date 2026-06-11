# Claude Code Hooks - Token Protection & Auto-Logging

Хуки для предотвращения перерасхода токенов и автоматического логирования уроков.

## Native Hooks (settings.json)

Настроены в `~/.claude/settings.json`:

### Stop Hook
- **Когда**: При завершении ответа Claude
- **Что делает**: Логирует время в `~/.claude/session_logs/sessions.log`

### PreToolUse → Read
- **Когда**: Перед чтением файла
- **Что делает**: Запускает `pre-read.sh` для проверки размера

## Установленные хуки

### 0. save_session.py (АВТОЛОГИРОВАНИЕ)
**Срабатывает**: В конце каждой сессии (SessionEnd hook)

**Что делает**:
- Анализирует сессию на наличие ошибок, паттернов, решений
- Записывает уроки в `~/.claude/session_logs/lessons_learned.md`
- Пропускает тривиальные сессии (простые вопрос-ответ)

**Формат записи**:
```markdown
## [2026-01-28 13:34] category
**Проект:** `/path/to/project`
**Что произошло:** описание
**Урок/Действие:** что запомнить
```

**Категории**: error, pattern, decision, optimization, setup

**Ручной вызов**:
```bash
~/.claude/hooks/save_session.py '{"category": "error", "description": "что случилось", "action": "что делать", "cwd": "/путь"}'
```

### 1. pre-read.sh
**Срабатывает**: Перед каждым Read tool

**Что делает**:
- Проверяет размер файла перед чтением
- Предупреждает о больших файлах (>2000 строк)
- Блокирует чтение огромных файлов (>10000 строк) без подтверждения
- Предлагает альтернативы: Grep, offset/limit

**Пороги**:
- 2000+ строк → info (показывает оценку токенов)
- 5000+ строк → warning (спрашивает подтверждение)
- 10000+ строк → critical (требует явного подтверждения)

### 2. context-monitor.sh
**Срабатывает**: Периодически во время сессии

**Что делает**:
- Отслеживает размер контекста
- Предупреждает при 75% заполнения (150K токенов)
- Критическое предупреждение при 90% (180K токенов)
- Рекомендует начать новую сессию или использовать Task tool

### 3. post-frontend.sh
**Срабатывает**: После вызова frontend-developer агента

**Что делает**:
- Проверяет созданные файлы
- Валидирует HTML/CSS

## Как работают хуки

Хуки автоматически вызываются Claude Code:
1. Claude собирается выполнить действие (Read, Task, etc.)
2. Проверяет наличие соответствующего хука
3. Запускает хук и передаёт параметры
4. Если хук возвращает exit 1 → действие блокируется
5. Если exit 0 → действие выполняется

## Конфигурация

Редактировать пороги в файлах хуков:
```bash
# pre-read.sh
LINE_COUNT > 5000  # изменить порог

# context-monitor.sh
WARNING_THRESHOLD=150000  # 75%
CRITICAL_THRESHOLD=180000 # 90%
```

## Тестирование

```bash
# Проверить pre-read.sh вручную
~/.claude/hooks/pre-read.sh /path/to/large/file.txt

# Проверить context-monitor.sh
~/.claude/hooks/context-monitor.sh
```

## Отключение хука

Временно отключить хук:
```bash
chmod -x ~/.claude/hooks/pre-read.sh
```

Включить обратно:
```bash
chmod +x ~/.claude/hooks/pre-read.sh
```

## usage-warn.sh + statusline-weekly.sh (недельный учёт расхода, linux-сетап stan)

Самодостаточная альтернатива связке `account-usage-tracker.sh`/VPS-синка — без внешних
зависимостей (`claude auth status`, artvision-data, Telegram): только python3 и сам Claude Code.

**Как работает:**
- `statusline-weekly.sh` (корень репы; ставится как `~/.claude/statusline.sh`) — статус-строка
  `user | model | dir | branch* | ctx:NN% | $сессия | w:$X/LIMIT (NN%)`. Claude Code передаёт
  statusline `cost.total_cost_usd` сессии при каждом обновлении; скрипт upsert'ит её по
  `session_id` в `~/.claude/account-usage.json` и держит rolling 7-дневную сумму `weekly_cost`.
  Маркеры: `w` → `w*` (≥50%) → `w!` (≥80%) → `W!` (≥97%).
- `hooks/usage-warn.sh` (UserPromptSubmit) — при входе в полосу 50/60/70/80/90/97%
  показывает `systemMessage` пользователю и инжектит `additionalContext` модели
  (Claude сам предупредит и учтёт при планировании тяжёлых операций).
  Дедуп: раз в 6 часов внутри полосы (`~/.claude/.usage-warn-state.json`).

**Подключение** (`~/.claude/settings.json`):
```json
"statusLine": { "type": "command", "command": "/home/USER/.claude/statusline.sh" },
"hooks": {
  "UserPromptSubmit": [
    { "hooks": [ { "type": "command", "command": "/home/USER/.claude/hooks/usage-warn.sh", "timeout": 10 } ] }
  ]
}
```

**Калибровка лимита:** трекер видит только локальные сессии этой машины (не другие
устройства/claude.ai). Лимит подбирается по `/usage`: `weekly_limit_usd = tracked_$ / (доля
из /usage)`. Пример: трекер $764, `/usage` 12% → лимит ≈ 6400. Правится в
`~/.claude/account-usage.json` (файл в .gitignore — данные не коммитятся).

**Известное отличие от /usage:** там фиксированный недельный сброс, тут rolling 7 дней —
сразу после сброса трекер временно завышает (предупреждает раньше, безопасная сторона).
