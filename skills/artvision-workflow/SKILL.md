---
name: artvision-workflow
description: "Комплексный скилл для SEO-агентства: коммиты, код-ревью, контент, синхронизация, генерация страниц, работа с клиентами. Триггеры: 'commit', 'коммит', 'code review', 'ревью', 'статья', 'контент', 'sync', 'синхронизация', 'шаблон страницы', 'создай HTML', 'ТЗ', 'RUSH'."
---

# Artvision Workflow Skill

> Комплексный скилл для SEO-агентства: коммиты, код-ревью, контент, синхронизация.

## Triggers

- "commit", "коммит" → §1
- "code review", "ревью" → §2
- "статья", "контент" → §3
- "sync", "синхронизация" → §4
- "ТЗ", "RUSH" → §5
- "chronicle", "дневник" → §6
- Geely, ANT Partners, Extru Tech → §7
- "ревизия скилла" → §8
- После нетривиальной задачи → §9

---

## 1. Commits

**Формат:**
```
<type>: <description>

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Типы:** feat, fix, docs, refactor, style, chore, sync

**Workflow:** `git status` → `git diff --staged` → сообщение → коммит только по запросу

**НЕ коммитить:** `.env`, `tokens.json`, `.claude_temp_scripts/`

---

## 2. Code Review (Python)

**Чеклист:**
- CLI с argparse, конфиг через env, нет хардкода
- Type hints, docstrings, try/except
- Нет секретов, валидация входа
- Совместимость с 88 скриптами SEO Pipeline

**Отчёт:** Критические → Рекомендации → Хорошо

---

## 3. SEO Content

**Правила:**
- H1 один с главным ключом, H2 по ТЗ, FAQ ≥3
- Уникальность ≥85%, тематичность ≥25%, вода <40%
- Главный ключ в первом абзаце, LSI равномерно

**Скрипты:** `text_generator.py --tz`, `content_checker.py --text --query`

---

## 4. Sync Protocol

**Начало:** `git pull` → `cat sync/SYNC_STATUS.md`

**Конец:** обновить SYNC_STATUS.md (дата, источник, сделано, файлы) → `git add sync/ && git commit && git push`

---

## 5. TZ Generator (RUSH)

**RUSH = Research Using SERP Heuristics**

| Источник | Маркер | Назначение |
|----------|--------|------------|
| Яндекс | 🟡 | Основа (интент, структура) |
| Google | 🔵 | Дополнение (уникальное) |
| Wordstat | 🟢 | Частотность |

**Интент КОМ:** URL `uslugi/catalog/price`, title "купить/заказать/₽"
**Интент ИНФО:** URL `blog/wiki/kak-`, title "что такое/обзор/сравнение"

**Фильтр мусора:** форумное (знаток, регистрация), даты, чужие бренды, UI

**Скрипт:** `tz_generator_v2.py --query "..." [--with-google] [--with-wordstat]`

---

## 6. Chronicle AI

**Workflow:** `/chronicle` → голосовое → Groq Whisper → Claude → пост

**Вопросы:** Что сделал? Что узнал? Что сложно? Приоритет завтра? Энергия 1-10?

**Формат:** `📅 Дневник: [дата]\n[текст]\n#chronicle #artvision`

---

## 7. Клиенты

| Клиент | Ниша | Специфика |
|--------|------|-----------|
| **Geely A2Auto** | Авто, СПб | Тон технический, регламенты ТО, избегать "автогермес" |
| **ANT Partners** | Юр. услуги | Hero→Проблемы→Решение→Кейсы→FAQ→CTA, только /service/ |
| **Extru Tech** | Оборудование | Без регионалок, видео в карточки |
| **artvision.pro** | SEO | Geo-страницы v1.0.3, Schema.org разметка |

**Детали:** см. `sync/SYNC_STATUS.md`, `sync/geely.md`

---

## 8. Ревизия скилла

**Когда:** "ревизия скилла", раз в неделю, после серии задач

**Workflow:**
1. Прочитать SKILL.md
2. Проанализировать sync/ — что повторялось, что затягивалось
3. Предложить: добавить / изменить / удалить
4. После одобрения: бэкап → изменения → тест

---

## 9. Задача → Скилл/Скрипт

**После задачи (>30 мин, несколько шагов, может повториться):**
```
Сделать из этого: Скрипт / Скилл / Ничего?
```

| Выбор | Когда |
|-------|-------|
| Скрипт | Данные, API, парсинг, генерация |
| Скилл | Workflow, чеклисты, правила |
| Оба | Скрипт делает, скилл говорит когда |

---

## 10. Платные API — СТОП

**Перед вызовом Topvisor/Wordstat/Anthropic:**
```
⚠️ ПЛАТНАЯ ОПЕРАЦИЯ
Действие: [что]
Стоимость: [рубли]
Подтвердить? (напиши "да")
```

**Без явного "да" — НЕ выполнять.**

---

## 11. Universal Page Generator (ВСЕ КЛИЕНТЫ)

**Триггеры:** "шаблон", "страница услуги", "сделай страницу", "page template", "создай HTML"

**Автоматический вызов:** Любая задача с клиентом + "шаблон/страница/html/услуга"

### ЦЕПОЧКА АГЕНТОВ:

```
┌─────────────────────────────────────────────────────────────────┐
│  1. ПАРСИНГ + ПОДСЧЁТ                                           │
│  ────────────────────                                           │
│  • WebFetch URL → ПОСЧИТАТЬ: H2=?, FAQ=?, услуг=?               │
│  • Загрузить конфиг клиента (config.yaml)                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  2. АГЕНТ: frontend-developer                                   │
│  ────────────────────────────                                   │
│  Task(subagent_type="frontend-developer", prompt=...)           │
│  • Контент из парсинга                                          │
│  • Стили из config.yaml клиента                                 │
│  • "СТРОГО X H2, Y FAQ — НЕ БОЛЬШЕ!"                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  3. АГЕНТ: code-reviewer                                        │
│  ────────────────────────                                       │
│  Task(subagent_type="code-reviewer", prompt=...)                │
│  • Сверка блоков с оригиналом                                   │
│  • Проверка CSS (нет overflow: hidden)                          │
│  • REJECTED → вернуться к frontend-developer                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  4. АГЕНТ: image-optimizer                                      │
│  ──────────────────────────                                     │
│  Task(subagent_type="image-optimizer", prompt=...)              │
│  • Тема из config.yaml клиента                                  │
│  • 4 уникальных фото на страницу                                │
│  • WebP + JPG, компрессия                                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  5. АГЕНТ: ui-comprehensive-tester                              │
│  ─────────────────────────────────                              │
│  Task(subagent_type="ui-comprehensive-tester", prompt=...)      │
│  • Playwright: скролл, элементы, ссылки                         │
│  • Мобильная версия                                             │
│  • FAILED → вернуться к frontend-developer                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  6. АГЕНТ: task-completion-validator                            │
│  ───────────────────────────────────                            │
│  Task(subagent_type="task-completion-validator", prompt=...)    │
│  • Финальная сверка всех блоков                                 │
│  • APPROVED → показать пользователю                             │
│  • REJECTED → указать что исправить                             │
└─────────────────────────────────────────────────────────────────┘
```

### Конфиги клиентов:

| Клиент | Конфиг | Тема фото | Шрифты |
|--------|--------|-----------|--------|
| ANT Partners | `clients/ant-partners/config.yaml` | marine | Montserrat, Cormorant |
| Geely A2Auto | `clients/geely/config.yaml` | automotive | — |
| Extru Tech | `clients/extru/config.yaml` | industrial | — |
| artvision.pro | `clients/artvision/config.yaml` | digital | — |

### Формат config.yaml:

```yaml
client: ant-partners
name: ANT Partners
theme: marine

styles:
  font_main: "Montserrat"
  font_title: "Cormorant"
  color_accent: "#45739b"
  color_dark: "#232528"

contacts:
  phone: "+7 (812) 241-78-78"
  email: "office@ant.partners"
  telegram: "@dvaA_bussines_law"
  address: "СПб, Саперный пер., д. 10"

templates:
  reference: "kameralnaya-proverka.html"
  output_dir: "output_v6/"

rules:
  consultation_first: true
  telegram_hover: true
```

### ЗАПРЕТЫ (code-reviewer + validator проверяют!):

| ❌ Нельзя | ✅ Правильно |
|-----------|-------------|
| Добавлять блоки от себя | Только то что на оригинале |
| overflow: hidden на html | scroll-behavior: smooth |
| Копировать фото между страницами | Новые 4 фото на каждую |
| Больше H2/FAQ чем на оригинале | ТОЧНОЕ соответствие |

---

---

## 12. Image Optimizer (ВСЕ ПРОЕКТЫ!)

**Триггеры:** "добавь фото", "нужны изображения", "картинки для страницы"

**Автоматический вызов:** При создании страниц с hero/секциями

### Требования:
- **Минимум 4 фото** на страницу услуги
- **WebP + JPG** fallback
- **Компрессия** без потери качества (TinyPNG или Pillow)
- **На сервере проекта** — не внешние ссылки!

### Темы по клиентам:
| Клиент | Тема | Ключевые слова |
|--------|------|----------------|
| ANT Partners | Морская | ocean, sea, nautical, maritime, waves |
| Geely A2Auto | Авто | car, vehicle, automotive, road |
| Extru Tech | Индустрия | machinery, equipment, factory |
| artvision.pro | Digital | technology, marketing, analytics |

### Скрипт:
```bash
# Морская тема (ANT Partners)
python3 ~/.artvision-data/.claude_temp_scripts/image_optimizer.py --theme marine --count 4 --output ./images/

# Компрессия существующих
python3 ~/.artvision-data/.claude_temp_scripts/image_optimizer.py --compress-dir ./images/
```

### HTML шаблон:
```html
<picture>
  <source srcset="images/photo.webp" type="image/webp">
  <img src="images/photo.jpg" alt="Описание" loading="lazy">
</picture>
```

### API ключи (опционально):
- `tinypng_api_key` — 500 бесплатных/месяц, лучшая компрессия
- `unsplash_access_key` — больше выбор фото

---

## Файлы

- `~/.claude/CLAUDE.md` — глобальные правила
- `artvision-data/sync/SYNC_STATUS.md` — статус и история
- `artvision-data/tokens.json` — ключи API
- `artvision-data/clients/ant-partners/templates/` — шаблоны ANT Partners
- `artvision-data/.claude_temp_scripts/image_optimizer.py` — оптимизатор изображений
