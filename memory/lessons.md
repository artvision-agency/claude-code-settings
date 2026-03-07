# Уроки и паттерны (из опыта)

## Рабочий процесс

### /sync — не спрашивать, сразу пушить (2026-02-06)
При команде "синк" или "пуш" — выполнять сразу без подтверждения.

### Скиллы/агенты/hooks — ВСЁ дублировать в git (2026-02-06)
При установке ЧЕГО УГОДНО в `~/.claude/` — ВСЕГДА копировать в `artvision-data/.claude/` и пушить.

### Короткие сообщения = инструкции, НЕ вопросы (2026-02-06)
"learning" = создай материалы, "asana monday" = задачи на понедельник, "sync" = пуш в git, "to continue" = продолжай.

### НИКОГДА не игнорировать просьбы пользователя (2026-02-13)
"рой"/"swarm"/"параллельно" — ДЕЛАТЬ. Можно предупредить о стоимости, но ВЫПОЛНИТЬ.

### Patch-система + Pre-Task Protocol (2026-02-12)
Источник: AI Factory. 4 уровня (fix/task/page/feature). Patches в `clients/[name]/patches/`.

## Данные и верификация

### ВЕРИФИКАЦИЯ ДАННЫХ — ОБЯЗАТЕЛЬНА (2026-02-06)
Собрал данные → запустил ревизоров → только потом в документ. Ошибка: SmartMed данные были неверны.

### Яндекс = ВСЕГДА через API токены (2026-02-13)
wordstat, direct, webmaster, metrika — всё в tokens.json. WebFetch на yandex.ru SERP = пустой ответ.

### SEO Pipeline = ПЕРВЫЙ инструмент (2026-02-13)
88 скриптов в `products/seo-pipeline/`. Семантика→wordstat, кластеризация→clusterer, ТЗ→tz_generator...

### Генерация текстов = Claude Code (2026-02-13)
Max подписка уже оплачена. НЕ использовать text_generator_v2.py (доп. расход API).

## Frontend / HTML

### Валидация HTML = DOM-парсинг, НЕ grep (2026-02-10)
grep считает строковые совпадения включая CSS. Скрипт: `scripts/validate_wave1_dom.py` (BeautifulSoup).

### Попапы/модалки — скилл popup-cro (2026-02-23)
CSS `:target` для попапов = хрупкий паттерн (конфликт с smooth scroll). Правильно: JS classList.toggle.

### КП/Презентации — извлекать дизайн-систему клиента (2026-02-09)
СНАЧАЛА парсить сайт на цвета/шрифты. Ошибка: КП DemosMed в cyan/purple вместо бренда.

### CSS nth-child перебивает классовые стили (2026-02-23)
`section:nth-child(even){background:...}` перебивает `.cta-section{background:...}` из-за shorthand `background` сбрасывающего `background-image` (градиент). Фикс: `!important` или более специфичный селектор.

### Скачивание HTML файлов — nginx Content-Disposition (2026-02-23)
Атрибут `download` в `<a>` не всегда работает (cross-origin, некоторые браузеры). Надёжный способ: nginx location с `if ($arg_dl = "1") { add_header Content-Disposition "attachment"; }`. URL: `file.html?dl=1`.

## Инфраструктура

### Telegram Instant View (2026-02-07)
Шаблон готов, НЕ активировано (нужен rhash). TG канал = @artvisionagency.

### ~/.claude/agents/ НЕ влияют на Task tool (2026-02-07)
162 файла = просто markdown. Task tool использует встроенные типы Anthropic.

### MODX + MySQL utf8 = emoji обрезают строку (2026-02-18)
Фикс: убрать emoji ДО деплоя или ALTER TABLE → utf8mb4.

### Нестабильный интернет (2026-02-20)
`172.20.10.x` = iPhone hotspot. ipsec0 зависший → `sudo ifconfig ipsec0 down`.

### Деплой КП = на artvision.pro/kp/ (2026-02-19)
Сейчас nginx на VPS. .htaccess с noindex уже в /kp/.

### VPS миграция (2026-02-17)
Node.js НЕ подхватывает SOCKS5 → proxychains4. WARP бесполезен из РФ. NL VPS = та же цена что RU.

## Инструменты

### react-best-practices скилл (2026-02-06)
57 правил, 8 категорий. Автоактивация при React/Next.js.

### Handy — офлайн голосовой набор (2026-02-09)
Option+Space (push-to-talk). Модель: Whisper Large V3 Turbo.

### screen-shot.xyz API (2026-02-16)
Бесплатно, без ключа. ТОЛЬКО для публичных URL.

### Верификация FTP = curl, не браузер (2026-02-16)
После загрузки — curl (без кэша), не Playwright.

## Регистрация сервисов (2026-02-23)
Email: antoniokmr@gmail.com (international), dune87@yandex.ru (RU). Подробности: `service-registration.md`.

## Автоматизация Claude Code (2026-02-24, из статьи Habr)

### Hooks = главный рычаг качества
11 хуков, 6 событий. Ключевое: PostToolUse hooks **автоматически** срабатывают на каждый Edit/Write — Claude не может их пропустить. Это надёжнее чем правила в CLAUDE.md (можно забыть).

### post-client-html-validate.sh — НЕ ПРОПУСКАТЬ
При работе с HTML в `clients/*/` — хук автоматически проверяет:
- Бренд-цвета из config.yaml (оба формата: brand.* и styles.*)
- Контент: H2≥3, CTA, телефон из contacts
- Размер <500KB, @media queries ≥2
Если хук показал предупреждения — **исправить ДО коммита**.

### Pre-Task Protocol — ОБЯЗАТЕЛЕН перед работой с клиентом
Прежде чем трогать файлы клиента:
1. Прочитать `config.yaml` (бренд, контакты)
2. Прочитать `CLAUDE.md` клиента (особые правила)
3. Прочитать `patches/` (известные баги/особенности)
4. Для ANT Partners: ТОЛЬКО через `generate_page.py`, НЕ прямой HTML

### Playwright проверка = ОБЯЗАТЕЛЬНА после HTML
375x812 / 768x1024 / 1440x900. Горизонтальный скролл = баг. CTA видны без скролла.

### Exit codes хуков
- exit 0 = тихо (всё ок)
- exit 1 = показать вывод Claude (предупреждение, Claude видит и должен исправить)
- exit 2 = заблокировать операцию (не выполнять tool)

### macOS grep -c баг
`grep -c` без совпадений возвращает пустую строку + exit 1 (не "0"). Фикс: `if [ -z "$VAR" ]; then VAR=0; fi`

## Нерешённые пробелы для новых людей
- MCP серверы — конфиги в `~/.claude/settings.json`, не в репо
- Python-зависимости — нет `requirements.txt`
- Системные утилиты (sips, pup, ggrep)
