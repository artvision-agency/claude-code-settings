#!/bin/bash
# cc-share — share a local skill/hook/agent to the shared repo
set -e

SETTINGS_DIR="$HOME/claude-code-settings"
CLAUDE_DIR="$HOME/.claude"

if [ -z "$1" ]; then
    echo "Usage: cc-share <skill-name|hook-name|agent-name>"
    echo ""
    echo "Examples:"
    echo "  cc-share resume-session     # share a skill"
    echo "  cc-share pre-read.sh        # share a hook"
    echo ""
    echo "Available local skills:"
    ls "$CLAUDE_DIR/skills/" 2>/dev/null | while read d; do
        [ -f "$CLAUDE_DIR/skills/$d/SKILL.md" ] && echo "  $d"
    done
    exit 1
fi

NAME="$1"

# Detect type: skill, hook, or agent
if [ -d "$CLAUDE_DIR/skills/$NAME" ] && [ -f "$CLAUDE_DIR/skills/$NAME/SKILL.md" ]; then
    TYPE="skills"
    SRC="$CLAUDE_DIR/skills/$NAME"
    DST="$SETTINGS_DIR/skills/$NAME"
    mkdir -p "$SETTINGS_DIR/skills"
    cp -r "$SRC" "$DST"
    echo "Shared skill: $NAME"
elif [ -f "$CLAUDE_DIR/hooks/$NAME" ]; then
    TYPE="hooks"
    SRC="$CLAUDE_DIR/hooks/$NAME"
    DST="$SETTINGS_DIR/hooks/$NAME"
    mkdir -p "$SETTINGS_DIR/hooks"
    cp "$SRC" "$DST"
    echo "Shared hook: $NAME"
elif [ -f "$CLAUDE_DIR/agents/$NAME" ]; then
    TYPE="agents"
    SRC="$CLAUDE_DIR/agents/$NAME"
    DST="$SETTINGS_DIR/agents/$NAME"
    mkdir -p "$SETTINGS_DIR/agents"
    cp "$SRC" "$DST"
    echo "Shared agent: $NAME"
else
    echo "Not found: $NAME"
    echo "Looked in: skills/, hooks/, agents/"
    exit 1
fi

# Commit and push
cd "$SETTINGS_DIR"
git add "$TYPE/$NAME"
git commit -m "feat: share $TYPE/$NAME

Co-Authored-By: $(git config user.name) <$(git config user.email)>"
git push

echo ""
echo "Pushed to shared repo. Others can get it with: cc-update"
