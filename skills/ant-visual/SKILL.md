---
name: ant-visual
description: "Визуальная проверка страниц ANT Partners — скриншоты на 3 breakpoints + сравнение с предыдущей версией. Триггеры: 'ant visual', 'скриншоты ant', 'визуальная проверка ant', 'ant screenshots'"
---

# ANT Partners Visual Check

Визуальная регрессия: скриншоты страниц на 3 breakpoints (375/768/1440), сравнение с baseline.

## Быстрая проверка (Playwright MCP)

Если Playwright MCP доступен, используй его напрямую:

```
1. browser_resize(1440, 900) → browser_navigate(URL) → browser_take_screenshot(fullPage, jpeg)
2. browser_resize(768, 1024) → browser_take_screenshot
3. browser_resize(375, 812) → browser_take_screenshot
```

URL формат: `http://ant-dev.artvision.pro/nashi-uslugi/{slug}.html`
Хабы: `http://ant-dev.artvision.pro/nashi-uslugi/{hub}/`

Проверить минимум 3 страницы: 1 хаб + 1 вложенная + 1 плоская.

## Автоматическая проверка (скрипт)

```bash
cd /Users/antonk/artvision-data/clients/ant-partners/templates/

# 5 sample pages
python3 ant-visual-check.py

# Все 29 страниц
python3 ant-visual-check.py --all

# Конкретные страницы
python3 ant-visual-check.py --pages bankrotstvo proverki advokat

# Обновить baseline
python3 ant-visual-check.py --update
```

Требует: `pip install playwright Pillow` + `npx playwright install chromium`

## Breakpoints

| Устройство | Ширина | Высота |
|-----------|--------|--------|
| Mobile | 375 | 812 |
| Tablet | 768 | 1024 |
| Desktop | 1440 | 900 |

## Что проверять визуально

1. **Hero** — картинка загружается, текст читается
2. **Статистика** — 4 блока в ряд (desktop), стек (mobile)
3. **Figures** — картинки загружаются, подписи видны
4. **FAQ** — аккордеон раскрывается
5. **Форма** — поля и кнопка видны
6. **Footer** — контакты, лого
