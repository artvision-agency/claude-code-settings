#!/usr/bin/env bash
# Регресс-тест fail-CLOSED фикса для pre-finance-deploy.sh
# Доказывает: отсутствие обязательного factcheck-скрипта = БЛОК (exit 2)
# в НОВОМ черновике там, где СТАРЫЙ live-хук пропускал (exit 0).
#
# НЕ трогает /Users/antonk/.claude/hooks/ и НЕ трогает live factcheck-скрипты.
# Все артефакты — только в /tmp.

set -uo pipefail

LIVE_HOOK="/Users/antonk/.claude/hooks/pre-finance-deploy.sh"
DRAFT_HOOK="/tmp/hookfix-pre-finance-deploy.sh"
WORKDIR="/tmp/hooktest-pfd-$$"
mkdir -p "$WORKDIR"

PASS=0
FAIL=0

ok()   { printf '  \033[32mPASS\033[0m %s\n' "$1"; PASS=$((PASS+1)); }
bad()  { printf '  \033[31mFAIL\033[0m %s\n' "$1"; FAIL=$((FAIL+1)); }

# --- фикстуры -----------------------------------------------------------
# Реалистичный финансовый HTML под FINANCE_PATTERN (personal/finance).
FIN_HTML="$WORKDIR/personal/finance/savings-test.html"
mkdir -p "$(dirname "$FIN_HTML")"
cat > "$FIN_HTML" <<'HTML'
<!doctype html><html><head><title>Вклады 3M</title></head>
<body><h1>Сравнение вкладов</h1>
<p>Ставка ВТБ 17% годовых, 3 000 000 ₽.</p></body></html>
HTML

# scp-команда деплоя финансового документа (как даёт харнес в CLAUDE_BASH_COMMAND)
FIN_SCP="scp $FIN_HTML user@host:/var/www/preview/savings-test.html"

# Не-финансовая scp (должна пропускаться обоими хуками независимо от зависимостей)
NONFIN_HTML="$WORKDIR/clients/foo/kp/index.html"
mkdir -p "$(dirname "$NONFIN_HTML")"
echo '<html><body>KP</body></html>' > "$NONFIN_HTML"
NONFIN_SCP="scp $NONFIN_HTML user@host:/var/www/kp/index.html"

# --- утилита запуска хука -----------------------------------------------
# $1=hook путь, $2=команда; возвращает exit-код в глоб. переменной RC, stdout в OUT
run_hook() {
    local hook="$1" cmd="$2"
    OUT=$(CLAUDE_TOOL_NAME="Bash" CLAUDE_BASH_COMMAND="$cmd" bash "$hook" 2>/dev/null)
    RC=$?
}

# Сделать тест-копию хука с подменённым путём к factcheck-скриптам на НЕСУЩЕСТВУЮЩИЙ.
# Это эмулирует "зависимость пропала" (скрипт перемещён/переименован/удалён),
# НЕ трогая реальные live-скрипты.
make_missing_dep_variant() {
    local src="$1" dst="$2"
    sed -E \
      -e 's#"/Users/antonk/artvision-data/\.claude-shared/scripts/factcheck-numeric\.py"#"/tmp/__NONEXISTENT_numeric_'"$$"'.py"#' \
      -e 's#"/Users/antonk/artvision-data/\.claude-shared/scripts/factcheck-finance-domain\.py"#"/tmp/__NONEXISTENT_domain_'"$$"'.py"#' \
      "$src" > "$dst"
}

echo "═══ pre-finance-deploy fail-CLOSED регресс ═══"
echo

# ============================================================
# T1 (КЛЮЧЕВОЙ): обязательный скрипт отсутствует.
#   СТАРЫЙ live-хук → exit 0 (fail-OPEN: банк-документ без проверки)
#   НОВЫЙ черновик  → exit 2 (fail-CLOSED: блок)
# ============================================================
echo "[T1] missing-dependency: финансовый scp при отсутствии factcheck-скрипта"

LIVE_VARIANT="$WORKDIR/live-missingdep.sh"
DRAFT_VARIANT="$WORKDIR/draft-missingdep.sh"
make_missing_dep_variant "$LIVE_HOOK"  "$LIVE_VARIANT"
make_missing_dep_variant "$DRAFT_HOOK" "$DRAFT_VARIANT"

run_hook "$LIVE_VARIANT" "$FIN_SCP"
LIVE_RC=$RC
if [[ "$LIVE_RC" -eq 0 ]]; then
    ok "СТАРЫЙ хук пропускал (exit 0) — подтверждена fail-OPEN уязвимость"
else
    bad "ожидался exit 0 от СТАРОГО хука (демонстрация бага), получен $LIVE_RC"
fi

run_hook "$DRAFT_VARIANT" "$FIN_SCP"
DRAFT_RC=$RC
if [[ "$DRAFT_RC" -eq 2 ]]; then
    ok "НОВЫЙ черновик БЛОКИРУЕТ (exit 2) при отсутствии зависимости — fail-CLOSED"
else
    bad "ожидался exit 2 от НОВОГО черновика, получен $DRAFT_RC"
fi
if echo "$OUT" | grep -q '"decision":"block"'; then
    ok "НОВЫЙ черновик вернул JSON decision=block для PreToolUse"
else
    bad "ожидался JSON {\"decision\":\"block\"} в stdout черновика"
fi

# ============================================================
# T2: domain-скрипт отсутствует (numeric есть) — должен блокировать.
#   Подменяем ТОЛЬКО domain-путь на несуществующий, numeric оставляем реальный.
# ============================================================
echo
echo "[T2] missing Layer-6 (domain) скрипт: numeric присутствует, domain пропал"
DRAFT_DOMAIN_MISSING="$WORKDIR/draft-domain-missing.sh"
sed -E \
  -e 's#"/Users/antonk/artvision-data/\.claude-shared/scripts/factcheck-finance-domain\.py"#"/tmp/__NONEXISTENT_domain_'"$$"'.py"#' \
  "$DRAFT_HOOK" > "$DRAFT_DOMAIN_MISSING"

run_hook "$DRAFT_DOMAIN_MISSING" "$FIN_SCP"
if [[ "$RC" -eq 2 ]]; then
    ok "НОВЫЙ черновик блокирует при отсутствии domain-скрипта (Layer 6 fail-closed)"
else
    bad "ожидался exit 2 при отсутствии domain-скрипта, получен $RC"
fi

# ============================================================
# T3 (НЕГАТИВНЫЙ КОНТРОЛЬ): не-финансовый scp — пропускается, не блокируется.
# ============================================================
echo
echo "[T3] не-финансовый scp — должен проходить (не в scope хука)"
run_hook "$DRAFT_HOOK" "$NONFIN_SCP"
if [[ "$RC" -eq 0 ]]; then
    ok "не-финансовый деплой проходит (exit 0)"
else
    bad "ожидался exit 0 для не-финансового scp, получен $RC"
fi

# ============================================================
# T4 (ПОЗИТИВНЫЙ): валидный безопасный вход + реальные factcheck-скрипты.
#   Деплой НЕ должен блокироваться по причине "missing dependency".
#   (Может быть exit 2 если factcheck нашёл числовое расхождение в фикстуре —
#    это легитимный блок контента, не fail-open. Поэтому проверяем что причина
#    блока — НЕ про отсутствие скрипта.)
# ============================================================
echo
echo "[T4] позитивный: реальные скрипты на месте"
if [[ -f "/Users/antonk/artvision-data/.claude-shared/scripts/factcheck-numeric.py" \
   && -f "/Users/antonk/artvision-data/.claude-shared/scripts/factcheck-finance-domain.py" ]]; then
    run_hook "$DRAFT_HOOK" "$FIN_SCP"
    if [[ "$RC" -eq 0 ]]; then
        ok "валидный вход проходит (exit 0) — fail-closed не ложно-блокирует"
    elif [[ "$RC" -eq 2 ]] && ! echo "$OUT" | grep -q 'FAIL-CLOSED: обязательный'; then
        ok "exit 2 по контентной причине (расхождение чисел), НЕ из-за отсутствия скрипта — корректно"
    else
        bad "блок по причине отсутствия зависимости при наличии реальных скриптов (ложный fail-closed). RC=$RC OUT=$OUT"
    fi
else
    printf '  \033[33mSKIP\033[0m реальные factcheck-скрипты недоступны — позитивный кейс не проверен\n'
fi

# ============================================================
# T5: bypass-env сохранён и работает (легитимный осознанный обход).
# ============================================================
echo
echo "[T5] легитимный bypass FINANCE_DEPLOY_SKIP=1 сохранён"
OUT=$(CLAUDE_TOOL_NAME="Bash" CLAUDE_BASH_COMMAND="$FIN_SCP" FINANCE_DEPLOY_SKIP=1 bash "$DRAFT_VARIANT" 2>/dev/null)
RC=$?
if [[ "$RC" -eq 0 ]]; then
    ok "bypass обходит даже при отсутствии зависимости (как и было) — не сломали легитимный путь"
else
    bad "ожидался exit 0 при FINANCE_DEPLOY_SKIP=1, получен $RC"
fi

# --- итог ---------------------------------------------------------------
echo
echo "─────────────────────────────────────────────"
printf 'PASS=%d  FAIL=%d\n' "$PASS" "$FAIL"
rm -rf "$WORKDIR"
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
