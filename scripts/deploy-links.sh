#!/bin/zsh
# deploy-links.sh <client-slug> [--check]
# Выводит deploy-URL клиента (artvision.pro/_priv-*, /preview/*) из clients/<slug>/.
# 0 LLM-токенов: чистый grep по файлам, печатает только ссылки (+ опц. HTTP-код).
# Примеры:
#   deploy-links.sh ds-lab            → список URL
#   deploy-links.sh ds-lab --check    → URL + HTTP статус каждого
set -u
BASE="${ARTVISION_DATA:-$HOME/artvision-data}/clients"
if [ $# -eq 0 ]; then
  print -u2 "Usage: deploy-links.sh <client-slug> [--check]"
  print -u2 "Существующие клиенты: $(ls "$BASE" 2>/dev/null | tr '\n' ' ')"
  exit 2
fi
SLUG="$1"; shift
CHECK=0; [ "${1:-}" = "--check" ] && CHECK=1
DIR="$BASE/$SLUG"
[ -d "$DIR" ] || { print -u2 "Нет папки клиента: $DIR"; exit 1; }

# Собрать deploy-URL из всех текстовых файлов клиента, убрать хвостовые **,.)>" и дубли
urls=$(grep -rohE 'https://artvision\.pro/(_priv|preview)[A-Za-z0-9/_.~-]*' "$DIR" 2>/dev/null \
  | sed -E 's#[*).,>"'"'"']+$##' \
  | sed -E 's#/+$##' \
  | sort -u)

if [ -z "$urls" ]; then
  print "deploy-URL не найдены в $DIR (искал artvision.pro/_priv* и /preview*)."
  exit 0
fi

print "Deploy-URL клиента '$SLUG':"
while IFS= read -r u; do
  [ -z "$u" ] && continue
  if [ "$CHECK" = "1" ]; then
    code=$(curl -sI -o /dev/null -w "%{http_code}" --max-time 12 "$u/" 2>/dev/null)
    print "  [$code] $u/"
  else
    print "  $u/"
  fi
done <<< "$urls"
