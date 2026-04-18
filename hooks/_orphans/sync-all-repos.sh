#!/bin/bash
# Sync all git repos on session stop
# Repos: artvision-data, artvision-tg-bot, devops-agent

# 1. Log session stats before syncing
python3 ~/artvision-data/scripts/session_logger.py 2>/dev/null

# 2. Sync session stats to Asana (creates/updates tasks)
python3 ~/artvision-data/scripts/session_to_asana.py 2>/dev/null

# 3. Sync repos
for repo in ~/artvision-data ~/artvision-tg-bot ~/devops-agent; do
  if [ -d "$repo/.git" ]; then
    cd "$repo"
    if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
      git add -A && git commit -m "chore: auto-sync on session stop

Co-Authored-By: Claude <noreply@anthropic.com>" --quiet 2>/dev/null
      git push --quiet 2>/dev/null
    fi
  fi
done
