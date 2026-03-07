# Outreach Emails Skill — Индекс файлов

Быстрая навигация по всем компонентам скилла.

## Основные файлы (читать в этом порядке)

1. **QUICK_START.md** (7 KB)
   - Быстрый старт за 20-30 минут
   - 3 шага к первому письму
   - Примеры команд
   - Таймлайн follow-up

2. **SKILL.md** (26 KB) — ГЛАВНЫЙ ФАЙЛ
   - Полная документация
   - 4 типа писем (GUEST_POST, LINK_EXCHANGE, EXPERT_COMMENT, MENTION_IN_REVIEW)
   - Шаблоны писем для каждого типа
   - 6 фаз генерации
   - Anti-spam правила
   - Примеры удачных писем
   - Бюджет времени

3. **README.md** (10 KB)
   - Обзор скилла
   - Примеры использования
   - Таблицы метрик
   - История версий

## Вспомогательные файлы

### research-template.md (4 KB)
Чек-лист для исследования сайта-донора перед написанием письма.

**Когда использовать:** перед каждым письмом (заполнить 10-15 минут)

**Содержит:**
- Основные данные сайта
- Контактная информация
- Анализ контента
- Выбор типа письма
- Спам-фильтры

### tracker.json (4 KB)
JSON-трекер отправленных писем и кампаний.

**Структура:**
```json
{
  "campaigns": [...],
  "emails": [...],
  "metrics": {...}
}
```

**Когда обновлять:** после отправки письма, после follow-up, после получения ответа

## Python-скрипты

### validate_email.py (8 KB)
Валидатор писем перед отправкой.

**Использование:**
```bash
python3 validate_email.py --subject "Subject" --body "Email body"
```

**Проверяет:**
- 15+ спам-слов (срочно, прибыль, гарантировано)
- Чрезмерное пунктирование
- Персонализацию
- Количество ссылок
- Длину письма (150-250 слов)
- CTA
- Приветствие

**Выход:** score (0-100), errors, warnings

**Score >= 70** = готово отправлять

### tracker_manager.py (12 KB)
Менеджер трекера писем (добавление, обновление, метрики).

**Основные команды:**

```bash
# Добавить письмо
python3 tracker_manager.py add \
  --campaign "ant-partners" \
  --website "nalogovoe.pro" \
  --recipient "Иван Петров" \
  --email "ivan@nalogovoe.pro" \
  --type "GUEST_POST" \
  --subject "Subject письма"

# Обновить статус
python3 tracker_manager.py update \
  --id "email-001" \
  --status "positive" \
  --response "Согласился"

# Отметить follow-up
python3 tracker_manager.py follow-up --id "email-001" --number 1

# Показать статус
python3 tracker_manager.py status --campaign "ant-partners"

# Метрики
python3 tracker_manager.py metrics

# Ожидающие follow-up
python3 tracker_manager.py pending
```

## Файлы данных

### tracker.json
Все отправленные письма, статус, follow-up, ответы.

**Обновляется:** вручную (tracker_manager.py) или при отправке письма

## Быстрая справка

### Как выбрать тип письма?

| Тип | Требует | Результат | Сложность |
|-----|---------|-----------|-----------|
| **GUEST_POST** | Готовая статья | Бэклинк + трафик | Высокая |
| **EXPERT_COMMENT** | Идея комментария | Бэклинк + упоминание | Средняя |
| **LINK_EXCHANGE** | Релевантный сайт | Быстрый бэклинк | Низкая |
| **MENTION_IN_REVIEW** | Рейтинг/список | Упоминание | Низкая |

### Как использовать скилл?

**День 1:**
1. Выбрать сайт-донор
2. Заполнить research-template.md (15 мин)
3. Попросить agenta сгенерировать письмо
4. Валидировать: `python3 validate_email.py --subject "..." --body "..."`
5. Добавить в трекер: `python3 tracker_manager.py add ...`
6. Отправить письмо (вручную)

**День 3:**
7. Запустить: `python3 tracker_manager.py pending`
8. Отправить follow-up 1
9. Обновить статус: `python3 tracker_manager.py follow-up --id "email-001" --number 1`

**День 7:**
10. Запустить: `python3 tracker_manager.py pending`
11. Отправить follow-up 2 или альтернативу
12. Обновить статус: `python3 tracker_manager.py follow-up --id "email-001" --number 2`

**Конец недели:**
13. Посмотреть результаты: `python3 tracker_manager.py status`
14. Метрики: `python3 tracker_manager.py metrics`

### Нормы успеха

- **Reply Rate:** 15-25% (1 ответ из 5-7)
- **Conversion Rate:** 5-10% (1 ссылка из 10-20)
- **Time to Reply:** 1-7 дней

Если Reply Rate < 10% → переоценить целевые сайты или улучшить персонализацию.

## Файл Размер
- SKILL.md | 26 KB | Полная документация (4 типа, шаблоны, примеры)
- README.md | 10 KB | Обзор и примеры использования
- QUICK_START.md | 7 KB | Быстрый старт за 20-30 минут
- research-template.md | 4 KB | Чек-лист исследования сайта
- tracker.json | 4 KB | JSON-трекер писем и кампаний
- tracker_manager.py | 12 KB | Менеджер трекера (add, update, metrics)
- validate_email.py | 8 KB | Валидатор писем (score, errors)
- INDEX.md | это файл | Индекс и быстрая справка

**Итого:** ~70 KB документации + 20 KB Python-скриптов

## Наиболее частые операции

```bash
# 1. Исследовать сайт и заполнить чек-лист
cat /Users/antonk/.claude/skills/outreach-emails/research-template.md

# 2. Генерировать письмо (через агента)
"Клод, генерируй письмо GUEST_POST для [сайта]..."

# 3. Валидировать письмо
python3 /Users/antonk/.claude/skills/outreach-emails/validate_email.py \
  --subject "Subject" --body "Body"

# 4. Добавить в трекер
python3 /Users/antonk/.claude/skills/outreach-emails/tracker_manager.py add \
  --campaign "ant-partners" \
  --website "example.com" \
  --recipient "Ivan" \
  --email "ivan@example.com" \
  --type "GUEST_POST" \
  --subject "Subject"

# 5. Показать статус
python3 /Users/antonk/.claude/skills/outreach-emails/tracker_manager.py status

# 6. Показать метрики
python3 /Users/antonk/.claude/skills/outreach-emails/tracker_manager.py metrics
```

## Интеграция с другими скиллами

- **content-writer:** для написания статей (если GUEST_POST требует контента)
- **presale-kp:** если нужно отправить КП вместе с письмом
- **copywriting:** для A/B тестирования subject line

## История

- **2026-03-07:** v1.0 — Первая версия скилла
  - 4 типа писем с шаблонами на русском
  - Валидатор писем (15+ проверок)
  - Менеджер трекера (add, update, status, metrics, follow-up, pending)
  - Anti-spam фильтры
  - Follow-up стратегия (дни 1, 3, 7)
  - Чек-лист исследования
  - Примеры удачных писем
