# Git Auto-Commit

После изменения файлов автоматически: `git add` → `git commit` → `git push`.

Формат: `<type>: <short description>` + `Co-Authored-By: Claude <noreply@anthropic.com>`
Типы: feat, fix, docs, refactor, style, chore

**НЕ коммитить:** .env, credentials, keys (кроме tokens.json), .claude_temp_scripts/.
**tokens.json:** сообщить что изменилось → спросить подтверждение → закоммитить.
**"sync" / "пуш":** выполнять сразу без подтверждения.

## Синхронизация

### Протокол
- **Начало сессии:** `git pull` + прочитать `sync/SYNC_STATUS.md` + `~/.claude/scripts/sync-memory.sh pull`
- **Конец сессии:** обновить SYNC_STATUS.md + `~/.claude/scripts/sync-memory.sh push` + git push

### Проекты

| Проект | Путь |
|--------|------|
| artvision-data | `/Users/antonk/artvision-data` |
| artvision-tg-bot | `/Users/antonk/artvision-tg-bot` |
| devops-agent | `/Users/antonk/devops-agent` |

### Аккаунты
- `justtrance@gmail.com` — основной (полные права)
- `adw.artvision.pro@gmail.com` — рабочий (полные права, планируется ограничение)

Между аккаунтами сессии НЕ видны — используй SYNC_STATUS.md через git.
