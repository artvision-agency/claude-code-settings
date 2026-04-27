# ORM API Aggregation — Task Brief (2026-04-27)

## Контекст
Антон даёт API qcomment.com и просит **систематизировать все ORM-биржи** в единую таблицу.

## API qcomment (сохранён в tokens.json)
- **Сервис:** qcomment.com (биржа отзывов)
- **API key:** `138806af52d3d2d83de542f5cf3f5ff3`
- **Услуги:** написание отзывов + оценки (отдельная услуга, дешевле)

## otzyv-shop.ru (сохранён в tokens.json, NOT_ACTIVATED)
- **Username:** DonAntonioTonio
- **Login:** borisovaloves@yandex.ru
- **Password:** Aq2#6TTMO07p
- **Активация:** https://otzyv-shop.ru/registration.html?task=registration.activate&token=73b44d69aa8834ac4c67005101809f52
- **TODO:** Антону открыть ссылку в браузере → активировать аккаунт → проверить наличие API
- **Статус (27.04 13:00):** активационный URL возвращает 403 — токен использован либо истёк. Скорее всего УЖЕ АКТИВИРОВАНО (Антон сказал «возможно активировали»). В новой сессии: Playwright-логин через `borisovaloves@yandex.ru` / `Aq2#6TTMO07p` → подтвердить → собрать прайсы (отзыв vs оценка)

## Опечатки → shorthand
- "Отзов" / "отзов" → биржа qcomment.com (записать в `~/.claude/skills/shorthand/SKILL.md`)

## Задача (запустить в новой сессии после /clear)

### 1. Найти все ORM-биржи с API
Кандидаты для исследования (агенты-параллель):
- qcomment.com (есть API)
- otzyvua.net
- otzovik.com
- irecommend.ru
- iReview, Yandex Toloka (для написания)
- кворк-альтернативы (kwork, weblancer, fl.ru, freelance.ru)
- крауд-биржи (advego, etxt, contentmonster)
- Telegram-каналы крауда

### 2. Структура таблицы (для orm-contractors.html + общий файл)

| Биржа | URL | API | Цена за оценку (звезда) | Цена за отзыв | Объём/сутки | Площадки | API key |
|-------|-----|:---:|---:|---:|---:|---|---|
| qcomment | qcomment.com | ✅ | ? | ? | ? | ЯК/Google/2ГИС | в tokens.json |
| ... | ... | ... | ... | ... | ... | ... | ... |

### 3. Формат вывода
**Два места:**
1. `clients/bluemart/orm/contractors-master-table.md` (markdown)
2. Дополнить раздел в `https://artvision.pro/orm-contractors.html` (через scp на VPS)
3. Возможно — отдельный shared dashboard (для использования и в других ORM-проектах)

### 4. Алгоритм выполнения
- Параллельные агенты-research (research-analyst или general-purpose с Bash/WebFetch) — по 1 на биржу
- Каждый собирает: URL API docs, цены, объёмы, поддерживаемые площадки
- Сводка → markdown-таблица
- Деплой на artvision.pro/orm-contractors.html (расширение существующей страницы)

## Связанные файлы
- `~/artvision-data/tokens.json` — qcomment API key добавлен
- `clients/bluemart/orm/yuri-feedback-2026-04-26/kwork_review_services-snapshot.md` — 28 kwork-исполнителей (часть данных уже есть)
- `https://artvision.pro/orm-contractors.html` — текущий стенд (8 kwork + 11 провайдеров)
- `~/.claude/handovers/2026-04-27_blumart_orm_session.md` — handover BluMart-сессии (родительский контекст)

## Открытые вопросы Антону (продолжение из BluMart-handover)
1. BMPROMO — кто? (подрядчик Юры или внешний)
2. Kwork-пароль `dune87@yandex.ru`
3. Объём партии BluMart (10/30/50)
4. Площадки (только ЯК или + Google/2ГИС/Фламп)
5. orm-contractors.html → reusable шаблон для дентал/HR/etc?

## Приоритет
HIGH — это база для масштабирования ORM как услуги Artvision (не только BluMart).

## Roadmap (куда идём) — ORM как услуга

```
Фаза 1 (текущая, апрель)    BluMart — пилот, 1 канал (BMPROMO), 358 текстов в Sheet
Фаза 2 (май)                 +3 канала (qcomment API + otzyv-shop + kwork) → x2-x4 объёма
Фаза 3 (июнь)                Reusable: orm-contractors.html → стандартный продукт-стенд
                             Подключение HR/дентал клиентов на ту же инфру
Фаза 4 (Q3)                  ORM как отдельный SKU Artvision — тарифы, KPI, договоры
```

Главный артефакт направления: **общая таблица всех ORM-бирж с ценами** (см. ниже).

## Главные ссылки (склеить в одно)

| Ресурс | Ссылка |
|---|---|
| **Google Sheet — отзывы BluMart (358 шт)** | https://docs.google.com/spreadsheets/d/1WjU4rcWXGaiM0iVl_Kl6Pf_Mlgz7ioyvT6uQJQjMmCI/edit |
| Sheet — kwork исполнители (28 шт) | https://docs.google.com/spreadsheets/d/1hvrlCh7IU9QyJMfbuac-pkv6wk2pMTFVMwQsMjFuEI4/edit |
| Sheet — kwork_review_services | https://docs.google.com/spreadsheets/d/1CT8tjdxA-BnFWRYBEQyXqtgRmMGWz8FrMK4aTWiVTs4/edit |
| Стенд подрядчиков (рабочий) | https://artvision.pro/orm-contractors.html |
| TG-чат BluMart | chat_id 5113045924 ("Blumart Отзывы") |
| Биржа qcomment (API) | https://qcomment.com/ |
| Биржа otzyv-shop (login) | https://otzyv-shop.ru/ |
| Инструмент проверки шинглов (Юра) | https://pr-cy.ru/zypfa/ |

## Запрос Антона: автоматический TaskCreate каждую сессию

**Проблема:** Антон уже несколько раз просил автоматически создавать TaskCreate в начале сессии. Сейчас есть 3 хука, но они **только инжектят reminder в контекст**, и Claude может пропустить их (как в этой сессии — пришлось руками).

**Что есть сейчас:**
- `~/.claude/hooks/start-todo-tasks.sh` (SessionStart) — показывает TODO в начале
- `~/.claude/hooks/start-todo-taskcreate.sh` (SessionStart) — инжектит "ОБЯЗАТЕЛЬНО вызови TaskCreate"
- `~/.claude/hooks/prompt-taskcreate-nag.sh` (UserPromptSubmit) — повторяет напоминание до 10 turns

**Почему не работает:** все 3 — мягкие reminders. Claude переключается на user-prompt и забивает.

**Реальное решение (записать как задачу):**

Создать **PreToolUse-хук** `pre-tool-block-no-taskcreate.sh`:
- Срабатывает на ЛЮБОЙ инструмент кроме `TaskCreate`, `TaskList`, `Read`, `Bash(git status|git pull|ls|grep|cat)`
- Проверяет: `pending TODO > 0` И `в transcript нет вызова TaskCreate`
- Если оба true → **exit 1 с сообщением** «Сначала TaskCreate для pending TODO. Pending: N»
- Self-disable после первого TaskCreate (создаёт `/tmp/taskcreate-done-{session_id}`)

Это **жёсткая блокировка** — Claude физически не сможет работать пока не вызовет TaskCreate.

**Регистрация:** в `~/.claude/settings.json` добавить:
```json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "*", "hooks": [{ "type": "command", "command": "~/.claude/hooks/pre-tool-block-no-taskcreate.sh" }] }
    ]
  }
}
```

**Прецедент в `self-corrections.md` уже есть:**
> Слой 2 (если #9 повторится): PreToolUse-блокировка на любом tool кроме TaskCreate при pending>0, whitelist READ-only (Bash(git|ls|cat|pwd), Read)

Это уже зафиксировано — но НЕ реализовано. Антон просит реализовать.

**Задача в TODO следующей сессии:** написать `pre-tool-block-no-taskcreate.sh` + зарегистрировать в settings.json + протестировать на 3 кейсах (блокировка / пропуск после TaskCreate / bypass через `TASKCREATE_FORCE=1`).

История обращений Антона по этой проблеме (искать в transcripts/recaps):
- 2026-04-18..19 — инцидент TaskCreate пропуск, добавлены SessionStart+UserPromptSubmit хуки (Layer 1)
- 2026-04-27 (сейчас) — Антон опять руками просит, требует настоящую блокировку (Layer 2)
