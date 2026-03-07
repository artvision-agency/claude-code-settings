---
name: context
description: "Entire-inspired context tracking: log decisions, prompts, commit context. Usage: /context [decision text] or /context --prompt [prompt] or /context --list"
disable-model-invocation: false
allowed-tools:
  - Bash
  - Read
  - Write
  - Grep
  - Glob
---

# Context Logger — Decision Tracking

Логирование контекста решений по аналогии с Entire (версионирование AI-диалогов).

## Как использовать

### Залогировать решение
Пользователь написал `/context` + текст решения.

1. Определить клиента из текста (если упомянут)
2. Определить категорию: `architecture`, `seo`, `design`, `process`, `content`, `product`, `general`
3. Выполнить:

```bash
python3 /Users/antonk/artvision-data/scripts/context_logger.py \
  --log "ТЕКСТ РЕШЕНИЯ" \
  --client "КЛИЕНТ" \
  --category "КАТЕГОРИЯ" \
  --tags "тег1,тег2" \
  --rationale "ОБОСНОВАНИЕ"
```

### Залогировать промпт
Если пользователь написал `/context --prompt` или `/context промпт`:

```bash
python3 /Users/antonk/artvision-data/scripts/context_logger.py \
  --prompt "ТЕКСТ ПРОМПТА" \
  --category "КАТЕГОРИЯ" \
  --result "ОПИСАНИЕ РЕЗУЛЬТАТА" \
  --quality ЧИСЛО_1_10 \
  --client "КЛИЕНТ"
```

### Показать решения
Если `/context --list` или `/context список`:

```bash
python3 /Users/antonk/artvision-data/scripts/context_logger.py --list --days 7
```

С фильтром по клиенту:
```bash
python3 /Users/antonk/artvision-data/scripts/context_logger.py --list --client ant-partners
```

### Поиск
```bash
python3 /Users/antonk/artvision-data/scripts/context_logger.py --search "ЗАПРОС"
```

## Категории решений

| Категория | Когда |
|-----------|-------|
| `architecture` | Выбор технологий, CMS, структуры |
| `seo` | SEO стратегия, ключи, приоритеты |
| `design` | Дизайн, UI/UX, цвета, шрифты |
| `process` | Изменение рабочих процессов |
| `content` | Контент-решения, тон, стиль |
| `product` | Продуктовые решения |
| `general` | Всё остальное |

## Автоматическое логирование

Claude ДОЛЖЕН автоматически логировать решения когда:
- Выбирается подход из нескольких альтернатив
- Клиент просит изменить стратегию
- Обнаружена ошибка и выбрано исправление
- Создаётся новый процесс или меняется существующий
