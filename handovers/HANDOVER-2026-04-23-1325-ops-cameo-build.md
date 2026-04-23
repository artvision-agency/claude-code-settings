---
session_id: f887858f-207c-4d27-af2f-b112c911a49f
date: 2026-04-23T13:25+03:00
context: ops
status: READY_FOR_EXECUTION
priority: HIGH
deadline: 2026-04-24 PM (конец выставки Дентал-Салон)
---

# Handover: 3 CAMEO-КП для Dental-Expo топ-3 экспонентов (Acteon / GC Russia / Рокада)

## 🎯 Задача новой сессии

**Собрать 3 CAMEO HTML-КП, задеплоить на VPS, проверить доступность.** Ревизия требования/факт уже сделана в этой сессии — в TODO всё ясно, данные есть, эталон есть. Осталась только сборка + деплой.

Deadline: **завтра (24.04) до вечера** — Антон очно показывает на стендах.

## 🧩 Контекст (почему сейчас handover)

Context 58% — «Dumb Zone» (bulletproof 40% rule). Каждый CAMEO-КП = 2000+ строк генерации из эталона + данные. 3 КП в текущем контексте = гарантированный цуг деградации. Поэтому: чистая сессия → 3 параллельных subagent'а → deploy из чистого контекста.

## ✅ Что уже готово (НЕ делать повторно)

### Данные экспонентов — все 3 файла в `clients/dentalexpo/seo/cameo-data/`
- `acteon-findings-2026-04-23.md` (4.7K) + `acteon-raw-2026-04-23.json` (4.2K)
- `gcrussia-findings-2026-04-23.md` (12K) + `gcrussia-raw-2026-04-23.json` (30K)
- `rocadamed-findings-2026-04-23.md` (16K) + `rocadamed-raw-2026-04-23.json` (46K)

### Эталон CAMEO
`clients/kamey/presale/kp/cameo_kp.html` — 2083 строки, Inter, чёрно-зелёный, tooltip `av-product`. Дизайн-система задокументирована в `clients/kamey/presale/design-system.md`.

### План (уже написан)
`docs/plans/2026-04-23-cameo-plus-design-system.md` — там есть архитектура, палитры по экспонентам, критерии приёмки.

### VPS уже настроен
- Путь: `/var/www/artvision/dental-expo/kp/` (создать при первом `scp`)
- Nginx: location `/dental-expo/` с `X-Robots-Tag: noindex, nofollow, noarchive` уже прописан (backup `artvision.pro.bak-dentalexpo-1776824188`)
- SSH: `root@80.90.181.152`
- Остальной `/dental-expo/` уже задеплоен (index, exhibitors, 4 TV, 10 prospects)

## ❌ Что НЕ сделано (= задача новой сессии)

1. **Build 3 CAMEO HTML**:
   - `clients/dentalexpo/presale/kp/acteon_kp.html`
   - `clients/dentalexpo/presale/kp/gcrussia_kp.html`
   - `clients/dentalexpo/presale/kp/rocadamed_kp.html`
2. **factcheck-v2.py** на каждый (0 CRITICAL обязательно)
3. **Deploy**: `scp *.html root@80.90.181.152:/var/www/artvision/dental-expo/kp/`
4. **Verify**: `curl -sI https://artvision.pro/dental-expo/kp/{acteon,gcrussia,rocadamed}_kp.html` = 200 на все 3
5. **Update TODO.md**:
   - Закрыть `[blocked-by: CAMEO HTML топ-3]` в задаче «Дентал-Салон: очный показ топ-3 CAMEO»
   - Закрыть `[routed]` задачу из presale/TODO.md «CAMEO-аудит для 1-3 топ-кандидатов»
6. **Commit + push** в ветку `feat/ops-crm-v1`

## 🎨 Бренд-токены по экспонентам (подтвердить subagent'ом при сборке)

| Экспонент | Primary | Accent | Шрифт | Tone |
|---|---|---|---|---|
| **Acteon Group** | Deep blue `#0B3D91` | Gold `#C9A227` | Dosis / Lato (Google Fonts) | Премиум, французский медтех |
| **GC Russia** | Aqua teal `#00A0C6` | Grey `#4A4A4A` | Noto Sans / Roboto | Японская точность, клиническая чистота |
| **Рокада Мед** | Red `#C8102E` | Navy `#003366` | PT Sans / Arial | Российский системный, надёжный |

**Важно:** токены — *ориентир*. Subagent ОБЯЗАН открыть сайт экспонента через `curl -sL domain | grep -oE '#[0-9a-fA-F]{3,8}'` и подтвердить/скорректировать палитру. Шрифт — `grep font-family`. Если бренд-шрифт платный — заменить на ближайший Google Font.

## 🚀 Рекомендованный workflow (новая сессия)

### Шаг 1. Setup (1 мин)
```bash
cd ~/artvision-data && git pull
mkdir -p clients/dentalexpo/presale/kp
cat docs/plans/2026-04-23-cameo-plus-design-system.md  # контекст
```

### Шаг 2. 3 subagent'а параллельно (~45-60 мин wallclock)

Каждому — один и тот же промпт-шаблон (меняется только `{brand}`). Важно: `run_in_background: true`, `subagent_type: fullstack-developer`, модель по умолчанию (opus).

**Промпт-скелет (копировать для 3 subagent'ов):**

```
Собрать CAMEO-КП для экспонента Дентал-Салон 2026 — {BRAND}.

ВХОД:
- Эталон: /Users/antonk/artvision-data/clients/kamey/presale/kp/cameo_kp.html (2083 строки, Inter, tooltip av-product)
- Дизайн-система эталона: /Users/antonk/artvision-data/clients/kamey/presale/design-system.md
- Данные: /Users/antonk/artvision-data/clients/dentalexpo/seo/cameo-data/{SLUG}-findings-2026-04-23.md
- Raw: /Users/antonk/artvision-data/clients/dentalexpo/seo/cameo-data/{SLUG}-raw-2026-04-23.json

ВЫХОД:
/Users/antonk/artvision-data/clients/dentalexpo/presale/kp/{SLUG}_kp.html (2000+ строк)

ТОКЕНЫ {BRAND}:
- Primary: {PRIMARY_HEX} (подтвердить с сайта через curl + grep)
- Accent: {ACCENT_HEX}
- Шрифт: {FONT} (если платный — заменить на Google Font-эквивалент, отметить в <!-- comment -->)
- Лого: скачать SVG/PNG с сайта, inline base64

ОБЯЗАТЕЛЬНО (правила из ~/.claude/rules/ и artvision-data/.claude/rules/):
1. HTML автономный (html-clients.md): inline CSS/JS, системные шрифты + Google Fonts через @import,
   без CDN скриптов, изображения base64. Viewport, lang="ru". Размер HTML < 500KB.
2. Бренд kp-brand.md: ЗАПРЕЩЕНО упоминать Topvisor/Ahrefs/SEMrush/Яндекс.Метрика/Google Analytics.
   Только экосистема Artvision: Flow (SEO), Scout (конкуренты), Radar (AI/GEO), Lens (A/B),
   LinkForge (ссылки), Content Lab (контент). Tooltip на av-product обязателен — брать из cameo_kp.html.
3. Все числа с источником: CONFIRMED/UNCONFIRMED/WRONG (factcheck.md). Из findings.md брать с метками.
4. Адаптивность: проверить на 375x812 / 768x1024 / 1440x900 через Playwright screenshot,
   скрины сложить в clients/dentalexpo/presale/kp/screenshots/{SLUG}-{bp}.jpg
5. Структура (все секции из cameo_kp.html): Hero → проблемы сайта (из findings) → SERP-анализ →
   что делаем (методология Artvision Flow/Scout/Radar) → тарифы 3-tier → кейсы → FAQ → CTA → footer
6. factcheck перед коммитом: scripts/factcheck-v2.py clients/dentalexpo/presale/kp/{SLUG}_kp.html
   — 0 CRITICAL. URL из HTML все отдают 200.

РЕЗУЛЬТАТ:
- HTML-файл создан
- Скриншоты созданы (3 breakpoint)
- factcheck прошёл 0 CRITICAL
- Git не коммитить (главная сессия сделает)

Возвращай: путь к файлу, размер в строках, путь к скриншотам, вывод factcheck.
```

Значения `{SLUG}` / `{BRAND}`:
- `acteon` / `Acteon Group` (acteongroup.com)
- `gcrussia` / `GC Russia` (gcrussia.com)
- `rocadamed` / `Рокада Мед` (rocadamed.ru)

### Шаг 3. Factcheck + Deploy (10 мин)
```bash
cd ~/artvision-data
# 1) factcheck
for f in clients/dentalexpo/presale/kp/{acteon,gcrussia,rocadamed}_kp.html; do
  python3 scripts/factcheck-v2.py "$f" || echo "FAIL: $f"
done

# 2) если все PASS — deploy
ssh root@80.90.181.152 "mkdir -p /var/www/artvision/dental-expo/kp && chown www-data:www-data /var/www/artvision/dental-expo/kp"
scp clients/dentalexpo/presale/kp/*.html root@80.90.181.152:/var/www/artvision/dental-expo/kp/

# 3) verify
for name in acteon gcrussia rocadamed; do
  curl -sI "https://artvision.pro/dental-expo/kp/${name}_kp.html" | head -1
done
# ожидается: HTTP/2 200 × 3
```

### Шаг 4. Close-out (5 мин)
- `TODO.md`: закрыть blocker CAMEO + отметить «очный показ» готов к 24.04
- `presale/TODO.md`: закрыть [routed] CAMEO-аудит
- Git commit: `feat(dental-expo): CAMEO+ КП топ-3 экспонентов (Acteon/GC/Рокада) к выставке 24.04`
- Git push (`feat/ops-crm-v1`)
- TG уведомление Антону: «3 CAMEO готовы: artvision.pro/dental-expo/kp/{acteon,gcrussia,rocadamed}_kp.html»

## 🧠 Решения и ПОЧЕМУ (из этой сессии)

| Решение | Альтернатива | Почему |
|---|---|---|
| Handover → /clear → 3 subagent в чистой сессии | Делать 3 КП последовательно в этой сессии | Контекст 58%, 3 CAMEO = ~30K доп токенов + риск Dumb Zone. Субагенты изолированы |
| CAMEO+ = base + target tokens (план) | Создавать каждый КП с нуля | Эталон уже есть (2083 строки), переиспользование + консистентность |
| Subagent'ы параллельно, не последовательно | По одному | Независимы (разные экспоненты, разные файлы) |
| Новая сессия подтверждает токены c сайта | Использовать токены из handover как есть | Мои hex в handover — ориентир, не факт. Subagent валидирует curl'ом |
| Deploy только после factcheck 0 CRITICAL | Deploy + исправить если что | R2 quality-gates: factcheck ПЕРЕД scp |

## ❗ Гачи

- **Ветка `feat/ops-crm-v1`**, не main
- **`scripts/factcheck-v2.py`** — проверить существование (HANDOVER-1100 п.6 «LOW: factcheck-v2.py создать» — могло быть не сделано). Если нет — создать минимальный: HTTP HEAD на все URL из HTML + парсер title/h1/meta. Fallback: `python3 scripts/factcheck-html.py` если v2 нет.
- **Chrome конфликт с Playwright** (если subagent делает скриншоты): `osascript -e 'tell application "Google Chrome" to quit'` перед запуском
- **Логотипы экспонентов** — скачать с их сайтов, inline base64. Если не скачивается — SVG-плейсхолдер с первой буквой бренда
- **FF Meta (эталон CAMEO)** — коммерческий, НЕ юзать. Inter через `@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap')` — допустимо (Google Fonts = не CDN библиотека)
- **av-product tooltip** — это ключевой визуальный якорь CAMEO. Найти в `cameo_kp.html` через `grep -n "av-product"` и переиспользовать один-в-один

## 🔜 После успешного деплоя (следующие шаги)

1. Антон 24.04 очно показывает 3 КП на стендах Acteon / GC / Рокада (closed by human)
2. После выставки — follow-up с ответившими, CAMEO для чистых экспонентов (Юнидент/Ревилайн/МегаДжен) как следующий этап
3. `design-systems/README.md` (ростер ДС) — отдельная сессия после 24.04
4. `amnesia` клон + `dentalexperts` ДС для Лакшина — параллельные треки, отложено

## 📂 Файлы, связанные с задачей

```
~/artvision-data/ (ветка feat/ops-crm-v1)
├── clients/kamey/presale/
│   ├── kp/cameo_kp.html                           ← ЭТАЛОН (2083 стр)
│   └── design-system.md                           ← дизайн-система CAMEO
├── clients/dentalexpo/
│   ├── seo/cameo-data/
│   │   ├── acteon-findings-2026-04-23.md         ← данные Acteon
│   │   ├── gcrussia-findings-2026-04-23.md       ← данные GC (12K)
│   │   └── rocadamed-findings-2026-04-23.md      ← данные Рокада (16K)
│   └── presale/kp/                                ← ✴ СОЗДАТЬ, сюда 3 HTML
├── docs/plans/2026-04-23-cameo-plus-design-system.md  ← план
├── scripts/factcheck-v2.py                        ← проверить наличие
└── TODO.md + presale/TODO.md                      ← закрыть в конце

VPS: root@80.90.181.152:/var/www/artvision/dental-expo/
├── (уже задеплоено) index.html, exhibitors.html, 4 TV, 10 prospects
└── kp/                                            ← ✴ СОЗДАТЬ, сюда scp
```

## 💡 Стартер для новой сессии

```
Прочитай ~/.claude/handovers/HANDOVER-2026-04-23-1325-ops-cameo-build.md

Коротко:
- Надо собрать 3 CAMEO HTML-КП (Acteon/GC/Рокада) по эталону kamey/cameo_kp.html
- Данные готовы в clients/dentalexpo/seo/cameo-data/*findings*.md
- Deploy на artvision.pro/dental-expo/kp/
- Deadline: 24.04 PM (выставка)

Запусти 3 subagent'а параллельно (fullstack-developer, background).
Промпт-шаблон в секции «Шаг 2» handover'а.

После готовности — factcheck + deploy + close TODO + commit + push.
```
