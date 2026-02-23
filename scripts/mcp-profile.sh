#!/bin/bash
# MCP Profile Switcher — переключение наборов плагинов по типу задачи
# Использование: mcp-profile.sh [profile]
# Профили: minimal, frontend, backend, content, full
#
# Из статьи Habr: "max 10 включённых MCP, 80 инструментов"
# Каждый ненужный MCP/плагин жрёт контекст из 200K окна

SETTINGS="$HOME/.claude/settings.json"

if [ ! -f "$SETTINGS" ]; then
  echo "Ошибка: $SETTINGS не найден"
  exit 1
fi

PROFILE="${1:-help}"

# Плагины по категориям
CORE="github,commit-commands,explanatory-output-style,ralph-loop,superpowers"
FRONTEND="playwright,frontend-design,code-simplifier"
BACKEND="supabase,pyright-lsp,typescript-lsp"
CONTENT="asana,context7,huggingface-skills"
REVIEW="code-review,pr-review-toolkit,feature-dev,security-guidance"
DEV="hookify,plugin-dev,agent-sdk-dev,claude-code-setup,claude-md-management"
PLAYGROUND="playground"

case "$PROFILE" in
  minimal)
    ENABLED="$CORE"
    DESC="Минимальный: git, коммиты, стиль вывода (5 плагинов)"
    ;;
  frontend)
    ENABLED="$CORE,$FRONTEND,$REVIEW"
    DESC="Frontend: + playwright, дизайн, ревью (13 плагинов)"
    ;;
  backend)
    ENABLED="$CORE,$BACKEND,$REVIEW"
    DESC="Backend: + supabase, LSP, ревью (13 плагинов)"
    ;;
  content)
    ENABLED="$CORE,$CONTENT"
    DESC="Контент: + asana, context7, HF (8 плагинов)"
    ;;
  full)
    ENABLED="$CORE,$FRONTEND,$BACKEND,$CONTENT,$REVIEW,$DEV,$PLAYGROUND"
    DESC="Полный: все 25 плагинов (осторожно с контекстом!)"
    ;;
  help|--help|-h)
    echo "MCP Profile Switcher — Artvision"
    echo ""
    echo "Использование: mcp-profile.sh <profile>"
    echo ""
    echo "Профили:"
    echo "  minimal   — git, коммиты, стиль (5 плагинов, ~15K токенов)"
    echo "  frontend  — + playwright, дизайн, ревью (13 плагинов, ~40K)"
    echo "  backend   — + supabase, LSP, ревью (13 плагинов, ~40K)"
    echo "  content   — + asana, context7 (8 плагинов, ~25K)"
    echo "  full      — все 25 плагинов (~80K токенов!)"
    echo ""
    echo "Текущий профиль:"
    ACTIVE=$(python3 -c "
import json
with open('$SETTINGS') as f:
    s = json.load(f)
enabled = [k.split('@')[0] for k,v in s.get('enabledPlugins',{}).items() if v]
print(f'{len(enabled)} плагинов: {', '.join(sorted(enabled))}')
" 2>/dev/null)
    echo "  $ACTIVE"
    exit 0
    ;;
  *)
    echo "Неизвестный профиль: $PROFILE"
    echo "Доступные: minimal, frontend, backend, content, full"
    exit 1
    ;;
esac

# Применяем профиль
python3 -c "
import json

with open('$SETTINGS') as f:
    settings = json.load(f)

enabled_list = '$ENABLED'.split(',')
plugins = settings.get('enabledPlugins', {})

# Выключаем все, включаем только нужные
for key in plugins:
    name = key.split('@')[0]
    plugins[key] = name in enabled_list

settings['enabledPlugins'] = plugins

with open('$SETTINGS', 'w') as f:
    json.dump(settings, f, indent=2, ensure_ascii=False)

on = sum(1 for v in plugins.values() if v)
off = sum(1 for v in plugins.values() if not v)
print(f'Профиль: $PROFILE')
print(f'Включено: {on}, выключено: {off}')
" 2>/dev/null

echo "$DESC"
echo ""
echo "Перезапустите Claude Code чтобы изменения вступили в силу."
