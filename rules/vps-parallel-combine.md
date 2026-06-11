# VPS Parallel Combine — параллель /combine на двух аккаунтах Claude Max

> **Установлено:** 2026-05-25 (сессия a09dc922) по запросу Антона «разные проекты/задачи параллелятся на разных аккаунтах».
> **Цель:** независимые задачи молотятся одновременно на двух аккаунтах = 2× пул лимитов токенов + настоящая параллель автономной работы.
> **Связано:** `~/.claude/skills/combine/SKILL.md` (§2 АККАУНТА), `~/.claude/rules/git.md`, `consilium-matrix.md` (Agent-рой — другой слой, внутри одного аккаунта).

## Архитектура

| Сторона | Аккаунт | Где | Юзер | Режим |
|---------|---------|-----|------|-------|
| **LOCAL** | justtrance@gmail.com | Mac (этот терминал) | antonk | интерактивный + фоновые агенты |
| **REMOTE** | adw.artvision.pro@gmail.com | VPS 80.90.181.152 | **andrey** (non-root!) | headless auto-mode (tmux) |

**Почему andrey, а не root:** Claude Code блокирует `--dangerously-skip-permissions` и `defaultMode: bypassPermissions` под root/sudo. Автономный режим работает ТОЛЬКО под non-root. У andrey: uid 1000, sudo-группа, свой клон `/home/andrey/artvision-data`, `/usr/bin/claude`.

**Координация:** через git (ветка `feat/ops-crm-v1`). Партиции задач не пересекаются по файлам → нет merge-конфликтов.

## Скрипты (примитивы)

| Скрипт | Назначение |
|--------|-----------|
| `~/.claude/scripts/combine-vps-dispatch.sh [--combine] "<prompt>"` | отправить задачу/партицию на VPS adw, запуск headless в tmux, возврат мгновенный |
| `~/.claude/scripts/combine-vps-status.sh [session]` | статус combine-сессий на VPS + хвост лога |
| `~/.claude/scripts/combine-vps-collect.sh` | VPS коммит+пуш → локальный git pull (забрать результаты) |

## Однократная настройка (статус на 2026-05-25)

| Шаг | Статус | Команда |
|-----|:------:|---------|
| andrey-репо на `feat/ops-crm-v1`, синхронизирован | ✅ | (сделано) |
| `core.symlinks=false` на root + andrey | ✅ | (сделано — обходит битый симлинк `.claude/rules-global/core.md` в origin) |
| SSH git-auth для andrey (ключ root скопирован) | ✅ | (сделано) |
| `--dangerously-skip-permissions` под andrey | ✅ | проверено (проходит root-check, падал только на 401) |
| **andrey авторизован на adw.artvision.pro** | ⏳ **ТРЕБУЕТ АНТОНА** | `ssh vps-andrey` → `claude` → `/login` → ввести код |

### Команда авторизации (выполняет Антон в терминале)

```bash
ssh vps-andrey
claude            # внутри: /login → выбрать adw.artvision.pro → открыть URL → вставить код
# проверить: claude -p "say AUTH_OK" --dangerously-skip-permissions
exit
```

Claude (ассистент) **не может** сделать этот шаг — нужен интерактивный ввод кода из браузера.

## Правила безопасности

- Партиции **не пересекаются по файлам** (разные `clients/<X>/`) — иначе git-конфликт между аккаунтами
- **CONFIRM-задачи (security.md) остаются LOCAL** — VPS не шлёт клиентам, не платит, не деплоит prod автономно
- VPS коммитит+пушит после каждой задачи (минимизирует окно конфликта)
- Перед стартом обе стороны `git -c core.symlinks=false pull`
- Локальный комбайн НЕ блокируется ожиданием VPS

## Известные проблемы

- **Битый симлинк в origin:** `.claude/rules-global/core.md` имеет target >255 символов (инцидент self-corrections #13). Любой `git reset/pull` без `core.symlinks=false` падает «File name too long». Все скрипты используют `-c core.symlinks=false`. TODO: починить симлинк в origin отдельно.
- **Протухший PAT andrey:** в git-remote andrey был зашит HTTPS-токен `ghp_…` (auth failed). Заменён на SSH. **Старый токен отозвать на github.com/settings/tokens.**
- **ssh рвёт большие fetch:** длинные операции запускать через `nohup ... &` на самом VPS (переживает разрыв ssh).

## Прецеденты

- **2026-05-25 (создание):** Антон — «отправь на впс и закончи, чтобы работало в комбайне, разные проекты/задачи параллелились на разных аккаунтах». Обнаружено: VPS был на justtrance (не давал +лимит), git разошёлся на 568/15821 коммитов, битый симлинк, протухший PAT. Всё примирено. Осталось — авторизация adw (ручной шаг Антона).

## Антипаттерны

- ❌ Запускать автономный claude под root (блок auto-mode)
- ❌ Партиции с общими файлами (git-конфликт)
- ❌ Отправлять CONFIRM/human-задачи на VPS (клиентские письма, платежи, prod-деплой)
- ❌ Держать VPS на том же аккаунте что локально (нет +лимита — теряется смысл)
- ❌ `git pull` без `core.symlinks=false` (падёт на битом симлинке)
