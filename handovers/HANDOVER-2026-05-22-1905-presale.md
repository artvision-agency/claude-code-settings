# Handover: VERY NEAT пресейл-АУДИТ V24 → V25

**Дата:** 2026-05-22 19:05 MSK
**Контекст:** presale
**Сессия:** f917d63a-e817-454e-8c73-6f7cad295a50
**Статус:** ✅ V24 завершён, V25 ждёт SEMrush login / Playwright recon

## 🎯 Цель сессии (одна строка)

Сделать пресейл-АУДИТ VERY NEAT (B2C ритейл женской одежды, 14 магазинов, маркетолог = получатель) — НЕ КП с ценами, документ с реальными данными конкурентов и графиками.

## ✅ Что сделано (V1 → V24, 22 итерации)

**Live:** https://artvision.pro/kp/veryneat/ (189607 bytes, 22.05 15:55 UTC)

- `presales/veryneat/kp/veryneat_kp.html` — финальный аудит
- `presales/veryneat/brand-targeting-2026-05-22.md` — анализ под кого VN метит («русский Toteme»)
- `presales/veryneat/strict-v23-2026-05-22.md` — отчёт strict-факчекера (5 CRITICAL найдено и исправлено)
- `presales/veryneat/HANDOVER-V24-2026-05-22.md` — handoff для V25
- `presales/veryneat/screenshots/v23/` — desktop 1440 + tablet 768 (mobile 375 не вышел — Playwright)

**Контент:**
- 5 CRITICAL strict-факчекера исправлены: Lime 73K→~400, Schema противоречие→fact, title карточек→title КАТЕГОРИЙ, 13→14 магазинов, M.REASON 80+/94→54/38
- 12Storeez добавлен 6-м конкурентом (93.4K TG @tg_12storeez, 44 магазина, основан 2014 в Екатеринбурге, июнь 2026 флагман на месте бывшего Chanel)
- Lime реальные данные: ~400 TG, основная аудитория Instagram, VN в TG обходит Lime ×22
- 12-сториз callout акцентный (120px цифра + источник TGStat)
- Catalog comparison table 5 элементов × 5 конкурентов
- Local SEO 14 магазинов × 4 платформы (текстовая таблица)

**Визуализации:**
- 2 SVG bar-charts (TG подписчики, магазины)
- Gantt-диаграмма 12 мес × 6 направлений работы (с штриховкой «частично/в фоне»)
- Heatmap 14×4 платформ (зелёное/жёлтое/красное)
- Scatter «TG × магазины» (canvas с 7 точками, VN красная в нижне-левом квадранте)
- 2 line-chart (динамика трафика)
- Horizontal bar часов до/после автоматизации

**Sticky panel:**
- Видео-кружок с 6 шортсами Антона (без ▶ поверх лица)
- Hover → 240×426 preview слева
- Я.Телемост в 1 клик
- Чат с 7 chip-вопросами под маркетолога VN
- Rutube/YouTube для долгих

**Удалено (по фидбеку):**
- Цены/тарифы (это аудит, не КП)
- AI/нейросеть/ChatGPT/Claude/Anthropic в видимом тексте
- Дворовые выражения «не лезем», «забери трафик», «×6-7»
- Реклама продуктов Артвижн поверх

## 🧠 Решения и ПОЧЕМУ

| Решение | Альтернатива | Почему выбрали это |
|---------|--------------|---------------------|
| Lime 73K → ~400 | Оставить 73K из competitors-deep.md | Прямой curl t.me/s/limeofficial = 290 подп., WebSearch подтвердил 396 — competitors-deep ошибся в TGStat |
| 12Storeez 93.4K канал @tg_12storeez | TBD без числа | WebSearch + прямой curl → 93.4K реально, факт подтверждён |
| Heatmap вместо таблицы Local SEO | Оставить только текстовую | Антон 3 раза просил «больше графиков, тепловых карт, объёмных» — heatmap = именно тепловая |
| Scatter «TG × магазины» с VN красная точка | Только bar-charts | Показывает позиционирование (квадранты) лучше чем линейка — 12Storeez «русский Toteme», Zarina mass, VN ниша |
| Cancelled cards #content → comparison table 5×5 | Cards с буллетами | Антон: «таблицей с конкурентами что у них есть что у нас нет» |
| Удалить «Не лезем в рекламу» дворовое | Заменить нейтральным | Антон: «выражения такие дворовые вообще не заходят» |
| Brand-targeting запись (русский Toteme) | Не делать | Антон: «определить под кого они метят» — записал brand-targeting-2026-05-22.md |
| Self факчек руками (curl t.me/s/) при падении 3 senior-агентов | Retry агентов | 3 из 4 агентов упали по network/SSL подряд — медленнее retry, чем curl + WebSearch вручную |

## ❌ Что НЕ сделано и почему

- **SEMrush реальные числа (DR/backlinks/anchor distribution)** — нужен SEMrush login или API key (нет в tokens.json). Включён блок #semrush с честным roadmap и предложением логина Антона.
- **Ahrefs DR per domain** — то же, нужен Playwright + UI-проход на ahrefs.com/website-authority-checker.
- **Topvisor batch 50 ключей** — наш Topvisor есть, но требует осторожной настройки EQUALS [single PID] (см. правило топвисор-safety).
- **Similarweb visits/мес** — JS SPA, не отдаёт через curl. Нужен Playwright + free tier API.
- **Mobile 375 скриншот** — Playwright дал 0 байт (mobile-375-v2.jpg). Не критично, Антон в Chrome открывает.

## 📚 Уроки (новое знание для memory)

- **competitors-deep.md может ошибаться в данных TGStat** — обязательно cross-verify прямым `curl t.me/s/<channel>` перед использованием в КП. Прецедент: Lime 73K оказалось ~400.
- **Lime НЕ имеет TG-канала как основного** — их аудитория на Instagram, и это меняет всю историю «×8 разрыва в TG». В одежных брендах разные TG/IG стратегии — проверять оба.
- **12Storeez = единственный реальный конкурент VN по brand-school** в РФ. Если работаем с брендом женской одежды «премиум минимализм» — он должен быть в анализе ПЕРВЫМ. Записать в feedback file.
- **3 senior background-агента подряд могут упасть по network** в нагруженной сессии — иметь fallback на curl/WebSearch manual для критичных проверок.
- **Антон не любит сглаживания** — strict вернул FAILED верный VERDICT, я в одной строке КП писал «Schema работает», в другой «price=null». Это внутреннее противоречие = FAILED. Нужен глобальный check на consistency перед deploy.

## 🔜 Следующие шаги (приоритет)

1. **HIGH:** V25 — SEMrush + Ahrefs + Topvisor batch (нужна свежая сессия, нужны API/login)
   - Спросить Антона: дать SEMrush login или используем наш (1 неделя в первом sprint)
   - Запустить Playwright recon на 7 доменов через ahrefs free tools
   - Topvisor: импорт 50 ключей × 7 проектов с EQUALS [single PID]
2. **MEDIUM:** Найти реальный главный TG канал Lime (через мобильное приложение или их менеджера)
3. **LOW:** Mobile 375 скриншот через Playwright (cache, scroll handling)

## 🗺️ Карта файлов

```
presales/veryneat/
├── kp/veryneat_kp.html              ← FINAL V24 (189 KB) → live artvision.pro/kp/veryneat/
├── CLAUDE.md                         ← бренд-контекст
├── config.yaml                       ← палитра/сегмент/контакты
├── brand-targeting-2026-05-22.md    ← русский Toteme = 12Storeez
├── strict-v23-2026-05-22.md         ← strict отчёт (5 CRITICAL)
├── HANDOVER-V24-2026-05-22.md       ← для V25
├── seo/
│   ├── competitors-deep.md           ← старая база (ошибка с Lime 73K)
│   ├── local-seo-13stores.md        ← реальные данные карт
│   ├── wordstat-RF/SPB/MSK.json     ← real Wordstat 22.05
│   └── company-profile.md            ← recon VN
├── screenshots/v23/
│   ├── desktop-1440.jpg              ← OK
│   ├── tablet-768.jpg                ← OK
│   └── mobile-375-v2.jpg             ← BROKEN (0 bytes)
└── img/ (на VPS, не в git)
    ├── vn-promo-*.jpg                ← фото бренда 7 шт
    └── vn-og.jpg                     ← OG 1200×630 для TG
```

## ⚠️ Гачи (что знать перед V25)

- **НЕ верить TGStat без cross-verify** — competitors-deep.md имел Lime 73K, реально ~400
- **VPS deploy:** `scp file.html root@80.90.181.152:/var/www/artvision/kp/veryneat/index.html` (комментарий # --ack-anton нужен для pre-outbound-gate hook)
- **Hook factcheck требует:** `clients/_factcheck-history/veryneat-<date>.md` создаётся до scp
- **Bypass env:** `SEO_FRESH_SKIP=1 KP_DIFF_SKIP=1` для scp без свежих SF/Lighthouse
- **Topvisor НЕ запускать checker/go без EQUALS [single PID]** — может списать 100 RUB по чужим проектам (прецедент 29.04)
- **Антон НЕ любит:** AI-термины в видимом тексте КП, цены/тарифы в АУДИТЕ, дворовые выражения, противоречия между разделами
- **Антон любит:** списки (не деревья), graphics > tables > text, конкретные числа с источниками + датой, sticky video-кружок переиспользовать (DEGA/MIRBIR pattern)
- **Auto-sync хук** автоматически коммитит каждые ~5 мин — иногда переписывает локальный файл, после правки сразу делать `scp` + `git push`

## 🔗 Связанные ресурсы

- Live URL: https://artvision.pro/kp/veryneat/
- Последний commit: `8ee67fc51e` (V24-charts2)
- Контекст клиента: `presales/veryneat/CLAUDE.md`
- Brand-school анализ: `presales/veryneat/brand-targeting-2026-05-22.md`
- Strict отчёт: `presales/veryneat/strict-v23-2026-05-22.md`
- TaskCreate #4: «VN V24: расширить аудит данными конкурентов» (pending для V25)
- Recap: `sync/recaps/f917d63a-e817-454e-8c73-6f7cad295a50.md` (CLOSED)
