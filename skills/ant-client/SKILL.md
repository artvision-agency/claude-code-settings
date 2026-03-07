---
name: ant-client
description: "Полный цикл работы с клиентом ANT Partners: генерация страниц по blueprint, деплой на тестовый сервер, визуальная проверка. Триггеры: 'создание страницы ANT', 'blueprint', 'wave3+', 'исправление страницы', 'ant deploy', 'залей ant', 'деплой ant', 'загрузи ant страницы', 'ant visual', 'скриншоты ant', 'визуальная проверка ant', 'ant screenshots'"
disable-model-invocation: true
---

# ANT Partners — полный цикл

## Маршрутизация по задаче

| Задача | Секция |
|--------|--------|
| Создать/исправить страницу | [S1 Генерация страниц](#s1-генерация-страниц) |
| Задеплоить на сервер | [S2 Деплой](#s2-деплой) |
| Визуальная проверка | [S3 Визуальная проверка](#s3-визуальная-проверка) |

---

# S1. Генерация страниц

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

### Фаза 2: Генерация (Task -> frontend-developer)
Передать агенту:
- **Blueprint** целиком (references/blueprint.html)
- **Section patterns** для нужных типов секций
- **Контент** страницы (тексты, цены, FAQ)
- **Slug** страницы (для images/[slug]/, id секций, canonical URL)

Промпт агенту ОБЯЗАТЕЛЬНО содержит:
```
СТРОГИЕ ПРАВИЛА:
1. Использовать ТОЛЬКО классы из blueprint. НЕ изобретать новые.
2. Чередование: .section -> .section.section-alt -> .section -> ...
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
- Темный фон: #2e3338 (sidebar, hero-bg, footer, service-card-header, case-card-header)
- Кнопка .btn-main: background #3b6589, color white, border-radius 30px

## Известные баги (из patches/)

1. **SVG иконки без размеров** -> advantage-icon растягивается до 730px. ВСЕГДА: width="24" height="24"
2. **margin-top: -90px** -> секции налезают друг на друга. НЕ использовать отрицательные margin
3. **Цвет #45739b vs #3b6589** -> использовать ТОЛЬКО #3b6589 (из CSS variables)
4. **grep vs DOM** -> валидация ТОЛЬКО через BeautifulSoup, НЕ grep
5. **Дублирование картинок** -> каждая страница = своя папка images/[slug]/

## Файлы для справки
- Blueprint: `~/.claude/skills/ant-client/references/blueprint.html`
- Section patterns: `~/.claude/skills/ant-client/references/section-patterns.md`
- Эталон: `/Users/antonk/artvision-data/clients/ant-partners/templates/kameralnaya-proverka.html`
- Wave1 (принятые): `/Users/antonk/artvision-data/clients/ant-partners/templates/output_v7/for_client/wave1/`
- Patches: `/Users/antonk/artvision-data/clients/ant-partners/patches/`

---

# S2. Деплой

Единый pipeline деплоя страниц ANT Partners на `ant-dev.artvision.pro`.

## ОБЯЗАТЕЛЬНО ПЕРЕД ДЕПЛОЕМ

1. Прочитать `clients/ant-partners/CLAUDE.md`
2. Прочитать все `clients/ant-partners/patches/*.md`

## Pipeline

```bash
cd /Users/antonk/artvision-data/clients/ant-partners/templates/

# 1. Preflight (JSON valid, images exist, hubs intact, sections stable)
bash ant-preflight.sh

# 2. Generate + validate
python3 generate_page.py --template master-template.html --content pages/ --output output_v7/for_client/
python3 validate_pages.py

# 3. Deploy (preflight + generate + upload + verify)
bash ant-deploy.sh              # полный деплой
bash ant-deploy.sh --skip-images  # без картинок
bash ant-deploy.sh --pages-only   # только HTML
bash ant-deploy.sh --dry-run      # предпросмотр
```

## Или одной командой:

```bash
bash ant-deploy.sh
```

Скрипт автоматически выполняет:
1. **Preflight** — 6 проверок (JSON, images, hubs, HTML, sections, validate)
2. **Generate** — 29 страниц через Jinja2
3. **Upload images** — scp 29 директорий -> `/files/images/`
4. **Upload HTML** — scp 29 HTML + 4 hub index.html
5. **Verify** — HTTP 200 для 5 sample pages

## Серверы

| Сервер | Назначение | IP |
|--------|-----------|-----|
| ant-dev.artvision.pro | ТЕСТ | 80.90.181.152 |
| ant.partners | БОЕВОЙ (ЗАПРЕЩЕНО) | 77.222.56.111 |

**ЗАПРЕЩЕНО** загружать тестовые файлы на 77.222.56.111.

## После деплоя

Запустить визуальную проверку (см. S3).

---

# S3. Визуальная проверка

Визуальная регрессия: скриншоты страниц на 3 breakpoints (375/768/1440), сравнение с baseline.

## Быстрая проверка (Playwright MCP)

Если Playwright MCP доступен, используй его напрямую:

```
1. browser_resize(1440, 900) -> browser_navigate(URL) -> browser_take_screenshot(fullPage, jpeg)
2. browser_resize(768, 1024) -> browser_take_screenshot
3. browser_resize(375, 812) -> browser_take_screenshot
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

---

# Скрипты (templates/)

| Скрипт | Назначение |
|--------|-----------|
| `generate_page.py` | Jinja2 генерация из JSON |
| `validate_pages.py` | 24 проверки JSON + HTML |
| `fix_image_paths.py` | Фикс путей hero/figure/form |
| `ant-preflight.sh` | Pre-deploy чеклист (6 проверок) |
| `ant-deploy.sh` | Единый деплой pipeline |
| `ant-visual-check.py` | Визуальная регрессия |
| `download_images.sh` | Скачивание картинок с Unsplash |
