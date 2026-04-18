---
name: design-review
description: >-
  Pixel-perfect визуальное сравнение страницы с референсом. Находит отличия в layout,
  цветах, типографике, отступах, анимациях, hover-эффектах. Генерирует VISUAL-AUDIT.md.
  Триггеры: pixel-perfect проверка, сравни с референсом, design review, визуальный аудит,
  сравнение дизайнов, похож ли на референс.
user-invocable: true
disable-model-invocation: false
allowed-tools: Read Write Edit Bash(node *) Bash(curl *) Bash(python3 *) Grep Glob WebFetch
metadata:
  author: artvision
  version: "1.0"
  category: design
---

# Design Review — pixel-perfect сравнение с референсом

## Вход

- `[1]` — путь к нашему HTML или URL
- `[2]` — URL референса ИЛИ путь к design-system-*.md

Если аргументы не переданы — спросить.

## Workflow

### Шаг 1: Подготовка

1. Прочитать наш файл (HTML)
2. Если есть design-system-*.md — прочитать (это источник правды по layout)
3. Если передан URL референса — извлечь CSS (как в `/design-extract`)

### Шаг 2: Скриншоты нашей страницы

```javascript
// Playwright — 3 viewport
const viewports = [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'tablet',  width: 768,  height: 1024 },
  { name: 'mobile',  width: 375,  height: 812 },
];

for (const vp of viewports) {
  await page.setViewportSize(vp);
  await page.screenshot({ 
    fullPage: true, 
    path: `screenshots/our-${vp.name}.jpg`,
    type: 'jpeg', quality: 85 
  });
}
```

### Шаг 3: Скриншоты референса

Попробовать Playwright → если блок, curl + local render → если блок, WebFetch.

```javascript
// Playwright attempt
try {
  await page.goto(refUrl, { waitUntil: 'networkidle', timeout: 20000 });
  await page.screenshot({ ... });
} catch {
  // Fallback: curl → file:// render
  // curl -sL refUrl -o /tmp/ref.html
  // await page.goto('file:///tmp/ref.html');
}
```

### Шаг 4: Извлечь computed styles

Через page.evaluate на обеих страницах:

```javascript
const styles = await page.evaluate(() => {
  const get = (sel) => {
    const el = document.querySelector(sel);
    if (!el) return null;
    const cs = getComputedStyle(el);
    return {
      fontSize: cs.fontSize,
      fontWeight: cs.fontWeight,
      lineHeight: cs.lineHeight,
      color: cs.color,
      backgroundColor: cs.backgroundColor,
      padding: cs.padding,
      margin: cs.margin,
      borderRadius: cs.borderRadius,
      boxShadow: cs.boxShadow,
      display: cs.display,
      gap: cs.gap,
      maxWidth: cs.maxWidth,
      minHeight: cs.minHeight,
    };
  };
  
  return {
    body: get('body'),
    h1: get('h1'),
    h2: get('h2'),
    header: get('header'),
    hero: get('section:first-of-type'),
    // ... все ключевые секции
  };
});
```

### Шаг 5: Сравнение и классификация

Для каждого элемента сравнить стили:

| Severity | Критерий |
|----------|----------|
| **CRITICAL** | Другой layout (flex vs grid, direction), отсутствующая секция, font-size разница >4px, wrong background, broken на mobile |
| **SECONDARY** | Spacing разница 4-16px, другой border-radius (16 vs 20), другой shadow, другой transition timing |
| **MINOR** | Spacing разница 1-3px, slightly different opacity, font-weight off by 100 |

### Шаг 6: Responsive check

Сравнить мобильный layout:
- Карточки стекаются вертикально?
- Горизонтальный скролл = БАГ
- Шрифты уменьшаются?
- Touch targets >= 44px?

### Шаг 7: Interaction check

Если Playwright доступен:
```javascript
// Check hover states
await page.hover('.card');
await page.screenshot({ path: 'screenshots/card-hover.jpg' });
// Compare with reference hover
```

### Шаг 8: Генерация VISUAL-AUDIT.md

```markdown
# Visual Audit: {our-page} vs {reference}

**Дата:** YYYY-MM-DD
**Наш файл:** {path}
**Референс:** {url/path}

## Score: X/10

## Critical Differences ({N})

| # | Секция | Элемент | Референс | У нас | Как исправить |
|---|--------|---------|----------|-------|---------------|
| 1 | Hero | Layout | bg-image full-width, min-h 407px | Стандартный flex | Добавить bg-image, min-height |

## Secondary Differences ({N})

| # | Секция | Элемент | Референс | У нас | Как исправить |
|---|--------|---------|----------|-------|---------------|

## Minor Differences ({N})

| # | Элемент | Разница |
|---|---------|---------|

## Responsive Check

| Viewport | Status | Issues |
|----------|--------|--------|
| Desktop 1440px | OK/FAIL | ... |
| Tablet 768px | OK/FAIL | ... |
| Mobile 375px | OK/FAIL | ... |

## Top 5 Fixes (по визуальному импакту)

1. **[CRITICAL]** ... → эффект: ...
2. ...

## Screenshots

Сохранены в `{folder}/screenshots/`:
- our-desktop.jpg, our-tablet.jpg, our-mobile.jpg
- ref-desktop.jpg, ref-tablet.jpg, ref-mobile.jpg
```

Записать в: `{folder}/VISUAL-AUDIT.md`

### Шаг 9: Auto-fix (опционально)

Если вызвано с `--fix`:
1. Взять все CRITICAL из аудита
2. Для каждого — применить исправление через Edit tool
3. Перепроверить скриншотом
4. Обновить VISUAL-AUDIT.md

## Выбор агента для сравнения

**ОБЯЗАТЕЛЬНО:** использовать `design-system-architect` или `ui-visual-validator` субагент.
**ЗАПРЕЩЕНО:** использовать `frontend-developer` (он не даёт pixel-perfect качество).

## Чеклист

- [ ] Скриншоты нашей страницы (3 viewport)
- [ ] Скриншоты или данные референса
- [ ] Computed styles обеих страниц
- [ ] Классификация различий (critical/secondary/minor)
- [ ] Responsive check
- [ ] Interaction/hover check
- [ ] VISUAL-AUDIT.md сгенерирован
- [ ] Top 5 fixes ранжированы по импакту
