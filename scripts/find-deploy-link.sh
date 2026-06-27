#!/usr/bin/env bash
# find-deploy-link.sh — найти deploy-URL артефакта клиента по реестрам DEPLOY-LINKS.md
# Правило: ~/.claude/rules/client-deliverables-registry.md
# Использование:
#   find-deploy-link.sh <slug> [тема]     — искать в реестре клиента
#   find-deploy-link.sh --all <тема>       — искать по ВСЕМ клиентам
#   find-deploy-link.sh <тема>             — если slug не папка → ищем по всем
# Выводит URL первой строкой (правило feedback_deploy_url_first), проверяет HTTP 200.
set -uo pipefail

DATA="${ARTVISION_DATA:-/Users/antonk/artvision-data}"
CLIENTS="$DATA/clients"

usage() { echo "usage: find-deploy-link.sh <slug> [тема] | --all <тема>"; exit 1; }
[ $# -lt 1 ] && usage

mode="client"; slug=""; topic=""
if [ "$1" = "--all" ]; then
  mode="all"; shift; topic="${*:-}"
elif [ -d "$CLIENTS/$1" ]; then
  slug="$1"; shift; topic="${*:-}"
else
  # первый аргумент не папка-клиент → считаем темой, ищем по всем
  mode="all"; topic="${*:-}"
fi

# собрать файлы-реестры
files=()
if [ "$mode" = "client" ]; then
  files=("$CLIENTS/$slug/DEPLOY-LINKS.md")
else
  while IFS= read -r ff; do files+=("$ff"); done < <(find "$CLIENTS" -maxdepth 2 -name DEPLOY-LINKS.md 2>/dev/null)
fi
[ "${#files[@]}" -eq 0 ] && { echo "Реестров DEPLOY-LINKS.md не найдено (mode=$mode slug=$slug)"; exit 2; }

# извлечь строки с URL, отфильтровать по теме (если задана), достать artvision.pro URL
matches=""
for f in "${files[@]}"; do
  [ -f "$f" ] || continue
  while IFS= read -r line; do
    if [ -n "$topic" ]; then
      echo "$line" | grep -qiE "$topic" || continue
    fi
    url=$(echo "$line" | grep -oE 'https://artvision\.pro/[A-Za-z0-9_/-]+' | head -1)
    [ -z "$url" ] && continue
    label=$(echo "$line" | grep -oE '\*\*[^*]+\*\*' | head -1 | tr -d '*' | cut -c1-70)
    [ -z "$label" ] && label=$(echo "$line" | sed -E 's/^[[:space:]*-]*//' | cut -c1-70)
    matches+="$url|$label|$(basename "$(dirname "$f")")"$'\n'
  done < <(grep -E 'https://artvision\.pro/' "$f")
done

matches=$(echo "$matches" | grep -v '^$' | sort -u)
[ -z "$matches" ] && { echo "Не найдено по теме '${topic:-*}' в реестрах. Искал в: ${files[*]}"; exit 2; }

# вывод: URL первой строкой + проверка 200
first=1
while IFS='|' read -r url label client; do
  [ -z "$url" ] && continue
  code=$(curl -s -o /dev/null -w "%{http_code}" -m 12 "$url" 2>/dev/null || echo "---")
  mark=$([ "$code" = "200" ] && echo "✅" || echo "⚠️$code")
  if [ $first -eq 1 ]; then echo "$url"; first=0; fi
  echo "  $mark [$client] $label — $url"
done <<< "$matches"
