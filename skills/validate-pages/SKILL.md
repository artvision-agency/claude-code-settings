---
name: validate-pages
description: "DOM-валидация HTML страниц клиентов против эталона. Проверяет CSS-классы, структуру секций, дубли H2, порядок, пустые секции. НЕ grep — реальный DOM-парсинг через BeautifulSoup."
---

# /validate-pages — DOM-валидация HTML страниц

## Когда использовать
- После генерации HTML страниц для клиентов
- После массовых правок (wave batches)
- Перед отдачей клиенту
- Когда есть сомнения в качестве проверки

## Как работает

### Шаг 1 — Определить проект и эталон

Если пользователь указал клиента/проект — найти:
- Папку с HTML файлами (обычно `output_v7/for_client/wave*/`)
- Эталонный файл (обычно `templates/analysis/[name].html`)

Текущие проекты с валидатором:
- **ANT Partners**: `scripts/validate_wave1_dom.py` — 14 страниц wave1

### Шаг 2 — Запустить валидатор

```bash
python3 scripts/validate_wave1_dom.py                  # все файлы
python3 scripts/validate_wave1_dom.py --file nds       # один файл
python3 scripts/validate_wave1_dom.py --reference-only # показать blueprint эталона
python3 scripts/validate_wave1_dom.py --json           # JSON для парсинга
```

### Шаг 3 — Анализ результатов

| Статус | Значение |
|--------|----------|
| `FAIL` | Отсутствует обязательная секция (stats, advantages, price-table, timeline, faq, form, footer, modal) |
| `DUPE H2` | Дублированные заголовки H2 (кроме "Оставить заявку") |
| `FORBIDDEN` | Запрещённые паттерны (пустые секции, внешние URL, лишние формы) |
| `WRONG CLASS` | Неправильный CSS класс (steps-grid вместо timeline, features-grid в price-секции) |
| `WARN` | Некритично (hero-cta, form tag, figcaptions) |
| `ORDER` | Нарушен порядок секций |

### Шаг 4 — Исправления

**FAIL/DUPE → обязательный фикс** прямой правкой Edit tool (НЕ через агентов — проверено, агенты могут не сохранить).

**WRONG CLASS в контентных секциях** (типа "Что такое допрос", "Признаки дробления") → это НЕ ошибка, `.features-grid` для информационных карточек — нормально.

**WRONG CLASS в steps/timeline секциях** ("Как мы работаем", "Как получить консультацию") → конвертировать `steps-grid/step-card` → `timeline/timeline-item`.

### Шаг 5 — Повторная проверка

ПОСЛЕ каждого фикса → перезапустить валидатор → убедиться в улучшении.

## Создание валидатора для нового проекта

Если эталон есть, но валидатора нет:

1. **Извлечь DOM blueprint из эталона:**
   ```python
   python3 scripts/validate_wave1_dom.py --reference-only
   ```

2. **Создать спецификацию:** `REQUIRED_SECTIONS` с:
   - `selector` — CSS-селектор секции
   - `min_count` — минимальное количество
   - `children` — обязательные дочерние элементы
   - `forbidden_alternatives` — запрещённые альтернативные классы

3. **Скопировать `validate_wave1_dom.py`** как шаблон, поменять пути и спецификацию.

## КРИТИЧЕСКОЕ ПРАВИЛО

**НИКОГДА не использовать grep для проверки HTML-структуры.**
grep `price-table` в `<style>` = ложный PASS. Только DOM-парсинг (BeautifulSoup).
