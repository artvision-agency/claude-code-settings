# Claude Memory — Artvision

## ГЛАВНАЯ ЦЕЛЬ: 2,000,000 RUB/month

**Установлена:** 2026-02-06
**Текущее состояние:** ~??? (нужно выяснить)
**Дедлайн:** не установлен, но чем быстрее тем лучше

### Два трека:
1. **Агентство Artvision** — увеличение чеков, upsell, новые клиенты
2. **Продукты/отдельно** — Structural Engineering, AI Vision, Портной, LoyalMed

### Команда:
- **Антон (Кирилл)** — owner, @antonkamer
- **Андрей Киселёв** — employee, @PandaCaffe

### Claude Max подписки (2026-02-16):
- **justtrance@gmail.com** — Антон, Max подписка, Claude Code + claude.ai
- **adw.artvision.pro@gmail.com** — Андрей, Max подписка, Claude Code + claude.ai
- Лимит сбрасывается в **3:00 MSK** (еженедельно)
- Если упёрся в лимит на одном аккаунте → переключиться на другой

### Обязательства Claude:
- Минимум 3 раза в день предлагать действия каждому (Asana чекбоксы)
- Всегда учитывать touchpoints с клиентами
- Sales plan через чекбоксы в Asana
- Задавать вопросы если что-то недодумано
- Итератор: не останавливаться пока цель не достигнута

### Подробности:
- См. `revenue-goal.md` — полная стратегия
- См. `client-revenue.md` — доходы по клиентам (после заполнения)

## Инфраструктура (обновлено 2026-02-17)

### VPS — ОДИН сервер в Amsterdam
- **IP:** 80.90.181.152
- **Расположение:** Amsterdam, NL (Timeweb nl-1)
- **Конфигурация:** 4 CPU / 8 GB RAM / 80 GB NVMe / 100 Mbit
- **Цена:** 1210 ₽/мес
- **Timeweb ID:** 6670871, name: artvision-main-nl
- **Credentials:** tokens.json → timeweb_cloud.vps
- **AI API:** работают НАПРЯМУЮ (EU IP), никаких прокси/туннелей не нужно
- **Claude Code:** работает напрямую, credentials в `/root/.claude/.credentials.json`
- **OpenClaw:** установлен но ВЫКЛЮЧЕН (systemctl disabled)

### Что работает на VPS:
- **PM2:** avportal-bot, smm-publish-api, claude-dispatcher
- **nginx:** kb.artvision.pro, reports.artvision.pro, reports-ip
- **cron:** git sync, SMM digest 4x/day, health check, log rotation
- **Claude Code v2.1.44** — Max подписка, напрямую без прокси

### История миграции (2026-02-17):
- **Было:** Novosibirsk VPS (109.71.242.6, 1210₽) + NL proxy (72.56.118.75, 510₽) = 1720₽
- **Стало:** Один NL сервер (80.90.181.152, 1210₽) = экономия 510₽/мес
- Старые серверы УДАЛЕНЫ (twc server remove)
- WARP бесполезен для обхода геоблока (выходит через RU PoP, loc=RU)

## Telegram — контакты и чаты
- **Бот:** @avportal_bot, token в .env
- **Группа команды:** "Стас и Антон и Андрей", chat_id: `-1003857976998`
- **Антон:** TG 161261562 (@AntonKamer), Claude justtrance@gmail.com, GitHub justtrance-web
- **Андрей:** TG 161261652, Claude adw.artvision.pro@gmail.com, GitHub justtrance-web (общий)
- **Стас:** TG 356640470 (@StasMura), GitHub Stanislav2014

## Ключевые файлы проекта
- `/Users/antonk/artvision-data/` — основной репо
- `products/ROADMAP-2026-Q1.md` — 4 продукта, цель 2.3M к дек 2026
- `schedule/reports-invoices.json` — расписание отчётов/счетов
- `processes.md` — все процессы

## Правила агентов

### Модели — дефолт (2026-02-20)
- **Основная сессия = Opus** (прописан в `~/.claude/settings.json`: `"model": "claude-opus-4-6"`)
- **Субагенты = Opus** по умолчанию
- **Sonnet** — если задача явно простая/быстрая (парсинг, поиск, утилиты)
- **Haiku = ЗАПРЕЩЁН полностью**

## Уроки → см. `lessons.md`

Краткий индекс (полные описания в `lessons.md`):
- Рабочий процесс: sync, короткие команды, не игнорировать просьбы, patches
- Данные: верификация обязательна, Яндекс=API, SEO pipeline, тексты=Claude Code
- Frontend: HTML валидация=DOM, попапы=popup-cro скилл, КП=бренд клиента
- Инфра: VPS миграция, MODX emoji, деплой КП, интернет диагностика
- Инструменты: Handy, screen-shot.xyz, react-best-practices, FTP curl
