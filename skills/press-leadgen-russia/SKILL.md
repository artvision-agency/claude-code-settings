---
name: press-leadgen-russia
description: "HARO для РФ — мониторинг журналистских запросов на Pressfeed/Deadline/Журналист Запрос, генерация ответов экспертом от имени клиента, получение high-DR backlinks. Триггеры: 'pressfeed', 'haro для рф', 'haro россия', 'журналист запрос', 'press leadgen', 'press pitch', 'журналистский запрос', 'pr backlink', 'deadline media', 'hero journalism', 'журналистские запросы'."
allowed-tools: [Read, Write, Edit, Bash, WebSearch, WebFetch, Grep, Glob]
user-invocable: true
---

# Press Leadgen Russia — HARO-аналог для РФ

## Что делает

Мониторит русскоязычные журналистские платформы (аналог HARO/Qwoted) → подбирает релевантные запросы клиентам Artvision → генерирует экспертные ответы от имени клиента → доставляет либо через outreach-emails, либо как копи-пасту для ручной публикации. Цель — high-DR backlinks из публикаций (Forbes RU, vc.ru, РБК, Sostav, Cossa и др.).

## Источники (3 рабочих + 1 опц.)

| # | Источник | Доступ | Скрипт | Что |
|---|----------|--------|--------|-----|
| 1 | **Pressfeed** | TG-зеркало `@Pressfeed_queries` (public preview) | `parse_pressfeed.py` | Главный поток, 20-50 запросов/день |
| 2 | **Deadline.media** | WP REST API `/wp-json/wp/v2/posts` (открытый, без ключа) | `parse_deadline.py` | Алертные запросы, 5-15/день |
| 3 | **«Журналист Запрос»** TG | Telethon userbot (наша инфра) — `@jouroffer` | `parse_tg_journalist.py` | 10-30/день |
| 4 | Sostav.ru "Эксперт ответил" | HTML scrape (опц.) | `parse_sostav.py` (TBD) | Реже, редкие но премиум |

Pressfeed имеет платный API (~$50/мес), но MVP работает на public TG-preview — без авторизации.

## Workflow (4 фазы)

### Фаза 1. Парсинг новых запросов

```bash
python3 ~/.claude/skills/press-leadgen-russia/scripts/parse_pressfeed.py --since 24h -o /tmp/press-queries-pressfeed.json
python3 ~/.claude/skills/press-leadgen-russia/scripts/parse_deadline.py --since 24h -o /tmp/press-queries-deadline.json
python3 ~/.claude/skills/press-leadgen-russia/scripts/parse_tg_journalist.py --since 24h -o /tmp/press-queries-jouroffer.json
```

Каждый эмитит JSON-array объектов вида:
```json
{
  "source": "pressfeed",
  "id": "194488",
  "url": "https://pressfeed.ru/query/194488",
  "title": "Журнал ИнтернетУрок: Комментарии о тревоге из-за оценок",
  "outlet": "ИнтернетУрок",
  "deadline": "2026-05-23T18:00:00",
  "topic_tags": ["образование", "психология", "родители"],
  "body": "...полный текст запроса...",
  "fetched_at": "2026-05-21T04:50:00",
  "hash": "sha256-..."
}
```

**Idempotency:** все запросы дедуплицируются по `hash(source+id+title)` через `~/.claude/state/press-leadgen-seen.json`. Повторный запуск не создаёт дубликаты.

### Фаза 2. Матчинг с клиентами

```bash
python3 ~/.claude/skills/press-leadgen-russia/scripts/match_clients.py \
  --queries /tmp/press-queries-*.json \
  --clients-dir ~/artvision-data/clients/ \
  -o /tmp/press-matches.json
```

Алгоритм:
1. Читает `clients/<slug>/config.yaml` каждого активного клиента: `segment`, `niche`, `expertise`, `region`
2. Для каждого запроса считает relevance-score по совпадению ключевых слов в `title+topic_tags+body` с `niche+expertise`
3. Бонусы:
   - `+3` если outlet — DR70+ медиа (Forbes RU, vc.ru, РБК, Коммерсантъ, Sostav, Cossa)
   - `+2` если регион клиента совпадает с регионом outlet (СПб/МСК)
   - `+2` если дедлайн ≥24ч (есть время на качественный ответ)
   - `-3` если дедлайн <6ч (skip, не успеем согласовать)
   - `-5` если outlet — порно/политика/чёрный список (см. `templates/blacklist-outlets.txt`)
4. Threshold: score ≥ 5 → попадает в `matches.json`

### Фаза 3. Генерация ответа

Для каждого match:

```bash
python3 ~/.claude/skills/press-leadgen-russia/scripts/draft_response.py \
  --match /tmp/press-matches.json \
  --client <slug> \
  -o ~/artvision-data/clients/<slug>/linkbuilding/press-drafts/<query-id>.md
```

Логика:
1. Читает `clients/<slug>/brand-voice/profile.md` (если есть — от skill `brand-voice`)
2. Читает `clients/<slug>/cases/` — выбирает 1-2 кейса релевантных запросу (для конкретики)
3. Выбирает шаблон из `templates/`:
   - `response-medical.md` — стомат/мед-клиники
   - `response-seo.md` — SEO/маркетинг-эксперт от Artvision
   - `response-business.md` — generic B2B
   - `response-realestate.md` — недвижимость
   - `response-education.md` — обучение/курсы
4. Заполняет: цитата эксперта (2-3 абзаца, конкретные числа из кейсов, без AI-клише), ссылка на клиента (1 шт, dofollow target), bio эксперта (ФИО + должность + клиент)

**Анти-паттерны (запрещено в драфтах):**
- ❌ «Как показывают исследования», «По мнению экспертов», «В современных реалиях»
- ❌ Упоминание AI/нейросетей/Claude/GPT в публичном ответе (security.md)
- ❌ Чужие бренды-сервисы (Semrush, Ahrefs) — заменять на Artvision-продукты в видимом тексте
- ❌ Числа без источника / без кейса клиента
- ❌ Скрытые UTM в ссылке (`?utm_*` — журналист увидит и спросит)

### Фаза 4. Доставка и трекинг

Два пути:

**A. Автомат через outreach-emails** (если у запроса есть email журналиста — Deadline.media часто публикует):
```bash
# Интегрируется как 5-й тип письма "press_response" в outreach-emails
python3 ~/.claude/skills/outreach-emails/tracker_manager.py add \
  --type press_response \
  --to <journalist-email> \
  --subject "Re: <query-title>" \
  --body-file <draft.md> \
  --client <slug>
```

**B. Ручная публикация** (Pressfeed/JourOffer требуют логина):
- TG-уведомление команде в `-4273200821` со ссылкой на драфт и URL запроса
- Антон/Андрей логинятся, копируют, отправляют
- Маркируют в `linkbuilding/press-leadgen.log` дату отправки

**Трекинг публикации (cron еженедельно):**
```bash
python3 ~/.claude/skills/press-leadgen-russia/scripts/check_published.py \
  --client <slug> \
  --since 14d
```
- WebSearch `"<имя клиента>" site:<outlet-domain>` для каждой отправки старше 7 дней
- Curl outlet и поиск ссылки на клиента
- Если найдено — запись в `clients/<slug>/linkbuilding/backlinks.yaml` с DR (через WebFetch ahrefs alternative или ручная пометка)

## Когда вызывать

| Команда | Что делает |
|---------|-----------|
| `/press-leadgen-russia` без аргументов | Парс всех источников за 24ч + матч всем клиентам + отчёт |
| `/press-leadgen-russia <client-slug>` | Только под одного клиента (Phase 2-4) |
| `/press-leadgen-russia --client <slug> --query-url <url>` | Один конкретный запрос → один драфт |
| `/press-leadgen-russia --published-check` | Phase 4 только, проверка ранее отправленных |

## Расписание (рекомендуемый cron)

```
0 9,15 * * *   python3 ~/.claude/skills/press-leadgen-russia/scripts/parse_*.py + match_clients.py
```
Утро 09:00 + день 15:00 МСК — два прохода/день. Pressfeed публикует пиками 10-12 МСК и 14-16 МСК.

Setup через `/schedule` skill (cron-задачи Claude Code).

## Логи и состояние

| Файл | Назначение |
|------|-----------|
| `~/.claude/logs/press-leadgen.log` | Все запуски + кол-во matches |
| `~/.claude/state/press-leadgen-seen.json` | Hash-set обработанных запросов (idempotency) |
| `~/artvision-data/clients/<slug>/linkbuilding/press-drafts/` | Драфты по клиенту |
| `~/artvision-data/clients/<slug>/linkbuilding/press-leadgen.log` | Лог отправок и ответов клиента |
| `~/artvision-data/clients/<slug>/linkbuilding/backlinks.yaml` | Полученные бэклинки |

## Pre-Task Protocol (для каждого клиента)

Перед генерацией драфта обязательно прочитать:
1. `clients/<slug>/CLAUDE.md`
2. `clients/<slug>/config.yaml` (segment, niche, region, expertise, contacts)
3. `clients/<slug>/brand-voice/profile.md` (если есть)
4. Последний `clients/<slug>/meetings/*.md` (свежий контекст)
5. `clients/<slug>/patches/*.md` (особенности клиента)

Без `CLAUDE.md` клиента — пропустить (нет L1 context environment, см. `~/.claude/rules/context-environment.md`).

## Интеграции

- **`brand-voice`** — забираем `profile.md` для tone of voice
- **`outreach-emails`** — отправка как 5-й type письма + tracker
- **`tg-chat-export`** — Telethon-паттерн для `@jouroffer` и `@Pressfeed_queries`
- **`linkbuilding`** — обновление контента в `clients/<slug>/linkbuilding/`
- **`factcheck`** — каждый драфт проходит factcheck перед отправкой клиенту/журналисту (числа из кейсов = реальные)

## TG-уведомления

Канал команды: `-4273200821` (id из `accounts.md`)

```bash
~/.claude/scripts/tg-send.sh team "🗞 Press-leadgen: <N> новых матчей.
Клиенты: <slug1>, <slug2>.
Драфты: ~/artvision-data/clients/<slug>/linkbuilding/press-drafts/
К рассмотрению: <url1>, <url2>"
```

Алерт ТОЛЬКО при `matches > 0` (иначе ежедневный спам).

## Прецеденты и эталоны

- **2026-05-21:** скилл создан. MVP — только `parse_pressfeed.py` рабочий, остальные скрипты — заглушки.
- **Эталонный outlet-стек** (DR70+ для РФ):
  - Forbes.ru (DR89), РБК (DR91), Коммерсантъ (DR89), Ведомости (DR88)
  - vc.ru (DR88), Habr (DR91), Sostav (DR75), Cossa (DR73), Rusbase (DR74)
  - Профильные медицине: Vademec, Medvestnik, Pharmvestnik (DR65-72)
  - Профильные SEO: SEOnews, Searchengines.ru (DR60-68)

## Антипаттерны (нельзя)

- ❌ Отправлять драфт без согласования с Антоном/клиентом (CONFIRM по security.md — любой контакт с третьей стороной)
- ❌ Парсить Pressfeed UI напрямую (нужна авторизация + capтча) — только TG-preview
- ❌ Выдумывать цифры в драфте — только из `clients/<slug>/cases/`
- ❌ Один драфт на 5+ клиентов одновременно (журналист увидит идентичные ответы)
- ❌ Запускать без `--since` (по умолчанию 24ч, иначе залётит весь архив)

## Связанные правила

- `~/.claude/rules/security.md` — CONFIRM для любого контакта с журналистом
- `~/.claude/rules/quality.md` — factcheck драфта перед отправкой
- `~/.claude/rules/context-environment.md` — клиент должен быть на L1+ уровне
- `~/.claude/rules/proven-tools-first.md` — TG-preview как proven channel вместо custom scraper
