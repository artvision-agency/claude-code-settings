#!/bin/bash
# Установка полного конфига Claude Code из artvision-data в ~/.claude/
# Цель: обе машины / оба аккаунта получают ОДИНАКОВЫЙ конфиг
# Запуск: bash ~/artvision-data/.claude/scripts/install-claude-config.sh

set -e

SRC="$HOME/artvision-data/.claude"
DST="$HOME/.claude"

echo "========================================="
echo "  INSTALL CLAUDE CONFIG"
echo "  Source: $SRC"
echo "  Target: $DST"
echo "========================================="
echo ""

# Проверки
if [ ! -d "$SRC" ]; then
    echo "❌ Нет $SRC — сначала клонируй artvision-data"
    exit 1
fi

mkdir -p "$DST/hooks" "$DST/scripts" "$DST/rules" "$DST/session_logs"

# 1. settings.json — МЕРЖ (сохраняем локальные hooks, добавляем model+permissions+plugins)
echo "📦 1/6 settings.json..."
if [ -f "$SRC/settings.json" ]; then
    if [ -f "$DST/settings.json" ]; then
        # Мержим: берём ВСЁ из project settings, т.к. он полнее
        # Но сохраняем локальный skipDangerousModePermissionPrompt если был
        cp "$DST/settings.json" "$DST/settings.json.bak"
        cp "$SRC/settings.json" "$DST/settings.json"
        echo "   ✅ Установлен (бэкап: settings.json.bak)"
    else
        cp "$SRC/settings.json" "$DST/settings.json"
        echo "   ✅ Создан"
    fi
else
    echo "   ⚠️  Нет source settings.json"
fi

# 2. CLAUDE.md — глобальный (модульная ссылка на rules/)
echo "📦 2/6 CLAUDE.md..."
cat > "$DST/CLAUDE.md" << 'HEREDOC'
# Claude Instructions

Правила модульно разнесены по `~/.claude/rules/`:

| Файл | Содержимое |
|------|-----------|
| `workflow.md` | Стиль работы, верификация данных, проверка файлов |
| `git.md` | Auto-commit, синхронизация, проекты, аккаунты |
| `tokens.md` | Оптимизация токенов, агенты, TeamCreate, антипаттерны |
| `security.md` | Публичный контент, платные API, credentials |

Проектные правила в `<project>/.claude/rules/` (загружаются условно).
HEREDOC
echo "   ✅ Создан"

# 3. Rules — глобальные (4 файла)
echo "📦 3/6 Rules..."
for rule in workflow.md git.md tokens.md security.md; do
    if [ -f "$DST/rules/$rule" ]; then
        echo "   ✅ $rule (уже есть)"
    else
        # Копируем из project global-* версии
        src_name="global-${rule}"
        if [ -f "$SRC/rules/$src_name" ]; then
            cp "$SRC/rules/$src_name" "$DST/rules/$rule"
            echo "   ✅ $rule (из $src_name)"
        else
            echo "   ⚠️  $rule — нет источника"
        fi
    fi
done

# 4. Hooks — все из project
echo "📦 4/6 Hooks..."
copied=0
for hook in "$SRC/hooks/"*.sh "$SRC/hooks/"*.py; do
    [ -f "$hook" ] || continue
    name=$(basename "$hook")
    [ "$name" = "README.md" ] && continue
    cp "$hook" "$DST/hooks/$name"
    chmod +x "$DST/hooks/$name"
    copied=$((copied + 1))
done
echo "   ✅ $copied хуков скопировано"

# 5. Scripts — все из project + глобальные
echo "📦 5/6 Scripts..."
copied=0
for script in "$SRC/scripts/"*.sh "$SRC/scripts/"*.py; do
    [ -f "$script" ] || continue
    name=$(basename "$script")
    cp "$script" "$DST/scripts/$name"
    chmod +x "$DST/scripts/$name"
    copied=$((copied + 1))
done
echo "   ✅ $copied скриптов скопировано"

# 6. Statusline
echo "📦 6/6 Statusline..."
if [ -f "$SRC/statusline.sh" ]; then
    cp "$SRC/statusline.sh" "$DST/statusline.sh"
    chmod +x "$DST/statusline.sh"
    echo "   ✅ Скопирован"
elif [ -f "$DST/statusline.sh" ]; then
    echo "   ✅ Уже есть"
else
    echo "   ⚠️  Нет source statusline.sh"
fi

echo ""
echo "========================================="
echo "  ГОТОВО! Проверка:"
echo "========================================="

# Быстрая проверка
echo ""
model=$(python3 -c "import json; print(json.load(open('$DST/settings.json')).get('model','НЕ ЗАДАНА'))" 2>/dev/null || echo "ОШИБКА")
perms=$(python3 -c "import json; d=json.load(open('$DST/settings.json')); print(len(d.get('permissions',{}).get('allow',[])))" 2>/dev/null || echo "0")
plugins=$(python3 -c "import json; d=json.load(open('$DST/settings.json')); print(sum(1 for v in d.get('enabledPlugins',{}).values() if v))" 2>/dev/null || echo "0")
hooks_count=$(ls "$DST/hooks/"*.sh 2>/dev/null | wc -l | tr -d ' ')
rules_count=$(ls "$DST/rules/"*.md 2>/dev/null | wc -l | tr -d ' ')

echo "  Model:       $model"
echo "  Permissions:  $perms правил"
echo "  Plugins:      $plugins включено"
echo "  Hooks:        $hooks_count скриптов"
echo "  Rules:        $rules_count файлов"
echo ""

# Предупреждения
if [ "$model" != "claude-opus-4-6" ]; then
    echo "⚠️  Model не opus! Проверь settings.json"
fi
if [ "$perms" -lt 50 ]; then
    echo "⚠️  Мало permissions ($perms) — будут постоянные запросы подтверждения"
fi
echo ""
echo "Перезапусти Claude Code чтобы применить."
