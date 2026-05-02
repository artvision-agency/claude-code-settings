# orm-pulse — настройка ручных сессий и cookies

> Что делать ОДИН РАЗ при первом запуске для нового клиента или восстановлении сессий.

## 1. Telethon (TG export, alerts, discover) — уже настроено

Сессия в `~/.claude/state/telethon_session.session` создана при настройке Telethon listener.
Скрипты делают клон-сессию, не блокируют listener.

Проверка: `python3 ~/.claude/skills/orm-pulse/scripts/tg-discover-serm.py bluemart --scan-subs` должен вывести 5+ matches.

## 2. Google Sheets (sheet-snapshot.sh) — Safari cookies

```bash
# Если sheet-snapshot падает с 401/403:
# 1. Открой sheet в Safari, залогинься
# 2. Куки автоматически читаются из ~/Library/Cookies/...
```

Скрипт берёт cookies из Safari через `security`/curl. Если перестало работать — в Safari сделать pull таблицы вручную, перезапустить.

## 3. QComment — API key

Уже в tokens.json (`qcomment.api_code`), скрипт `qcomment-monitor.py` работает напрямую через POST /api/projects + /api/balance + /api/comments.

Live dashboard: https://artvision.pro/qcomment/ (admin/111)

## 4. Kupi-otziv — cookie session (требует setup от Антона)

```bash
# Один раз:
# 1) Safari → kupi-otziv.ru/kabinet/ → залогиниться (borisovaloves@yandex.ru)
# 2) Cookie-Editor extension → export Netscape txt
# 3) Сохранить в:
mkdir -p ~/.claude/.cache
# Положить файл в ~/.claude/.cache/kupi-otziv-cookies.txt

# Прогон:
python3 ~/.claude/skills/orm-pulse/scripts/kupi-otziv-monitor.py bluemart
# Должен вывести: BALANCE / PROJECTS / ORDERS / TASKS

# Путь к cookies прописан в tokens.json.kupi-otziv.cookies_file
```

Текущий статус: 0 заказов, 0 ₽ баланс, бриф проекта 1101 пуст.

## 5. Kwork — manual session (требует ручного login)

Background-агент 03.05 не смог пройти SmartCaptcha через Playwright (mobile-first home-page блокирует автоматику).

**Вариант A — ручная Chrome-сессия:**

```bash
osascript -e 'tell application "Google Chrome" to quit'
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --user-data-dir=/tmp/kwork-pw-profile \
  --disable-blink-features=AutomationControlled \
  https://kwork.ru/login

# В Chrome:
# - login: dune87@yandex.ru / Newboroda123
# - решить SmartCaptcha вручную
# - дойти до "Мои заказы" чтобы убедиться что сессия работает
# - закрыть Chrome (профиль сохранится)

# Проверка:
ls -la /tmp/kwork-pw-profile/Default/Cookies
# должен быть SQLite с актуальными cookies
```

После этого скрипт `python3 /tmp/kwork-login-v2.py` (от агента) сможет переиспользовать профиль.

**Вариант B — Kwork Public API (рекомендуется в долгосрок):**

1. https://kwork.ru/personal_cabinet → API → создать токен
2. В tokens.json: `"kwork": {"api_token": "..."}`
3. Endpoints: `actor`, `dialogs`, `messages`, `orders`
4. Без Playwright/captcha — стабильнее

## 6. Zenno.club — auth НЕ требуется

Целевые треды `84969`, `99134`, `113555` оказались публичными. Креды в tokens.json.zenno_club устарели (оба пароля отвергнуты), но они и не нужны для текущего research.

Финальный отчёт: https://artvision.pro/orm-research/bluemart-zenno-deepdive-2026-05-03.html

## 7. SBIS / VPS / прочее — общая Artvision-инфра

Не часть orm-pulse, см. соответствующие скиллы (`/sbis-support`, etc).

---

## Расписание автоматики (cron / LaunchAgent)

| Что | Когда | Кто |
|-----|-------|-----|
| reviews-tracker (rating/total) | 09/13/18/22 МСК | `pro.artvision.orm-pulse.bluemart-tracker` |
| auto-refresh (qcomment + sheet + orders-state + command-center + alerts) | каждые 30 мин | `pro.artvision.orm-pulse.bluemart-refresh` |

Проверка: `launchctl list | grep orm-pulse`

Управление:
```bash
launchctl unload ~/Library/LaunchAgents/pro.artvision.orm-pulse.bluemart-refresh.plist
launchctl load ~/Library/LaunchAgents/pro.artvision.orm-pulse.bluemart-refresh.plist
tail -f ~/.claude/logs/orm-pulse-bluemart.log
```

## Live URLs (внутренние, X-Robots-Tag noindex)

- 🎯 **Command Center**: https://artvision.pro/orm-command-center/bluemart.html
- 📊 QComment dashboard: https://artvision.pro/qcomment/ (admin/111)
- 🤝 Contractors: https://artvision.pro/orm-contractors.html
- 🔬 Research: https://artvision.pro/orm-research/bluemart-yandex-moderation-2026-05-03.html
- 🔬 Research: https://artvision.pro/orm-research/bluemart-zenno-deepdive-2026-05-03.html
