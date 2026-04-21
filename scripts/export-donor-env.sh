#!/bin/bash
# export-donor-env.sh — запустить на ДОНОРСКОЙ машине (1-й или 2-й аккаунт)
# ПЕРЕД упаковкой. Генерирует exports/ для воспроизведения окружения.
#
# Использование:
#   bash ~/.claude/scripts/export-donor-env.sh
#   cd ~/.claude && git add exports/ && git commit -m "chore: update env exports" && git push
#
# После этого 3-й аккаунт через full-setup.sh подтянет точное окружение.

set -e
EXPORTS="$HOME/.claude/exports"
mkdir -p "$EXPORTS"

echo "▶ Экспорт окружения → $EXPORTS/"

# 1. Brewfile (все brew formulas + casks)
if command -v brew &>/dev/null; then
    brew bundle dump --file="$EXPORTS/Brewfile" --force
    echo "  ✓ Brewfile ($(wc -l < $EXPORTS/Brewfile) строк)"
fi

# 2. pip freeze
if command -v pip3 &>/dev/null; then
    pip3 freeze > "$EXPORTS/pip-freeze.txt"
    echo "  ✓ pip-freeze.txt ($(wc -l < $EXPORTS/pip-freeze.txt) пакетов)"
fi

# 3. bun globals
if command -v bun &>/dev/null; then
    bun pm ls -g 2>/dev/null > "$EXPORTS/bun-globals.txt" || true
    echo "  ✓ bun-globals.txt"
fi

# 4. npm globals (fallback)
if command -v npm &>/dev/null; then
    npm ls -g --depth=0 --json 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print('\n'.join(d.get('dependencies',{}).keys()))" > "$EXPORTS/npm-globals.txt" || true
fi

# 5. ~/.local/bin wrappers
ls -la "$HOME/.local/bin/" 2>/dev/null > "$EXPORTS/local-bin.txt" || true

# 6. LaunchAgents inventory (НЕ содержимое — только имена)
ls "$HOME/Library/LaunchAgents/" 2>/dev/null | grep -E "^(pro|com)\.artvision" > "$EXPORTS/launchagents-list.txt" || true
echo "  ✓ launchagents-list.txt ($(wc -l < $EXPORTS/launchagents-list.txt 2>/dev/null || echo 0) plist)"

# 7. tokens.json — только список ключей (template без значений)
if [ -f "$HOME/artvision-data/tokens.json" ]; then
    python3 << 'PY' > "$EXPORTS/tokens-keys.txt"
import json
try:
    d = json.load(open("/Users/antonk/artvision-data/tokens.json"))
    for k in sorted(d.keys()):
        if not k.startswith("_"):
            print(k)
except Exception as e:
    print(f"# error: {e}")
PY
    echo "  ✓ tokens-keys.txt ($(wc -l < $EXPORTS/tokens-keys.txt) ключей)"
fi

# 8. MCP servers из settings.json
python3 << 'PY' > "$EXPORTS/mcp-servers.txt" 2>/dev/null || true
import json
try:
    d = json.load(open("/Users/antonk/.claude/settings.json"))
    srv = d.get("mcpServers", {})
    for name, cfg in srv.items():
        cmd = cfg.get("command", "")
        print(f"{name}\t{cmd}")
except Exception as e:
    print(f"# error: {e}")
PY
echo "  ✓ mcp-servers.txt"

# 9. Memory master → mirror (актуализируем перед упаковкой)
if [ -x "$HOME/.claude/scripts/sync-memory.sh" ]; then
    "$HOME/.claude/scripts/sync-memory.sh" push 2>/dev/null || echo "  ⚠ sync-memory.sh push failed"
    echo "  ✓ memory засинкана в git-mirror"
fi

# 10. Снимок счётчиков (для актуализации README/docs)
cat > "$EXPORTS/counts.txt" << EOF
skills=$(ls -1d $HOME/.claude/skills/*/ 2>/dev/null | wc -l | tr -d ' ')
rules=$(ls -1 $HOME/.claude/rules/*.md 2>/dev/null | wc -l | tr -d ' ')
hooks_sh=$(ls -1 $HOME/.claude/hooks/*.sh 2>/dev/null | wc -l | tr -d ' ')
hooks_py=$(ls -1 $HOME/.claude/hooks/*.py 2>/dev/null | wc -l | tr -d ' ')
agents=$(ls -1 $HOME/.claude/agents/*.md 2>/dev/null | wc -l | tr -d ' ')
scripts=$(ls -1 $HOME/.claude/scripts/* 2>/dev/null | wc -l | tr -d ' ')
commands=$(ls -1 $HOME/.claude/commands/* 2>/dev/null | wc -l | tr -d ' ')
memory=$(ls -1 $HOME/.claude/projects/-Users-$(whoami)/memory/*.md 2>/dev/null | wc -l | tr -d ' ')
launchagents=$(ls -1 $HOME/Library/LaunchAgents/{pro,com}.artvision.*.plist 2>/dev/null | wc -l | tr -d ' ')
exported_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
exported_from=$(whoami)@$(hostname)
EOF
echo "  ✓ counts.txt"

echo ""
echo "✅ Exports готовы. Закоммить:"
echo "   cd ~/.claude && git add exports/ && git commit -m 'chore: env exports' && git push"
