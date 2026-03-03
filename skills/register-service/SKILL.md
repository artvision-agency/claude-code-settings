---
name: register-service
description: "Регистрация на сервисах + получение API ключа (end-to-end). Playwright: регистрация → подтверждение email через Gmail → создание API key → сохранение в tokens.json. НЕ останавливается до получения ключа."
disable-model-invocation: true
allowed-tools:
  - mcp__plugin_playwright_playwright__browser_navigate
  - mcp__plugin_playwright_playwright__browser_click
  - mcp__plugin_playwright_playwright__browser_fill_form
  - mcp__plugin_playwright_playwright__browser_snapshot
  - mcp__plugin_playwright_playwright__browser_take_screenshot
  - mcp__plugin_playwright_playwright__browser_wait_for
  - mcp__plugin_playwright_playwright__browser_type
  - mcp__plugin_playwright_playwright__browser_press_key
  - mcp__plugin_playwright_playwright__browser_tabs
  - mcp__plugin_playwright_playwright__browser_select_option
  - mcp__plugin_playwright_playwright__browser_handle_dialog
  - Read
  - Write
  - Edit
  - Bash
  - Grep
  - Glob
  - AskUserQuestion
---

# /register-service — Регистрация + получение API ключа

## ЦЕЛЬ: API ключ в tokens.json

Регистрация — НЕ самоцель. Скилл считается ЗАВЕРШЁННЫМ только когда:
1. Аккаунт зарегистрирован и подтверждён
2. API ключ получен
3. API ключ протестирован (curl → 200)
4. API ключ сохранён в `tokens.json`
5. `accounts.md` обновлён

**НЕ ОСТАНАВЛИВАТЬСЯ** на этапе "email отправлен" или "аккаунт создан". Довести до ключа!

## Использование
```
/register-service <сервис> [email_override]
```

Примеры:
- `/register-service remove.bg` — зарегистрирует + получит API key
- `/register-service yandex.cloud` — зарегистрирует + получит API key
- `/register-service openai antoniokmr@gmail.com` — с конкретным email

## Аккаунты по умолчанию

Прочитай файл памяти для актуальных данных:
```
/Users/antonk/.claude/projects/-Users-antonk/memory/accounts.md
```

### Правило выбора email:
- **Русские сервисы** (yandex, vk, mail.ru, timeweb, selectel, ru-домены): `dune87@yandex.ru`
- **Международные сервисы** (всё остальное): `antoniokmr@gmail.com`
- **Пароль:** `Testtest123]`

### Телефон (если требуется):
- Спросить у пользователя номер через AskUserQuestion
- SMS-код тоже запросить у пользователя (Claude не может читать SMS)

## Алгоритм

### 0. Подготовка браузера (КРИТИЧНО!)
```
# Chrome БЛОКИРУЕТ Playwright! Закрыть ПЕРЕД запуском:
osascript -e 'tell application "Google Chrome" to quit'
sleep 2

# Если Playwright всё равно не запускается — очистить lock:
rm -rf /tmp/playwright-*
```
**Опыт:** Playwright использует Chrome, и если Chrome уже запущен — новая вкладка откроется в текущем сеансе вместо управляемого окна. ВСЕГДА закрывать Chrome первым делом.

### 1. Подготовка
- Определить тип сервиса (RU/international)
- Выбрать email и пароль
- Проверить в `accounts.md` — может аккаунт уже есть
- Проверить в `tokens.json` — может API key уже есть

### 2. Регистрация через Playwright
```
browser_navigate → страница регистрации
browser_snapshot → понять структуру формы (поля, кнопки, чекбоксы)
browser_fill_form → email, пароль, подтверждение пароля
browser_click → чекбокс terms, кнопка "Register"/"Sign Up"
browser_wait_for → ожидание результата
```

**Важные нюансы:**
- **Cookie banner** часто перекрывает элементы — кликнуть "Accept all"/"Принять все" ПЕРВЫМ ДЕЛОМ
- **Повторная регистрация** — если email уже зарегистрирован, сервис покажет ошибку. Попробовать залогиниться с паролем.
- **hCaptcha** — на некоторых сервисах (Kaleido/remove.bg) невидимая капча проходит автоматически
- **Язык интерфейса** — сервисы могут переключиться на русский по GeoIP. Не паниковать, элементы те же.

### 3. Подтверждение email (ПОЛНЫЙ АЛГОРИТМ)

Многие сервисы требуют подтверждения email. Полный алгоритм из реального опыта:

#### 3.1. Gmail (antoniokmr@gmail.com)
```
1. browser_navigate → https://mail.google.com
2. Google может потребовать авторизацию:
   - Если показывает форму логина → ввести email → "Далее"
   - Если passkey/2FA → кликнуть "Другой способ" / "Try another way"
   - Google может спросить домашний адрес, фото профиля — ВСЁ ПРОПУСКАТЬ (Skip/Not now)
3. Дождаться загрузки inbox
4. Искать письмо подтверждения:
   a) Поиск в inbox по имени сервиса
   b) Проверить вкладки: "Промоакции", "Оповещения", "Соцсети"
   c) **ОБЯЗАТЕЛЬНО проверить СПАМ** — confirmation emails ЧАСТО попадают в спам!
      - Кликнуть "Спам" в боковом меню
      - Искать письмо от сервиса
5. Открыть письмо → найти ссылку "Activate"/"Confirm"/"Подтвердить"
6. Кликнуть ссылку → откроется в новой вкладке
7. Переключиться на новую вкладку (browser_tabs → select)
8. Проверить что аккаунт активирован
```

**Ключевой урок:** Gmail IMAP НЕ работает с обычным паролем (требует App Password + 2FA). Используй ТОЛЬКО Playwright для чтения почты!

#### 3.2. Yandex (dune87@yandex.ru)
```
1. browser_navigate → https://mail.yandex.ru
2. Ввести логин/пароль dune87@yandex.ru
3. Найти письмо подтверждения
4. Кликнуть ссылку активации
```

#### 3.3. Если автоматически не получается
- Попросить пользователя через AskUserQuestion: "Подтверди email — открой почту и кликни ссылку"
- Сообщить от какого отправителя ждать письмо
- После подтверждения пользователем — продолжить автоматически

### 4. Получение API ключа
После успешной регистрации и подтверждения:
```
browser_navigate → dashboard/api-key/settings страница
browser_snapshot → найти кнопку "Create API Key" / "Generate"
browser_click → создать ключ
browser_snapshot → скопировать ключ со страницы
```

**Нюансы:**
- Некоторые сервисы (remove.bg) показывают ключ только 1 раз при создании — СКОПИРОВАТЬ СРАЗУ
- API key может быть в `<code>` или `<input>` элементе — смотри snapshot внимательно
- Dashboard может быть на поддомене (accounts.kaleido.ai для remove.bg)

### 5. Сохранение
```python
# Добавить в tokens.json:
python3 -c "
import json
with open('/Users/antonk/artvision-data/tokens.json', 'r') as f:
    d = json.load(f)
d['service_name'] = {
    '_desc': 'Service description',
    'email': 'email@used.com',
    'api_key': 'THE_KEY',
    'plan': 'free',
    'registered': '2026-XX-XX',
    'limits': 'N requests/month'
}
d['_updated'] = '2026-XX-XX'
with open('/Users/antonk/artvision-data/tokens.json', 'w') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
"
```

- API key → `tokens.json` (в соответствующую секцию)
- Обновить `accounts.md` — статус, дата, наличие ключа
- **tokens.json = спросить подтверждение** перед коммитом (правило CLAUDE.md)
- Сообщить пользователю результат

### 6. Тестирование API ключа
```bash
# Проверить что ключ работает:
curl -s -H "X-Api-Key: THE_KEY" "https://api.service.com/account"
# Должен вернуть 200 и данные аккаунта
```

## Известные сервисы (из опыта)

### remove.bg (Kaleido)
- **Регистрация:** https://www.remove.bg/users/sign_up
- **Подтверждение:** email от noreply@remove.bg (часто в СПАМЕ Gmail!)
- **Аккаунт через:** accounts.kaleido.ai (общий для remove.bg, unscreen, designify)
- **Dashboard:** https://www.remove.bg/dashboard#api-key
- **API key:** кнопка "New API Key" → показывает ключ в модальном окне
- **Лимиты free:** 50 API previews/мес (до 625x400), 1 credit (full HD)
- **Cookie banner:** перекрывает интерфейс — кликнуть "Принять все" первым делом
- **API test:** `curl -s -H "X-Api-Key: KEY" "https://api.remove.bg/v1.0/account"`
- **Капча:** hCaptcha невидимая — проходит автоматически

## Ограничения

### Что НЕ может сделать автоматически:
- **SMS-верификация** — нужен физический доступ к телефону. Решение: запросить код у пользователя через AskUserQuestion
- **Сложная капча** — image captcha, puzzle, "выберите все картинки с...". Решение: попросить пользователя решить в окне браузера
- **2FA/TOTP** — нужен authenticator app. Решение: запросить код у пользователя

### Что МОЖЕТ (подтверждено опытом):
- Закрывать Chrome и запускать Playwright
- Заполнять формы регистрации
- Принимать cookies и terms of service
- Проходить невидимые капчи (hCaptcha/reCAPTCHA v3)
- Логиниться в Gmail через Playwright (с обходом passkey через "Другой способ")
- Находить confirmation emails (включая СПАМ-папку!)
- Кликать ссылки активации
- Создавать и копировать API ключи
- Переключаться между вкладками браузера
- Сохранять credentials в tokens.json и accounts.md
- Тестировать API ключи через curl
- Логиниться в сервисы с email/паролем

## Формат tokens.json

```json
{
  "service_name": {
    "_desc": "Service — что делает",
    "email": "antoniokmr@gmail.com",
    "api_key": "key_here",
    "plan": "free",
    "registered": "2026-02-23",
    "limits": "50 API previews/month"
  }
}
```

## Безопасность
- Пароль НЕ хранить в tokens.json (только API ключи)
- Пароль берётся из accounts.md (в memory, не в git)
- tokens.json — коммитить только после подтверждения пользователя
- При первом логине в Gmail — Google может задавать вопросы безопасности (адрес, фото). Пропускать все.

## Критерий завершения (Definition of Done)

Скилл НЕ ЗАВЕРШЁН пока не выполнены ВСЕ пункты:

- [ ] Аккаунт зарегистрирован (форма заполнена, submit прошёл)
- [ ] Email подтверждён (ссылка активации кликнута, аккаунт активен)
- [ ] API ключ создан (на dashboard сервиса)
- [ ] API ключ протестирован (`curl → HTTP 200`)
- [ ] API ключ сохранён в `tokens.json` (через python3 скрипт)
- [ ] `accounts.md` обновлён (статус Active, ключ указан)
- [ ] Пользователю сообщён результат (ключ, лимиты, план)

**Если сервис НЕ предоставляет API** — завершить после подтверждения email и сообщить пользователю что API недоступен.
