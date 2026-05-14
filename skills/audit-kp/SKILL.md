---
name: audit-kp
description: Полный SEO-аудит-КП клиента (12 шагов pipeline + 8 секций структуры). Триггер любая фраза «сделай аудит сайта <url>», «КП для <client>», «presale <slug>», «audit <domain>». Шаблон `~/artvision-data/templates/audit-kp-template.html` (276 KB) + правило `~/.claude/rules/audit-kp-pipeline.md`. Эталон — spb-kursy v3.
---

# /audit-kp — SEO-аудит-КП клиента

## Когда вызывать

Любая фраза:
- «сделай аудит сайта https://X»
- «КП для клиента Y»
- «presale Z»
- «audit Х» / «расширенный SEO для…»
- «стоматология ABC — аудит» / «парикмахер DEF — аудит» / etc.

## Что делает skill

Запускает **12-шаговый pipeline** по эталону spb-kursy v3:

1. Brand extraction с сайта клиента (палитра + шрифт) → `config.yaml`
2. parse_html главной (title/H1/Schema/alt/canonical/word_count) → JSON
3. PSI Lighthouse mobile (через `youtube.api_key`) → scores + LCP/CLS/TBT
4. Sitemap.xml + robots.txt + llms.txt
5. Direct API hasSearchVolume + ForecastNew — 10 ком + 10 инфо ключей (регион клиента)
6. Topvisor — добавить searcher через `add/positions_2/searchers` + snapshot позиций
7. SF crawl 3 прямых конкурентов + parse + PSI
8. SEMrush UI scrape — backlinks (Overview + Anchors + Geo + RefDomains)
9. Wordstat CSV (если ≤30 дней) — точные частоты, иначе прокси × 1.15 коэф
10. strict-factchecker (Agent code-reviewer) — все цифры vs источники
11. #market-presence — размер рынка / доля клиента / незанятое пространство
12. Content Volume Benchmark — word count target vs ТОП-10

## Структура КП (8 секций, вариант B)

```
hero → TOC →
#tldr (4 цветные плашки двойным языком: ✅ Где сильны / 🔴 Главные риски / 🎯 Точки роста / ⚔️ Главный конкурент)
#family (если родственные домены — таблица + robots/llms)
#score (4 фактора SEO: Коммерч / Текст / Ссылоч / Поведенч)
#visibility (10 ком + 10 инфо × позиции × CSS-bars чарт)
#potential (Wordstat × CTR × AI_loss + Конверсия 1% → заявки)
#backlinks (4 домена SEMrush — клиент + 3 конкурента + Top-5 анкоров конкурента)
#tech (топ-5 показателей)
#market-presence (размер рынка / доля / незанятое)
```

## Что подставить под нового клиента (от пользователя)

1. **Домен клиента** — `https://example.com`
2. **Регион** (lr=) — Москва=213, СПб=2, Казань=43, etc. (см. `~/.claude/rules/medical-kp.md` таблица)
3. **10 коммерческих ключей** под кластер клиента
4. **10 информационных ключей**
5. **3 прямых конкурента** (если известны — иначе автопоиск через WebSearch)
6. **Профиль клиента** — `enterprise` / `b2c-polished` / `lux-marketing` / `dashboard-relationship` / `mvp-prototype` (см. `~/.claude/rules/design-profile-routing.md`)

## Запуск

```bash
# В новой сессии:
/audit-kp https://stoma-clinic.ru
# или
/audit-kp клиент=ABC регион=Казань профиль=enterprise

# Skill читает:
# - templates/audit-kp-template.html (276 KB шаблон с {{placeholders}})
# - ~/.claude/rules/audit-kp-pipeline.md (12 шагов)
# - ~/.claude/rules/medical-kp.md (если медицина — расширенный набор)
# - ~/.claude/rules/design-profile-routing.md (выбор UI стиля)
```

## Эталон-референс

**spb-kursy v3** (11.05.2026):
- Локально: `~/artvision-data/presales/spb-kursy/kp/spb-kursy_kp_v3.html` (~255 KB)
- На проде: https://artvision.pro/kp/spb-kursy-v3/
- Артефакты данных: `~/artvision-data/clients/spb-kursy/seo/2026-05-11/`

Прошёл все 12 шагов pipeline. Используется как образец структуры/палитры/стиля.

## Время выполнения

- Минимальный pipeline (без агентов на конкурентов): 30-45 мин
- С параллельными агентами (3+ в фоне): 50-90 мин
- Финальный strict-factcheck: +10 мин

## Хуки которые автоматически защитят pipeline

- `pre-kp-brand-extract-check.sh` — блокирует Write КП без WebFetch домена
- `pre-bash-topvisor-guard.sh` — блокирует NOT_IN/MATCH/EXISTS (broadcast)
- `pre-kp-bred-block.sh` — блокирует UNCONFIRMED/AI/нейросети в тексте
- `pre-claim-no-rule-check.sh` — warning если «правило не зафиксировано» без проверки 4 источников
- `pre-scp-factcheck.sh` — блокирует scp если CRITICAL

## Что можно/нельзя в КП (уточнено 11.05.2026)

**МОЖНО:** Topvisor, SEMrush, Ahrefs, Keys.so (инструменты), AI/нейропоиск/Я.Нейро/AI Overview (как реальный SEO-фактор в выдаче).

**НЕЛЬЗЯ:** AI как «наш метод» / «нейросеть генерит» (хайп), WebFetch / curl / CONFIRMED / UNCONFIRMED (внутренние маркеры).

Брендирование (опционально, для премиальности): LinkForge / Flow / Scout / Radar / Lens.

## 🆕 Обязательные элементы каждого нового КП (добавлено 12.05.2026)

### 1. TG-popup чат-бабл (Voice widget)

**ВСЕГДА** добавлять перед `</body>` в любом КП:

```html
<!-- Artvision Voice — TG chat widget -->
<script src="https://artvision.pro/widgets/voice.js"
  data-bot="avportal"
  data-chat-id="161261562"
  data-name="Антон Камеристый"
  data-avatar="АК"
  data-palette-primary="<КЛИЕНТСКИЙ HEX 1>"
  data-palette-secondary="<КЛИЕНТСКИЙ HEX 2>"
  data-endpoint="https://artvision.pro/api/kp-message.php"
  data-tg-fallback="+79110861888"
  data-online-mode="hours"
  data-chips="Q1|Q2|Q3|Q4|Q5|Q6|Q7"></script>
```

`data-chips` — 7 готовых вопросов под нишу клиента (полный текст, не лейблы).

### 2. Mobile h-scroll fix (override-CSS обязателен)

```html
<style id="readability-override">
@media (max-width: 768px) {
    html, body { overflow-x: hidden !important; max-width: 100vw !important; }
    section table { display: block !important; overflow-x: auto !important; max-width: 100% !important; }
    h2.section-title { font-size: 24px !important; }
}
[class*="pc-"] { max-width: 100vw !important; }
</style>
```

+ обернуть **все `<table>`** в `<div class="t-scroll" style="overflow-x:auto;max-width:100vw;width:100%;">`.

### 3. TH/TD валидация таблиц (обязательная проверка перед deploy)

В каждой `<table>` count(`<th>`) **должен ровняться** count(`<td>`) в каждой `<tr>`. Если меньше — таблица «съедет». Скрипт валидации:

```python
from bs4 import BeautifulSoup
soup = BeautifulSoup(html, 'html.parser')
for t in soup.find_all('table'):
    ths = len(t.find_all('th'))
    for tr in t.find_all('tr'):
        tds = len(tr.find_all('td'))
        if tds and tds != ths:
            print(f'BAD: {tr}')
```

### 4. Brand extraction (хук блокирует Write без него)

ОБЯЗАТЕЛЬНО до создания КП:

```bash
curl -sL https://<CLIENT-DOMAIN> | grep -oE '#[0-9a-fA-F]{6}' | sort -u | head -10
curl -sL https://<CLIENT-DOMAIN> | grep -oE 'font-family:[^;]+' | sort -u | head
```

Записать 2 primary цвета + шрифт в `clients/<slug>/config.yaml` под `design.palette.primary/secondary`.

### 5. Семантика 100% при копировании шаблона

Если копируешь spb-kursy → cosmetology — **проверь grep**:
- В cosmetology НЕ должно быть «массаж»/«массажист» (кроме контекста "массаж лица" как продукт косметологии)
- В hair-courses НЕ должно быть «массаж»/«косметология» (кроме контекста сравнения родственных доменов)

```bash
grep -c "массаж" cos_kp.html  # должно быть < 10 (только спец-контекст)
```

### 6. «Главный конкурент» = доказательство по позициям, не интуиция

В #backlinks секции обязательная плашка:

```
Почему shkolamm.ru = главный конкурент:
  • ТОП-1 по «школа массажа спб» (= наш ТОП-1 ключ)
  • ТОП-2 по «курсы массажа спб» (= наш ТОП-1 ключ)
  • Прямая борьба за один трафик
```

Без обоснования по Topvisor snapshot — НЕ называть домен «главным конкурентом».

### 7. CSS-bars chart в #backlinks (визуализация RD)

После таблицы AS/RD/BL — обязательно CSS-bar chart с разрезом RD клиент vs 3 конкурента (главный конкурент = красный, клиент = зелёный/жёлтый, остальные = серые).

### 8. #market-presence с дисклеймером (НЕ TAM)

В заголовке: **«Доля в анализируемом кластере (20 ключей)»** — НЕ «Размер рынка». Дисклеймер обязателен:

> ⚠️ Это не TAM/SAM. Реальный рынок шире (сотни синонимов и long-tail). Эта секция — относительная база сравнения по нашей выборке 20 ключей.

### 9. Online indicator в чате (MSK 9-23 work hours по умолчанию)

Виджет `voice.js` сам определяет онлайн/офлайн по MSK time или через `/api/anton-status.json`. На клиентских КП — режим `data-online-mode="hours"` (бизнес-часы).

## 🔌 Backend API (для всех КП)

Endpoint: `https://artvision.pro/api/kp-message.php` (uses POST JSON)

**Запрос:**
```json
{
  "question": "текст вопроса",
  "kp_url": "https://artvision.pro/kp/<slug>/",
  "contact": "@username | +7999... | empty",  // optional
  "source": "<URL источника>"                   // optional
}
```

**Ответ:**
- `{"ok":true}` — отправлено в TG
- `{"ok":false,"err":"empty"}` — пустой вопрос
- `{"ok":false,"err":"rate_limit","retry_after":60}` — превышен лимит 5 req/60s
- `{"ok":false,"err":"daily_limit"}` — превышен 50 req/day per IP
- `{"ok":false,"err":"tg_failed"}` — Telegram API не ответил

**Защита:**
- 5 req / 60s per IP (rate-limit) — задеплоено 12.05 02:54
- 50 req / day per IP (daily cap)
- HTML-escape (XSS protection)
- @username → автоматически кликабельная ссылка `t.me/username`
- +телефон → автоматически кликабельная `tel:`
- Bot: @avportal_bot, chat_id 161261562 (Антон)

**Файл бэкенда:** `/var/www/artvision/api/kp-message.php` (на VPS 80.90.181.152)
**Бэкап:** `/var/www/artvision/api/kp-message.php.bak.YYYYMMDD-HHMM`

## ⚠️ Известные баги (в TODO)

См. `~/artvision-data/TODO.md` секция «UI swarm findings 2026-05-12»:
- ⚠️ FAB чат-бабла может перекрывать sticky bar (тел/TG-кнопка) — фикс `.avc-fab { bottom: 170px }` (применён 12.05 02:50)
- ⚠️ Cosmetology lavender палитра не у всех CTA — частично пофикшено

## 🔮 Voice product roadmap

Виджет = MVP product «Artvision Voice». Полный roadmap (16 фаз) в `~/artvision-data/products/voice/BRAINSTORM-2026-05-12.md`:
- Фазы 1-4 ✅ DONE (виджет + 3 КП используют external script)
- Фаза 5-7: CRM-интеграция (Bitrix24/amoCRM/HubSpot/Generic webhook)
- Фаза 11-14: Live (видео-кружки приветствие, Calendly, WebRTC, hover talking-head)
- Фаза 15: User Enrichment (rusprofile/checko/Apollo по email/домену)
- Фаза 16: Push notifications (Web/TG/Email — без SMS на MVP)

При разработке нового КП — Voice виджет уже подключается автоматически через `<script src=...>`. Для расширения функционала — отдельная сессия по продукту.

## Связь с другими правилами

- `~/.claude/rules/audit-kp-pipeline.md` — детальный 12-шаговый pipeline
- `~/artvision-data/templates/audit-kp-template.html` — HTML шаблон с placeholders
- `~/.claude/rules/medical-kp.md` — расширения для мед-клиник
- `~/.claude/rules/design-profile-routing.md` — 5 design profiles
- `~/.claude/rules/seo-tools-routing.md` — какой инструмент для какой задачи

## Прецедент

11.05.2026 — spb-kursy + cosmetology-kursy + hair-courses (3 родственных домена одного владельца).
- 5 часов работы, 8 параллельных агентов, 3 КП на проде
- Структура 8 секций по варианту B (после сжатия с 13)
- Урок: при копировании КП от одного клиента к другому НЕ забывать что **семантика должна быть подменена 100%** (cosmetology содержала 57× «массаж» из spb после программной копии — strict factcheck поймал → исправлять до отправки)
