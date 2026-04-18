#!/bin/bash
# rollback-karpathy.sh — возврат к состоянию ДО эксперимента Karpathy Wiki + AutoResearch (2026-04-17).
#
# Что восстанавливает:
#   1. artvision-data → git tag baseline-pre-karpathy-2026-04-17
#   2. ~/.claude/settings.json → из snapshot
#   3. ~/.claude/projects/-Users-antonk/memory/ → из tar
#   4. ~/.claude/rules/ → из tar
#
# Безопасность:
#   - Всегда делает backup current state перед откатом в snapshots/before-rollback-<ts>/
#   - Требует подтверждения (запуск с --yes для скипа)

set -euo pipefail

SNAPSHOT="$HOME/.claude/snapshots/pre-karpathy-2026-04-17"
TAG="baseline-pre-karpathy-2026-04-17"
YES_FLAG="${1:-}"

if [ ! -d "$SNAPSHOT" ]; then
    echo "❌ Snapshot not found: $SNAPSHOT"
    exit 1
fi

cat << EOF
═════════════════════════════════════════════════
  ROLLBACK KARPATHY EXPERIMENT
  Snapshot: $SNAPSHOT
  Tag: $TAG
═════════════════════════════════════════════════

Что будет сделано:
  1. artvision-data: git checkout $TAG
  2. ~/.claude/settings.json: восстановление из snapshot
  3. ~/.claude/projects/-Users-antonk/memory/: распаковка из tar
  4. ~/.claude/rules/: распаковка из tar

Текущее состояние сохранится в ~/.claude/snapshots/before-rollback-<ts>/
EOF

if [ "$YES_FLAG" != "--yes" ]; then
    read -rp "Продолжить? [y/N] " ans
    case "$ans" in [yY]*) ;; *) echo "Отменено."; exit 0 ;; esac
fi

# 1. Backup CURRENT state
TS=$(date +%Y%m%dT%H%M%S)
CUR_BAK="$HOME/.claude/snapshots/before-rollback-$TS"
mkdir -p "$CUR_BAK"
cp ~/.claude/settings.json "$CUR_BAK/settings.json.bak"
cp ~/artvision-data/TODO.md "$CUR_BAK/TODO.md.bak" 2>/dev/null || true
tar czf "$CUR_BAK/memory.tar.gz" -C ~/.claude/projects/-Users-antonk/ memory/ 2>/dev/null
tar czf "$CUR_BAK/rules.tar.gz" -C ~/.claude/ rules/ 2>/dev/null
echo "✅ Current state backed up to $CUR_BAK"

# 2. Restore artvision-data
cd ~/artvision-data
if git rev-parse "$TAG" >/dev/null 2>&1; then
    # Мягкий возврат через branch (не detached HEAD)
    git stash push -u -m "pre-rollback-$TS" 2>/dev/null || true
    git checkout -B rollback-to-baseline "$TAG"
    echo "✅ artvision-data: checkout $TAG (branch rollback-to-baseline)"
else
    echo "⚠️  Tag $TAG not found — пропустить git rollback"
fi

# 3. Restore settings.json
cp "$SNAPSHOT/settings.json.bak" ~/.claude/settings.json
echo "✅ settings.json restored"

# 4. Restore memory/
rm -rf ~/.claude/projects/-Users-antonk/memory/
tar xzf "$SNAPSHOT/memory.tar.gz" -C ~/.claude/projects/-Users-antonk/
echo "✅ memory/ restored"

# 5. Restore rules/
rm -rf ~/.claude/rules/
tar xzf "$SNAPSHOT/rules.tar.gz" -C ~/.claude/
echo "✅ rules/ restored"

cat << EOF

═════════════════════════════════════════════════
  ✅ ROLLBACK COMPLETE
═════════════════════════════════════════════════

Backup текущего состояния: $CUR_BAK

Что делать дальше:
  - artvision-data сейчас на branch rollback-to-baseline
  - Если всё ок → git push -u origin rollback-to-baseline
  - Merge в main через PR

Если нужно вернуться обратно к Karpathy-эксперименту:
  ~/.claude/scripts/restore-from-backup.sh $CUR_BAK
EOF
