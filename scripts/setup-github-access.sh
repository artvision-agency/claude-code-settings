#!/bin/bash

# Скрипт настройки доступа к Artvision репозиториям для нового аккаунта Claude
# Дата: 2026-01-28

set -e

# Загрузить токен из .secrets
if [ -f ~/.claude/.secrets ]; then
    source ~/.claude/.secrets
elif [ -n "$GITHUB_TOKEN" ]; then
    # Токен передан через переменную окружения
    :
else
    echo "❌ Токен не найден!"
    echo "   Создайте файл ~/.claude/.secrets с GITHUB_TOKEN=..."
    echo "   Или передайте через: GITHUB_TOKEN=xxx $0"
    exit 1
fi

echo "════════════════════════════════════════════════════"
echo "  Настройка GitHub доступа для Artvision Agency"
echo "════════════════════════════════════════════════════"
echo ""

# Проверка установки gh CLI
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) не установлен"
    echo "   Установите: brew install gh"
    exit 1
fi

echo "✅ GitHub CLI установлен"
echo ""

# Проверка текущей авторизации
echo "📋 Проверка текущей авторизации..."
if gh auth status &> /dev/null; then
    echo "✅ GitHub CLI уже авторизован"
    gh auth status 2>&1 | grep "Logged in to"
else
    echo "⚙️  Авторизация GitHub CLI..."
    echo "$GITHUB_TOKEN" | gh auth login --with-token
    echo "✅ Авторизация выполнена"
fi

echo ""
echo "════════════════════════════════════════════════════"
echo "  Проверка доступа к репозиториям"
echo "════════════════════════════════════════════════════"
echo ""

# Проверка доступа к artvision-agency
echo "📦 Репозитории artvision-agency:"
gh repo list artvision-agency --limit 5 --json name,isPrivate | \
    jq -r '.[] | "   \(if .isPrivate then "🔒" else "🌍" end) \(.name)"'

echo ""

# Проверка локальных репозиториев
echo "════════════════════════════════════════════════════"
echo "  Локальные репозитории"
echo "════════════════════════════════════════════════════"
echo ""

for repo in ~/artvision-data ~/artvision-tg-bot ~/artvision-portal ~/devops-agent; do
    if [ -d "$repo" ]; then
        name=$(basename "$repo")
        if [ -d "$repo/.git" ]; then
            remote=$(cd "$repo" && git remote get-url origin 2>/dev/null || echo "No remote")
            branch=$(cd "$repo" && git branch --show-current 2>/dev/null || echo "No branch")
            echo "✅ $name"
            echo "   Remote: $remote"
            echo "   Branch: $branch"
        else
            echo "⚠️  $name (не git репозиторий)"
        fi
    else
        echo "❌ $name (не найден)"
    fi
    echo ""
done

# Проверка глобальных настроек
echo "════════════════════════════════════════════════════"
echo "  Глобальные настройки Claude"
echo "════════════════════════════════════════════════════"
echo ""

if [ -f ~/.claude/CLAUDE.md ]; then
    echo "✅ ~/.claude/CLAUDE.md"
else
    echo "⚠️  ~/.claude/CLAUDE.md не найден"
fi

if [ -f ~/.claude/ARTVISION_REPOS.md ]; then
    echo "✅ ~/.claude/ARTVISION_REPOS.md"
else
    echo "⚠️  ~/.claude/ARTVISION_REPOS.md не найден"
fi

if [ -d ~/.claude/agents ]; then
    agent_count=$(ls ~/.claude/agents/*.md 2>/dev/null | wc -l | xargs)
    echo "✅ ~/.claude/agents/ ($agent_count агентов)"
else
    echo "⚠️  ~/.claude/agents/ не найден"
fi

echo ""

# Тестовое чтение файла
echo "════════════════════════════════════════════════════"
echo "  Тест доступа к приватному репозиторию"
echo "════════════════════════════════════════════════════"
echo ""

echo "Чтение artvision-data/sync/SYNC_STATUS.md..."
if gh api repos/artvision-agency/artvision-data/contents/sync/SYNC_STATUS.md --jq .content 2>/dev/null | base64 -d > /dev/null 2>&1; then
    echo "✅ Доступ к приватным репозиториям работает"
else
    echo "❌ Не удалось прочитать приватный репозиторий"
    echo "   Проверьте права токена на github.com/settings/tokens"
fi

echo ""
echo "════════════════════════════════════════════════════"
echo "  ✅ Настройка завершена!"
echo "════════════════════════════════════════════════════"
echo ""
echo "📖 Полная инструкция: ~/.claude/SETUP_NEW_CLAUDE_ACCOUNT.md"
echo ""
