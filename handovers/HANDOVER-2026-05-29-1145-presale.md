# Handover: Avto.World PPC (2 РК) + бот-проверщик + авто-план параллели + Codex/форки

**Дата:** 2026-05-29 11:45 MSK · **Контекст:** presale/ads + infra · **Статус:** завершено (1 пункт ждёт 13:00)

## 🎯 Цель
Запустить рекламу Avto.World на CTO Expo, построить бота-проверщика показов, сделать чтобы план задач с параллелью включался АВТОМАТИЧЕСКИ в каждой сессии.

## ✅ Сделано
- 2 РК Я.Директ (avprocontext, 8/8 объявлений ACCEPTED+ON): `710254277` ретаргет РСЯ (сегмент «Все пользователи» 1008001087, 5000₽/сут) + `710291086` РСЯ ключи-выставка (10 ключей, 1000₽/сут). Показы 0 — узкая аудитория + выставка кончается 29.05.
- Бот `scripts/ads_show_verifier.py` — max-диагностика ВКЛ/ВЫКЛ (баланс v4 + StatusPayment + EndDate + статус + условия + Reports + вердикт 🟢/🟡/🔴 + строгая кросс-проверка «кабинет врёт о показах» + APIDOWN не спамит). Конфиг ads_verifier_config.json.
- Автозапуск: LaunchAgent `pro.artvision.ads-verify` (09:30/13:00/17:00/20:30) → runner → PPC-чат + HTML.
- PPC-чат `-4564169720` «AV: Контекстная, Аналитика, PPC» → канал `ppc` в tg-send.sh, бот шлёт туда.
- АВТО-ПЛАН ПАРАЛЛЕЛИ: SessionStart-хук start-parallel-plan-reminder.sh + UserPromptSubmit prompt-parallel-orchestration-detect.sh + правило parallel-task-orchestration.md (+копия в artvision-data). Зарегистрированы в settings.json (backup), 3/3 теста.
- Codex починен: npm i -g @openai/codex@latest → 0.135.0, CODEX_OK. Работает через ChatGPT OAuth (НЕ OpenRouter).
- Форк di-sukharev: 5 репо в artvision-agency (opencommit/AI-TDD/vibe/devil/pipepiper), Wave5 каталог.
- /ads-max скилл (реклама в Max). Рефакторинг cto-expo 13→5 папок.

## 🧠 Решения
- Авто-план = ХУКИ не только правило (Антон: «не хочу просить про todo» → md не срабатывает сам)
- Свежий субагент при мигающем API (ловит окно с 1й попытки)
- Бот → PPC-чат не ЛК (команда там: Антон/Андрей/Дима)
- Codex = reinstall битого бинаря, не re-auth

## ❌ Ждёт
- HTML-отчёт проверщика в PPC-чат — окно API Яндекса (автозапуск 13:00 сам пришлёт в -4564169720)
- Хвосты баннеров (карта стенда/лого CTO Expo/промокод) — LAUNCH-SPEC.md
- visitors_v2 мутный — решение Антона убрать ли

## 📚 Уроки
- Мигающий API v5 → свежий субагент · Codex битый бинарь = reinstall · Telethon py3.14 = asyncio.run · Антон не хочет просить todo → авто-хуки

## 🔜 Дальше
1. Проверить хуки на старте чистой сессии (авто-план появляется)
2. К 13:00 — PPC-отчёт пришёл в -4564169720?
3. LOW: хвосты баннеров

## ⚠️ Гачи
- API v5 мигает → субагент, Reports стабильнее · Хуки активны СО СЛЕДУЮЩЕЙ сессии · PPC=-4564169720 канал ppc · avprocontext наш кабинет, Telethon-сессия ЖИВА (AntonKamer) · контекст колоссальный

## 🔗 Связанные
Предыдущий: HANDOVER-2026-05-29-1120-presale.md · goals/GOAL_ads-*.md (3) · галерея artvision.pro/preview/avtoworld-cto-expo/
