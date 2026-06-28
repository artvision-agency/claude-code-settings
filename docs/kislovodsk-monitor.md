# Монитор безопасности Кисловодска (КМВ) — справка

## Что это
- Личный мониторинг риска БПЛА/воздушной тревоги для поездки в Кисловодск (КМВ)
  и по ж/д-маршруту СПб → Кисловодск через Ростовскую обл.
- Источник: публичные TG-каналы оповещения (через Telethon, userbot-сессия @AntonKamer).
- Получатель: DM Антона (chat_id `161261562`) через Bot API.
- Эвристика по сводкам каналов — НЕ гарантия. Сверять с официальным (губернатор
  @VVV5807 / МЧС / SMS-оповещение).

## 2 компонента
- **Дайджест** — `kislovodsk-safety-digest.py`
  - Раз в сутки в **08:30** (LaunchAgent `pro.artvision.kislovodsk-safety`).
  - Обзор за последние 24ч по КМВ + маршрут + аэропорт Минводы.
  - Шлёт карту-картинку (если есть точки) + текст. Общий уровень = худший из зон.
- **Real-time алерт** — `kislovodsk-realtime-alert.py`
  - Каждые **30 мин** (LaunchAgent `pro.artvision.kislovodsk-alert`, StartInterval 1800).
  - Ловит ТОЛЬКО новые сигналы за окно ~10 мин (`ALERT_WINDOW_MIN`) из быстрых каналов.
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
- **Не алертить**: «отбой» (`ALLCLEAR` — снятие угрозы), «удар»/«атака» без БПЛА-слов
  (шумные: «удар по воротам») — НЕ триггеры.
- В дайджесте per-message: `level = red if (БПЛА-триггер AND KMV_CITY) else yellow`;
  агрегация зоны — `zone_summary()` (🔴 если есть red, иначе 🟡, иначе 🟢).

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

## Как сменить интервал / тюнить пороги
- **Интервал real-time**: `StartInterval` в `pro.artvision.kislovodsk-alert.plist`
  (сек; сейчас 1800 = 30 мин). После правки: `launchctl unload <plist> && launchctl load <plist>`.
- **Время дайджеста**: `StartCalendarInterval` (Hour/Minute) в `…-safety.plist`.
- **Окно свежести сигнала**: `ALERT_WINDOW_MIN` в `kislovodsk-realtime-alert.py` (мин).
- **Сколько сообщений тянуть**: `READ_LIMIT` (alert) / `limit=80` (digest).
- **Словари триггеров/городов**: `DRONE`, `AIRRAID`, `KMV_CITY`, `ROUTE_LOC`, `ALLCLEAR`
  в обоих скриптах. После правки — прогнать `qa-kislovodsk.sh` (тесты ловят регресс).
- **Добавить канал**: дописать в `CHANNELS` (digest) / `FAST_CHANNELS` (alert).

## Troubleshooting
- **`portal_bot` 401 Unauthorized** → отправка перебирает ботов по `BOT_PREF`
  (`vps_bot` → `portal_bot` → `backup_bot`); `vps_bot` подтверждённо DM-ит Антона.
  Если все боты молчат — последний фолбэк `tg-send.sh` (digest). Токены — из tokens.json.
- **Telethon `TypeNotFound` / транзиентные сбои канала** → ловятся per-канал, job не
  падает целиком; недоступные источники → пометка «данные частичные».
- **NO_SESSION** → нет рабочей session-копии. Источник копии: основная
  `telethon_session.session` (или копия дайджеста для alert). Auth тот же userbot.
- **Сессия .session должна быть 0600** (SQLite с авторизацией) — скрипты сами chmod.
- **Секреты НЕ в коде** (файлы синкаются в публичный repo): `api_id`/`api_hash` и
  bot-токены читаются из `~/artvision-data/tokens.json` в рантайме (self-corrections #31).

## Пути
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
- Дедуп-файл: `~/.claude/state/kislovodsk-alert-seen.json`
