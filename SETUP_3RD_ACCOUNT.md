# SETUP — 3-й аккаунт Claude Max 20x (или другая машина / друг)

**Дата ревизии:** 2026-04-21
**Текущий стейт окружения:** 169 skills / 30 rules / 61 hooks / 199 agents / 107 scripts / 156 memory-файлов / 58 LaunchAgents

## Какой у тебя сценарий?

| Сценарий | Суть | Инструкция |
|---|---|---|
| **A. Тот же Mac, тот же пользователь, 3-й аккаунт Anthropic** | `~/` общий, `~/.claude/` общий — нужно только переключить авторизацию. **Ничего ставить не надо.** | [§1](#a-тот-же-mac-тот-же-пользователь) |
| **B. Другая машина (свой ноут), тот же `antonk`** | Полная установка: brew, deps, clone репо, memory restore, tokens.json transfer | [§2](#b-другая-машина-тот-же-пользователь) |
| **C. Друг — его машина, его пользователь** | Публичная opensource-версия без клиентских данных/memory. Отдельный пайплайн через `opensource-forker` | [§3](#c-друг-другой-пользователь) |

---

## A. Тот же Mac, тот же пользователь

Переключение между двумя уже настроенными аккаунтами → теперь три.

```bash
# 1. Разлогиниться с текущего
claude auth logout

# 2. Залогиниться 3-м аккаунтом
claude auth login
# → откроется браузер, использовать email третьего аккаунта Claude Max

# 3. Проверить
claude auth status
/status    # внутри claude — покажет email и Usage
```

**Что общее между аккаунтами на одной машине:**
- `~/.claude/skills/`, `~/.claude/rules/`, `~/.claude/hooks/`, `~/.claude/scripts/`, `~/.claude/agents/`, `~/.claude/commands/`
- `~/.claude/projects/-Users-antonk/memory/` (156 файлов, auto-memory)
- `~/artvision-data/`, `~/artvision-tg-bot/`, `~/devops-agent/`
- `~/artvision-data/tokens.json` (секреты)
- `~/Library/LaunchAgents/` (58 plist — **работают независимо от аккаунта Claude**)
- SSH-ключи, gh auth, Telethon sessions

**Что РАЗНОЕ:**
- `~/.claude/history.jsonl` (история сообщений per Anthropic account)
- `~/.claude/projects/*/sessions/*.jsonl` (сессии per account)
- Лимит Claude Max (у каждого аккаунта свой weekly-reset)

**Переключение без потери контекста:**
```bash
# Перед переключением — handover в git чтобы 3-й аккаунт поднял:
# 1. Заверши сессию, сделай git push artvision-data
# 2. Разлогинься, залогинься 3-м
# 3. На 3-м аккаунте: claude, затем `claude --resume` (если нужна старая сессия — её нет, только handover через sync/)
```

Подробнее про переключение: `~/.claude/rules/session-commands.md` §«Команды для обоих аккаунтов».

---

## B. Другая машина, тот же пользователь

### One-liner установка

```bash
curl -sL https://raw.githubusercontent.com/artvision-agency/claude-code-settings/main/scripts/full-setup.sh | bash
```

Скрипт делает 18 шагов:

| # | Что |
|---|---|
| 1 | Homebrew |
| 2 | GitHub CLI + проверка auth (если не залогинен — попросит `gh auth login`) |
| 3 | `gh repo clone artvision-agency/claude-code-settings ~/.claude` |
| 4 | bun, node, python3, uv |
| 5 | `brew bundle` из `~/.claude/exports/Brewfile` (если экспортирован донором) |
| 6 | `pip install -r ~/.claude/exports/pip-freeze.txt` + playwright browsers |
| 7 | bun globals (agent-browser, hex-ssh-mcp, vercel, wrangler, lighthouse, pa11y) |
| 8 | Clone `artvision-data`, `artvision-tg-bot`, `devops-agent` |
| 9 | Clone `external-agents/{voltagent-subagents, voltagent-skills, alirezarezvani-skills}` + wshobson-agents marketplace |
| 10 | **Восстановление memory**: `rsync artvision-data/.claude/memory-sync/ → ~/.claude/projects/-Users-$(whoami)/memory/` (156 .md) + `rules-global/ → ~/.claude/rules/` (31 .md) |
| 11 | Symlinks c-level skills из alirezarezvani-skills |
| 12 | Local MCP: `llm-consilium`, `medical-mcp`, `healthcare-mcp-public` |
| 13 | `chmod +x` на hooks/scripts |
| 14 | Screaming Frog wrapper `~/.local/bin/sf` (если Spider установлен) |
| 15 | `cc-update` / `cc-share` команды |
| 16 | `tokens.json` — либо из template, либо scp с донора, либо `sync-tokens.sh pull` (см. §4) |
| 17 | Auto-bootstrap в `.zshrc` |
| 18 | Итоговый отчёт |

### Что нужно СНАЧАЛА (prerequisites)

На **донорской машине** (1-й аккаунт) единоразово перед тем как 3-й аккаунт будет ставиться:

```bash
bash ~/.claude/scripts/export-donor-env.sh
cd ~/.claude && git add exports/ && git commit -m "chore: env exports $(date +%Y-%m-%d)" && git push
```

Это закоммитит в `claude-code-settings/exports/`:
- `Brewfile` — все brew formulas/casks
- `pip-freeze.txt` — Python deps
- `bun-globals.txt`, `npm-globals.txt` — JS deps
- `mcp-servers.txt` — список MCP
- `launchagents-list.txt` — имена LaunchAgents
- `tokens-keys.txt` — какие ключи есть в tokens.json (без значений)
- `counts.txt` — актуальные счётчики
- **Master memory** пушнется в `artvision-data/.claude/memory-sync/`

### Передача секретов (не через git)

После `full-setup.sh` на новой машине нужно ОТДЕЛЬНО получить:

```bash
# Вариант 1 (рекомендуется) — через VPS-канал, который уже автоматизирован:
#   1. Скопируй SSH-ключ к VPS с донора:
scp -r ~/.ssh/                             NEW_MACHINE:~/.ssh/
#   2. На новой машине:
~/.claude/scripts/sync-tokens.sh pull       # подтянет tokens.json с VPS
# Дальше любые правки tokens.json будут авто-синкаться через post-edit hook
# (см. ~/.claude/hooks/post-edit-tokens-sync.sh + start-sync-tokens.sh)

# Вариант 2 — прямой scp с донора (если VPS недоступен):
scp ~/artvision-data/tokens.json           NEW_MACHINE:~/artvision-data/
scp -r ~/.ssh/                             NEW_MACHINE:~/.ssh/

# Опционально (если та же Anthropic установка на второй машине):
scp ~/.claude/.secrets                     NEW_MACHINE:~/.claude/  # gitignored
```

**Авто-синк tokens.json (установлено 2026-05-05):**
- Канал: `root@80.90.181.152:/root/.claude-sync/tokens.json` (chmod 600)
- Push при каждом изменении локального файла (PostToolUse Edit/Write hook)
- Pull на старте каждой Claude-сессии (SessionStart hook)
- SHA-checksum + mtime-merge — newer wins, идемпотентно
- Ручной запуск: `~/.claude/scripts/sync-tokens.sh [push|pull|sync]`

**НЕ копировать:**
- Telethon `.session` файлы (риск флуд-вейта при параллельном логине с 2 машин — перелогиниться)
- `~/.claude/history.jsonl`, `~/.claude/projects/*/sessions/` (сессии per machine/account)
- `node_modules/`, `.venv/`, `__pycache__/` (пересоздать)

### После установки

```bash
claude auth login    # 3-м аккаунтом
cd ~ && claude        # запуск, проверить что CLAUDE.md загружается, memory видна
```

Smoke-проверка:
```bash
ls ~/.claude/projects/-Users-$(whoami)/memory/*.md | wc -l   # должно быть ~156
ls ~/.claude/skills/*/SKILL.md 2>/dev/null | wc -l          # ~130+
ls ~/.claude/rules/*.md | wc -l                              # ~30
gh repo list artvision-agency                                # доступ к репо
```

### §4 LaunchAgents (опционально)

58 plist-ов в `~/Library/LaunchAgents/`: TG listener/responder, vps-healer, ai-evolve, asana-sync, evening-digest, combine-auto, и т.д.

**Вариант A (рекомендуется)** — ставить только **уникальные для этой машины** демоны, не дублировать cron с донорской.

**Вариант B** — полный клон с переименованием Label (`pro.artvision.*` → `pro.artvision3.*`):

```bash
# С донорской машины
scp ~/Library/LaunchAgents/{pro,com}.artvision.*.plist NEW_MACHINE:~/Library/LaunchAgents/

# На новой машине — переименовать Label чтобы не конфликтовать:
# (только если обе машины будут работать одновременно с одним Asana/TG)
cd ~/Library/LaunchAgents
for f in pro.artvision.*.plist; do
    new_label="${f/pro.artvision/pro.artvision3}"
    mv "$f" "$new_label"
    sed -i '' "s|pro.artvision|pro.artvision3|g" "$new_label"
done

# Загрузить
for f in ~/Library/LaunchAgents/pro.artvision3.*.plist; do
    launchctl bootstrap "gui/$UID" "$f"
done

# Проверка
launchctl list | grep pro.artvision3 | wc -l
```

**Что НЕЛЬЗЯ дублировать** (иначе 2× действие):
- `asana-sync*`, `asana-overdue`, `asana-andrey-control` — задачи создадутся 2 раза
- `tg-listener`, `tg-responder` — 2× ответ пользователю
- `evening-digest`, `habr-ai-digest`, `smm-digest` — 2× публикация
- `daily-git-push`, `daily-tasks-tg`, `combine-auto-morning/evening`
- `backup-tokens`, `vps-backup`, `cloud-backup` — удвоенный трафик

**Можно дублировать:**
- Мониторы (watchdog, healer) — fail-safe OK
- `weekly-learning`, `ai-evolve-prep` — идемпотентны

### Re-login сервисов на новой машине

```bash
claude auth login            # Claude Max
gh auth login                # GitHub (токен repo + read:org)
# Telethon (TG userbot):
python3 -c "from telethon import TelegramClient; TelegramClient('new_session', API_ID, API_HASH).start()"
# MCP с OAuth — через claude mcp (откроется браузер):
#   Google Drive, Gmail, Google Calendar, Asana, Stripe, Vercel, HuggingFace, Figma
```

---

## C. Друг (другой пользователь)

**НЕ используй этот репо как есть** — в нём memory/clients/presales с чувствительными данными.

Отдельный пайплайн — 3 скилла:

```bash
# На твоей машине:
claude                          # запусти
/opensource-forker              # скопирует публичную часть в новую папку
/opensource-sanitizer           # уберёт секреты, PII, клиентские имена
/opensource-packager            # соберёт README, LICENSE, setup.sh
```

Результат — публичный репо с:
- Всеми skills (кроме клиентских)
- Всеми rules (кроме проприетарных процессов)
- Всеми hooks/scripts (кроме auth/tokens)
- Структурным шаблоном `artvision-data/` **без содержимого**
- `tokens.json.template` вместо tokens.json

Друг получает:
```bash
curl -sL https://github.com/<FRIEND-REPO>/raw/main/install.sh | bash
```

---

## Troubleshooting

| Проблема | Решение |
|---|---|
| `gh auth status` fail | `gh auth login` → выбрать SSH или HTTPS → follow prompts |
| `Permission denied` на git push в `~/.claude` | `git remote set-url origin git@github.com:artvision-agency/claude-code-settings.git` + проверить SSH-ключ |
| memory пусто после установки | `~/.claude/scripts/sync-memory.sh pull` (подтянет из artvision-data git-mirror) |
| hook X не срабатывает | `chmod +x ~/.claude/hooks/X.sh` + проверь `~/.claude/settings.json` → `"hooks"` секция |
| LaunchAgent не стартует | `launchctl error $(launchctl print-disabled gui/$UID | grep X)` + `log show --predicate 'processID==<pid>' --last 1h` |
| tokens.json потерялся | `cp ~/.claude/templates/tokens.json.template ~/artvision-data/tokens.json` + заполнить. Или `scp` с донора |
| Claude не видит skills | `ls ~/.claude/skills/` → если меньше 100, `cd ~/.claude && git pull` |

---

## Репозитории

| Репо | URL | Назначение |
|---|---|---|
| claude-code-settings | git@github.com:artvision-agency/claude-code-settings | `~/.claude/` mirror |
| artvision-data | git@github.com:artvision-agency/artvision-data | CRM, knowledge, memory-mirror |
| artvision-tg-bot | git@github.com:artvision-agency/artvision-tg-bot | Telegram-боты |
| devops-agent | git@github.com:artvision-agency/devops-agent | VPS-инфра |

## Связанные документы

- `~/.claude/CLAUDE.md` — глобальные правила + карта memory
- `~/.claude/rules/*.md` — 30 правил работы
- `~/artvision-data/PROJECTS.md` — source of truth по проектам
- `~/artvision-data/TODO.md` — активные задачи
- `~/.claude/SETUP_TELEGRAM_CHANNELS.md` — настройка TG каналов
- `~/.claude/AGENTS_CATALOG.md` — каталог 199 агентов
- `~/.claude/ARTVISION_REPOS.md` — все репо агентства
