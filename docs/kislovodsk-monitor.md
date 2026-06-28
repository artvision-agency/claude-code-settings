# Монитор безопасности Кисловодска (КМВ) — справка

## Что это
- Личный мониторинг риска БПЛА/воздушной тревоги для поездки в Кисловодск (КМВ)
  и по ж/д-маршруту СПб → Кисловодск через Ростовскую обл.
- Источник: публичные TG-каналы оповещения (через Telethon, userbot-сессия @AntonKamer).
- Получатель: DM Антона (chat_id `161261562`) через Bot API.
- Эвристика по сводкам каналов — НЕ гарантия. Сверять с официальным (губернатор
  @VVV5807 / МЧС / SMS-оповещение).

## Архитектура (3 модуля)
- **`kislovodsk_common.py`** — общий модуль (импортируется обоими скриптами):
  словари триггеров/городов (`DRONE/AIRRAID/PRIMARY/IMPACT/KMV_CITY/KMV_LOC/
  ROUTE_LOC/TRANSPORT/DISRUPT`), `is_allclear()`/`near()`/`has()`/`normalize_snippet()`/
  `tg_link()`, гео (`COORDS/PLACE_KEYS/detect_places()/collect_points()`), Telegram-
  отправка (`_bot_token/send_tg/send_photo/render_map/dispatch_with_map`), session-
  хелперы (`telethon_creds/ensure_session_copy/authorized_client`). Импорт сети НЕ делает.
  - Словари — КОНСОЛИДИРОВАННЫЙ superset: `DRONE` без бесплатного «дрон» (защита
    real-time от false-🔴 на «квадродрон»), `AIRRAID/KMV_LOC/ROUTE_LOC` — объединение.
- В скриптах остаётся ТОЛЬКО оркестрация (список каналов, своя `classify_*`, сборка,
  какой state/session/log).

## 2 компонента (оркестрация)
- **Дайджест** — `kislovodsk-safety-digest.py`
  - Раз в сутки в **08:30** (LaunchAgent `pro.artvision.kislovodsk-safety`).
  - Обзор за последние 24ч по КМВ + маршрут + аэропорт Минводы (окно 24ч считается
    ВНУТРИ `collect()`, не при импорте).
  - `classify_digest_message(zone, text)` — чистая, тестируемая. Отсекает «отбой»,
    аэропорт-события маркирует зоной `kmv`, 🔴 требует триггер РЯДОМ с городом.
  - Шлёт карту-картинку (если есть точки) + текст. Общий уровень = худший из зон.
- **Real-time алерт** — `kislovodsk-realtime-alert.py`
  - Каждые **30 мин** (LaunchAgent `pro.artvision.kislovodsk-alert`, StartInterval 1800).
  - НОВИЗНА = строго по watermark (`id > watermark`), НЕ по возрасту. Возраст — лишь
    soft-cap `MAX_AGE_HOURS=6` (не алертить совсем древние на первом прогоне; буфер ≥
    интервала). Раньше жёсткое окно 10 мин при интервале 30 мин теряло сообщения.
  - `classify_realtime(text)` — 🔴 ТОЛЬКО при явном КМВ-городе + триггере.
  - Доступ к state защищён fcntl-локом (overlap прогонов → дубли/потеря watermark).
  - Мгновенный пуш ТОЛЬКО на 🔴 (см. логику уровней).

## Источники (TG-каналы)
- Официальный: `VVV5807` (губернатор Ставрополья — приоритет/достоверность).
- Локальные КМВ: `moy_kislovodsk`, `Kislovodsx7`, `MinVody_Life_1`, `MinvodyOnline`,
  `mvairport`, `stav_kray`, `minvody26`.
- Нац. агрегаторы БПЛА (фильтр по зоне): `radarrussiia`, `astrapress`, `SHOT_SHOT`,
  `exilenova_plus`, `rybar`, `bazabazon`, `kavkaz_leakbez`.
- Зона канала: `kmv` | `route` | `both` (both сканируется по обеим зонам).

## Логика уровней
- **🔴 (real-time пуш)** — ТОЛЬКО при ЯВНОМ городе-курорте КМВ + триггер БПЛА.
  - `KMV_CITY` = кисловодск, минеральн, минвод, ессентук, пятигорск, железноводск.
  - Триггер `PRIMARY` = слова БПЛА (`DRONE`) + воздушной тревоги (`AIRRAID`).
- **🟡 (только в дайджесте, НЕ мгновенно)** — общекраевое (Ставропольский край без
  города), маршрутные города (Ростов/Тихорецк/Невинномысск…), сбои транспорта.
- **🟢** — тихо, значимых сообщений нет.
- **Не алертить**: «отбой» (`is_allclear()` — regex по «отбой … опасности/тревоги»,
  «опасность/угроза миновала»; НЕ ловит «угроза МИНеральным Водам» как раньше
  substring `ALLCLEAR`), «удар»/«атака» без БПЛА-слов («удар по воротам») — НЕ триггеры.
- В дайджесте per-message: `red если (БПЛА-триггер AND KMV_CITY AND триггер в ≤80 симв.
  от города)`, иначе `yellow`; «отбой» отсекается целиком; аэропорт-события → зона `kmv`.
  Агрегация зоны — `zone_summary()` (🔴 если есть red, иначе 🟡, иначе 🟢).

## Карта + ссылки
- Карта OSM (staticmap) с пинами городов: 🔴 КМВ, 🟠 маршрут, 🔵 опорный Кисловодск.
- Координаты `COORDS` ЗАПЕЧЕНЫ (геокод Nominatim один раз 28.06.2026, sanity-сверка
  lat 43..49 / lon 38..45) — в рантайме за геокодом в сеть НЕ ходим.
- Города на пине определяются `detect_places()` (детерминированно, по ключевым словам;
  «ставропольского края» НЕ ставит пин города Ставрополь).
- В каждом сообщении — кликабельная ссылка `https://t.me/<channel>/<msg_id>`.
- Карта не отрисовалась / нет staticmap → фолбэк на текст без карты (не падаем).

## Дедуп (anti-spam, только real-time)
- State-файл `~/.claude/state/kislovodsk-alert-seen.json`:
  - `watermark` — high-water-mark `message.id` по каждому каналу;
  - `incidents` — sha1-хеши уже отправленных инцидентов (хранится последние ~800).
- Watermark двигается за неотправленные матчи только ПОСЛЕ успешной отправки (retry
  при сбое отправки в следующий запуск). Один инцидент = один пуш.
- Доступ к state защищён fcntl-локом `…-seen.json.lock` (эксклюзивный неблокирующий
  на весь прогон): overlap двух launchd-прогонов → второй выходит тихо (нет гонки,
  дублей, потери watermark).

## Как сменить интервал / тюнить пороги
- **Интервал real-time**: `StartInterval` в `pro.artvision.kislovodsk-alert.plist`
  (сек; сейчас 1800 = 30 мин). После правки: `launchctl unload <plist> && launchctl load <plist>`.
- **Время дайджеста**: `StartCalendarInterval` (Hour/Minute) в `…-safety.plist`.
- **Soft-cap возраста сигнала**: `MAX_AGE_HOURS` в `kislovodsk-realtime-alert.py` (ч;
  только чтобы не алертить совсем древнее на первом прогоне — новизна по watermark).
- **Сколько сообщений тянуть**: `READ_LIMIT` (alert) / `limit=80` (digest).
- **Словари триггеров/городов**: `DRONE`, `AIRRAID`, `KMV_CITY`, `KMV_LOC`, `ROUTE_LOC`,
  `is_allclear()` — в **`kislovodsk_common.py`** (один источник для обоих скриптов).
  После правки — прогнать `qa-kislovodsk.sh` (тесты ловят регресс).
- **Добавить канал**: дописать в `CHANNELS` (digest) / `FAST_CHANNELS` (alert).

## Troubleshooting
- **`portal_bot` 401 Unauthorized** → отправка перебирает ботов по `BOT_PREF`
  (`vps_bot` → `portal_bot` → `backup_bot`); `vps_bot` подтверждённо DM-ит Антона.
  Если все боты молчат — последний фолбэк `tg-send.sh` (digest). Токены — из tokens.json.
- **Telethon `TypeNotFound` / транзиентные сбои канала** → ловятся per-канал, job не
  падает целиком; недоступные источники → пометка «данные частичные».
- **NO_SESSION** → нет рабочей session-копии. Источник копии: основная
  `telethon_session.session` (или копия дайджеста для alert). Auth тот же userbot.
- **Сессия .session должна быть 0600** (SQLite с авторизацией) — `ensure_session_copy()`
  сам chmod 600 И рабочую копию, И исходную `telethon_session.session` (раньше она
  оставалась world-readable 0644).
- **Секреты НЕ в коде** (файлы синкаются в публичный repo): `api_id`/`api_hash` и
  bot-токены читаются из `~/artvision-data/tokens.json` в рантайме (self-corrections #31).

## Пути
- Общий модуль: `~/.claude/scripts/kislovodsk_common.py`
- Скрипты: `~/.claude/scripts/kislovodsk-safety-digest.py`,
  `~/.claude/scripts/kislovodsk-realtime-alert.py`
- Тесты: `~/.claude/scripts/tests/test_kislovodsk_monitor.py`
- Verify-gate: `~/.claude/scripts/qa-kislovodsk.sh`
- Плисты: `~/Library/LaunchAgents/pro.artvision.kislovodsk-safety.plist` (08:30),
  `~/Library/LaunchAgents/pro.artvision.kislovodsk-alert.plist` (30 мин)
- Логи: `~/.claude/logs/kislovodsk-safety.log`, `~/.claude/logs/kislovodsk-alert.log`
  (+ `.out.log` / `.err.log` от launchd)
- Telethon-сессии: `~/.claude/state/telethon_kislovodsk.session` (digest),
  `~/.claude/state/telethon_kislovodsk_rt.session` (alert)
- Дедуп-файл: `~/.claude/state/kislovodsk-alert-seen.json` (+ `.lock` для fcntl)
