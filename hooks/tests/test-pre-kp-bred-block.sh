#!/bin/bash
# Тесты для pre-kp-bred-block.sh — все 7 категорий + bypass + non-KP path
# Run: bash test-pre-kp-bred-block.sh

HOOK="$HOME/.claude/hooks/pre-kp-bred-block.sh"
PASS=0
FAIL=0

assert_blocked() {
    local desc="$1" content="$2" expected_cat="$3"
    local input='{"tool_name":"Write","tool_input":{"file_path":"/var/www/artvision/kp/test/index.html","content":"'"$content"'"}}'
    local out exit_code
    out=$(echo "$input" | bash "$HOOK" 2>&1)
    exit_code=$?
    if [ $exit_code -eq 2 ] && echo "$out" | grep -q "$expected_cat"; then
        echo "  ✓ $desc"
        PASS=$((PASS + 1))
    else
        echo "  ✗ $desc — expected exit 2 with $expected_cat, got $exit_code"
        FAIL=$((FAIL + 1))
    fi
}

assert_passed() {
    local desc="$1" content="$2"
    local input='{"tool_name":"Write","tool_input":{"file_path":"/var/www/artvision/kp/test/index.html","content":"'"$content"'"}}'
    local exit_code
    echo "$input" | bash "$HOOK" >/dev/null 2>&1
    exit_code=$?
    if [ $exit_code -eq 0 ]; then
        echo "  ✓ $desc"
        PASS=$((PASS + 1))
    else
        echo "  ✗ $desc — expected exit 0, got $exit_code"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== Тесты pre-kp-bred-block.sh ==="

# 1. AI_MODELS — должно блокировать
assert_blocked "Llama в тексте" "<p>Использовали Llama-3 для анализа</p>" "AI_MODELS"
assert_blocked "ChatGPT в тексте" "<p>В ChatGPT нашли</p>" "AI_MODELS"
assert_blocked "Groq провайдер" "<p>через Groq</p>" "AI_PROVIDERS"

# 2. HARSH_WORDS
assert_blocked "обвал трафика" "<p>обвал трафика на 90%</p>" "HARSH_WORDS"
assert_blocked "токсичный рейтинг" "<p>токсичный рейтинг 3.5</p>" "HARSH_WORDS"
assert_blocked "галлюцинируют модели" "<p>галлюцинируют</p>" "HARSH_WORDS"

# 3. SALES_CLICHES
assert_blocked "стать №1 в нише" "<p>стать № 1 в нише</p>" "SALES_CLICHES"
assert_blocked "уникальное решение" "<p>уникальное решение для вас</p>" "SALES_CLICHES"
assert_blocked "под ключ" "<p>SEO под ключ</p>" "SALES_CLICHES_GENERIC"

# 4. INTERNAL_MARKERS
assert_blocked "CONFIRMED в тексте" "<p>4,7 CONFIRMED</p>" "INTERNAL_MARKERS_TAGS"
assert_blocked "WebFetch упомянут" "<p>через WebFetch</p>" "INTERNAL_TOOLS"
assert_blocked "Topvisor API" "<p>Topvisor API даёт</p>" "INTERNAL_API_NAMES"

# 5. ARTVISION_CONTACTS
assert_blocked "@antonkamer" "<p>напишите @antonkamer</p>" "ARTVISION_CONTACTS"
assert_blocked "info@artvision" "<p>info@artvision.pro</p>" "ARTVISION_CONTACTS"

# 6. ARTVISION brand в КП партнёра (AdvertMed)
assert_blocked "Artvision Radar в тексте" "<p>через Artvision Radar</p>" "ARTVISION_BRAND"

# 7. PLAN_OVER_DETAIL
assert_blocked "JSON-LD: LocalBusiness +" "<p>JSON-LD: LocalBusiness + Service</p>" "PLAN_OVER_DETAIL"

# 8. ЧИСТЫЙ контент — должно пропускать
assert_passed "обычный текст" "<p>Аудит показал 14 разрывов по 4 модулям</p>"
assert_passed "технические термины OK" "<p>robots.txt и Schema.org нужно настроить</p>"
assert_passed "генеративные ассистенты OK" "<p>Видимость в генеративных ассистентах</p>"

# 9. Не-КП файл — должно пропускать даже резкие
assert_passed_outside() {
    local desc="$1" content="$2"
    local input='{"tool_name":"Write","tool_input":{"file_path":"/tmp/test.txt","content":"'"$content"'"}}'
    local exit_code
    echo "$input" | bash "$HOOK" >/dev/null 2>&1
    exit_code=$?
    if [ $exit_code -eq 0 ]; then
        echo "  ✓ $desc"
        PASS=$((PASS + 1))
    else
        echo "  ✗ $desc"
        FAIL=$((FAIL + 1))
    fi
}
assert_passed_outside "non-KP path с резкими словами игнорируется" "<p>обвал трафика, ChatGPT, Llama</p>"

# 10. Bypass работает
KP_BRED_OK=1 bash -c '
INPUT=$(echo '"'"'{"tool_name":"Write","tool_input":{"file_path":"/var/www/artvision/kp/test/index.html","content":"<p>обвал ChatGPT</p>"}}'"'"')
echo "$INPUT" | bash '"$HOOK"' >/dev/null 2>&1
test $? -eq 0
' && {
    echo "  ✓ Bypass KP_BRED_OK=1 работает"
    PASS=$((PASS + 1))
} || {
    echo "  ✗ Bypass не работает"
    FAIL=$((FAIL + 1))
}

echo ""
echo "=== Итог: $PASS PASS / $FAIL FAIL ==="
exit $FAIL
