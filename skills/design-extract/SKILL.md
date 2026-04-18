---
name: design-extract
description: >-
  Извлечь полную дизайн-систему (палитра, типографика, отступы, тени, анимации, layout секций)
  из любого сайта-референса. Используй когда нужно клонировать/адаптировать дизайн.
  Триггеры: дизайн-система, извлеки стили, design tokens, референс сайта, клонируй дизайн,
  pixel-perfect, шаблон сайта.
user-invocable: true
disable-model-invocation: false
allowed-tools: Read Write Edit Bash(curl *) Bash(node *) Bash(python3 *) Grep Glob WebFetch
metadata:
  author: artvision
  version: "1.0"
  category: design
---

# Design Extract — извлечение дизайн-системы из референса

## Вход

`<arguments>` = URL сайта-референса (например `https://ldg-clinic.ru/`)

Если URL не передан — спросить.

## Workflow

### Шаг 1: Fetch HTML + CSS

```bash
# HTML
curl -sL -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)" "<url>" -o /tmp/ref-site.html

# Найти внешние CSS файлы
grep -oE '<link[^>]+href="([^"]*\.css[^"]*)"' /tmp/ref-site.html

# Скачать каждый CSS файл темы (НЕ cdn/bootstrap/normalize)
curl -sL "<css-url>" -o /tmp/ref-theme.css
```

Если сайт блокирует curl — попробовать Playwright. Если и Playwright блокирует — использовать WebFetch.

### Шаг 2: Извлечь CSS Variables

```bash
grep -oE '\-\-[a-zA-Z0-9_-]+:\s*[^;]+' /tmp/ref-theme.css | sort -u
```

### Шаг 3: Извлечь палитру

```bash
# Hex colors (частотность)
grep -oE '#[0-9a-fA-F]{3,8}' /tmp/ref-theme.css | sort | uniq -c | sort -rn | head -30

# RGBA
grep -oE 'rgba?\([^)]+\)' /tmp/ref-theme.css | sort | uniq -c | sort -rn | head -20

# HSL
grep -oE 'hsla?\([^)]+\)' /tmp/ref-theme.css | sort | uniq -c | sort -rn | head -10
```

Классифицировать:
- **Primary** — основной акцентный цвет (кнопки, ссылки)
- **Secondary** — второстепенный акцент
- **Background** — фоны секций (warm/cool/neutral)
- **Text** — основной, мягкий, мутный
- **Border** — линии, разделители
- **Footer** — тёмный фон

### Шаг 4: Извлечь типографику

```bash
# Font families
grep -oE 'font-family:[^;]+' /tmp/ref-theme.css | sort -u

# Font sizes (частотность)
grep -oE 'font-size:\s*[^;]+' /tmp/ref-theme.css | sort | uniq -c | sort -rn | head -20

# Font weights
grep -oE 'font-weight:\s*[^;]+' /tmp/ref-theme.css | sort | uniq -c | sort -rn

# Line heights
grep -oE 'line-height:\s*[^;]+' /tmp/ref-theme.css | sort | uniq -c | sort -rn | head -15

# Letter spacing
grep -oE 'letter-spacing:\s*[^;]+' /tmp/ref-theme.css | sort -u
```

Построить шкалу: body → h6 → h5 → h4 → h3 → h2 → h1

### Шаг 5: Извлечь spacing

```bash
# Paddings
grep -oE 'padding:\s*[^;]+' /tmp/ref-theme.css | sort | uniq -c | sort -rn | head -20

# Margins
grep -oE 'margin:\s*[^;]+' /tmp/ref-theme.css | sort | uniq -c | sort -rn | head -20

# Gaps
grep -oE 'gap:\s*[^;]+' /tmp/ref-theme.css | sort | uniq -c | sort -rn | head -15
```

Определить base unit (обычно 4px или 8px).

### Шаг 6: Извлечь shadows

```bash
grep -oE 'box-shadow:\s*[^;]+' /tmp/ref-theme.css | sort -u
```

### Шаг 7: Извлечь border-radius

```bash
grep -oE 'border-radius:\s*[^;]+' /tmp/ref-theme.css | sort | uniq -c | sort -rn | head -15
```

### Шаг 8: Извлечь структуру секций

```bash
# Из HTML — все section с классами
grep -oE '<section[^>]*class="([^"]*)"' /tmp/ref-site.html

# Все H1/H2 заголовки
grep -oE '<h[12][^>]*>.*?</h[12]>' /tmp/ref-site.html
```

Построить карту секций: порядок, фон, padding, содержимое.

### Шаг 9: Извлечь layout каждой секции

Для каждой ключевой секции (hero, advantages, services, doctors, etc.) извлечь:
- display (flex/grid)
- grid-template-columns
- flex-direction
- gap
- alignment
- min-height / max-width
- background

```bash
# Найти правила для конкретной секции
python3 -c "
import re
with open('/tmp/ref-theme.css') as f:
    css = re.sub(r'\s+', ' ', f.read())
for m in re.finditer(r'([^{}]*SECTION_NAME[^{]*)\{([^}]+)\}', css):
    print(m.group(1).strip())
    for p in m.group(2).split(';'):
        if p.strip(): print(f'  {p.strip()};')
    print()
"
```

### Шаг 10: Извлечь анимации

```bash
grep -oE 'transition:\s*[^;]+' /tmp/ref-theme.css | sort -u
grep -oE 'animation:\s*[^;]+' /tmp/ref-theme.css | sort -u
grep -oE '@keyframes[^{]+' /tmp/ref-theme.css | sort -u
grep -oE 'transform:\s*[^;]+' /tmp/ref-theme.css | sort -u | head -10
```

### Шаг 11: Извлечь responsive breakpoints

```bash
grep -oE '@media[^{]+' /tmp/ref-theme.css | sort -u
```

### Шаг 12: Сгенерировать отчёт

Записать файл: `{client-folder}/presale/design-system-{sitename}-reference.md`

Формат отчёта:

```markdown
# Design System — {site name}
Источник: {url}
Дата извлечения: {date}
CSS: {size} chars из {N} файлов

## Палитра
| Роль | Цвет | Hex | Использований |
|------|------|-----|:-------------:|

## Типографика
| Элемент | Size | Weight | Line-height | Family |
|---------|------|--------|-------------|--------|

## Spacing
Base unit: Xpx
| Паттерн | Значение | Где используется |

## Shadows
| Тип | Значение |

## Border-radius
| Тип | Значение |

## Карта секций
| # | Секция | Класс | Фон | Padding | Layout |

## Layout деталей секций
### Hero
- display: ...
- min-height: ...
...

### Advantages
...

## Анимации
| Свойство | Значение |

## Breakpoints
| Breakpoint | Что меняется |

## CSS Variables (готовый блок)
```css
:root {
  --primary: ...;
  ...
}
```
```

## Чеклист завершения

- [ ] Палитра: primary, secondary, bg, text, border, footer
- [ ] Типографика: h1-h6, body, small, links
- [ ] Spacing: section padding, card padding, gaps
- [ ] Shadows: card, hover, dropdown
- [ ] Border-radius: cards, buttons, inputs, pills
- [ ] Секции: порядок, фоны, содержимое
- [ ] Layout: flex/grid pattern каждой секции
- [ ] Анимации: transitions, transforms, keyframes
- [ ] Breakpoints: mobile, tablet, desktop
- [ ] CSS variables: готовый блок для нового проекта
