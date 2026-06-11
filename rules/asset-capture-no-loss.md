# Asset Capture — никогда не теряем URL/доступы из чата

> **Установлено:** 2026-05-20 (сессия d4c2037d, dental-experts).
> **Прецедент:** Антон передал галерею Малютина (193 фото для landings) — URL ушёл в session.jsonl и не сохранился в git. Через 1.5 мес `rodionlakshin.wfolio.com` → NXDOMAIN, не восстановить.
> **Связано:** `kp-brand.md` (Pre-Task Protocol), `client-docs-storage.md` (документы клиентов в git), `quality.md` (verification gates).

## Проблема

Антон передаёт активы (URL фото, доступы, пароли, brand-files) в чате → они уходят в `~/.claude/projects/-Users-antonk/*.jsonl` → следующая сессия их не видит → потеря данных, нужно переспрашивать или восстанавливать через WebFetch (часто невозможно).

## Решение — 4 независимых слоя защиты

### Слой 1: WRITE-FIRST правило (моя дисциплина)

Когда Антон в prompt передаёт **актив клиента** — Claude обязан **первым tool call** сделать Write в файл клиента, **до** ответа в чат.

«Актив клиента» = любое из:
- URL фото/видео/PDF клиента (`i.wfolio.ru`, `*.tildacdn.com`, `drive.google.com/file`, `dropbox.com/...`, `disk.yandex.ru/...`)
- URL галерей (`wfolio.com/...`, `behance.net/...`, `instagram.com/p/...`)
- Доступы (login + password, API keys, CMS-credentials)
- Юр.реквизиты (ИНН, ОГРН, КПП, расчётный счёт)
- Контакты команды клиента (телефон, email, telegram-handle)
- Бренд-файлы (логотип, brandbook URL, color codes)

Куда писать:
- `clients/<slug>/assets/external-urls.yaml` — URL медиа
- `clients/<slug>/access.md` — доступы (gitignore если public репо)
- `clients/<slug>/config.yaml` — добавить контакт/реквизиты в существующее поле

Формат записи в `external-urls.yaml`:
```yaml
last_updated: YYYY-MM-DD
last_session: <session-id>
galleries:
  - source: "wfolio | drive | dropbox | yandex-disk | other"
    url: "<полный URL>"
    description: "Что внутри (193 фото Малютина — процесс/результат/портреты)"
    contact_who_provided: "Антон | Андрей | Клиент-имя"
    contact_date: "YYYY-MM-DD"
    expires: "YYYY-MM-DD | unknown"
direct_urls:
  category_name:
    - "https://..."
```

### Слой 2: Хук `post-userprompt-asset-capture.sh` (UserPromptSubmit)

Перехватчик: regex на prompt пользователя, если есть URL медиа/доступа/реквизита И определён client_slug (по cwd ИЛИ последнему упоминанию клиента в сессии) — инжектит system-reminder с императивом WRITE-FIRST в `assets/external-urls.yaml`.

Защищает от пропуска WRITE-FIRST мной.

### Слой 3: Шаблон при `/new-client`

Каждый новый клиент получает заполненный шаблон `clients/<slug>/assets/external-urls.yaml` сразу при онбординге. Pre-Task Protocol (см. `kp-brand.md`) дополнен — Шаг 0.5 «прочитать `assets/external-urls.yaml`» обязателен при работе с landings/КП.

Защищает от «папки нет → нечего читать».

### Слой 4: Хук `stop-asset-recap-check.sh` (Stop)

При закрытии сессии: проверяет `clients/*/assets/external-urls-pending.md`. Если есть entries без коммита в основной `external-urls.yaml` → recap получает блок «🚧 PENDING ASSETS — N URL'ов не сохранены в git».

Защищает от утечки в конец сессии.

## Применение

- ВСЕ клиенты получают `clients/<slug>/assets/` при онбординге
- Существующие клиенты — мигрируем по мере касания (создаём `assets/external-urls.yaml` при первой задаче)
- В чате при получении актива от Антона — WRITE-FIRST, не «потом запомню»

## Антипаттерны

- ❌ «Запишу в memory» — memory эфемерна, git вечен
- ❌ «Сначала отвечу что понял, потом запишу» — отвечу и забуду
- ❌ «URL в context-log.md» — context-log это лог действий, не источник правды по активам
- ❌ «URL в reply Антону Telegram» — Antонов чат не grep'абелен из сессии

## Прецеденты потери

- **2026-05-20 dental-experts** — URL галереи `rodionlakshin.wfolio.com` записан как факт в CLAUDE.md, но реальные i.wfolio.ru/x/... никогда не попали в git. Поддомен через 1.5 мес NXDOMAIN. 193 фото утрачены без бэкапа.
- (TBD: добавлять каждый новый кейс)

## Файлы

| Компонент | Путь |
|---|---|
| Правило | `~/.claude/rules/asset-capture-no-loss.md` (этот файл) |
| Хук UserPromptSubmit | `~/.claude/hooks/post-userprompt-asset-capture.sh` |
| Хук Stop | `~/.claude/hooks/stop-asset-recap-check.sh` |
| Шаблон | `~/.claude/templates/client-assets-external-urls.yaml` |
| Регистрация | `~/.claude/settings.json` (hooks.UserPromptSubmit + hooks.Stop) |
