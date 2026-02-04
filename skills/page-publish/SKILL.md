---
name: page-publish
description: "Публикация контента на CMS клиентов: WordPress REST API, MODX/Bitrix/Tilda через Playwright MCP. Маршрутизация по CMS, автозаполнение форм, проверка публикации. Триггеры: 'опубликуй на сайт', 'размести на сайте', 'залей контент', 'publish page', 'загрузи на CMS'."
---

# Page Publish — Универсальный публикатор контента

## Назначение
Размещение готового HTML/контента на CMS клиентов: WordPress, MODX, Битрикс, Tilda, кастомные админки.

## Маршрутизация по CMS

```
Входные данные: контент + клиент
         │
         ├── WordPress (artvision.pro)
         │    └── REST API (wp-json/wp/v2) — быстро, без браузера
         │
         ├── MODX (ant.partners)
         │    └── Playwright MCP → admin panel
         │    └── Скриншоты форм: references/modx-*.png
         │
         ├── Битрикс (geely-a2auto.ru)
         │    └── SSH + файловая система ИЛИ Playwright MCP
         │
         ├── Tilda (tvorimsovershenstvo.ru)
         │    └── Playwright MCP → визуальный редактор
         │    └── ⚠️ API недоступен (Personal план)
         │
         └── Кастомная CMS
              └── Playwright MCP → автоопределение формы
```

---

## 1. WordPress — REST API

### Когда использовать
- Публикация статей/страниц на artvision.pro
- Дайджесты, SEO-статьи, блог-посты

### Доступы
- **URL:** `https://artvision.pro/wp-json/wp/v2`
- **Логин/пароль:** из `tokens.json` → `artvision_pro.wordpress`
- **MCP:** `claudeus-wp-mcp` (установлен, конфиг в `~/.claude/wp-sites.json`)

### Создание черновика (REST API)
```python
import requests, os

def publish_to_wordpress(title, content, excerpt="", status="draft", categories=[], tags=[]):
    """Публикует контент в WordPress через REST API."""
    wp_url = "https://artvision.pro/wp-json/wp/v2/posts"
    wp_user = "admin"
    wp_pass = os.environ.get("WP_APP_PASSWORD")  # Или из tokens.json

    data = {
        "title": title,
        "content": content,
        "excerpt": excerpt,
        "status": status,  # draft | publish | pending
        "categories": categories,
        "tags": tags
    }

    response = requests.post(wp_url, json=data, auth=(wp_user, wp_pass))
    result = response.json()

    post_id = result.get("id")
    edit_url = f"https://artvision.pro/wp-admin/post.php?post={post_id}&action=edit"
    view_url = result.get("link")

    return {"id": post_id, "edit_url": edit_url, "view_url": view_url}
```

### Через MCP (альтернатива)
WordPress MCP позволяет управлять постами напрямую из Claude Code без Python-скриптов. Используется пакет `claudeus-wp-mcp`.

### Чек-лист WordPress
- [ ] Title заполнен (≤60 символов для SEO)
- [ ] Content — полный HTML
- [ ] Excerpt — 1-2 предложения (meta description)
- [ ] Категория выбрана
- [ ] Статус: draft (по умолчанию) — НЕ publish без подтверждения!
- [ ] После создания: открыть edit_url и проверить визуально

---

## 2. MODX — Playwright MCP

### Когда использовать
- Публикация страниц на ant.partners
- Создание/редактирование ресурсов

### Доступы
- **Менеджер:** `https://ant.partners/manager/`
- **Логин/пароль:** из `tokens.json` → `ant_partners.manager`

### Справочные скриншоты
В `references/` лежат 4 скриншота MODX админки:

| Файл | Что показывает |
|------|---------------|
| `modx-dashboard.png` | Главная: список шаблонов, дерево ресурсов |
| `modx-form-title-fields.png` | **Ключевой!** Поля формы: Заголовок*, Расширенный заголовок, Описание, Аннотация, Фокусные фразы, Шаблон (dropdown), Псевдоним, Пункт меню, чекбоксы (Скрыть из меню, Опубликован) |
| `modx-form-fields.png` | Редактор контента: HTML-код, SEO-превью, кнопки действий |
| `modx-tv-fields.png` | TV-переменные: Оглавление, Превью, Главный экран, Контент, Контент 2, Кейсы |

### Процесс публикации через Playwright

```
ШАГ 1: АВТОРИЗАЦИЯ
  browser_navigate → https://ant.partners/manager/
  browser_fill_form → login + password
  browser_click → "Войти"
  browser_wait_for → dashboard loaded

ШАГ 2: СОЗДАНИЕ РЕСУРСА
  browser_click → "Новый ресурс" (в дереве)
  browser_snapshot → получить актуальную разметку формы

ШАГ 3: ЗАПОЛНЕНИЕ ОСНОВНЫХ ПОЛЕЙ
  (Ориентироваться на modx-form-title-fields.png)
  - Заголовок* → H1 страницы
  - Расширенный заголовок → SEO title (≤60 символов)
  - Описание → meta description (≤160 символов)
  - Аннотация → краткое описание для каталога
  - Псевдоним → URL slug (латиница, через дефис)
  - Шаблон → выбрать нужный из dropdown
  - Пункт меню → название в навигации
  - Опубликован → ✅ (если согласовано)

ШАГ 4: ЗАПОЛНЕНИЕ TV-ПОЛЕЙ
  (Ориентироваться на modx-tv-fields.png)
  - Перейти на вкладку "Дополнительные поля"
  - Контент → основной HTML контент
  - Контент 2 → дополнительный контент (если есть)
  - Превью → текст/картинка для карточки
  - Оглавление → содержание (если страница длинная)

ШАГ 5: СОХРАНЕНИЕ
  browser_click → "Сохранить"
  browser_wait_for → подтверждение сохранения
  browser_snapshot → проверить что ресурс создан
```

### Чек-лист MODX
- [ ] Шаблон выбран правильный
- [ ] Заголовок = H1 страницы
- [ ] Псевдоним — транслит, нет кириллицы
- [ ] Описание (meta description) ≤ 160 символов
- [ ] Контент — полный HTML (не обрезан)
- [ ] Ресурс в правильном разделе дерева
- [ ] Опубликован/скрыт — как согласовано с клиентом

---

## 3. Битрикс — SSH + Файлы

### Когда использовать
- Публикация на geely-a2auto.ru
- Статьи, сервисные страницы

### Доступы
- **SSH:** из `tokens.json` → `geely_a2auto.ssh`
- **Корень:** `/home/z/zazan5bw/geely-a2auto.ru/public_html`
- **Шаблон:** `/bitrix/templates/a2avto`
- **Include:** `/include`

### Процесс через SSH

```bash
# 1. Подключиться
ssh -i ~/.ssh/beget_key zazan5bw@zazan5bw.beget.tech

# 2. Создать файл страницы
# Битрикс использует PHP-файлы с включением шаблона
cat > /path/to/section/page-name/index.php << 'EOF'
<?php
require($_SERVER["DOCUMENT_ROOT"]."/bitrix/header.php");
$APPLICATION->SetTitle("Заголовок страницы");
?>

<!-- Контент страницы -->
<div class="article-content">
  ...HTML контент...
</div>

<?php require($_SERVER["DOCUMENT_ROOT"]."/bitrix/footer.php"); ?>
EOF

# 3. Установить права
chmod 644 /path/to/page/index.php

# 4. Очистить кеш Битрикс (если нужно)
# Обычно через админку: Настройки → Автокеширование → Очистить
```

### Альтернатива: Playwright MCP
Если нужно создать через админку (инфоблоки, статьи из каталога):
1. Авторизоваться в `/bitrix/admin/`
2. Перейти в нужный инфоблок
3. Заполнить форму через browser_fill_form
4. Сохранить

### Чек-лист Битрикс
- [ ] Файл index.php с правильным заголовком
- [ ] require header.php + footer.php
- [ ] SetTitle() совпадает с H1
- [ ] Права 644
- [ ] Если инфоблок — проверить что статья появилась в каталоге
- [ ] Проверить что страница в sitemap (частая проблема Битрикс!)

---

## 4. Tilda — Playwright MCP

### Когда использовать
- Редактирование tvorimsovershenstvo.ru
- Добавление блоков, обновление контента

### Доступы
- **URL:** `https://tilda.cc/login/`
- **Логин/пароль:** из `tokens.json` → `tilda.tvorim_sovershenstvo`
- **API:** ❌ Недоступен (Personal план)

### Особенности Tilda
- **Визуальный редактор** — нет HTML-формы для вставки кода
- **Блочная структура** — контент добавляется блоками (Zero Block, Text, Image...)
- **Zero Block** — единственный способ вставить кастомный HTML/CSS
- **Публикация** — кнопка "Опубликовать все страницы"

### Процесс через Playwright

```
ШАГ 1: АВТОРИЗАЦИЯ
  browser_navigate → https://tilda.cc/login/
  browser_fill_form → email + password
  browser_click → "Войти"
  browser_wait_for → dashboard

ШАГ 2: ВЫБОР СТРАНИЦЫ
  browser_navigate → https://tilda.cc/page/?pageid=[ID]
  ИЛИ найти страницу в списке проекта

ШАГ 3: РЕДАКТИРОВАНИЕ
  Для текстовых блоков:
  - browser_click → блок с текстом
  - browser_type → новый текст

  Для Zero Block (кастомный HTML):
  - browser_click → Zero Block
  - Найти HTML-редактор
  - Вставить код

ШАГ 4: ПУБЛИКАЦИЯ
  browser_click → "Опубликовать"
  browser_wait_for → подтверждение
```

### Чек-лист Tilda
- [ ] Правильная страница выбрана
- [ ] Текст обновлён без потери форматирования
- [ ] Мобильная версия проверена (Tilda адаптивная)
- [ ] Нажата "Опубликовать" (иначе изменения не видны!)

---

## 5. Кастомная CMS — Универсальный подход

### Когда использовать
- Любая незнакомая CMS или админка
- Новый клиент с неизвестной платформой

### Процесс

```
ШАГ 1: РАЗВЕДКА
  browser_navigate → URL админки
  browser_snapshot → получить структуру страницы
  browser_take_screenshot → визуальный снимок для анализа

ШАГ 2: АВТОРИЗАЦИЯ
  - Найти форму логина (обычно input[type=password])
  - browser_fill_form → логин + пароль
  - browser_click → кнопка входа

ШАГ 3: НАВИГАЦИЯ
  browser_snapshot → изучить меню/навигацию
  - Найти раздел "Контент" / "Страницы" / "Статьи"
  - Перейти к созданию нового материала

ШАГ 4: ЗАПОЛНЕНИЕ
  browser_snapshot → получить все поля формы
  - Сопоставить поля с контентом:
    - Заголовок → H1
    - Описание → meta description
    - Контент → HTML тело
    - URL → slug
  - browser_fill_form → заполнить все поля

ШАГ 5: СОХРАНЕНИЕ И ПРОВЕРКА
  browser_click → "Сохранить" / "Опубликовать"
  browser_navigate → URL страницы на сайте
  browser_take_screenshot → проверить результат
```

---

## Общие правила безопасности

### ЗАПРЕЩЕНО без подтверждения:
- ❌ Публиковать в статусе "Опубликовано" (только "Черновик")
- ❌ Удалять существующие страницы/ресурсы
- ❌ Менять шаблоны/темы сайта
- ❌ Изменять настройки CMS

### ОБЯЗАТЕЛЬНО:
- Показать пользователю ЧТО будет опубликовано
- Дождаться подтверждения "да" / "публикуй"
- После публикации — показать ссылку на страницу
- Если черновик — показать ссылку на редактирование

### Формат запроса подтверждения:
```
ПУБЛИКАЦИЯ КОНТЕНТА

Сайт: [URL]
CMS: [WordPress/MODX/Битрикс/Tilda]
Действие: Создать [черновик/страницу]
Заголовок: [H1]
URL: [slug]

Подтвердить? (напиши "да")
```

---

## Определение CMS по клиенту

| Клиент | Сайт | CMS | Метод публикации |
|--------|------|-----|-----------------|
| Artvision | artvision.pro | WordPress | REST API |
| ANT Partners | ant.partners | MODX | Playwright MCP |
| Geely A2Auto | geely-a2auto.ru | Битрикс | SSH + файлы |
| Творим Совершенство | tvorimsovershenstvo.ru | Tilda | Playwright MCP |

Алиасы клиентов — см. `artvision-data/CLAUDE.md` → "КЛИЕНТЫ + АЛИАСЫ"

---

## Триггеры
- "опубликуй на сайт"
- "размести на сайте"
- "залей контент"
- "publish page"
- "загрузи на CMS"
- "создай черновик"
- "выложи статью"
