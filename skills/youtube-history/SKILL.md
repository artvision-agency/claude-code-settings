---
name: youtube-history
description: Автоматически извлекает историю просмотров YouTube через Safari AppleScript + JS. Работает потому что (a) Ghostty имеет Accessibility permission, (b) Safari AllowJavaScriptFromAppleEvents=true, (c) Safari уже залогинен в Google. Извлекает title, URL, канал, даты. Поддерживает /feed/history и myactivity.google.com/product/youtube. Триггеры — 'история youtube', 'что смотрел на ютубе', 'youtube history', 'youtube watch history', 'моя история просмотров'.
---

# youtube-history — история просмотров YouTube без API

## Когда использовать
- Нужно вспомнить конкретное видео которое смотрел
- Проанализировать что смотрит пользователь (интересы, контент-план)
- Найти ролик для совместного монтажа (как в инциденте 2026-04-18)

## Почему не через API
YouTube Data API v3 НЕ отдаёт watch history — Google убрал endpoint ~2016. Единственный способ читать историю программно = через залогиненный браузер.

## Пререквизиты
1. Safari AllowJavaScriptFromAppleEvents=true:
   ```bash
   defaults write com.apple.Safari AllowJavaScriptFromAppleEvents -bool true
   defaults write com.apple.Safari IncludeDevelopMenu -bool true
   # Перезапустить Safari
   ```
2. Safari залогинен в Google (проверить: открыть youtube.com → должен показать аватар)
3. Ghostty/terminal имеет Accessibility permission (System Settings → Privacy)

## Использование

```bash
python3 ~/.claude/skills/youtube-history/fetch.py
# JSON output: [{title, url, channel, section}]

# С фильтром
python3 ~/.claude/skills/youtube-history/fetch.py --search "галустян"
python3 ~/.claude/skills/youtube-history/fetch.py --limit 50
```

## Алгоритм

1. Открыть https://www.youtube.com/feed/history в Safari
2. Дождаться загрузки (2-3 сек)
3. Если страница "История недоступна — Войти" → JS-клик на кнопку "Войти" → Google OAuth выберет существующий аккаунт автоматом
4. Проскроллить вниз несколько раз (YouTube использует infinite scroll)
5. JS-query: `document.querySelectorAll('h3, #video-title')` + закрытый `<a>` с href
6. Dedupe по title
7. Также извлечь date markers (Thursday, Mar 3) из `ytd-item-section-header-renderer`
8. Вернуть JSON

## Известные ограничения
- **History на паузе** (myactivity.google.com/activitycontrols/youtube) → список будет пустой. Проверь статус.
- **Другой аккаунт в iPhone** — история с iPhone sync'ается только если Google-аккаунт тот же. Проверь который залогинен в приложении YouTube.
- **Инкогнито просмотры** не логируются нигде.
- Max ~50-100 последних роликов через UI. Для полной истории → Google Takeout.

## История

- **2026-04-18:** Создан после инцидента когда не могли достать историю. Попробовали API (нет endpoint), Chrome SQLite (стар), Safari History.db (TCC блок), Playwright (не залогинен). Сработало через существующую Safari-сессию + AppleScript JS, как с github-auth-auto.
