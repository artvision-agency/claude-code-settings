---
name: bot-test-matrix
description: >-
  Автоматический анализ state machine Telegram-бота: парсит код, строит граф
  состояний, считает комбинации путей, генерит тест-кейсы и запускает
  параллельных агентов-тестировщиков. Вызывается после деплоя или вручную.
  Триггеры: "тест матрица", "test matrix", "проверь бота", после deploy-tvorims.sh.
argument-hint: "[path-to-bot]"
user-invocable: true
allowed-tools: Read Grep Glob Bash(python3 *)
metadata:
  author: artvision
  version: "1.0"
  category: testing
---

# Bot Test Matrix

Автоматический QA для Telegram-ботов на python-telegram-bot.

## Workflow

### Step 1: Определить проект

Если аргумент не передан — использовать текущий cwd.
Найти основные файлы бота:

```
Glob: **/handlers/*.py, **/bot.py, **/config.py, **/llm.py
```

### Step 2: Запустить анализатор графа

```bash
python3 ~/.claude/skills/bot-test-matrix/scripts/state-graph-analyzer.py <path-to-bot>
```

Скрипт выводит JSON:
```json
{
  "nodes": [...],
  "edges": [...],
  "entry_points": [...],
  "terminal_states": [...],
  "branching_factors": {...},
  "total_paths": N,
  "recommended_tests": N,
  "test_groups": [
    {"name": "...", "count": N, "scenarios": ["..."]}
  ]
}
```

### Step 3: Показать пользователю сводку

Формат:

```
## State Machine бота

| Метрика | Значение |
|---------|----------|
| Состояний | X |
| Переходов | X |
| Уникальных путей | X |
| Рекомендуемых тестов | X |

### Группы тестов
1. Happy path (avg >= порога): N тестов
2. Unhappy path (avg < порога): N тестов
3. QR lobby: N тестов
4. Edge cases: N тестов
```

### Step 4: Запустить тестировщиков

Разбить тесты на группы по 12-15. Запустить параллельных агентов (Agent tool):

- Каждый агент получает свою группу сценариев
- Агент проверяет ПО КОДУ (не запуская бот): находит строки, проверяет логику
- Формат ответа: `#N: PASS/FAIL — объяснение (файл:строка)`

Количество агентов = ceil(total_tests / 13).

### Step 5: Собрать результаты

Агрегировать PASS/FAIL по всем агентам. Показать:

```
## Результат: X/Y PASS

| # | Сценарий | Результат | Файл:строка |
|---|----------|-----------|-------------|
| 1 | ... | PASS | survey.py:748 |
| 2 | ... | FAIL | reviews.py:320 |

### FAIL детали
#2: Ожидалось X, найдено Y в reviews.py:320
```

## Автозапуск после деплоя

При вызове `./deploy-tvorims.sh` или команде "деплой" — автоматически предложить:
"Бот задеплоен. Запустить тест-матрицу? (Y/n)"

## Правила

- НЕ запускать бот, НЕ отправлять сообщения в Telegram
- Проверка ТОЛЬКО по коду (статический анализ)
- Каждый сценарий = конкретные строки кода + логика
- FAIL только если логика реально сломана, не Pyright warnings
- Агенты = opus (по правилам tokens.md)
