#!/bin/bash
# sync-skills.sh — двусторонняя синхронизация skills
# source: claude-code-settings (git) ↔ target: .claude/skills/ (проект)
# Запускается ежедневно через cron
#
# Настройка:
#   1. Скопировать в scripts/sync-skills.sh проекта
#   2. Изменить PROJECT_DIR, SOURCE_REPO, SKILLS
#   3. Добавить в cron: 0 6 * * * /path/to/scripts/sync-skills.sh >> data/logs/sync-skills.log 2>&1
#   4. BOT_TOKEN и ADMIN_CHAT_ID — из .env для TG-уведомлений при конфликтах

# ══════════════ НАСТРОИТЬ ПОД ПРОЕКТ ══════════════
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE_REPO="$HOME/claude-code-settings"
SKILLS="tdd solid-dry-kiss ddd-hexagonal project-audit"
# ══════════════════════════════════════════════════

set -a; source "$PROJECT_DIR/.env" 2>/dev/null; set +a

SOURCE="$SOURCE_REPO/skills"
TARGET="$PROJECT_DIR/.claude/skills"
HASH_DIR="$PROJECT_DIR/data/.skills-hashes"
CHAT_ID="${ADMIN_CHAT_ID:-}"
CHANGED=0
CONFLICTS=""

mkdir -p "$HASH_DIR"

send_tg() {
    [ -z "$BOT_TOKEN" ] || [ -z "$CHAT_ID" ] && return
    curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d chat_id="$CHAT_ID" -d parse_mode=HTML -d "text=$1" > /dev/null
}

# Стянуть обновления из git
cd "$SOURCE_REPO" && git pull --quiet 2>&1 || echo "[sync-skills] git pull failed"

for skill in $SKILLS; do
    SOURCE_DIR="$SOURCE/$skill"
    TARGET_DIR="$TARGET/$skill"
    HASH_FILE="$HASH_DIR/$skill.md5"

    # Считаем хеши (только содержимое файлов, без путей)
    source_hash=""
    target_hash=""
    [ -d "$SOURCE_DIR" ] && source_hash=$(find "$SOURCE_DIR" -type f | sort | xargs cat 2>/dev/null | md5sum | cut -d' ' -f1)
    [ -d "$TARGET_DIR" ] && target_hash=$(find "$TARGET_DIR" -type f | sort | xargs cat 2>/dev/null | md5sum | cut -d' ' -f1)

    # Предыдущий хеш (после последней синхронизации)
    prev_hash=""
    [ -f "$HASH_FILE" ] && prev_hash=$(cat "$HASH_FILE")

    # Первый запуск — сохранить хеш, не трогать
    if [ -z "$prev_hash" ]; then
        echo "$source_hash" > "$HASH_FILE"
        continue
    fi

    source_changed=false
    target_changed=false
    [ "$source_hash" != "$prev_hash" ] && source_changed=true
    [ "$target_hash" != "$prev_hash" ] && target_changed=true

    if $source_changed && $target_changed; then
        # Оба изменились — конфликт, не трогаем
        echo "[sync-skills] CONFLICT: $skill изменён и в git, и в проекте — пропускаю"
        CONFLICTS="$CONFLICTS $skill"
        continue
    elif $source_changed; then
        # Только source → обновить проект
        rsync -a --delete "$SOURCE_DIR/" "$TARGET_DIR/"
        echo "[sync-skills] $skill: обновлён из git → проект"
        echo "$source_hash" > "$HASH_FILE"
        CHANGED=1
    elif $target_changed; then
        # Только проект → обновить source и запушить
        rsync -a --delete "$TARGET_DIR/" "$SOURCE_DIR/"
        cd "$SOURCE_REPO" && git add "skills/$skill" && \
            git -c user.name="sync-skills" -c user.email="sync@local" \
            commit -m "sync: обновить skill $skill из проекта" --quiet && \
            git push --quiet 2>&1 || echo "[sync-skills] git push failed for $skill"
        echo "[sync-skills] $skill: обновлён из проекта → git"
        echo "$target_hash" > "$HASH_FILE"
        CHANGED=1
    fi
done

if [ -n "$CONFLICTS" ]; then
    send_tg "⚠️ <b>Skills sync conflict</b>
Изменены и в git, и в проекте:$CONFLICTS
Нужно решить вручную."
fi

if [ "$CHANGED" -eq 0 ] && [ -z "$CONFLICTS" ]; then
    echo "[sync-skills] все skills актуальны"
fi
