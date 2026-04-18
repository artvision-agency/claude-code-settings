#!/bin/bash
# ai-evolve-prep.sh — собирает сигналы за неделю для ручного запуска /ai-evolve в сессии.
# Запускается еженедельно (воскресенье 10:30) через LaunchAgent pro.artvision.ai-evolve-prep.
#
# НЕ запускает Claude CLI (дорого + риск авто-правок). Готовит отчёт.
# Следующая сессия Claude увидит алерт через хук session-start-ai-evolve.sh.
#
set -euo pipefail

REPO="$HOME/artvision-data"
MEMORY="$HOME/.claude/projects/-Users-antonk/memory"
QUEUE_DIR="$HOME/.claude/learning-queue"
OUT_DIR="$HOME/.claude/ai-evolve-suggestions"
mkdir -p "$OUT_DIR"

WEEK=$(date +%Y-W%V)
OUTPUT="$OUT_DIR/$WEEK.md"

cd "$REPO" 2>/dev/null || exit 0

{
    echo "# AI Evolve Suggestions — $WEEK"
    echo ""
    echo "Сгенерировано: $(date '+%Y-%m-%d %H:%M')"
    echo ""

    # 1. Необработанная learning-queue
    echo "## 1. Learning Queue"
    QUEUE_COUNT=$(ls "$QUEUE_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ')
    echo "- Файлов в очереди: $QUEUE_COUNT"
    if [ "$QUEUE_COUNT" -gt 10 ]; then
        echo "- ⚠️ Накопилось >10, обработать /ai-evolve"
    fi
    echo ""

    # 2. Новые client patches недели
    echo "## 2. Новые client patches (7 дней)"
    find clients/*/patches/ -type f -name "*.md" -mtime -7 2>/dev/null | head -20 | while read -r f; do
        echo "- \`$f\` (mtime: $(stat -f %Sm -t %Y-%m-%d "$f"))"
    done
    echo ""

    # 3. Новые/изменённые feedback_*.md в memory за неделю
    echo "## 3. Memory изменения недели (feedback_/trend_/project_)"
    find "$MEMORY" -name "feedback_*.md" -o -name "trend_*.md" -o -name "project_*.md" 2>/dev/null \
        | xargs -I {} stat -f "%Sm %N" -t "%Y-%m-%d" {} 2>/dev/null \
        | awk -v d="$(date -v-7d +%Y-%m-%d)" '$1 >= d' \
        | sort -r | head -15
    echo ""

    # 4. Memory-lint отчёт
    echo "## 4. Memory Lint"
    if [ -x "$REPO/scripts/memory-lint.py" ]; then
        python3 "$REPO/scripts/memory-lint.py" 2>&1 | head -10
    else
        echo "- lint script недоступен"
    fi
    echo ""

    # 5. Часто меняющиеся skills
    echo "## 5. Skills с правками недели"
    find "$HOME/.claude/skills" -name "SKILL.md" -mtime -7 2>/dev/null | head -10 | while read -r f; do
        echo "- $(basename "$(dirname "$f")")"
    done
    echo ""

    # 6. Значимые коммиты с сигналами
    echo "## 6. Коммиты с fix/feat/docs (7 дней)"
    git log --oneline --since="7 days ago" --all --no-merges 2>/dev/null \
        | grep -iE "^(.{8})\s+(fix|feat|docs|refactor|chore: disable|add rule|new rule)" \
        | head -20
    echo ""

    echo "---"
    echo ""
    echo "## Рекомендация"
    echo ""
    echo "При следующей сессии в artvision-data запустить:"
    echo '```'
    echo '/ai-evolve'
    echo '```'
    echo ""
    echo "Агент прочитает этот файл и применит правки к skills/rules."
} > "$OUTPUT"

# Маркер "свежий" — на неделю
ln -sf "$OUTPUT" "$OUT_DIR/latest.md" 2>/dev/null || true

echo "AI Evolve suggestions saved: $OUTPUT"
