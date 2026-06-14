# Handover: Fable5-применение + ротация утёкшего токена @avportal_bot

**Дата:** 2026-06-14 ~03:00
**Контекст:** infra / security
**Сессия:** 03ae9e9f-da68-4bee-b74c-62a9f66c24bf
**Статус:** завершено (1 хвост: VPS-токен, заблокирован сетью)

> Полное состояние → recap `sync/recaps/03ae9e9f-...md` (читать ПЕРВЫМ) + self-corrections #31.

## 🎯 Цель сессии
Проверить, сохранены/применены ли находки Fable 5 → разрослось в security-инцидент (утечка bot-токена в публичном репо).

## ✅ Что сделано
- **Fable5 применён в процессах:** `~/.claude/rules/auto-routing-table.md` перегенерён (5 скиллов в слой-2), `artvision-data/CLAUDE.md` (слой-1 триггеры), `smm-post-production.js` фаза Generate ← `/photo-compose` встроен (уровень 5). Запушено.
- **Хук** `~/.claude/hooks/prompt-numbers-determinism-nudge.sh` (Fable5 enforcement, inject-only, тесты 5/5+6/6, зарегистрирован в settings.json).
- **Ротация токена @avportal_bot (id 8399522625):** Антон сделал `/revoke` в @BotFather → оба старых токена (`...LKQ4` утёкший + `...h1ho` живой) МЕРТВЫ. Новый `...L9A` записан в `~/artvision-data/tokens.json` `telegram.portal_bot` (gitignored, не в репо).
- **Де-хардкод:** `notify-telegram.sh` + `remind-tg-video-publish.sh` → читают tokens.json (был живой токен в публичном claude-code-settings). Запушено.
- **Стас:** бандл `~/secrets-handoff-stas-2026-06-14.tgz` доставлен в TG (msg 15008) + resync-инструкция в DM. Его 67 коммитов целы на origin/main.

## 🧠 Решения и ПОЧЕМУ
| Решение | Альтернатива | Почему |
|---|---|---|
| Антон делает revoke в @BotFather | filter-repo истории | revoke чище: старая копия в публичной истории становится мёртвой; filter-repo+force снова ломает Стаса + Dumb Zone риск |
| Новый токен только в gitignored tokens.json | коммит в приватный репо | tokens.json gitignored = не в git вообще = самое безопасное |
| Скрипты читают tokens.json, не хардкод | sed замена old→new | хардкод нового в публичные скрипты = повторная утечка |
| rebase моих коммитов поверх Стаса | force-push | force переписал бы работу Стаса; rebase сохранил |

## ❌ Что НЕ сделано
- **VPS-токен (`...L9A`) не вписан в VPS tokens.json** — мой сетевой путь к VPS мёртв (SSH banner-timeout 5×, ping 100% loss). VPS ЗДОРОВ (внешние узлы FR/SI/UA → HTTP 200, сайты/croны работают) — деградация МОЕГО пути (ISP/роутинг). Не подтверждено даже, использует ли VPS avportal_bot.
- Мёртвый токен в паре публичных `.bak`/`.disabled` файлов — безвреден (токен мёртв), не чистил.

## 📚 Уроки (для self-corrections)
- **`git push -q 2>&1 | tail -1 && echo "✅"` МАСКИРУЕТ отказ push** — tail всегда exit 0 → ложное «pushed». Мои Fable5-коммиты висели локально, не на origin. ВСЕГДА проверять `git rev-list @{u}..HEAD` после push.
- Утёкший секрет в публичном git — недостаточно убрать из рабочего дерева, он в ИСТОРИИ → только revoke/ротация закрывает.
- `tr [:upper:][:lower:]` корраптит UTF-8 кириллицу (byte-oriented) — для детекта в bash-хуках использовать `[[ == *kw* ]]`, не tr/grep (self-corrections #31).

## 🔜 Следующие шаги
1. **HIGH (когда сеть до VPS поднимется ИЛИ с VPN):** `ssh root@80.90.181.152` → grep использует ли VPS avportal_bot → если да, вписать `...L9A` в VPS `tokens.json` `telegram.portal_bot` → проверить croны.
2. MEDIUM: Стас выполняет resync (`git reset --hard origin/main` + распаковать бандл) — на ЕГО машине.
3. LOW: вычистить мёртвый токен из публичных .bak/.disabled (косметика).

## ⚠️ Гачи
- VPS 80.90.181.152 SSH-ится НЕ со всех сетей — у меня путь был мёртв, у Антона с VPN может работать.
- Новый токен `...L9A` только локально на маке Антона (gitignored) → НЕ синкается на VPS/Стаса через git. Раздавать вручную.
- tokens.json gitignored в artvision-data — НЕ форсить `git add -f`.
- claude-code-settings ПУБЛИЧНЫЙ — секреты туда НИКОГДА.

## 🔗 Связанные
- Задачи трекера: #2 (ротация — сделана, хвост VPS), #3 (Стас — бандл доставлен)
- research/fable5-wins-2026-06-12/ (источник Fable5)
- self-corrections #31 (public secret leak), recap 03ae9e9f

---

## ОБНОВЛЕНИЕ (дальше по сессии) — ротация ДОВЕДЕНА почти до конца

**КРИТИЧНОЕ, что чуть не упустил:** @avportal_bot — это ГЛАВНЫЙ прод-бот (vps-bot/bot.js, pm2 `avportal-bot`, polling), не только нотификатор. Revoke его функционально уронил (401). **Восстановлен:** обновил `vps-bot/.env` TELEGRAM_BOT_TOKEN + VPS tokens.json (4 копии: /root/, /root/artvision-data/, /root/.claude-sync/, /root/artvision-tg-bot/) → новый токен → `pm2 restart avportal-bot` → polling OK, 401 ушли.

**Урок (в self-corrections):** ротация токена бота = чинить СНАЧАЛА сам рантайм бота (pm2 process + .env), потом хелперы. Я сперва лез в notification-скрипты, а главный бот висел сломанным.

**Де-хардкод сделан (локально + VPS, читают tokens.json):**
- `tvorims-bot/nps_reader.py` (import os + чтение `~/artvision-tg-bot/tokens.json`)
- `vps-bot/health-check.sh` (паттерн чтения как notify-telegram.sh)
- Запушено в fix/vps-bot-security; VPS подтянут (конфликт разрешён в пользу де-хардкод версии).

**GitHub Secrets — разобрано (Антон спросил «зачем»):**
- НЕ нужны для токена: 2 workflow (`bot-healthcheck.yml`, `read_nps.yml`) — РУЧНЫЕ (workflow_dispatch), главный путь = запуск де-хардкоженного nps_reader.py на VPS. Удалять НЕ надо (не мешают).
- Секреты `TELEGRAM_BOT_TOKEN`/`TG_BOT_TOKEN`/`TELEGRAM_BACKUP_TOKEN_1` содержат СТАРЫЙ мёртвый токен (от января). Если scheduled Action их юзает — падает. Все значения Secrets ДУБЛИРОВАНЫ в приватном tokens.json (ничего не потеряется).

**ОСТАЛОСЬ (косметика, LOW, свежая сессия):**
1. Мёртвый токен-литерал в fallback 2 YAML (`read_nps.yml:21`, `bot-healthcheck.yml`) — не триггерится (fallback). Заменить на чтение `/root/artvision-data/tokens.json` (Edit промахнулся из-за escape-кавычек YAML — делать на свежем контексте).
2. Опц: `gh secret set TELEGRAM_BOT_TOKEN`/`TG_BOT_TOKEN` новым токеном (если scheduled Actions используют).
3. Стас resync (его машина).

**Гача:** локальный `~/artvision-data/tokens.json` portal_bot = СТРОКА (я перезаписал dict), на VPS = dict {token,...}. notify-скрипты обрабатывают оба (`t["token"] if isinstance(t,dict) else t`). Для консистентности можно вернуть dict локально (LOW).

**Новый токен avportal_bot: только в приватных tokens.json (локально стр + VPS dict). НЕ в публичном репо. Старые мертвы.**
