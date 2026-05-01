# Handover: HH-Recruiter — каркас + переезд в новую сессию

**Дата:** 2026-05-01 19:58
**Контекст:** ops (продукт `products/hh-recruiter/`)
**Статус:** 🟡 в работе, перенос в другую сессию по решению Антона
**Текущая сессия:** ceca35be... (resumed)
**Связанная сессия:** f7f2c961 (hh-leadgen восстановление, закрыта 01.05 утром)

## 🎯 Цель

Создать TG-бот HH-Recruiter для Творим Совершенство (LPR Вероника Губина): мониторинг свежих резюме на hh.ru + отправка откликов прямо из Telegram.

## ✅ Что сделано в этой сессии

- **decision-doc:** `decisions/2026-05-01-hh-recruiter-tvorim.md` — feasibility, 3 варианта реализации, UX-флоу 6 шагов FSM, двухслойный фильтр (hard HH params + soft Claude Haiku), карточка резюме
- **TODO.md** — 5 задач #9-13 для hh-recruiter, все актуализированы
- **TaskCreate** в текущей сессии:
  - #9 feasibility-doc — completed
  - #11 интервью Вероники (через Антона) — completed
  - #10 подача второго HH-app — pending
  - #12 реализация бота — in_progress (только CLAUDE.md создан)
  - #13 пилот 30 дней — pending
- **products/hh-recruiter/CLAUDE.md** — правила проекта, архитектура, отличия от hh-leadgen, file structure plan
- **Git коммиты** в `feat/ops-crm-v1`:
  - `67abff7bd` — hh-recruiter: контакт LPR — Вероника, не Ирина
  - `890690a86` — интервью Вероники closed → финальный UX (без Mini App)
  - `94e523f27` — hh-recruiter: каркас CLAUDE.md

## 🧠 Решения и ПОЧЕМУ (важно для новой сессии)

| Решение | Почему |
|---------|--------|
| Контакт LPR = Вероника Губина (НЕ Ирина) | Ирина — операционка. Решения по подписке hh.ru и найму спецов — за владельцем-врачом Вероникой. Источник: `clients/tvorimsovershenstvo/CLAUDE.md` |
| Творим = стоматклиника (не бьюти-салон) | Спецы: стоматолог-терапевт, ортопед, хирург-имплантолог, гигиенист, ассистент. Не «стилист/барбер/маникюр» — это была ошибка в первом черновике |
| БЕЗ Telegram Mini App | Решение Антона 01.05. Только обычные TG inline-кнопки + текстовый ввод. Стек: aiogram 3 FSM + InlineKeyboardMarkup |
| Двухслойный фильтр (hard + soft) | Hard через HH search params отсекает 80% нерелевантных. Soft через Claude Haiku оценивает свободные комментарии Вероники («опыт с Trios», «без перерывов»). ~$30/мес LLM gypothesis при 50 резюме/день |
| Идём по варианту A (полный API) | Вероника готова платить hh.ru подписку 10-30K/мес → доступ к /resumes и /negotiations |
| ОТКРЫТЫЙ ВОПРОС: новый app vs расширение существующего | См. ниже Open questions |

## ❌ Что НЕ сделано

- **Каркас бота `src/*.py`** — НЕ начат (только CLAUDE.md). Стоп пришёл когда начал.
- **Подача второго HH-app** — Антон должен сделать, не делал
- **Текст обращения в HH-support** на расширение #20952 — НЕ написал (открытый вопрос)
- **Проверка подписки Творим на hh.ru** — нужен login Творим как employer'а, не имеется

## 🔜 Следующие шаги (приоритет для новой сессии)

### HIGH

1. **Антон решает: новый HH-app или расширение #20952?** Это блокер всей реализации.
   - Вариант 1: Подать новый app на dev.hh.ru/admin — описание готово в `decisions/2026-05-01-hh-recruiter-tvorim.md` секция «Описание для модерации (вариант A)». Срок 3-15 дней.
   - Вариант 2: Написать HH-support (api@hh.ru или через форму) запрос на расширение scope #20952 на `resume:read + negotiations:write`. Текст обращения нужно написать.
   - Рекомендовано: оба пути параллельно — что одобрят первым.
2. **Каркас бота** — создать `src/main.py`, `src/bot.py`, `src/fsm.py`, `src/handlers.py`, `src/db.py`, `src/hh_api.py`, `src/scoring.py`, `src/notifier.py`, `src/templates.py`, `src/oauth.py`, `config.yaml`, `requirements.txt`, `.env.example`. Файловая структура — в `products/hh-recruiter/CLAUDE.md`.

### MEDIUM

3. **Узнать у Вероники доуточнения** — топ-3 спеца к мониторингу (хирург и ортопед уже названы, нужен 3-й), детали по ЗП-диапазонам.
4. **Проверить подписку Творим на hh.ru как employer'а** — Антону зайти в личный кабинет работодателя Творим. Если есть — указать тариф, если нет — оформить.
5. **Задеплоить каркас на VPS** `/opt/hh-recruiter/` (по аналогии с `hh-leadgen`).

### LOW

6. Создать systemd-юниты `hh-recruiter-bot.service` + `hh-recruiter-poll.timer` + `hh-recruiter-digest.timer`.

## 🗺️ Карта файлов

```
artvision-data/
├── products/hh-recruiter/             ← новый продукт (создан 01.05)
│   ├── CLAUDE.md                      ← правила, архитектура, file structure
│   ├── src/                           ← пусто (каркас не начат)
│   ├── tests/                         ← пусто
│   └── scripts/                       ← пусто
├── products/hh-leadgen/                ← рабочий, восстановлен 01.05 (refer)
│   ├── src/collectors/hh.py           ← пример обёртки HH API + кеш токена
│   ├── src/notifier.py                ← пример TG-нотификатора
│   ├── src/db.py                      ← пример SQLAlchemy моделей
│   └── ...                            ← вся структура — образец
├── decisions/2026-05-01-hh-recruiter-tvorim.md  ← КЛЮЧЕВОЙ файл, читать ПЕРВЫМ
├── clients/tvorimsovershenstvo/CLAUDE.md         ← контакты клиента, бренд
├── tokens.json                                   ← hh_api ключ (текущий app #20952)
└── TODO.md                                       ← блок hh-recruiter — задачи #10, #12, #13 pending

VPS root@80.90.181.152:
└── /opt/hh-recruiter/                 ← НЕ создано ещё, на следующей сессии
```

## ⚠️ Гачи

- **HH API для employer-методов (/resumes, /negotiations) ТРЕБУЕТ платной подписки работодателя** — у hh.ru. Без подписки 403. Источник: `https://github.com/hhru/api/blob/master/docs/employer_resumes.md`
- **HH client_credentials = ОДИН long-lived токен** — повторный grant возвращает 403 «app token refresh too early». См. `~/.claude/projects/-Users-antonk/memory/feedback_hh_api_long_lived_token.md`. Кешировать в env как сделано в hh-leadgen.
- **Творим — стоматклиника**, не бьюти-салон. Спецы: стоматолог/ортопед/гигиенист/ассистент. НЕ стилист/барбер/маникюр.
- **Контакт по проекту = Вероника Губина (LPR/владелец-врач)**, НЕ Ирина (операционка)
- **Бот без Telegram Mini App** — только inline-кнопки + текст
- **VPS `80.90.181.152`** — наш Artvision VPS (не путать с `147.45.232.226` старая)

## 🔗 Связанные ресурсы

- Recap текущей сессии: `~/artvision-data/sync/recaps/f7f2c961-04db-4e0a-a1d0-b11a1f43eed3.md` (старый, hh-leadgen)
- Decision-doc: `~/artvision-data/decisions/2026-05-01-hh-recruiter-tvorim.md` ← главный
- Client context: `~/artvision-data/clients/tvorimsovershenstvo/CLAUDE.md`
- TODO блок hh-recruiter: `~/artvision-data/TODO.md` (задачи #9-13 в section «✅ DONE 2026-05-01» + новые блоки)
- HH-leadgen handover (предыдущая сессия): `~/.claude/handovers/HANDOVER-2026-04-29-0215-ops-hh-leadgen.md`
- HH official docs: https://github.com/hhru/api/blob/master/docs/employer_resumes.md, https://github.com/hhru/api/blob/master/docs/employer_negotiations.md

## Стартовый промпт для новой сессии

```
Продолжаю работу над HH-Recruiter (бот для Вероники Творим, мониторинг резюме hh.ru).

Прочитай:
1. ~/.claude/handovers/HANDOVER-2026-05-01-1958-ops-hh-recruiter.md
2. ~/artvision-data/decisions/2026-05-01-hh-recruiter-tvorim.md  
3. ~/artvision-data/products/hh-recruiter/CLAUDE.md

Текущий блокер: решение Антона по HH-app (новый vs расширение #20952).
Что делать дальше: либо текст обращения в HH-support, либо каркас бота, либо оба.
```
