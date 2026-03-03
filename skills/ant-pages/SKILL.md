---
name: ant-pages
description: "Генерация HTML-страниц для ANT Partners по blueprint из принятых wave1 страниц. Жёсткий скелет + плейсхолдеры. Автоматическая валидация DOM."
disable-model-invocation: true
---

# ANT Partners Page Generator

## Назначение
Создание новых HTML-страниц для ant.partners по точному blueprint, извлечённому из принятых wave1 страниц. Исключает "творчество" агента — только заполнение шаблона.

## Когда использовать
- Создание новой страницы услуги/практики для ANT Partners
- Исправление существующей страницы (пересоздание по blueprint)
- Добавление новой страницы в wave3+

## Обязательный pipeline

### Фаза 1: Подготовка данных
1. Прочитать `clients/ant-partners/CLAUDE.md` (правила клиента)
2. Прочитать `clients/ant-partners/patches/*.md` (все патчи)
3. Прочитать эту skill: `references/section-patterns.md` + `references/blueprint.html`
4. Собрать контент для страницы (WebFetch источника или от пользователя)

### Фаза 2: Генерация (Task → frontend-developer)
Передать агенту:
- **Blueprint** целиком (references/blueprint.html)
- **Section patterns** для нужных типов секций
- **Контент** страницы (тексты, цены, FAQ)
- **Slug** страницы (для images/[slug]/, id секций, canonical URL)

Промпт агенту ОБЯЗАТЕЛЬНО содержит:
```
СТРОГИЕ ПРАВИЛА:
1. Использовать ТОЛЬКО классы из blueprint. НЕ изобретать новые.
2. Чередование: .section → .section.section-alt → .section → ...
3. SVG иконки: ВСЕГДА width="24" height="24" fill="none" stroke="currentColor" stroke-width="2"
4. Изображения: src="images/{{SLUG}}/hero.jpg" и т.д.
5. Шрифты: @font-face Cormorant + Montserrat из fonts/*.woff2
6. CSS переменные: --color-accent: #3b6589; --color-dark: #232528; --color-bg: #2e3338
7. Боковое меню: 13 ссылок (из blueprint), текущая = class="active"
8. TOC: горизонтальный скролл, ссылки на sec-* якоря
9. Footer: логотип base64 SVG, адрес СПб, тел +7 (812) 241-78-78
10. Modal form: Bootstrap 5 modal с 3 полями (имя, тел, email)
11. Первая секция (без id) = stats (4 числа)
12. section-form перед footer = форма обратной связи
13. Telegram кнопки в price-table: href="https://t.me/dvaA_bussines_law"
```

### Фаза 3: Валидация (ОБЯЗАТЕЛЬНО!)
Запустить DOM-валидацию через `/validate-pages` или вручную:

```python
from bs4 import BeautifulSoup
# Проверить:
# 1. aside.sidebar существует с nav > ul.sidebar-nav
# 2. header.header существует
# 3. nav.toc с ul.toc-list
# 4. section.hero с .hero-bg и .hero-content
# 5. Минимум 8 section.section (чередование alt)
# 6. section.section-form с формой
# 7. footer.footer с 3 колонками
# 8. .modal#modalForm
# 9. .advantage-icon svg имеет width="24" height="24"
# 10. Нет внешних URL (CDN, fonts, scripts)
```

### Фаза 3.5: Проверка image paths
После генерации JSON — ОБЯЗАТЕЛЬНО проверить:
```bash
python3 fix_image_paths.py --dry-run  # preview
python3 fix_image_paths.py             # fix
```
**Причина:** hero.image внутри nested dict перезаписывает top-level hero_image при flatten.
Скрипт проверяет что все пути ведут на `images/{filename-slug}/`, а НЕ на `images/{full-slug}/`.

### Фаза 3.6: Проверка хабов
```bash
# 4 хаба ОБЯЗАНЫ существовать:
for hub in proverki donachisleniya riski spory; do
  ls pages/$hub.json || echo "MISSING: $hub"
done
```
Удаление хаба = потеря SEO topical authority кластера.

### Фаза 4: Изображения
- Создать папку `images/[slug]/`
- Изображения: hero.jpg, fig1.jpg, fig2.jpg, fig3.jpg, form.jpg
- Тематика: МОРСКАЯ (океан, волны, корабли, маяки)
- НЕ повторять изображения с других страниц
- Скачать через `bash download_images.sh` или ручной curl с Unsplash napi
- **ВАЖНО:** image dir = filename slug (blokirovka-scheta), НЕ full slug (nashi-uslugi/riski/blokirovka-scheta)

## Дизайн-токены (из wave1)

```css
:root {
  --font-main: "Montserrat", sans-serif;
  --font-title: "Cormorant", serif;
  --color-dark: #232528;
  --color-accent: #3b6589;
  --color-bg: #2e3338;
}
```

- Заголовки H2: font-family: var(--font-title), font-size: 2.4rem, color: var(--color-dark)
- H3: font-family: var(--font-title), font-size: 1.6rem
- Body: font-family: var(--font-main), font-size: 17px, line-height: 1.7
- Акцент: #3b6589 (ссылки, кнопки, иконки stroke)
- Тёмный фон: #2e3338 (sidebar, hero-bg, footer, service-card-header, case-card-header)
- Кнопка .btn-main: background #3b6589, color white, border-radius 30px

## Известные баги (из patches/)

1. **SVG иконки без размеров** → advantage-icon растягивается до 730px. ВСЕГДА: width="24" height="24"
2. **margin-top: -90px** → секции налезают друг на друга. НЕ использовать отрицательные margin
3. **Цвет #45739b vs #3b6589** → использовать ТОЛЬКО #3b6589 (из CSS variables)
4. **grep vs DOM** → валидация ТОЛЬКО через BeautifulSoup, НЕ grep
5. **Дублирование картинок** → каждая страница = своя папка images/[slug]/

### Фаза 5: Деплой
Использовать единый pipeline:
```bash
bash ant-deploy.sh              # полный деплой
bash ant-deploy.sh --dry-run    # предпросмотр
```

### Фаза 6: Визуальная проверка
```bash
python3 ant-visual-check.py --pages {slug}
# или через Playwright MCP: 3 breakpoints (375/768/1440)
```

## Файлы для справки
- Blueprint: `~/.claude/skills/ant-pages/references/blueprint.html`
- Section patterns: `~/.claude/skills/ant-pages/references/section-patterns.md`
- Эталон: `/Users/antonk/artvision-data/clients/ant-partners/templates/kameralnaya-proverka.html`
- Wave1 (принятые): `/Users/antonk/artvision-data/clients/ant-partners/templates/output_v7/for_client/wave1/`
- Patches: `/Users/antonk/artvision-data/clients/ant-partners/patches/`

## Скрипты (templates/)
| Скрипт | Назначение |
|--------|-----------|
| `generate_page.py` | Jinja2 генерация из JSON |
| `validate_pages.py` | 24 проверки JSON + HTML |
| `fix_image_paths.py` | Фикс путей hero/figure/form |
| `ant-preflight.sh` | Pre-deploy чеклист (6 проверок) |
| `ant-deploy.sh` | Единый деплой pipeline |
| `ant-visual-check.py` | Визуальная регрессия |
| `download_images.sh` | Скачивание картинок с Unsplash |
