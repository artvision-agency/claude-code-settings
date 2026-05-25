#!/usr/bin/env bash
# combine-vps-collect.sh — забрать результаты VPS-задачи в локальный репо через git
# VPS-аккаунт коммитит+пушит свою работу; этот скрипт делает git pull локально.
set -euo pipefail
LOCAL_REPO="$HOME/artvision-data"
VPS_HOST="vps-andrey"

echo "=== 1. Убедиться что VPS запушил свою работу ==="
ssh -o ConnectTimeout=20 -o ServerAliveInterval=15 "$VPS_HOST" \
  "cd ~/artvision-data && git add -A 2>/dev/null; \
   git -c core.symlinks=false commit -m 'combine-vps: автономный прогон $(date +%F_%H:%M)' 2>&1 | tail -1 || echo 'нечего коммитить'; \
   git -c core.symlinks=false push origin feat/ops-crm-v1 2>&1 | tail -2" 2>&1 | head -10 || echo "⚠️ VPS push не удался — проверь вручную"

echo ""
echo "=== 2. Подтянуть в локальный репо ==="
cd "$LOCAL_REPO"
git -c core.symlinks=false pull --no-edit origin feat/ops-crm-v1 2>&1 | tail -5

echo ""
echo "✅ Результаты VPS-задачи подтянуты. Проверь: git log --oneline -10"
