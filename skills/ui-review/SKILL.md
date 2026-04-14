---
name: ui-review
description: "Визуальное ревью HTML/страниц/дашбордов через скриншоты на 3 breakpoints. Вызывает ui-visual-validator агента. Триггеры: 'ui ревью', 'визуальная проверка', 'скриншот', 'как выглядит', 'проверь визуал', 'review ux ui'"
---

# UI Review — Визуальное ревью

## Цель
Проверить визуальное состояние HTML/страницы на 3 breakpoints, выявить регрессии, обрезания, белые экраны, overflow. Используется в ФАЗЕ 4 комбайна для `result_type: html`.

## Когда вызывается
- После любого изменения HTML/CSS
- После деплоя страницы на VPS
- Проверка дашборда перед отправкой клиенту
- Триггер `review ux ui` / `blocks` / `pictures` / `визуал`

## Процесс

### ШАГ 1: Определить цель

| Цель | Breakpoints | Фокус |
|------|:-----------:|-------|
| Десктоп лендинг | 1920, 1440, 1280 | Hero, fold, CTA |
| Респонсив | 1440, 768, 375 | Адаптивность |
| Мобильный-first | 414, 375, 320 | Читаемость, кнопки |
| Дашборд | 1920, 1440 | Графики, таблицы |
| КП/документ | 1440, 768 | Логика блоков |

По умолчанию: `desktop:1440`, `tablet:768`, `mobile:375`.

### ШАГ 2: Снять скриншоты

```bash
# Вариант 1: Playwright (если есть)
python3 ~/.claude/scripts/screenshot-breakpoints.py <url> --out /tmp/review/

# Вариант 2: screenshot.xyz API (см. feedback_screenshot_xyz.md)
# Вариант 3: headless Chrome
for w in 1440 768 375; do
  chrome --headless --screenshot=/tmp/review/${w}.png --window-size=${w},900 "$url"
done
```

Файлы: `/tmp/review/<name>-<width>.png`.

### ШАГ 3: Автоматические проверки

Сначала автопроверки без агента (быстрее, дешевле):

```python
# scripts/ui-autocheck.py
from PIL import Image

checks = {
  "not_white": lambda img: img.getcolors() != [(1, (255,255,255))],
  "min_height": lambda img: img.height > 500,
  "has_content": lambda img: len(set(img.getdata())) > 100,
}
```

| Проверка | FAIL |
|----------|------|
| Белый экран (99% белого) | CRITICAL — rollback |
| Высота < 500px | CRITICAL |
| Меньше 100 уникальных цветов | WARNING — пустая/сломанная |
| Горизонтальный scrollbar | WARNING |
| Файл < 5KB | CRITICAL — не отрендерилось |

### ШАГ 4: Агент-ревью (ui-visual-validator)

Если автопроверки PASS — передать скриншоты агенту:

```
Agent(ui-visual-validator):
  "Проверь 3 скриншота <name> на 1440/768/375.
   Фокус:
   1. Белый экран / пустой контент
   2. Horizontal overflow
   3. Обрезанный текст
   4. Битые картинки (broken-image icons)
   5. Налезающие блоки
   6. Читаемость контраста
   7. TOC/nav видны
   Верни PASS/WARN/FAIL + список проблем + приоритет."
```

### ШАГ 5: Autofix цикл

| Проблема | Autofix |
|----------|---------|
| Horizontal overflow | `overflow-x: hidden` на `body` или `max-width: 100%` на проблемном блоке |
| Битая картинка | Вызов `factcheck-v2.py` → замена URL |
| Обрезанный текст | `word-wrap: break-word` |
| Белый экран | Проверить HTML-валидность, консоль, JS-ошибки |

Макс 2 цикла autofix → если не починилось → skip с записью в `patches/`.

### ШАГ 6: Отчёт

`clients/<c>/reviews/<date>-<name>.md`:
```markdown
# UI Review — <name> — <date>

## Скриншоты
- Desktop: /tmp/review/<name>-1440.png
- Tablet: /tmp/review/<name>-768.png
- Mobile: /tmp/review/<name>-375.png

## Autocheck
- PASS / WARN / FAIL
- ...

## Agent review
- PASS / WARN / FAIL
- Проблемы: ...
- Autofixed: ...
- Остались: ...

## Verdict
- [ ] READY for deploy
- [ ] NEEDS WORK: ...
```

## Запреты
- Не одобрять visual с белым экраном (даже если HTTP 200)
- Не пропускать horizontal overflow на мобильном
- Не использовать скриншоты продакшена в публичных отчётах без разрешения клиента

## Связанные
- `validate-pages` — DOM-валидация (не визуал)
- `factcheck-v2.py` — URL-проверка
- `ui-visual-validator` агент — финальное ревью
- `feedback_white_screen_debug.md` — дебаг белого экрана
- `feedback_screenshot_xyz.md` — альтернативный сервис скриншотов
