#!/usr/bin/env bash
# Регресс-тест fail-CLOSED для stop-deploy-url-check.sh
# Доказывает: на проблемном входе (malformed JSON / нет session_id / пустой stdin)
# НОВЫЙ черновик блокирует (exit 2), а СТАРЫЙ live тихо пропускал (exit 0).
# Плюс позитивный кейс: валидный безопасный вход без деплоя → проходит (exit 0)
# у обоих.
#
# ВАЖНО: тест не пишет в ~/.claude/hooks/. Только читает live для сравнения
# и гоняет /tmp-черновик.

set -u

OLD="/Users/antonk/.claude/hooks/stop-deploy-url-check.sh"
NEW="/tmp/hookfix-stop-deploy-url-check.sh"

PASS=0
FAIL=0

# run <hook> <stdin-payload> [extra-env]  → печатает rc
run_hook() {
    local hook="$1" payload="$2" env_extra="${3:-}"
    if [[ -n "$env_extra" ]]; then
        printf '%s' "$payload" | env "$env_extra" bash "$hook" >/dev/null 2>&1
    else
        printf '%s' "$payload" | bash "$hook" >/dev/null 2>&1
    fi
    echo $?
}

check() {
    local name="$1" expect="$2" got="$3"
    if [[ "$got" == "$expect" ]]; then
        echo "PASS: $name (exit=$got)"
        PASS=$((PASS+1))
    else
        echo "FAIL: $name (expected exit=$expect, got exit=$got)"
        FAIL=$((FAIL+1))
    fi
}

echo "=== Sanity ==="
[[ -f "$OLD" ]] && echo "live hook present: $OLD" || echo "WARN: live hook missing (old-behavior comparison skipped)"
[[ -f "$NEW" ]] || { echo "FATAL: draft missing $NEW"; exit 1; }
echo

# ---------------------------------------------------------------------------
# 1. MALFORMED JSON  — главный кейс fail-CLOSED
#    Старый: python3 json.load падает → 2>/dev/null → SESSION_ID="" → exit 0 (тихо)
#    Новый:  parse failure → exit 2 (видимый warn)
# ---------------------------------------------------------------------------
MALFORMED='{ this is : not valid json ,,, '
echo "=== Case 1: malformed JSON payload ==="
OLD_RC=$(run_hook "$OLD" "$MALFORMED")
NEW_RC=$(run_hook "$NEW" "$MALFORMED")
echo "  old live exit=$OLD_RC (ожидаем тихий пропуск 0 — баг)"
echo "  new draft exit=$NEW_RC (ожидаем блок 2 — fix)"
check "C1 new blocks malformed JSON" "2" "$NEW_RC"
# Доказываем что старый именно ПРОПУСКАЛ (демонстрация регрессии, не строгий гейт):
if [[ "$OLD_RC" == "0" ]]; then
    echo "  [demo] подтверждено: СТАРЫЙ пропускал (exit 0) там где НОВЫЙ блокирует (exit 2)"
fi
echo

# ---------------------------------------------------------------------------
# 2. VALID JSON, но session_id отсутствует
#    Старый: SESSION_ID="" → exit 0 (тихо)
#    Новый:  rc=3 → fail_closed → exit 2
# ---------------------------------------------------------------------------
NO_SID='{"stop_hook_active": true, "foo": "bar"}'
echo "=== Case 2: valid JSON, no session_id ==="
OLD_RC=$(run_hook "$OLD" "$NO_SID")
NEW_RC=$(run_hook "$NEW" "$NO_SID")
echo "  old live exit=$OLD_RC / new draft exit=$NEW_RC"
check "C2 new blocks missing session_id" "2" "$NEW_RC"
echo

# ---------------------------------------------------------------------------
# 3. EMPTY stdin
#    Старый: INPUT='{}' (через ||echo) → SESSION_ID="" → exit 0 (тихо)
#    Новый:  пустой stdin → fail_closed → exit 2
# ---------------------------------------------------------------------------
echo "=== Case 3: empty stdin ==="
OLD_RC=$(run_hook "$OLD" "")
NEW_RC=$(run_hook "$NEW" "")
echo "  old live exit=$OLD_RC / new draft exit=$NEW_RC"
check "C3 new blocks empty stdin" "2" "$NEW_RC"
echo

# ---------------------------------------------------------------------------
# 4. VALID JSON, session_id есть, но транскрипта НЕТ
#    Старый: [[ ! -f JSONL ]] → exit 0 (тихо)
#    Новый:  fail_closed → exit 2
# ---------------------------------------------------------------------------
NO_FILE='{"session_id": "nonexistent-session-zzz-9999"}'
echo "=== Case 4: session_id valid but transcript missing ==="
OLD_RC=$(run_hook "$OLD" "$NO_FILE")
NEW_RC=$(run_hook "$NEW" "$NO_FILE")
echo "  old live exit=$OLD_RC / new draft exit=$NEW_RC"
check "C4 new blocks missing transcript" "2" "$NEW_RC"
echo

# ---------------------------------------------------------------------------
# 5. PATH TRAVERSAL в session_id
#    Новый: case-guard → exit 2
# ---------------------------------------------------------------------------
TRAVERSAL='{"session_id": "../../etc/passwd"}'
echo "=== Case 5: path traversal in session_id ==="
NEW_RC=$(run_hook "$NEW" "$TRAVERSAL")
echo "  new draft exit=$NEW_RC"
check "C5 new blocks path traversal" "2" "$NEW_RC"
echo

# ---------------------------------------------------------------------------
# 6. ПОЗИТИВ: валидный JSON + реальный транскрипт без deploy-маркеров → exit 0
#    Создаём временный транскрипт под фейковым session_id в реальной директории.
# ---------------------------------------------------------------------------
PROJ_DIR="$HOME/.claude/projects/-Users-antonk"
echo "=== Case 6: valid transcript, no deploy markers (legit pass) ==="
if [[ -d "$PROJ_DIR" && -w "$PROJ_DIR" ]]; then
    FAKE_SID="hooktest-fake-$$-$RANDOM"
    FAKE_JSONL="$PROJ_DIR/$FAKE_SID.jsonl"
    # один assistant-message без deploy-маркеров
    printf '%s\n' '{"type":"assistant","message":{"content":[{"type":"text","text":"Готово, всё проверил. Никакого деплоя."}]}}' > "$FAKE_JSONL"
    GOOD_PAYLOAD="{\"session_id\": \"$FAKE_SID\"}"
    NEW_RC=$(run_hook "$NEW" "$GOOD_PAYLOAD")
    echo "  new draft exit=$NEW_RC (ожидаем 0 — нет деплоя, легитимный пропуск)"
    check "C6 new passes valid no-deploy transcript" "0" "$NEW_RC"
    rm -f "$FAKE_JSONL"
else
    echo "  SKIP: $PROJ_DIR недоступна для записи — позитивный кейс с реальным файлом пропущен"
    echo "  (remaining_risk: позитив проверен только косвенно)"
fi
echo

# ---------------------------------------------------------------------------
# 7. ПОЗИТИВ: транскрипт с deploy-маркером И URL первой строкой → exit 0
# ---------------------------------------------------------------------------
echo "=== Case 7: valid transcript, deploy + URL first line (legit pass) ==="
if [[ -d "$PROJ_DIR" && -w "$PROJ_DIR" ]]; then
    FAKE_SID="hooktest-ok-$$-$RANDOM"
    FAKE_JSONL="$PROJ_DIR/$FAKE_SID.jsonl"
    printf '%s\n' '{"type":"assistant","message":{"content":[{"type":"text","text":"https://artvision.pro/kp/test/\nОпубликовано. Live URL: https://artvision.pro/kp/test/"}]}}' > "$FAKE_JSONL"
    GOOD_PAYLOAD="{\"session_id\": \"$FAKE_SID\"}"
    NEW_RC=$(run_hook "$NEW" "$GOOD_PAYLOAD")
    echo "  new draft exit=$NEW_RC (ожидаем 0 — URL в первой строке)"
    check "C7 new passes URL-first deploy" "0" "$NEW_RC"
    rm -f "$FAKE_JSONL"
else
    echo "  SKIP: $PROJ_DIR недоступна"
fi
echo

# ---------------------------------------------------------------------------
# 8. КОНТРОЛЬ enforcement: deploy-маркер есть, но URL НЕ в первых 3 строках → exit 2
#    (оригинальная функция хука должна сохраниться)
# ---------------------------------------------------------------------------
echo "=== Case 8: deploy URL present but NOT in first 3 lines (original enforcement) ==="
if [[ -d "$PROJ_DIR" && -w "$PROJ_DIR" ]]; then
    FAKE_SID="hooktest-late-$$-$RANDOM"
    FAKE_JSONL="$PROJ_DIR/$FAKE_SID.jsonl"
    printf '%s\n' '{"type":"assistant","message":{"content":[{"type":"text","text":"Строка 1\nСтрока 2\nСтрока 3\nСтрока 4 Опубликовано https://artvision.pro/kp/late/"}]}}' > "$FAKE_JSONL"
    GOOD_PAYLOAD="{\"session_id\": \"$FAKE_SID\"}"
    NEW_RC=$(run_hook "$NEW" "$GOOD_PAYLOAD")
    echo "  new draft exit=$NEW_RC (ожидаем 2 — URL не первой строкой)"
    check "C8 new keeps original URL-first enforcement" "2" "$NEW_RC"
    rm -f "$FAKE_JSONL"
else
    echo "  SKIP: $PROJ_DIR недоступна"
fi
echo

# ---------------------------------------------------------------------------
# 9. BYPASS сохранён: DEPLOY_URL_OK=1 → exit 0 даже на malformed
# ---------------------------------------------------------------------------
echo "=== Case 9: legit bypass DEPLOY_URL_OK=1 still works ==="
NEW_RC=$(run_hook "$NEW" "$MALFORMED" "DEPLOY_URL_OK=1")
echo "  new draft exit=$NEW_RC (ожидаем 0 — легитимный bypass)"
check "C9 legit bypass preserved" "0" "$NEW_RC"
echo

echo "============================================"
echo "RESULT: PASS=$PASS FAIL=$FAIL"
echo "============================================"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
