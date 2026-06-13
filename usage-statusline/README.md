# usage-statusline — реальные лимиты `/usage` в статуслайне + предупреждения

Показывает в статуслайне Claude Code **настоящие проценты лимитов плана** — те же, что и команда `/usage`, — и предупреждает заранее, когда лимит на исходе.

```
stan@host | Opus 4.8 | my-home | master* | ctx:5% | $1.06 | 5h:9% wk:2%
```

- **`5h:N%`** — 5-часовое окно сессии. Общее по аккаунту → учитывает и другие устройства.
- **`wk:N%`** — недельный лимит (все модели), сброс как в `/usage`.
- Цвет: зелёный <50 · жёлтый ≥50 (за половину) · красный ≥80 (на исходе) · `~` = данные старше 5 мин.

Плюс **активное предупреждение** в чате (хук `usage-warn.sh`) при входе в полосу:
неделя — 50/70/80/90/97%, 5ч-окно — 50/80/95% (дедуп раз в 6 ч).

## Как работает

Источник — эндпоинт `/api/oauth/usage` (его же дёргает встроенный `/usage`), запрос идёт OAuth-токеном из `~/.claude/.credentials.json`.

- `usage-refresh.sh` — тянет эндпоинт и пишет кэш `~/.claude/.usage-cache.json`.
- `statusline.sh` — читает кэш мгновенно; если кэш старше 60 с, запускает `usage-refresh.sh` в фоне (не чаще раза в 10 с, throttle-метка `~/.claude/.usage-refresh.attempt`). Рендер сеть не ждёт.
- `hooks/usage-warn.sh` — на отправку промпта читает тот же кэш и предупреждает по полосам.

Опрос не по таймеру: запрос уходит только при активности (рендер статуслайна / новый промпт) и не чаще ~раза в минуту; при простое — ноль запросов. Демона/cron нет.

## Файлы

| Файл | Куда ставится |
|---|---|
| `statusline.sh` | `~/.claude/statusline.sh` |
| `usage-refresh.sh` | `~/.claude/usage-refresh.sh` |
| `hooks/usage-warn.sh` | `~/.claude/hooks/usage-warn.sh` |
| `install.sh` | — (запускается отсюда) |

## Установка

```bash
bash install.sh
```
Копирует скрипты в `~/.claude` и прописывает в `~/.claude/settings.json`:
- `statusLine.command` → `~/.claude/statusline.sh`
- `UserPromptSubmit`-хук → `~/.claude/hooks/usage-warn.sh`

Существующие ключи settings.json (env, плагины и т.д.) сохраняются; рядом кладётся бэкап `settings.json.bak.usage-statusline`. Затем перезапусти сессию Claude Code.

## Зависимости
`bash`, `python3`, `curl`. Без `flock`/jq — переносимо на macOS и Linux.

## Требуется
Подписка Claude (Pro/Max) с OAuth-логином — токен лежит в `~/.claude/.credentials.json`.
На API-ключе (без OAuth-сессии) эндпоинт `/api/oauth/usage` недоступен.

## Откат

1. Восстановить settings.json из бэкапа:
   ```bash
   mv ~/.claude/settings.json.bak.usage-statusline ~/.claude/settings.json
   ```
   (или вручную убрать `statusLine` / хук `usage-warn.sh`).
2. При желании удалить скрипты:
   ```bash
   rm -f ~/.claude/usage-refresh.sh ~/.claude/.usage-cache.json ~/.claude/.usage-refresh.attempt
   ```
   `statusline.sh` и `hooks/usage-warn.sh` замени своими прежними версиями, если они были.
