# Настройка второй машины для работы с Artvision

**Дата:** 2026-01-28
**Для:** Ваших аккаунтов Claude на РАЗНЫХ компьютерах

---

## Быстрая установка (One-liner)

```bash
# Клонировать настройки Claude
cd ~ && rm -rf .claude && gh repo clone artvision-agency/claude-code-settings .claude

# Создать файл с токеном
cat > ~/.claude/.secrets << 'EOF'
GITHUB_TOKEN=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
EOF

# Запустить setup
~/.claude/scripts/setup-github-access.sh
```

---

## Пошаговая настройка

### Шаг 1: Установить GitHub CLI

```bash
# macOS
brew install gh

# Linux
sudo apt install gh  # Debian/Ubuntu
sudo yum install gh  # RHEL/CentOS

# Windows
winget install GitHub.cli
```

### Шаг 2: Авторизация GitHub

```bash
# Через токен
echo "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" | gh auth login --with-token

# Проверка
gh auth status
```

### Шаг 3: Клонировать настройки Claude

```bash
# Удалить старую папку .claude (если есть)
cd ~
mv .claude .claude.backup  # сохранить старую

# Клонировать из GitHub
gh repo clone artvision-agency/claude-code-settings .claude
```

### Шаг 4: Создать файл с секретами

```bash
cat > ~/.claude/.secrets << 'EOF'
# GitHub Personal Access Token
GITHUB_TOKEN=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
EOF

chmod 600 ~/.claude/.secrets
```

### Шаг 5: Клонировать рабочие репозитории

```bash
cd ~

# Основные проекты
gh repo clone artvision-agency/artvision-data
gh repo clone artvision-agency/artvision-tg-bot
gh repo clone artvision-agency/artvision-portal
gh repo clone artvision-agency/devops-agent

# Опционально: sub-agents.directory для справки
gh repo clone artvision-agency/sub-agents.directory
```

### Шаг 6: Проверка

```bash
~/.claude/scripts/setup-github-access.sh
```

Должно вывести:
```
✅ GitHub CLI авторизован
✅ Доступ к приватным репозиториям работает
✅ Локальные репозитории найдены
✅ Глобальные настройки загружены
```

---

## Синхронизация настроек между машинами

### После изменения настроек на любой машине:

```bash
cd ~/.claude

# Закоммитить изменения
git add CLAUDE.md agents/ hooks/ scripts/
git commit -m "chore: update Claude settings"
git push
```

### Перед началом работы на другой машине:

```bash
cd ~/.claude
git pull
```

---

## Автоматическая синхронизация

Добавьте в `~/.zshrc` или `~/.bashrc`:

```bash
# Claude Code settings sync
alias claude-sync-push='cd ~/.claude && git add . && git commit -m "chore: sync settings" && git push && cd -'
alias claude-sync-pull='cd ~/.claude && git pull && cd -'

# Автоматическая проверка обновлений при запуске
if [ -d ~/.claude/.git ]; then
  (cd ~/.claude && git fetch --quiet && \
   [ $(git rev-parse HEAD) = $(git rev-parse @{u}) ] || \
   echo "⚠️  Claude настройки обновились! Выполните: claude-sync-pull")
fi
```

---

## Структура после установки

```
~/
├── .claude/                          # Глобальные настройки (из Git)
│   ├── CLAUDE.md                     # Инструкции для Claude
│   ├── ARTVISION_REPOS.md            # Список репозиториев
│   ├── .secrets                      # Токены (НЕ в Git!)
│   ├── agents/                       # 130+ агентов
│   ├── hooks/                        # Хуки для оптимизации
│   └── scripts/                      # Скрипты автоматизации
│
├── artvision-data/                   # Рабочие репозитории
├── artvision-tg-bot/
├── artvision-portal/
└── devops-agent/
```

---

## Различия между машинами

**Синхронизируется через Git:**
- ✅ CLAUDE.md (глобальные инструкции)
- ✅ ARTVISION_REPOS.md (список репозиториев)
- ✅ agents/ (все агенты)
- ✅ hooks/ (хуки)
- ✅ scripts/ (скрипты)

**НЕ синхронизируется (локально на каждой машине):**
- ❌ .secrets (токены)
- ❌ settings.json (настройки Claude Code)
- ❌ history.jsonl (история сессий)
- ❌ cache/ (кэши)

---

## Troubleshooting

### Проблема: "Permission denied" при git push

```bash
cd ~/.claude
git remote set-url origin https://github.com/artvision-agency/claude-code-settings.git
gh auth refresh
```

### Проблема: Конфликты при git pull

```bash
cd ~/.claude
git stash
git pull
git stash pop
```

### Проблема: Нет доступа к приватным репозиториям

```bash
# Проверить токен
gh auth status

# Переавторизация
echo "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" | gh auth login --with-token
```

---

## Дополнительные настройки

### Для VS Code

Если используете Claude в VS Code, установите расширение:
```bash
code --install-extension anthropic.claude
```

### Для Cursor

Cursor автоматически использует настройки из `~/.claude/`

---

## Контакты

**Репозиторий настроек:**
https://github.com/artvision-agency/claude-code-settings

**При проблемах:**
1. Проверьте `gh auth status`
2. Проверьте файл `~/.claude/.secrets`
3. Попробуйте `~/.claude/scripts/setup-github-access.sh`
