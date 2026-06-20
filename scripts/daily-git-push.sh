#!/bin/bash
set -euo pipefail

LOG="/tmp/daily-git-push.log"
REPOS=(
  "/Users/antonk/artvision-data"
  "/Users/antonk/artvision-tg-bot"
  "/Users/antonk/devops-agent"
)

echo "========================================" >> "$LOG"
echo "daily-git-push started: $(date)" >> "$LOG"

for repo in "${REPOS[@]}"; do
  echo "--- $repo ---" >> "$LOG"

  if [ ! -d "$repo/.git" ]; then
    echo "SKIP: not a git repo" >> "$LOG"
    continue
  fi

  (
    cd "$repo"

    # ── DATA-LOSS-SAFE sync (исправлено 2026-06-20, инцидент потери файлов/токена) ──
    # БЫЛО: git stash push → git pull --rebase → git stash pop.
    #   stash pop конфликт = потеря незакоммиченного (yail307-токен слетел);
    #   pull --rebase переписывает/ОТВЯЗЫВАЕТ локальные коммиты → dangling (потеря файлов).
    # СТАЛО: commit-first (без stash) → merge (без rebase). Потеря невозможна:
    #   любое локальное изменение становится РЕАЛЬНЫМ коммитом ДО сети,
    #   merge НИКОГДА не отвязывает коммиты (в отличие от rebase).

    # 1. Закоммитить ВСЁ локальное ДО pull (вместо stash — stash теряет при конфликте)
    if ! git diff --quiet || ! git diff --cached --quiet || [ -n "$(git ls-files --others --exclude-standard)" ]; then
      git add -A
      git commit -m "auto-sync: pre-pull commit [$(date '+%Y-%m-%d %H:%M')]" >> "$LOG" 2>&1 || echo "WARN: nothing to commit" >> "$LOG"
    fi

    # 2. MERGE (НЕ rebase). --no-edit чтобы не висеть на редакторе.
    #    При конфликте НЕ трогаем дерево (никаких reset/checkout) — оставляем для ручного разбора.
    if ! git -c core.symlinks=false pull --no-rebase --no-edit >> "$LOG" 2>&1; then
      echo "WARN: merge conflict/pull failed for $repo — дерево НЕ тронуто, push пропущен, нужен ручной разбор" >> "$LOG"
      git merge --abort >> "$LOG" 2>&1 || true   # откат только незавершённого merge, локальные коммиты целы
      exit 0
    fi

    # 3. Push (только если merge чистый)
    git push >> "$LOG" 2>&1 || echo "ERROR: push failed for $repo" >> "$LOG"
    echo "Synced (commit-first+merge) successfully" >> "$LOG"
  ) || echo "ERROR: failed processing $repo" >> "$LOG"
done

echo "daily-git-push finished: $(date)" >> "$LOG"
echo "========================================" >> "$LOG"
