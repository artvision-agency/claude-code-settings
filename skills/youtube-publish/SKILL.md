---
name: youtube-publish
description: Загрузка видео на YouTube (включая Shorts) через YouTube Data API v3 OAuth. НЕ через GUI Studio — надёжный программный путь. Поддерживает title/description/tags/privacy. Триггеры — 'залить на youtube', 'опубликовать shorts', 'youtube upload', 'upload видео youtube'.
---

# youtube-publish — загрузка видео на YouTube через API

## Когда использовать

- Надо опубликовать готовый ролик (обычное видео или Shorts)
- Автоматизация публикации серии роликов
- GUI-автоматизация через Safari/Playwright ненадёжна → берём API

## Пререквизиты

1. OAuth client `client_secret.json` в `~/artvision-data/scripts/`
2. Token после первого OAuth flow: `~/artvision-data/scripts/youtube_token.json`
3. scopes: `youtube.upload`, `youtube.force-ssl`, `youtube`
4. Python deps: `google-auth`, `google-auth-oauthlib`, `googleapiclient`

## Первый запуск (если token отсутствует или истёк)

```bash
python3 ~/.claude/skills/youtube-publish/setup.py
# Откроется браузер → выбираешь Google-аккаунт → подтверждаешь scope → готово
```

## Публикация

```bash
python3 ~/.claude/skills/youtube-publish/upload.py \
  --file ~/Desktop/montage_A_WithSubs.mp4 \
  --title "Заголовок видео" \
  --description "Описание..." \
  --privacy unlisted \
  --tags "мем,квн,ремонт"

# Shorts detection автоматом если длительность < 60 сек + вертикальный формат
```

## Privacy options
- `private` — только ты
- `unlisted` — по ссылке (безопасно для теста)
- `public` — всем

## Shorts правила
- Длительность < 60 сек
- Вертикальный формат (9:16)
- Можно добавить `#Shorts` в title/description для явной метки

## История

- **2026-04-18:** Созданo после инцидента. Хотели опубликовать мем Галустян+Мастерская, GUI Studio upload через System Events не сработал (Cmd+Shift+G конфликтует с Safari). Перешли на API.
