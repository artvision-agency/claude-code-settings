#!/usr/bin/env bash
# Detect project type for qa-pipeline runner selection.
# Usage: detect-project-type.sh <path>
# Output: one of: telegram-bot-python, telegram-bot-typescript, web-scraper, web-app, api, cli, data-pipeline, python-generic, node-generic, unknown

set -euo pipefail

ROOT="${1:-.}"
[[ -d "$ROOT" ]] || { echo "unknown"; exit 0; }

cd "$ROOT"

# Helper: match pattern in any Python/TS file
has_import() {
  local pattern="$1"
  grep -rqE "$pattern" --include="*.py" --include="*.ts" --include="*.tsx" --include="*.js" \
    --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=__pycache__ \
    . 2>/dev/null
}

has_pkg() {
  local name="$1"
  [[ -f "package.json" ]] && grep -q "\"$name\"" package.json 2>/dev/null
}

has_pip() {
  local name="$1"
  [[ -f "requirements.txt" ]] && grep -qiE "^${name}([=<>]|$)" requirements.txt 2>/dev/null
  [[ -f "pyproject.toml" ]] && grep -qi "\"$name" pyproject.toml 2>/dev/null
}

# --- Priority 1: Telegram bots ---
if has_import "from telethon" || has_import "from aiogram" \
   || has_import "^from telegram\b" || has_import "^import telegram\b" \
   || has_pip "aiogram" || has_pip "python-telegram-bot" \
   || has_pip "telethon" || has_pip "pyrogram"; then
  echo "telegram-bot-python"
  exit 0
fi

if has_pkg "grammy" || has_pkg "telegraf" || has_pkg "node-telegram-bot-api"; then
  echo "telegram-bot-typescript"
  exit 0
fi

# --- Priority 2: Web scraper (Playwright/Selenium but not bot) ---
if has_pip "playwright\|selenium\|seleniumbase\|scrapy\|beautifulsoup"; then
  # Is this a bot? already checked above → no
  # Is this a web-app (has frontend)? check separately
  if [[ -f "package.json" ]] && has_pkg "react\|vue\|next\|vite"; then
    : # fall through to web-app
  else
    echo "web-scraper"
    exit 0
  fi
fi

# --- Priority 3: API (backend) ---
if has_pip "fastapi\|flask\|django\|starlette" || \
   has_pkg "express\|fastify\|koa\|nestjs"; then
  echo "api"
  exit 0
fi

# --- Priority 4: Web app (frontend) ---
if has_pkg "next\|vite\|react\|vue\|svelte\|nuxt"; then
  echo "web-app"
  exit 0
fi

# --- Priority 5: Data pipeline ---
if has_pip "airflow\|dagster\|prefect\|luigi" || \
   (has_pip "pandas" && [[ -d "dags" || -d "pipelines" ]]); then
  echo "data-pipeline"
  exit 0
fi

# --- Priority 6: CLI ---
if has_pip "click\|typer\|argparse" && [[ -f "setup.py" || -f "pyproject.toml" ]]; then
  # Check if __main__ or console_scripts entry
  if grep -qE "(console_scripts|\\[project.scripts\\]|if __name__ == .__main__.)" \
     pyproject.toml setup.py 2>/dev/null; then
    echo "cli"
    exit 0
  fi
fi

# --- Fallback ---
if [[ -f "requirements.txt" || -f "pyproject.toml" ]]; then
  echo "python-generic"
elif [[ -f "package.json" ]]; then
  echo "node-generic"
else
  echo "unknown"
fi
