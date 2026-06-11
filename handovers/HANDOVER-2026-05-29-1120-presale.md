# Handover: Avto.World CTO Expo PPC + бот-проверщик показов + Codex fix

**Дата:** 2026-05-29 11:20 MSK
**Контекст:** presale/ads (clients/avtoworld)
**Сессия:** PPC: AVTO.WORLD (4ce39641 → dae365de)
**Статус:** в работе (2 РК запущены; бот построен; goal #2 не дописан)

## 🎯 Цель сессии
Запустить ретаргет Я.Директ для Avto.World на выставку CTO Expo (28-29.05), затем построить бота-проверщика показов + максимальную диагностику «реклама ВКЛ/ВЫКЛ».

## ✅ Что сделано
- **2 РК в Я.Директе** (кабинет avprocontext, все объявления ACCEPTED+ON):
  - `710254277` — ретаргет РСЯ, группа 5755191065, 5 баннеров, условие = сегмент Метрики «Все пользователи» 1008001087 (WARM). Бюджет 5000₽/сут (WeeklySpendLimit 35000).
  - `710291086` — РСЯ по ключам выставки, группа 5755593778, 3 баннера, 10 ключей. Бюджет 1000₽/сут. StartDate 29.05 (28.05 сервер отклонил «дата в прошлом»).
  - **Показы = 0** (Reports API): причина не техника (всё одобрено), а узкая аудитория + выставка фактически кончается 29.05.
- **Баннеры:** 5 V2 real-brand (4:3 1080×810, не сплющены, QA-команда подтвердила). Галерея live: https://artvision.pro/preview/avtoworld-cto-expo/
- **Бот-проверщик** `scripts/ads_show_verifier.py` + `scripts/ads_verifier_config.json` — статус РК/объявлений + показы (Reports) + строгая кросс-проверка «кабинет декларирует показы, а факт 0» + хеш креативов + флаг обрезки форматов.
- **Автозапуск:** `~/.claude/scripts/ads-verify-runner.sh` + LaunchAgent `pro.artvision.ads-verify.plist` (09:30/13:00/17:00/20:30, --tg алёрт + HTML). Загружен, тест end-to-end прошёл (TG-алёрт ушёл).
- **Правило** `~/artvision-data/.claude/rules/yandex-direct-creatives.md` — форматы РСЯ (4:3 валиден!) + урок про мигающий API.
- **Скилл** `/ads-max` — реклама в Max через Я.Директ (данные eLama) + routing + memory.
- **Форк sukharev_ii** (Task #3): di-sukharev → 5 репо в artvision-agency (opencommit 7.3K, AI-TDD, vibe, devil, pipepiper). В external-tools-catalog Wave 5.
- **Codex починен:** был битый бинарь @openai/codex (ENOENT нативного arm64), `npm i -g @openai/codex@latest` → 0.135.0, smoke CODEX_OK. Плагин codex:codex-rescue рабочий.
- **Рефакторинг:** clients/avtoworld/ads/cto-expo-2026/ — 13 папок баннеров → 5 + _archive/, README-карта, мёртвый launch_avtoworld.py в архив.

## 🧠 Решения и ПОЧЕМУ

| Решение | Альтернатива | Почему |
|---------|--------------|--------|
| Запуск через свежий субагент при мигающем API | долбить из основного процесса | API v5 отдавал error 1000 ~1 из 20-40; субагент ловил окно с 1й попытки, основной — 150 попыток мимо |
| Reports API для показов | ads/get | ads/get мигает жёстко, Reports проходит стабильно |
| 4:3 баннеры оставить | пересобирать в 1:1/16:9 | офсправка Яндекса: 4:3 валиден для РСЯ (PPC-субагент ошибочно сказал что нет) |
| Бот = «строгий сеньор» | просто статус из кабинета | кабинет пишет «идут показы» при 0 impressions — ловим это противоречие |
| Codex reinstall | codex login (re-auth) | корень был не auth (он сам обновился), а отсутствующий нативный бинарь |

## ❌ Что НЕ сделано
- **Task #2 (goal max-диагностика ВКЛ/ВЫКЛ)** — goal-файл создан (`goals/GOAL_ads-onoff-max-diagnostic_2026-05-29.md`), код в ads_show_verifier.py НЕ дописан. Нужно добавить: баланс кабинета (v4 AccountManagement — работает всегда), StatusPayment, срок кампании (EndDate), бюджет-исчерпание, статус условий таргета, явный вердикт ВКЛ/ВЫКЛ на кампанию + понизить severity «API недоступен» (не CRITICAL, не спамить).
- **Task #4 (SessionStart-хук task-list)** — Антон: «todo/task=словарь, хук при начале сессии, обновляемый список». Не начато (инфра).
- **Хвосты Avto.World** (в LAUNCH-SPEC.md): карта стенда 13-713.1 на баннер, лого CTO Expo, промокод EXCTECL vs CROCUSCTOY уточнить у Феди, visitors_v2 мутный (убрать?).

## 📚 Уроки
- Мигающий API Я.Директ v5 → свежий субагент, не долбёж (записано в yandex-direct-creatives.md)
- Codex битый бинарь = npm reinstall, не re-auth
- Выставочные РК поднимать ДО старта выставки (подняли в последний день — окно <суток)

## 🔜 Следующие шаги
1. **HIGH:** дописать Task #2 — max-диагностика ВКЛ/ВЫКЛ в `scripts/ads_show_verifier.py` (можно через codex:codex-rescue — он теперь работает). Goal: `goals/GOAL_ads-onoff-max-diagnostic_2026-05-29.md`
2. MEDIUM: коммит всех изменений сессии (ads_show_verifier, runner, plist, /ads-max skill, catalog Wave5, рефакторинг cto-expo, goal-файлы, yandex-direct-creatives)
3. MEDIUM: Task #4 — SessionStart task-list хук
4. LOW: хвосты баннеров (карта стенда, лого выставки)

## 🗺️ Карта файлов
```
clients/avtoworld/ads/cto-expo-2026/
├── LAUNCH-SPEC.md        ← параметры + хвосты
├── README.md             ← карта папки + хеши баннеров
├── api-created-ids.json  ← все ID (кампании/группы/баннеры/сегменты)
├── assets/banners-v2-real-brand/ ← 5 баннеров В ПОКАЗЕ
└── _archive/             ← черновики
scripts/ads_show_verifier.py   ← бот (Task #2 дописать)
scripts/ads_verifier_config.json
~/.claude/scripts/ads-verify-runner.sh + LaunchAgent pro.artvision.ads-verify
goals/GOAL_ads-onoff-max-diagnostic_2026-05-29.md
.claude/rules/yandex-direct-creatives.md ← правило + уроки
```

## ⚠️ Гачи
- API Я.Директ v5 мигает (error 1000) — статусы читать через свежий субагент, не из основного процесса
- Reports API стабильнее ads/get для показов
- avprocontext = НАШ кабинет (не Феди); пароля для UI нет, только API-токен в tokens.json
- Выставка CTO Expo = домен **cto-expo.ru** (латиницей CTO, не sto-expo)
- Контекст сессии был колоссальный → этот handover для чистого старта

## 🔗 Связанные
- Goal-файлы: goals/GOAL_ads-show-verifier-bot_2026-05-29.md + GOAL_ads-onoff-max-diagnostic_2026-05-29.md
- Память: reference_yandex_direct_max_ads.md
- Галерея: https://artvision.pro/preview/avtoworld-cto-expo/
