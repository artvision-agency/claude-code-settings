# Handover: TELEGRAM Kredity — IG-reels анализ + LEGAL_BRIEF для адвокатов

**Дата:** 2026-04-29 02:10
**Контекст:** personal (личная юридическая работа Антона; technically запущено в cwd `/Users/antonk` = ops)
**Сессия:** bef5d1bd-3420-48cf-882d-bd9fb3c6ad0f (TELEGRAM Kredity)
**Статус:** ✅ завершено (deliverable готов, ждёт go от Антона на передачу адвокатам)

## 🎯 Цель сессии

Извлечь через Telethon финансовые Instagram-reels из личных TG-сообщений Антона (бот @avportal_bot), мульти-агентным анализом превратить в юридический бриф для адвокатов клиента — со сценарием «обеспеченный друг выкупает долг» и анализом путей вывода квартиры из-под залога Альфа-Банка.

## ✅ Что сделано (с файлами)

```
~/artvision-data/.claude_temp_scripts/credit-reels-2026-04-28/  (gitignored, 281 KB, 14 файлов)
├── LEGAL_BRIEF_for_lawyers.md          ← ГЛАВНЫЙ deliverable, 543 строки, 12 разделов
├── FINAL_synthesis.md                  ← промежуточный синтез по reels
│
│  -- Анализ reels (волна 1, 3 senior-агента) --
├── agent1_advice_from_captions.md      ← Senior 1 (data-analyst) — 4 механики из captions
├── agent2_comments_analysis.md         ← Senior 2 (research-analyst) — 72 коммента классифицированы
├── agent3_risk_priority.md             ← Senior 3 (general-purpose) — оценка реалистичности
│
│  -- Юридический бриф (волна 2, 7 senior-агентов) --
├── agent4_tax_law.md                   ← НДФЛ-риски (general-purpose, 970 слов, 8 sources)
├── agent4_tax_law_memo.md              ← НДФЛ-риски (legal-advisor, 1184 слов, 11 sources) — альт. версия
├── agent5_banking_law.md               ← банковское право (1338 слов, 8 sources)
├── agent6_mortgage_law.md              ← ипотечное право, 3 пути А/Б/В (1592 слова)
├── agent7_cases_interest.md            ← Researcher 1: 17 кейсов по % (1500 слов)
├── agent8_cases_collateral.md          ← Researcher 2: 13 кейсов по залогу (1750 слов)
├── agent9_cession_practice.md          ← Researcher 3: 10 кейсов цессии (1750 слов)
├── agent10_structuring_friend_cession.md ← Senior 7: structuring memo «друг выкупает» (2214 слов)
│
│  -- Исходные данные --
├── swarm_input.md                      ← 11 reels с captions + 72 коммента
├── credit_reels_with_comments.jsonl
├── raw_messages.jsonl                  ← 3452 сообщения @avportal_bot DM
└── saved.jsonl                         ← 686 Saved Messages с URL/fin
```

**Sync:** session recap `~/artvision-data/sync/recaps/bef5d1bd-3420-48cf-882d-bd9fb3c6ad0f.md` закоммичен (`eec2eb128`). Push на `feat/ops-crm-v1` ✅.

## 🧠 Решения и ПОЧЕМУ

| Решение | Альтернатива | Почему выбрали это |
|---|---|---|
| **Telethon с `~/.telegram_session.session`** (авторизованный пользовательский аккаунт Antona) | Bot API, `~/.tg_artvision.session`, `bot_session.session` | Bot API не читает чужие чаты. `.tg_artvision.session` и `telegram_session.session` НЕ авторизованы (NOT_AUTH). `bot_session.session` авторизован как Bot, не User. Только `~/.telegram_session.session` = Anton (id 161261562) и читает DM с @avportal_bot |
| **yt-dlp для обогащения IG URL** | WebFetch / Jina Reader / link-processor cards | IG auth-wall блокирует WebFetch и Jina. yt-dlp пробивает (99/134 успешно). Из 95 link-processor cards 5/11 финансовых reels были «Без заголовка» / «UNAVAILABLE» — yt-dlp вытащил captions целиком |
| **2 волны роя** (3 + 7 агентов) | 1 большой рой / 1 агент с 7 ролями | Первая волна (пользователь не уточнил scope) — общий анализ reels. Вторая волна (после уточнения «для адвокатов») — узкие легальные специалисты. Каждый агент с одной ролью даёт глубину больше чем мульти-роль |
| **Артефакты в `.claude_temp_scripts/`** | `personal/divorce-alimony/`, `clients/personal/` | `.claude_temp_scripts/` gitignored по правилу `core.md` — личные TG сообщения, реквизиты кредитного договора, NDFL расчёты не должны коммититься. **Локально доступны, в git нет** |
| **LEGAL_BRIEF структурирован для юристов** (legal-memo style с цитатами норм + URL footnotes) | Layman-style summary | Документ передаётся юристам, они работают с нормами, не с пересказом. Нужны точные ссылки на КонсультантПлюс/Гарант/vsrf.ru |
| **Сценарий «друг выкупает» детально расписан** | Только упоминание | Это центральный операционный кейс который Антон явно запросил. Нужны pre-conditions + 3 пост-цессионных сценария (А/Б/В) + защита от переквалификации + бюджет |
| **Включил Путь В (ст.35 ч.3 СК)** как отдельный детальный раздел | Просто mention | Это **сильнейший рычаг** против Альфы — если согласия супруги в досье нет, шансы 70-80% (новелла 2022 даёт обратное бремя доказывания на банк) |

## ❌ Что НЕ сделано и почему

- **Передать документ адвокатам** — ждёт явный go от Антона. Документ содержит конфиденциальные данные (реквизиты кредитного договора F0PM1020S24010900331, расчёты НДФЛ, информация о супруге) — отправлять без подтверждения нельзя
- **Верификация номеров дел и реквизитов писем Минфина** — в дисклеймере явно: «требует независимой проверки адвокатом по карточке дела на vsrf.ru / sudrf.ru / СПС». Агенты использовали WebSearch — реквизиты могут содержать ошибки
- **Реальная политика Альфы по продажам долгов 2026** — оценили по публикациям Коммерсанта/РБК/Frank Media за 2023-2024 (выставление СКМ на продажу в окт.2023). Текущая политика 2026 — нужен прямой запрос через адвоката
- **Фактчек комментов с лайками** — yt-dlp вытащил тексты, но IG режет API на счётчиках лайков комментариев. Ранжировал по содержательности, не по лайкам как просил пользователь — отметил это в финальном дисклеймере
- **35 IG `p/*` posts не обработаны** — yt-dlp не пробивает carousel-посты. Среди 134 URL это 26% — возможно там были credit-related, но не извлечены

## 📚 Уроки (новое знание для memory)

1. **`~/.telegram_session.session` — единственная авторизованная Telethon-сессия как Anton (id 161261562).** Использовать её, не `~/.tg_artvision.session` (NOT_AUTH). Сохранить в `reference_telethon_session.md`
2. **yt-dlp пробивает IG auth-wall для reels.** Когда link-processor card возвращает UNAVAILABLE / «Без заголовка» — попробовать `yt-dlp --skip-download --print '%()j' <url>` (метаданные + caption). Сохранить в `lessons-tg-scraping.md` или `feedback_yt_dlp_ig_bypass.md`
3. **`.claude_temp_scripts/` gitignored по `core.md`** — локально доступно, в git нет. Артефакты сессии не пушатся. Уже зафиксировано в правилах, но напомнить: **если артефакт нужен в git — копировать вручную в нужную папку**
4. **Multi-agent на legal задачи: разделять по специализации, не по фазам.** 7 узких юристов (tax / banking / mortgage / 3 researcher / structuring) дали глубину выше чем 1 агент с 7 ролями. Каждый ~1500-2200 слов, суммарно 132K токенов
5. **`risk-manager` subagent_type иногда падает** (`API Error: socket connection closed unexpectedly`) — fallback на `general-purpose` с тем же промптом
6. **Сценарий «обеспеченный друг выкупает долг» — операционная стратегия для дел о развод+кредиты.** Структурно: pre-condition (раздел общих долгов с супругой) + цессия (ст.382-388 ГК + регистрация ЕГРН для ипотеки) + пост-цессионный сценарий (А/Б/В). Сохранить как reference-pattern для подобных случаев

## 🔜 Следующие шаги (приоритет)

1. **HIGH** (waiting Anton's go): Передать `LEGAL_BRIEF_for_lawyers.md` адвокатам Антона + ant-attorneys
2. **HIGH (immediate ROI):** Подать претензию на возврат страховки в Альфа-Банк — прецедент 503 901 ₽ (Researcher 1, кейс № 13). Альфа часто возвращает БЕЗ суда
3. **HIGH (срочно):** Закрыть 7-дневную просрочку на залоговом — иначе ст.213.10-1 ФЗ-127 (Путь Б) не применима
4. **MEDIUM:** Запросить у Альфы копию кредитного досье через адвоката — главный вопрос: **есть ли нотариальное согласие супруги?** От ответа зависит, активируется ли Путь В (сильнейший рычаг)
5. **MEDIUM:** Раздел общих долгов с супругой через брачный договор / соглашение — **БЛОКЕР** для любых будущих сделок (без него цессия ничтожна по ст.10 ГК)
6. **LOW:** Скопировать `LEGAL_BRIEF_for_lawyers.md` в `~/artvision-data/personal/divorce-alimony/legal-brief-credit-reels-2026-04-29.md` если хочется сохранить в git (с условием — это конфиденциальный документ, проверить что папка приватная)
7. **LOW:** Сохранить уроки 1-2 в memory как `reference_telethon_session.md` и `feedback_yt_dlp_ig_bypass.md`

## 🗺️ Карта файлов

```
~/.telegram_session.session              ← АВТОРИЗОВАННАЯ Telethon-сессия Antona

~/artvision-data/.claude_temp_scripts/credit-reels-2026-04-28/  ← 14 файлов, gitignored
├── LEGAL_BRIEF_for_lawyers.md           ← ГЛАВНЫЙ файл, 543 строки
├── FINAL_synthesis.md                   ← промежуточный
├── agent{1-10}*.md                      ← выходы 10 senior-агентов
├── swarm_input.md                       ← 11 reels с captions + 72 коммента
├── raw_messages.jsonl                   ← 3452 TG сообщения @avportal_bot DM
└── *.py                                 ← Python-скрипты для повторного запуска

~/artvision-data/personal/divorce-alimony/   ← КОНТЕКСТ Антона по кредитам
├── credits-summary.md
├── credit-relief-mechanisms-2026-04-21.md
└── legal-strategy.md

~/artvision-data/sync/recaps/bef5d1bd-3420-48cf-882d-bd9fb3c6ad0f.md  ← recap, в git
```

## ⚠️ Гачи

- **Артефакты в `.claude_temp_scripts/credit-reels-2026-04-28/` — gitignored.** Если будет cleanup или переустановка — потеряются. Если что-то важно сохранить — **скопировать в `personal/divorce-alimony/` явно**
- **`raw_messages.jsonl` содержит личные TG сообщения Антона** (3452 шт.) — НЕ копировать в публичные/клиентские папки. Это личные данные
- **`LEGAL_BRIEF_for_lawyers.md` содержит реквизиты кредитного договора** F0PM1020S24010900331 + расчёты НДФЛ + информацию о супруге — **конфиденциально**, не пушить публично, отправлять только адвокатам через защищённый канал
- **Все номера дел и письма Минфина в брифе** — приведены агентами на основе WebSearch. **Адвокаты обязаны верифицировать** через СПС перед использованием в процессе. Дисклеймер явный в § 12 документа
- **`risk-manager` subagent_type ломается** — для legal/risk анализа использовать `general-purpose` с детальным промптом
- **При повторном запуске Telethon-скриптов** (`scan_avportal.py`, `enrich_py.py`, `fetch_comments.py`) — sessions уже выгружены в .jsonl, можно фильтровать локально без перезапуска. Если нужен свежий scan — `python3 scan_avportal.py` обновит `raw_messages.jsonl`
- **Антон не любит «может быть»** — давать прямые ответы. На запросы «найди что-то скормленное» сначала проверять каналы; если нет — честно «нет данных», не выдумывать. (применил `feedback_no_smoothing.md`)

## 🔗 Связанные ресурсы

- Recap: `~/artvision-data/sync/recaps/bef5d1bd-3420-48cf-882d-bd9fb3c6ad0f.md`
- Контекст по кредитам: `~/artvision-data/personal/divorce-alimony/`
- Предыдущий handover: `~/.claude/handovers/HANDOVER-2026-04-28-1740-ops.md`
- Memory: `~/.claude/projects/-Users-antonk/memory/legal-divorce.md`
- Skill: `tg-chat-export` (если понадобится повторить Telethon-выгрузку)
- Правило: `~/.claude/CLAUDE.md` → `core.md` (про `.claude_temp_scripts/` gitignored)
