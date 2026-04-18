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

    # Stash local changes before pull to avoid rebase conflicts
    stashed=false
    if ! git diff --quiet || ! git diff --cached --quiet; then
      git stash push -m "daily-git-push auto-stash" >> "$LOG" 2>&1 && stashed=true
    fi
    git pull --rebase >> "$LOG" 2>&1 || echo "WARN: pull failed for $repo" >> "$LOG"
    if [ "$stashed" = true ]; then
      git stash pop >> "$LOG" 2>&1 || echo "WARN: stash pop conflict for $repo" >> "$LOG"
    fi

    # Check for changes
    if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
      echo "No changes, skipping" >> "$LOG"
    else
      git add -A
      git commit -m "auto-sync: daily push [$(date '+%Y-%m-%d %H:%M')]" >> "$LOG" 2>&1 || echo "WARN: nothing to commit" >> "$LOG"
      git push >> "$LOG" 2>&1 || echo "ERROR: push failed for $repo" >> "$LOG"
      echo "Pushed successfully" >> "$LOG"
    fi
  ) || echo "ERROR: failed processing $repo" >> "$LOG"
done

echo "daily-git-push finished: $(date)" >> "$LOG"
echo "========================================" >> "$LOG"
