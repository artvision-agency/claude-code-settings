# Handover: OPS — CRM-попап, безопасность, диета, договорные сроки (продолжение)

**Дата:** 2026-06-11 18:10 · **Контекст:** ops · **Сессия:** CRM OPS (da57619d) · **Статус:** много сделано, остаток staged
> Полное состояние → `~/artvision-data/docs/ops-dashboard.md` (главный документ) + `dashboards/ops-api/README.md` + TODO.md (ops) + предыдущий handover `HANDOVER-2026-06-11-1425-ops.md`.

## 🎯 Что закрыто в этой сессии (после 14:25)

### CRM-дашборд (https://artvision.pro/ops.html, логин `ops` / tokens.json→ops_dashboard)
- ✅ Вкладка «Договорные сроки» (3-я) — `ops-contract-dates.yaml` → генератор `scripts/ops-contract-tab.py`. **9/10 клиентов = дырки** (сроки не вынесены из договоров, красным). Грелка — реальные (Акт 25.06).
- ✅ Авто-проверщик `scripts/ops-contract-checker.py` + LaunchAgent `pro.artvision.contract-checker` (ежедневно 10:15 → TG).
- ✅ **CRM-попап управления задачей** (исходный запрос Антона): клик по задаче в Gantt → модал (проект/исполнитель/срок/статус/заметки) + кнопки ✅Завершить (`/done`) · 🔗Asana · Закрыть. Проверено скриншотом (79 задач, 0 ошибок). BUILD-решение подтверждено round_table.

### 🔴 Безопасность (инцидент + 4/5 шагов укрепления, round_table HIGH SOLID)
- ✅ **NDA-утечка ЗАКРЫТА**: gantt-data.json+ops.html+/api/gantt были публичны (Blumart NDA утекал) → nginx `auth_basic` (htpasswd `/var/www/artvision/.htpasswd-ops`, юзер `ops` добавлен + `artvision`). Аноним→401, логин→200.
- ✅ CORS сужен (nginx json + Flask after_request) до artvision.pro.
- ✅ rate-limit nginx (`/etc/nginx/conf.d/ratelimit-ops.conf` zone ops_api 10r/s burst5) на /api/gantt/.
- ✅ CSRF custom-header `X-Ops-CSRF:1` на POST /api/gantt/task (бэк требует, ops.html шлёт). Тест: no-CSRF→403.
- ✅ Version drift закрыт: прод `gantt_api.py` → git `dashboards/ops-api/gantt_api.py`. Launcher = **PM2** (`pm2 restart gantt-api --update-env`).
- Бэкапы nginx: `/etc/nginx/sites-enabled/artvision.pro.bak-*` (всё обратимо).

### Прочее
- ✅ Context-diet Wave 1: 5 правил rules/→rules-conditional (−44KB), ветка `~/.claude` `context-diet-w1` (НЕ влита). Спека `decisions/2026-06-11-context-diet-spec.md`, карта `rules/_RELOCATION-MAP.md`.
- ✅ Разбор `di-sukharev/vibe` → `research/2026-06-11-sukharev-vibe-arch-review.md` (стек не наш; брать структуру инженерного стандарта CLAUDE.md).
- ✅ ANT Partners → presale (registry + MEMORY). Geely/BluMart/ANT задачи в Asana.

## 🔜 ОСТАЛОСЬ (следующая чистая сессия)

1. **HMAC-секрет + expiry для `/done`** [HIGH, осторожно] — ЕДИНСТВЕННЫЙ незакрытый шаг укрепления. ⚠️ signer = `/home/andrey/artvision-data/scripts/evening_digest_tg.py` (генерит вечерние ✅-ссылки КОМАНДЕ), verifier = `gantt_api.py sign_gid`. Менять ВМЕСТЕ + тест живой TG-ссылки, иначе сломается дайджест. PM2-рестарт с `DONE_HMAC_SECRET` в env (`pm2 set` / ecosystem). План в `dashboards/ops-api/README.md`.
2. **Договорные сроки 9 клиентов** — вынести из реальных договоров (legal/sent) в CONTRACT-DELIVERABLES.md → дырки в дашборде закроются (генератор+чекер уже их подтянут).
3. **PIN 1234/5678 → random** [LOW — теперь за auth_basic+rate-limit+CSRF, не публичны] — координированно gantt_api VALID_PINS + ops.html U[].p + tokens.json.
4. **Context-diet:** мерж Wave 1 (или keyword-триггер для Wave 2 −200KB) · хуки 161→40.
5. **#6 ops-как-продукт** — стратсессия /cons (white-label).
6. BluMart процесс жалоб (готов, ждёт ОК+доступы) · Asana-гигиена (520 просроченных, PAT) · Грелка Акт 25.06.

## ⚠️ Гачи
- ops.html за auth_basic → `deploy-ops.sh` verify пишет «401» (это НОРМА, проверяет анонимно). Деплой при этом успешен.
- PM2-процесс называется `gantt-api` (НЕ gantt_api). Рестарт: `pm2 restart gantt-api --update-env`. ASANA_TOKEN в env переживает рестарт (проверено).
- `/done` + `/task_info` = GET (CSRF не нужен). CSRF только на create_task (POST).
- tg-send.sh глушит сообщения с ❌/🚨 в теле → `NOTIFY_FORCE=1` для рабочих.
- Telethon ЖИВ (хук врёт EXPIRED). PM2 launcher для Flask.

## 🔗 Ключевые файлы
- `docs/ops-dashboard.md` — главный (как работает + что изменилось + остаток)
- `dashboards/ops-api/{gantt_api.py,README.md}` — прод Flask + план HMAC
- `ops.html` · `ops-contract-dates.yaml` · `scripts/ops-contract-{tab,checker}.py`
- VPS: `/opt/artvision/gantt_api.py` (PM2 gantt-api) · `/etc/nginx/sites-enabled/artvision.pro` (auth блоки ~270-325)
