---
name: note-search
description: >
  Бесплатный поиск по личным заметкам Антона ОДНОВРЕМЕННО в Telegram «Избранное»
  (Saved Messages) и Google Keep заметках justtrance@gmail.com. Заточен под поиск
  по 3 цифрам (#касса 235 191 448 и т.п.) и по тексту. Триггеры: 'найди в избранном',
  'поиск по заметкам', 'найди по цифрам', '#касса', 'note search', 'keep заметки',
  'тг избранное поиск', 'найди в keep', 'искать по 3 цифрам', 'найди записку'.
---

# note-search — поиск по ТГ-Избранному + Google Keep

Единый бесплатный поиск по двум личным источникам заметок Антона:
1. **Telegram «Избранное»** (Saved Messages) — через Telethon (@AntonKamer).
2. **Google Keep** заметки `justtrance@gmail.com` — через gkeepapi.

Инструмент: `~/.claude/scripts/note-search.py`. Всё бесплатно, без платных API.

## Как вызывать

```bash
# AND (по умолчанию): записи со ВСЕМИ перечисленными числами/словами
python3 ~/.claude/scripts/note-search.py 235 191 448

# OR: с любым из
python3 ~/.claude/scripts/note-search.py --any 235 191 448

# текст
python3 ~/.claude/scripts/note-search.py "#касса"

# только один источник
python3 ~/.claude/scripts/note-search.py --tg-only 235 191
python3 ~/.claude/scripts/note-search.py --keep-only касса
```

- Числа матчатся как ЦЕЛЫЕ токены (`\b235\b`) — не ловит «235» внутри URL.
- TG сканирует Saved Messages (по умолчанию 5000 последних), `--limit N` глубже.
- Сессия Telethon копируется во временный файл → не конфликтует с фоновым демоном (database is locked).

## Настройка Google Keep (одноразово, бесплатно)

Keep требует master-token (хранится в `tokens.json/google_keep`). Один раз:

**Вариант A — oauth_token из браузера:**
1. Открыть `https://accounts.google.com/EmbeddedSetup`, войти как justtrance@gmail.com.
2. DevTools → Application → Cookies → скопировать cookie `oauth_token` (начинается с `oauth2_4/...`).
3. `python3 ~/.claude/scripts/note-search.py --keep-auth-token 'oauth2_4/...'`

**Вариант B — app-password** (нужен включённый 2FA на аккаунте):
`python3 ~/.claude/scripts/note-search.py --keep-auth-app 'xxxx xxxx xxxx xxxx'`

После настройки токен сохраняется навсегда — Keep ищется автоматически вместе с ТГ.

## Финансы
Записи `#касса` — кассовые суммы (финансовые данные). Показ сводок на экране —
правило `finance-password-gate` (пароль 151064). Поиск/нахождение конкретной записи
по запросу Антона — операционно, не сводка.

## Зависимости
`pip install --user telethon gkeepapi gpsoauth` (уже установлено 2026-06-28).
