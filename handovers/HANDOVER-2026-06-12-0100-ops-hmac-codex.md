# Handover: OPS — HMAC завершён, codex-lifecycle собран, meeting-prep (продолжение)

**Дата:** 2026-06-12 ~01:00 · **Контекст:** ops · **Сессия:** CRM OPS (da57619d, продолжение после compact) · **Статус:** основное закрыто, остаток → чистая сессия
> Полное состояние → `~/artvision-data/docs/ops-dashboard.md` + `dashboards/ops-api/README.md` (секция HMAC) + предыдущий handover `HANDOVER-2026-06-11-1810-ops-crm-security.md`.

## 🎯 Что закрыто в этой сессии (после 18:10 / compact)

### HMAC /done — ✅ ЗАВЕРШЁН end-to-end (был последний шаг безопасности из прошлого handover)
- Метод: codex-dev-lifecycle (план→ревью→build→verify). **Codex упал 403 (codex login слетел)** → по правилу не долбил → fallback **round_table** (3 модели) на ревью плана → REVISE → находки отфильтрованы через наши ограничения.
- **Схема:** `sign(gid,exp)=HMAC-SHA256(secret,"gid:exp")[:32]` (128 бит) + expiry TTL 7д + fail-CLOSED. Принято из round_table: 128-бит, expiry-bound, fail-closed, sync-проверка. Отклонено обоснованно: POST-переписка (TG-ссылка только GET), nonce (закрытие идемпотентно), salt (HMAC keyed).
- **Signer:** `scripts/evening_digest_tg.py` (Mac launchd `pro.artvision.evening-digest`!), секрет ← `tokens.json→artvision.done_hmac_secret`. Ссылка `?gid=&exp=&sig=`.
- **Verifier:** `/opt/artvision/gantt_api.py` (pm2 gantt-api), секрет ← env DONE_HMAC_SECRET ИЛИ файл `/opt/artvision/.done_hmac_secret` (600, fallback — pm2-env капризил «change group ID»).
- **nginx:** добавлены `location = /api/gantt/done` + `/api/gantt/task_info` БЕЗ auth_basic (защита = sig + rate-limit), иначе клик ✅ из TG ловил пароль. `/api/gantt/task` (POST) + `/api/gantt-data.json` — auth_basic ЦЕЛ. Backup: `artvision.pro.bak-hmac-done-20260611-224333`.
- **Verify (https реальный):** валидная подпись→502 (auth прошёл), без/битая подпись→401, gantt-data.json→401 (NDA цел). Mac-подпись→VPS-verifier True. Прод жив (ping 200).

### codex-dev-lifecycle — ✅ воркфлоу собран
- `.claude/workflows/codex-dev-lifecycle.js` — план→Codex-ревью→build→Codex-ревью→рефактор, луп до «ожидание==результат». Триггеры в CLAUDE.md. 7/7 проверок (синтаксис/параллель=0/null-guard/runtime-verify). Правило `~/.claude/rules/codex-dev-lifecycle.md` обновлён (был кандидат).
- ⚠️ Граница: ТОЛЬКО код/воркфлоу-как-код/хуки/API. НЕ маркетинг (PPC/КП/контент → наши домен-гейты).
- Урок: при 403 Codex fallback на round_table сохраняет принцип «другое семейство».

### Встреча Ярмолинский 12.06 10:45 (метро Московская) — ✅ подготовлено
- Чек-лист (СКИНУТЬ клиенту на встрече, обещан с прошлой): `clients/usmile/CHECKLIST-usmile-2026-06-12.xlsx` (73 пункта, ✅31 ⏳20 🔒12 🔄3).
- Бриф: `clients/usmile/meetings/2026-06-12-meeting-brief.md` (темы+ссылки+проверка прошлых обещаний).
- Правило `~/.claude/rules/meeting-prep-auto.md` — авто-бриф встреч + проверка нерешённого с прошлой встречи.

## 🔜 ОСТАЛОСЬ (чистая сессия — harness/прод на 3 аккаунта, НЕ в Dumb Zone)
1. **context-diet Wave 1 — МЕРЖ** ветки `~/.claude` `context-diet-w1` в main (Wave 1 готова, верифицирована, НЕ влита). Затем Wave 2 (−200KB keyword-триггер) · хуки 161→40. Спека: `artvision-data/decisions/2026-06-11-context-diet-spec.md`.
2. **Codex login** — Антон: `codex login` в терминале (403, авторизация слетела) → вернётся Codex-ревью вместо round_table.
3. **PIN 1234/5678 → random** [LOW, всё за auth] — координированно gantt_api VALID_PINS + ops.html U[].p + tokens.json.
4. **#6 ops-как-продукт** — стратсессия /cons (white-label) — Антон.
5. **#8 договорные сроки 7 клиентов** — нужны файлы договоров от Антона → CONTRACT-DELIVERABLES.md → дашборд закроет дырки.
6. Календарь Ярмолинского — Антон OAuth bootstrap (`~/.claude/scripts/gcal-bootstrap.sh`). · BluMart жалобы (ОК+доступы). · adopt `adversarial-review` скилл (round_table+ОК).

## ⚠️ Гачи
- evening_digest (signer) крутится на **Mac** (launchd `pro.artvision.evening-digest`), не на VPS — секрет нужен в Mac `tokens.json`.
- Codex-субагенты падают 403 (codex login) → fallback round_table, НЕ долбить.
- pm2 env капризит «change group ID» → секрет verifier'у через файл `.done_hmac_secret`, не env.
- Ротация HMAC-секрета (TODO v2): обновить `.done_hmac_secret` (VPS) + `tokens.json→done_hmac_secret` (Mac) одним значением + pm2 restart gantt-api.
- nginx изменён → backup `artvision.pro.bak-hmac-done-*`. Откат: восстановить backup + reload.
- Локальный `read VAR < file` в zsh даёт «failed to change group ID» — избегать в bash-командах с ssh.

## 🔗 Ключевые файлы
- `dashboards/ops-api/{gantt_api.py,README.md}` (HMAC секция) · `scripts/evening_digest_tg.py`
- `.claude/workflows/codex-dev-lifecycle.js` · `~/.claude/rules/{codex-dev-lifecycle,meeting-prep-auto}.md`
- `clients/usmile/{CHECKLIST-usmile-2026-06-12.xlsx,meetings/2026-06-12-meeting-brief.md}`
- VPS: `/opt/artvision/{gantt_api.py,.done_hmac_secret}` · `/etc/nginx/sites-enabled/artvision.pro`
