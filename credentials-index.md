# Credentials Index — карта где какой доступ лежит

> **Назначение:** перед утверждением «нет доступа / не нашёл пароль / нет токена» — проверить ВСЕ источники по этой карте. Защита от false-negative (прецедент: avprocontext пароль был, я сказал «нет»).
> **Связано:** `~/.claude/rules/no-false-negative.md`, `~/.claude/skills/find-anywhere/SKILL.md`, `~/.claude/scripts/cred-get.sh`, `self-corrections.md` #20.
> **Проверено на диске:** 2026-05-29.

## Матрица источников (искать ВЕЗДЕ перед «нет»)

| # | Источник | Путь / команда | Что лежит |
|---|----------|----------------|-----------|
| 1 | **tokens.json** (главный) | `~/artvision-data/tokens.json` | 43 сервиса: API-ключи, OAuth, SaaS. Top-level ключи см. ниже |
| 2 | **access.md** клиентов | `~/artvision-data/clients/*/access.md` (9 шт) | CMS/FTP/хостинг/панели клиентов |
| 3 | **memory** | `~/.claude/projects/-Users-antonk/memory/*.md` | reference_*credentials*, project_*, feedback_* с креды-деталями |
| 4 | **jsonl сессий** | `~/.claude/projects/-Users-antonk/*.jsonl` (301 шт) | где предыдущий Claude уже находил/использовал доступ |
| 5 | **macOS Keychain** | `security find-generic-password -s "<svc>" -w` | "Claude Code-credentials", "Claude Safe Storage", прочее |
| 6 | **git log -S** | `cd <repo> && git log -S'<key>' --all -- tokens.json` | вычищенные аудитом ключи (история) |
| 7 | **.env файлы** | `find ~/artvision-* -name ".env" -o -name ".env.*"` | локальные креды ботов/скриптов |
| 8 | **config.yaml** клиентов | `~/artvision-data/clients/*/config.yaml` | site/contacts/иногда доступы |

## tokens.json — top-level ключи (43, на 2026-05-29)

```
2index_ninja, adsgram, ant_partners, anthropic, artvision, artvision_pro,
asana, crazygames, dataforseo, deepseek, expired_domains, extru_tech,
firstvds_panel, fl_ru, gameanalytics, geely_a2auto, gemini, github,
google_indexing, google_search, groq, healthchecks, hh_api, huggingface,
instagram, kb_artvision_pro, kupi-otziv, kwork, openai, openrouter, orm,
otzyv_shop, qcomment, regru, remove_bg, semrush, supabase, telegram, tilda,
timeweb_cloud, topvisor, turbo_text, userator, uptimerobot, vercel,
vk_workspace, vps, yandex, yandex_360, yandex_mail, youtube, zenno_club
```

Читать: `python3 -c "import json; print(json.load(open('/Users/antonk/artvision-data/tokens.json'))['<key>'])"`

## Важные нюансы (из прецедентов)

- **Anthropic API key ≠ Claude Max** — `tokens.json['anthropic']` это программный `sk-ant-` ключ, отдельный от OAuth подписки Claude Code (Keychain "Claude Code-credentials"). Не путать (memory `feedback_anthropic_api_vs_max_oauth.md`).
- **Telethon/Telegram api_id/api_hash** — `tokens.json['telegram']`. Security-аудиты могут молча вычищать (`git log -S'api_id' -- tokens.json`). Прецедент `self-corrections.md` #20.
- **Клиентские доступы** — сначала `clients/<slug>/access.md`, потом `config.yaml`. Если public-репо — access.md может быть gitignored, искать локально.
- **VPS** — `tokens.json['vps']` + `~/.ssh/config` (host `vps`, `vps-andrey`).

## Алгоритм «не нашёл» (обязательный перед негативным ответом)

```
1. /find-anywhere <что ищу>   (multi-source grep сразу по 8 источникам)
   ИЛИ вручную grep по матрице выше
2. git log -S — не вычищено ли аудитом
3. Только если ВСЕ 8 пусты → «не найдено в: [список где искал]»
   НЕ «нет» / «не существует» — указать ГДЕ искал
```

## 🔑 ВОЗМОЖНОСТИ ДОСТУПА — что РЕАЛЬНО включено (читать ПЕРВЫМ при API/доступ-вопросе)
> Установлено 2026-06-27 (Антон: «создай файл чтоб ЗАРАНЕЕ видел что в доступе + читал заранее»). Прецедент: я фумблил — говорил «Wordstat new API нужна регистрация», хотя токен УЖЕ работал в parse_implant_keywords.py. Метка `_desc` в tokens.json вводит в заблуждение («v4»), реальные возможности — здесь.

### Яндекс
| Токен (tokens.json) | Аккаунт/назначение | Что РЕАЛЬНО работает |
|---|---|---|
| `yandex.wordstat.token` | app 16ce5df0…, _desc «v4» (НО шире) | **v4 Direct** `api.direct.yandex.ru/v4/json CreateNewWordstatReport` ✅ (частотность, лимит 1000 вызовов/сут/аккаунт). **Новый API** `api.wordstat.yandex.net/v1/topRequests` — использовался parse_implant_keywords.py (auto-sync 22.06); при тесте 27.06 → **404** (проверить метод/доступ/транзиент). `/v1/dynamics`, `/v1/userInfo` → **404** (НЕ на нашем доступе или иной путь). SSL: нужен `ssl.CERT_NONE` (cert hostname mismatch). |
| `yandex.direct.{reklamaspb1,yail307,avprocontext,artvisionelama_e2}` | reklamaspb1=Otido · yail307=USmile(Ярмолинский) · avprocontext=Artvision свои · elama_e2=агентский eLama | Direct API v5 + v4-Wordstat (каждый свой лимит 1000/сут) → используются round-robin для массового сбора Wordstat |
| `yandex.webmaster.token` | user_id 126256095, OAuth | Вебмастер API v4 (показы/клики/запросы сайтов) ✅ |
| `yandex.metrika.token` | OAuth | Метрика Stat API ✅ (+ varikozanet_counters view) |
| `yandex.cloud.api_key` | folder b1g3skikcv7e3aehpu26 | SpeechKit + Translate. **Search API (Wordstat-через-Cloud) НЕ включён** (нужно включить в folder + billing) |

### Динамика спроса во времени (тренды 2018+) — СТАТУС
- НЕ закрыто детерминированно: `/v1/dynamics` нашим токеном = 404. Опции: (1) разобрать почему topRequests 404 теперь (был жив 22.06) → если оживёт, проверить есть ли там time-series; (2) CSV-экспорт из Wordstat-UI (кнопка «Скачать» во вкладке Динамика) — быстрый ручной путь; (3) включить Cloud Search API. См. `knowledge/services/yandex-wordstat/official-kb.md`.

### Прочее (где НЕ Яндекс)
GitHub (primary/backup токены), Telegram (portal/vps/medmarketplace боты), Asana, DataForSEO, anthropic/gemini/deepseek, adsgram, SaaS-панели (firstvds/hostland) — детали в tokens.json + клиентских access.md. Полный список top-level ключей — выше в этом файле.
