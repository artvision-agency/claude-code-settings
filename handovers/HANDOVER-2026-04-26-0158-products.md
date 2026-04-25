# Handover: Scout (Direct-Radar) — ревизия продукта + переосмысление спеки

**Дата:** 2026-04-26 01:58
**Контекст:** products
**Сессия:** ab0ab5bd... (cwd: ~)
**Статус:** в работе — backlog 10 задач, готов критический путь к пилоту

---

## 🎯 Цель сессии

Полная ревизия продукта Direct-Radar (публичное имя — Artvision Scout): что показывает свою рекламу на основании Директа конкурентов и брендового трафика. Найти спеку, поэтапно описать как продукт работает, расширить функционалом клон-перехвата + engagement-замером.

---

## ✅ Что сделано

### Документы
- `products/direct-radar/README.md` (был, не правил) — прочитан 345 строк
- `products/direct-radar/CLAUDE.md` — публичное имя «Artvision Scout»
- `~/.claude/projects/-Users-antonk/memory/yandex-direct-2026.md` — контекст справки
- `products/TODO.md` — добавил блок Scout (строки ~32-42)

### Критика и проверки
- **round_table** через `mcp__llm-consilium` (llama+qwen3+gpt-oss-groq) — выявил юридический провал утверждения C
- **WebSearch** ФАС-прецеденты — найдено решение **15AP-5921/19** (июнь 2019), с тех пор ФАС квалифицирует таргет на чужой ТМ как недобросовестную конкуренцию
- **Ревизия direct_radar.py 603 строки** — есть SerpCollector / SQLite / TG-алерты / отчёт; **нет вообще** DirectIntegrator / Wordstat / Роспатент / BrandScorer / ROI

### Код
- `products/direct-radar/scripts/engagement_probe.py:1-84` — spike Метрика API: visits/time/depth/bounce per UTM
  - Тест на artvision.pro (22056523): 10 визитов с UTM
  - Тест на otido (26554326): 3770 визитов, baseline time=50с depth=1.65 bounce=49.3%, ad-group расслоение в 30×
  - Тест на tvorimsovershenstvo (98907521): **0 визитов с UTM** — UTM не размечен

### Коммиты (4 в feat/ops-crm-v1)
- `4802faf4e` — критика выявила ложное УТП C, добавлены задачи
- `69fd9bd37` — ревизия direct_radar.py + корректировка задач после фидбека Антона
- `cb6d2176f` — engagement_probe.py spike
- `+ session-state autocommits`

---

## 🧠 Решения и ПОЧЕМУ

| Решение | Альтернатива | Почему |
|---------|--------------|--------|
| **Kill-switch + blacklist крупных сетей** вместо «не работаем по бренду» | Полный отказ от бренд-таргета (юр.чистота) | Антон оспорил: «все пользуются, никто не жалуется». Реальный риск только при жалобе с зарегистрированным ТМ. Гасим за час по жалобе. Не таргетим СМ-Клиника / МедСИ / Стома / Инвитро. |
| **CPC «-30..60%»** вместо «3-5× дешевле» | Оставить «3-5×» | 3-5× = -70..-80%. Открытые источники (yagla, click.ru, ashmanov) дают -30..60%. В КП клиенту 3-5× = легко проверяемая ложь. |
| **Убрать «конверсия 2-3×» вообще** | Смягчить до «1.5-2×» | Один источник даёт 2-2.5×, другой говорит CR может быть **ниже** (юзер ждёт конкурента, попадает к другому). До пилота — данных нет. |
| **11-критериальный BrandScorer + LiveMultiplier** | Простой `min_frequency=2` который сейчас в коде | Критерий 1 наивен. 8 pre-campaign + 3 engagement-прокси (SimilarWeb avg session/bounce/pages) + Live слой через Метрика API на UTM. ScoutScore = PreScore × LiveMultiplier (0.5-1.5). |
| **Жёсткий ТМ-фильтр ДО скоринга** | ТМ как один из весов | Нельзя «частично» рисковать ФАС: если ТМ зарегистрирован + бренд уникальный (не родовой) → исключить полностью. Скоринг только для остатка. |
| **OTIDO как первый пилот вместо Творим** | Творим (изначальный план) | На счётчике Творим 98907521 — 0 UTM-визитов за 30 дней. На OTIDO 26554326 — 3770 визитов, baseline уже виден, можно стартовать без перенастройки разметки. |
| **Premium CloneEngine отдельным треком** (Firecrawl+SingleFile+Flux.1) | Включить в основной MVP | Большой кусок (~22ч) + tool-adoption-proof round-table обязателен + юр.фильтр (logo/palette/title perceptual hash). Делаем после базового Scout. |
| **Чек ТМ через Роспатент перед добавлением каждого бренда** | Чек только при жалобе | Превентивно ловить ТМ-зарегистрированные бренды дешевле чем разбираться с жалобой. |

---

## ❌ Что НЕ сделано

- **Переписывание README/SALES-KIT** — задача #2, ещё открыта (1-2ч)
- **Запуск direct_radar.py --scan** на любом из 3 yaml — не делал, кода-ревизия достаточно для понимания gaps
- **Round-table tool-adoption** для Firecrawl/SingleFile/Flux.1 — обязателен перед CloneEngine, не делал (это для Premium-трека)
- **Юрист-ревью шаблона** — задача #5, ассайнена Антону

---

## 📚 Уроки сессии

1. **Round-table критика → переворачивает УТП.** Без независимой проверки утверждение «нельзя заблокировать» прошло бы в КП клиента и поймали бы по факту. Round-table обязателен перед презентацией продукта клиенту. → fixed в `tool-adoption-proof.md`, аналогично надо для product launch.

2. **Ревизия ≠ рисёрч.** Антон поймал что я взял scoring-алгоритм из gpt-oss-groq и наложил на README, не открыв `direct_radar.py`. Правильная последовательность: revision actual code → research best practice → diff → update plan. → стоит сохранить как `feedback_revision_before_research.md`.

3. **Цифры с разной шкалой («3-5×» vs «-30..60%») надо разъяснять.** Антон не понял разницу с первого раза. → в КП всегда показывать **обе** формы: «в 1.4-2.5 раза дешевле = на 30-60%».

4. **«Никто не жалуется» ≠ «риска нет», но и ≠ «нельзя».** Юридический риск асимметричен: реализуется только при активной жалобе. Стратегия = kill-switch + blacklist + не таргетить крупные сети, а не полный отказ.

5. **Engagement-прокси (Метрика API) на artvision-собственных счётчиках работает.** Авторизация через единый OAuth-token, доступ к 122 счётчикам. Spike подтвердил формат данных. Не нужна отдельная авторизация на каждого клиента, если Артвижн уже гостевой.

---

## 🔜 Следующие шаги (приоритет)

### Критический путь к пилоту (3-4 рабочих дня + 1 неделя замера)

1. **HIGH #2** Переписать УТП (README/SALES-KIT/service-description/upsell-script) — 1-2ч, не блокировано
2. **HIGH #10** Решить пилот: OTIDO (готов) vs Творим (UTM не размечен) — 30 мин
3. **HIGH #8** blacklist.yaml + /scout_kill — 3ч
4. **HIGH #3** Trademark-фильтр через Роспатент — 2ч
5. **HIGH #7** DirectIntegrator + /radar_approve — 6ч
6. **HIGH #4** BrandScorer 8 крит + Wordstat + миграция схемы — 10ч
7. **HIGH #5** Юрист-ревью (Антон) — параллельно
8. **HIGH #6** Пилот 30 дней — 1 неделя замера

### Medium

- **#9** Engagement-слой 11 крит + LiveMultiplier — 6ч (после #4 + #7)
- Premium CloneEngine track (round-table tool-adoption + 22ч код) — отдельно

### Рекомендация для следующей сессии

Старт: **#2 + #10 параллельно** (одна сессия 2-3ч). Они не блокированы, снимают риски до того как писать код, дают ясность по пилоту.

---

## 🗺️ Карта файлов

```
products/direct-radar/
├── direct_radar.py          ← 603 стр, есть SERP-парсер + SQLite + TG-алерт
├── traffic_simulator.py     ← 492 стр, не трогали
├── scripts/
│   ├── engagement_probe.py  ← НОВОЕ (spike Метрика API)
│   └── radar_monitor.py     ← 803 стр, не трогали
├── test-configs/
│   ├── tvorim.yaml          ← пилот-кандидат, но UTM не размечен
│   ├── otido.yaml           ← рекомендован как первый пилот
│   └── extru.yaml
├── data/                    ← пустая (БД не запускалась)
├── README.md                ← 345 стр, требует правок (#2)
├── SALES-KIT.md             ← требует правок (#2)
├── service-description.md   ← требует правок (#2)
└── upsell-script.md         ← требует правок (#2)

artvision-data/products/TODO.md (стр 28-42)
└── 8 задач Scout high + 2 medium

~/.claude/handovers/
└── HANDOVER-2026-04-26-0158-products.md  ← этот файл
```

---

## ⚠️ Гачи

- **Метрика API counter Творим = 98907521** показал 0 UTM-визитов. До пилота на Творим **обязательно** проверить разметку UTM в текущих кампаниях, иначе LiveMultiplier не сработает.
- **OTIDO counter 26554326** уже даёт baseline (3770 визитов, time 50с, depth 1.65, bounce 49.3%) — пилот можно стартовать сразу.
- **tokens.json[yandex.metrika.token]** даёт доступ к 122 счётчикам в т.ч. всех клиентов — НЕ нужен отдельный гостевой доступ.
- **Я.Директ API v5** — 3 аккаунта в `tokens.json[yandex.direct]`, для DirectIntegrator брать `reklamaspb1` (для Творим) или нужный по client.
- **ФАС-прецедент 15AP-5921/19** — основа правильной формулировки в КП. Ссылка должна быть в материалах для прозрачности.
- **Cron Scout пока на ноуте** (LaunchAgent написан в README, не зарегистрирован). Перед пилотом перенести на VPS 80.90.181.152.
- **Антон не понял «3-5×» с первого объяснения** — в материалах писать обе формы числа.

---

## 🔗 Связанные ресурсы

- TaskCreate IDs: #1 (completed) #2-#10 (pending)
- Коммиты: `4802faf4e`, `69fd9bd37`, `cb6d2176f` в `feat/ops-crm-v1`
- Memory справка: `~/.claude/projects/-Users-antonk/memory/yandex-direct-2026.md`
- Spike результат на OTIDO: `python3 scripts/engagement_probe.py 26554326 30`
- Recap другой задачи (НЕ Scout): `sync/recaps/ab0ab5bd-5b0e-4984-a8d0-31aa121df9d8.md` (circon-clinic SEO, PARTIAL)

---

## Источники

- [yagla.ru — реклама на бренды конкурентов](https://yagla.ru/blog/kontekstnaya-reklama/kak-pravilno-nastroit-reklamu-na-brendy-konkurentov/)
- [garant.ru — может ли предприниматель запретить](https://www.garant.ru/article/1264866/)
- [onlinepatent.ru — как остановить недобросовестную рекламу](https://onlinepatent.ru/faq/trademark/how-to-stop-context/)
- [click.ru — изменения CPC/CTR/CPM](https://blog.click.ru/analytics/god-reklamy-v-cifrax-kak-izmenilis-cpc-ctr-i-cpm/)
- [ashmanov.com — средняя цена клика](https://www.ashmanov.com/education/articles/srednyaya-tsena-klika-yandekdirekt/)
