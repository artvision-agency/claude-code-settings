---
name: decision
description: Создать запись в decision journal. Используй при значимых архитектурных/процессных решениях. Триггеры — "decision", "решение", "зафиксировать выбор", "decision log".
---

# Decision Journal

## Protocol

**Перед значимым решением** (архитектура, клиент, процесс, стек):
1. `grep -rli "<topic>" /Users/antonk/artvision-data/decisions/` — prior decisions
2. Если найдено → следовать, если не опровергнуто новыми данными
3. Если новое → создать файл через скрипт

## Создание

```bash
/Users/antonk/artvision-data/scripts/decision-new.sh <slug> "<Title>"
```

Пример: `decision-new.sh kp-design-standard "КП дизайн = CAMEO шаблон"`

Скрипт создаёт `decisions/YYYY-MM-DD-<slug>.md` с шаблоном и автоматически грепает prior decisions.

## Формат (обязательные секции)

- **Decision** — что решили
- **Context** — почему возник вопрос
- **Alternatives Considered** — что ещё рассматривали (2-3 варианта)
- **Reasoning** — почему этот вариант победил
- **Trade-offs Accepted** — что теряем
- **Supersedes** — какое prior decision заменяет (если есть)

## Когда записывать

✅ Записывать:
- Выбор стека/инструмента/архитектуры
- Решения по клиенту (бренд, дизайн, процесс)
- Отказ от варианта по весомым причинам
- Изменение ранее принятого подхода

❌ НЕ записывать:
- Одноразовые тактические действия
- Очевидные решения из документации
- То что уже есть в `knowledge/<domain>/rules.md`

## Workflow

1. Пользователь или Claude видит значимый выбор
2. Grep prior decisions
3. Запустить `decision-new.sh` → файл создан
4. Заполнить секции — можно inline или Edit tool
5. Коммит + push (auto-sync подхватит)
