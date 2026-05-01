# Handover: na-sklad.ru SEO-КП + автоматизация паттернов

**Дата:** 2026-05-01 21:05
**Контекст:** presale (na-sklad.ru, ООО «Трилон-М»)
**Сессия:** ef3a112f-59d5-4ad2-8727-fff9a84ab739 (resumed после кросс-сессионных блоков хуков)
**Статус:** ✅ завершено — КП в проде, паттерны зафиксированы, Asana задача создана

## 🎯 Цель сессии

Закрыть SEO-КП для na-sklad.ru (СПб, ответственное хранение) → залить в `clients/`, добавить в реестр, запушить, создать follow-up в Asana. Параллельно — зафиксировать новые паттерны (графики, структура 15 разделов, sticky-TOC, 2 формата) для будущих SEO-аудитов.

## ✅ Что сделано

### na-sklad.ru — артефакты в репо
- `clients/na-sklad/kp/index.html` — финальный КП (~96 KB), на VPS https://artvision.pro/kp/na-sklad/
- `clients/na-sklad/kp/img/{pulse-radar,sitemap-diff,backlinks,traffic}.png` — 4 matplotlib-графика
- `clients/na-sklad/audit/{index,commercial,text,link,behavioral}-2026-05-01.html` — 5 модулей аудита
- `clients/na-sklad/CLAUDE.md` — клиентский контекст (бизнес, статус, артефакты, правила)
- `.claude/rules/clients-registry.md` — добавлен в Presale → КП отправлено

### Автоматизация (зафиксировано на ~/.claude)
- `~/.claude/hooks/pre-kp-bred-block.sh` — расширен до 7 категорий + 21 тестов
- `~/.claude/hooks/tests/test-pre-kp-bred-block.sh` — 21/21 PASS
- `~/.claude/skills/presale-kp/SKILL.md` — Вариант B (15 разделов), 2 формата (95К + 70К/мес)
- `~/.claude/skills/presale-kp/templates/` — 9 партиалов:
  - `gen-charts.py` — параметризованный matplotlib (4 типа графиков)
  - `mini-toc.html` — sticky TOC на ≥1024px
  - `mobile-responsive.css` — 6 breakpoints + overflow-x: clip
  - `chat-widget.html` — псевдо-менеджер → POST /api/lead
  - `audit-summary-box.html` — блок «Суть аудита»
  - `horizons-3-6-12.html` — 3 цветные карточки результатов
  - `seo-kp-structure.md` — 15-секционный скелет
  - `soften-language.json` — карта замен 7 категорий резких слов
  - `seo-audit-patterns.md` — **NEW (этот session)** обзор всех паттернов для будущих аудитов
- `~/.claude/rules/seo-kp-horizons.md` — правило горизонтов 3/6/12 + блок «Суть аудита»

### Asana
- Задача создана: https://app.asana.com/1/860693669973770/project/1212305892582815/task/1214456345910471
- Assignee: Anton, due: 2026-05-01, статус: открыта (follow-up по отправленному КП)

### Фактчек 2 WARNING
- `clients/na-sklad/kp/index.html:1337` — alt-теги цифры исправлены: было «75 без alt + 264 с пустым alt» (числа из несуществующего источника), стало «25 без alt + 42 с пустым alt из 67» (реально проверено `curl https://na-sklad.ru/`)
- Title формулировка `/otvetstvennoe-hranenie/` — фактически верифицирована: «Ответственное хранение - "Трилон М"» (без СПб) — наш текст корректен

## 🧠 Решения и ПОЧЕМУ

| Решение | Альтернатива | Почему выбрали |
|---------|--------------|----------------|
| 15 разделов структуры | Стандартные 10 (вариант A из SKILL.md) | Большой аудит на 4 модуля + горизонты — нужно показать масштаб работы |
| 2 формата (95К одноразово + 70К/мес) | 3 тарифа (стартовый/опт/комплекс) | Антон явно: «убрать тариф-стиль, дать честный выбор: купи план или закажи реализацию» |
| Sticky mini-TOC только ≥1024px | Inline TOC сверху | На длинном КП (15 разделов) клиент теряется при скролле; на mobile inline-TOC уже есть в начале |
| Виджет чата «Анна Ширшова» | Прямые контакты Артвишн | kp-brand: контакты Artvision не показывать в КП клиента — единственный канал контакта = виджет |
| 4 matplotlib-графика как обязательные | Один сводный или текст | Антон явно: «графики разные новые понравились» — закрепить как стандарт. Pulse-radar даёт визуальный «удар» score |
| Хук + 21 тест | Только правила в md | Правила в md забываются (инциденты #8 #9 в self-corrections). Хук = детерминистичная блокировка |
| Strip-цифры (75/264 → 25/42 реальных) | Оставить как было | Числа без источника = риск что клиент проверит. Реальные через `curl` — устойчиво |

## ❌ Что НЕ сделано и почему

- **P3: унификация pulse-radar данных с `seo-factors-audit`** — отложено до 2-го SEO-КП на новом клиенте. Сейчас pulse строится отдельно от 4 модулей audit/, что создаёт двойную работу. Когда повторится паттерн — рефакторить.
- **P3: sub-skill `presale-kp-seo`** — отложено по той же причине. Если структура SEO-КП разойдётся со standard-КП на 2-м кейсе — выделить.
- **`seo-factors-audit` обновление палитры** — pulse-radar генерится по правильной палитре только в `gen-charts.py`. Сводный отчёт в `seo-factors-audit/reports/` ещё использует старую палитру. Рефакторинг ленив.

## 📚 Уроки (новое знание)

- **Графики matplotlib + единая палитра** = заметный wow-эффект на КП. Антон отметил явно. → закреплено в `seo-audit-patterns.md`.
- **Хук-первый подход:** инцидент в md-правилах → не хук = повтор. Каждый класс ошибок (резкие слова, AI-упоминания, контакты Артвишн) → отдельная regex-категория в хуке.
- **strict-factcheck даёт WARNING на цифры из «памяти»** — числа всегда проверять `curl`'ом перед записью в КП. Прецедент: 75/264 alt-теги были взяты «на глаз», реально 25/42.
- **Asana required-fields hook блокирует без due_on** — даже follow-up задачи с «уже отправил» = нужна дата. По умолчанию ставить дату создания (=сегодня) или +7 дней.
- **AskUserQuestion для assignee+due одним вызовом** — пользователь отвечает быстрее, чем при последовательных вопросах.
- **Lexicon-хук срабатывает на токен `claude` в путях** (например `~/.claude/skills/...`) — в клиентских md избегать упоминаний путей где есть «claude».

## 🔜 Следующие шаги (приоритет)

1. **HIGH:** Дождаться ответа клиента na-sklad по КП → созвон → согласование цены и формата.
2. **MEDIUM:** На 2-м SEO-КП (вероятно UNO Trans / DentalExpo / Marulidi) — применить `seo-audit-patterns.md`. Если структура разойдётся — выделить `presale-kp-seo` sub-skill.
3. **MEDIUM:** Унифицировать pulse-radar генератор с `seo-factors-audit` — единая точка построения 4-модульного score.
4. **LOW:** ant-partners patterns пересмотреть — там тоже есть свой шаблон, возможно стоит подсветить отличия.

## 🗺️ Карта файлов

```
artvision-data/clients/na-sklad/
├── CLAUDE.md                              ← клиентский контекст
├── kp/
│   ├── index.html                         ← финальный КП (deployed)
│   └── img/{pulse-radar,sitemap-diff,backlinks,traffic}.png
└── audit/
    ├── index.html                         ← сводный аудит
    └── {commercial,text,link,behavioral}-2026-05-01.html

~/.claude/
├── hooks/
│   ├── pre-kp-bred-block.sh               ← 7 категорий + 21 теста
│   └── tests/test-pre-kp-bred-block.sh
├── rules/seo-kp-horizons.md
└── skills/presale-kp/
    ├── SKILL.md                           ← Вариант B 15 разделов + 2 формата
    └── templates/
        ├── seo-audit-patterns.md          ← обзор паттернов (этот session)
        ├── seo-kp-structure.md            ← скелет 15 разделов
        ├── gen-charts.py                  ← 4 графика matplotlib
        ├── mini-toc.html                  ← sticky навигация
        ├── mobile-responsive.css          ← 6 breakpoints
        ├── chat-widget.html               ← виджет менеджера
        ├── audit-summary-box.html         ← блок «Суть аудита»
        ├── horizons-3-6-12.html           ← 3 карточки горизонтов
        └── soften-language.json           ← замены резких слов
```

## ⚠️ Гачи (gotchas)

- Хук `pre-kp-bred-block.sh` срабатывает на путях `*/clients/*/kp/*.html`, `*/var/www/artvision/kp/*` и др. Bypass только `KP_BRED_OK=1` с явным обоснованием.
- Хук `pre-asana-required-fields.sh` блокирует `mcp__asana__asana_create_task` без `due_on`. Решение: ставить `due_on=сегодня` или прямой spec от пользователя.
- Хук `pre-client-lexicon.sh` блокирует путь `*/clients/*` если в контенте AI/нейросети/Claude. Триггер на токен `claude` в любых путях `~/.claude/...` тоже срабатывает — переформулировать.
- `auto-sync` коммитит `clients/*/` каждые ~2 минуты. Файлы могут быть уже committed к моменту явного `git add`.
- `clients-registry.md` — file rewrites автоматически (linter/auto-process). Любое ручное добавление дублировать **сразу** — может быть перезаписано.

## 🔗 Связанные ресурсы

- Asana: https://app.asana.com/1/860693669973770/project/1212305892582815/task/1214456345910471
- KP live: https://artvision.pro/kp/na-sklad/
- Audit live: https://artvision.pro/audit/na-sklad/
- Recap: `artvision-data/sync/recaps/ef3a112f-59d5-4ad2-8727-fff9a84ab739.md`
- Commit hooks/skills: `a0ac04b8` в claude-code-settings (main)
