#!/usr/bin/env bash
# pre-yandex-maps-place-check.sh
# Hook: PreToolUse on Write/Edit для JSON/HTML с Yandex Maps URLs
# Прецедент: 15.05.2026 СОШ 91 — URL org/1003859771 указал на школу в Ижевске вместо СПб
# Bypass: PLACE_VERIFY_OFF=1

set -eo pipefail

# Bypass via env
if [ "${PLACE_VERIFY_OFF:-0}" = "1" ]; then
    exit 0
fi

INPUT=$(cat)

TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || echo "")
if [ "$TOOL_NAME" != "Write" ] && [ "$TOOL_NAME" != "Edit" ]; then
    exit 0
fi

FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // empty' 2>/dev/null || echo "")
# Only check JSON or HTML
case "$FILE_PATH" in
    *.json|*.html) ;;
    *) exit 0 ;;
esac

# Get content (Write: content; Edit: new_string)
CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // .tool_input.new_string // empty' 2>/dev/null || echo "")
if [ -z "$CONTENT" ]; then
    exit 0
fi

# Look for Yandex Maps org URLs
URLS=$(echo "$CONTENT" | grep -oE 'https?://yandex\.(com|ru)/maps/org/[a-zA-Z0-9_-]+/[0-9]+' 2>/dev/null | sort -u || echo "")
if [ -z "$URLS" ]; then
    exit 0
fi

# Detect target city patterns (simple if-else for bash 3.x compat)
# Returns: city_key, pattern (separator: |||)
detect_city() {
    local TEXT="$1"
    local LOWER
    LOWER=$(echo "$TEXT" | tr '[:upper:]' '[:lower:]')

    if echo "$LOWER" | grep -qE 'санкт-петербург|санкт петербург|спб|петроградск|васильевск|приморск|невск|калининск|кировск|выборг|петергоф|пушкин|колпино|сестрорецк|кронштадт'; then
        echo "spb|||санкт-петербург|санкт петербург|спб|петроградск|васильевск|приморск|невск|калининск|кировск|выборг"
        return
    fi
    if echo "$LOWER" | grep -qE 'москва|moscow|тверская|арбат|таганск|пресн|чисто-пруд|якиманк'; then
        echo "msk|||москва|moscow"
        return
    fi
    if echo "$LOWER" | grep -qE 'екатеринбург|свердловск'; then
        echo "ekb|||екатеринбург|свердловск"
        return
    fi
    if echo "$LOWER" | grep -qE 'новосибирск'; then
        echo "nsk|||новосибирск"
        return
    fi
    if echo "$LOWER" | grep -qE 'казан'; then
        echo "kazan|||казан"
        return
    fi
    if echo "$LOWER" | grep -qE 'нижн.*новгород|нижегород'; then
        echo "nn|||нижний новгород|нижегород"
        return
    fi
    echo ""
}

# Detect from path first, then from content
PATH_DETECT=$(detect_city "$FILE_PATH")
if [ -n "$PATH_DETECT" ]; then
    TARGET_INFO="$PATH_DETECT"
else
    CONTENT_DETECT=$(detect_city "$(echo "$CONTENT" | head -c 2000)")
    TARGET_INFO="$CONTENT_DETECT"
fi

if [ -z "$TARGET_INFO" ]; then
    # Can't determine target city — skip
    exit 0
fi

TARGET_CITY="${TARGET_INFO%%|||*}"
TARGET_PATTERN="${TARGET_INFO#*|||}"

OTHER_CITIES_RE='ижевск|саратов|самара|омск|пермь|воронеж|краснодар|ростов|уфа|тула|ярославль|тверь|калуга|рязань|липецк|тамбов|курск|орёл|орел|брянск|смоленск|псков|новгород|архангельск|мурманск|петрозаводск|сыктывкар|вологда|череповец|кострома|иваново|владимир|чебоксары|казан|ульяновск|пенза|оренбург|стерлитамак|челябинск|курган|тюмень|сургут|нижневартовск|омск|новосибирск|барнаул|кемерово|новокузнецк|томск|красноярск|иркутск|чита|улан-удэ|якутск|хабаровск|владивосток|петропавловск|южно-сахалинск|калининград|сочи|ставрополь|махачкала|грозный|нальчик|владикавказ|астрахань|элиста|симферополь|севастополь|ивановск|иркутск'

# Check each URL
PROBLEM_URLS=""
for URL in $URLS; do
    PAGE=$(timeout 8 curl -sL -A "Mozilla/5.0 (PlaceCheck-Hook)" --max-time 8 "$URL" 2>/dev/null | head -c 15000 || echo "")
    if [ -z "$PAGE" ]; then
        continue  # captcha/timeout - skip silently
    fi

    PAGE_LOWER=$(echo "$PAGE" | tr '[:upper:]' '[:lower:]')

    # Does page mention target city?
    if echo "$PAGE_LOWER" | grep -qE "$TARGET_PATTERN"; then
        continue  # OK
    fi

    # Does page mention OTHER city (likely mismatch)?
    OTHER_CITY=$(echo "$PAGE_LOWER" | grep -oiE "$OTHER_CITIES_RE" 2>/dev/null | head -1 || echo "")
    if [ -n "$OTHER_CITY" ]; then
        PROBLEM_URLS="${PROBLEM_URLS}    • ${URL} → найдено: ${OTHER_CITY} (ожидалось: ${TARGET_CITY})
"
    fi
done

if [ -n "$PROBLEM_URLS" ]; then
    {
        echo ""
        echo "🚫 [pre-yandex-maps-place-check] BLOCKED: подмена города в Yandex Maps URLs"
        echo ""
        echo "  File: $FILE_PATH"
        echo "  Target city: $TARGET_CITY"
        echo ""
        echo "  Проблемные URL:"
        printf "%b" "$PROBLEM_URLS"
        echo ""
        echo "  Прецедент: 15.05.2026 СОШ 91 — URL org/1003859771 указал на школу в Ижевске,"
        echo "  попал в schools-yandex.json как СПб. Strict-факчекер обнаружил через 30 мин."
        echo ""
        echo "  Bypass: PLACE_VERIFY_OFF=1"
        echo ""
    } >&2
    exit 2
fi

exit 0
