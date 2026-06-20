#!/bin/bash
# cc-update — pull latest shared skills, hooks, agents from claude-code-settings
set -e

SETTINGS_DIR="$HOME/claude-code-settings"
CLAUDE_DIR="$HOME/.claude"

if [ ! -d "$SETTINGS_DIR" ]; then
    echo "Cloning claude-code-settings..."
    git clone https://github.com/artvision-agency/claude-code-settings.git "$SETTINGS_DIR"
else
    echo "Pulling latest..."
    # DATA-LOSS-SAFE (2026-06-20, инцидент потери файлов/токена yail307):
    # БЫЛО: git pull --rebase — отвязывал локальные коммиты settings-репо → dangling.
    # СТАЛО: ff-only; иначе merge (--no-rebase) только при чистом дереве; грязное → пропуск.
    if ! git -C "$SETTINGS_DIR" pull --ff-only 2>/dev/null; then
        if [ -z "$(git -C "$SETTINGS_DIR" status --porcelain)" ]; then
            git -C "$SETTINGS_DIR" pull --no-rebase --no-edit \
                || { git -C "$SETTINGS_DIR" merge --abort 2>/dev/null || true; echo "⚠️  merge-конфликт settings — merge --abort, локальные коммиты целы"; }
        else
            echo "⚠️  settings-репо грязный — pull пропущен (rebase/stash не делаем, локальные правки целы)"
        fi
    fi
fi

# Sync skills
if [ -d "$SETTINGS_DIR/skills" ]; then
    mkdir -p "$CLAUDE_DIR/skills"
    for skill_dir in "$SETTINGS_DIR/skills"/*/; do
        skill_name=$(basename "$skill_dir")
        if [ -f "$skill_dir/SKILL.md" ]; then
            cp -r "$skill_dir" "$CLAUDE_DIR/skills/$skill_name"
            echo "  + skill: $skill_name"
        fi
    done
fi

# Sync hooks
if [ -d "$SETTINGS_DIR/hooks" ]; then
    mkdir -p "$CLAUDE_DIR/hooks"
    for hook in "$SETTINGS_DIR/hooks"/*.sh; do
        [ -f "$hook" ] || continue
        cp "$hook" "$CLAUDE_DIR/hooks/"
        chmod +x "$CLAUDE_DIR/hooks/$(basename "$hook")"
        echo "  + hook: $(basename "$hook")"
    done
fi

# Sync agents
if [ -d "$SETTINGS_DIR/agents" ]; then
    mkdir -p "$CLAUDE_DIR/agents"
    for agent in "$SETTINGS_DIR/agents"/*.md; do
        [ -f "$agent" ] || continue
        cp "$agent" "$CLAUDE_DIR/agents/"
        echo "  + agent: $(basename "$agent")"
    done
fi

echo ""
echo "Done! All shared configs updated."
