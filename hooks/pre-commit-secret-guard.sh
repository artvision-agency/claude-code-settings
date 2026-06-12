#!/usr/bin/env bash
# pre-commit-secret-guard — блокирует коммит секретов в публичный settings-репо.
# Установлен после инцидента 2026-06-12 (WP-пароль + TG-токен утекли в публичный
# github.com/artvision-agency/claude-code-settings, потому что в .gitignore был
# КОММЕНТАРИЙ про wp-sites.json вместо реального правила).
# Bypass (на свой риск): SECRET_GUARD_OK=1 git commit ...
set -euo pipefail

[ "${SECRET_GUARD_OK:-0}" = "1" ] && exit 0

# staged-файлы (added/copied/modified)
staged=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null || true)
[ -z "$staged" ] && exit 0

fail=0
emit() { echo "⛔ pre-commit-secret-guard: $1" >&2; fail=1; }

# 1) Запрещённые ПУТИ/ИМЕНА (секрет-несущие файлы)
path_re='(^|/)(wp-sites\.json|tokens\.json|.*\.env|.*\.env\..*|.*cookies.*\.txt|id_rsa|.*\.pem|.*\.key|.*\.p12|.*secret.*|.*credential.*)$'
while IFS= read -r f; do
  [ -z "$f" ] && continue
  # разрешённые шаблоны/примеры
  case "$f" in
    *.template|*.example|*.sample|*.md|*.disabled) continue ;;
  esac
  if printf '%s' "$f" | grep -qiE "$path_re"; then
    emit "секрет-файл в коммите: $f"
  fi
done <<< "$staged"

# 2) Запрещённый КОНТЕНТ в staged-диффе (живые секреты)
content_re='-----BEGIN [A-Z ]*PRIVATE KEY-----|sk-ant-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}|"PASS"[[:space:]]*:[[:space:]]*"[^"]{6,}"|TELEGRAM_BOT_TOKEN=[0-9]{6,}:[A-Za-z0-9_-]{30,}|[0-9]{8,}:AA[A-Za-z0-9_-]{30,}'
added=$(git diff --cached -U0 --diff-filter=ACM 2>/dev/null | grep '^+' | grep -vE '^\+\+\+' || true)
if printf '%s' "$added" | grep -qE -- "$content_re"; then
  emit "в добавленных строках найден паттерн секрета (private key / sk-ant / ghp_ / AKIA / PASS / bot-token)"
fi

if [ "$fail" = 1 ]; then
  echo "" >&2
  echo "Секреты НЕ коммитятся в публичный репо. Вынеси в gitignored-файл / Keychain / tokens.json (приватный репо)." >&2
  echo "Если уверен что это не секрет: SECRET_GUARD_OK=1 git commit ..." >&2
  exit 1
fi
exit 0
