#!/usr/bin/env bash
# orm-pulse: Sheet snapshot через curl + Safari cookies
# Usage: ./sheet-snapshot.sh <client_slug>
# Example: ./sheet-snapshot.sh blumart
#
# Читает clients/<client>/orm/registry.yaml, экспортирует все вкладки всех Sheets в CSV.
# Сохраняет в clients/<client>/orm/snapshots/<YYYY-MM-DD-HHMM>/<sheet_name>_<gid>.csv
# Сравнивает MD5 с предыдущим snapshot, выдаёт diff.

set -euo pipefail

CLIENT="${1:?Usage: $0 <client_slug>}"
ARTVISION="${HOME}/artvision-data"
REGISTRY="${ARTVISION}/clients/${CLIENT}/orm/registry.yaml"

if [[ ! -f "$REGISTRY" ]]; then
    echo "❌ Registry not found: $REGISTRY" >&2
    exit 1
fi

# Cookies — из /tmp/orm-pulse/<client>/google_cookies.txt (если был fresh-fetch ранее)
# Иначе экстрактим из Safari binarycookies
COOKIES_DIR="/tmp/orm-pulse/${CLIENT}"
COOKIES_FILE="${COOKIES_DIR}/google_cookies.txt"
mkdir -p "$COOKIES_DIR"

extract_safari_cookies() {
    local out="$1"
    local safari_db="${HOME}/Library/Containers/com.apple.Safari/Data/Library/Cookies/Cookies.binarycookies"

    if [[ ! -f "$safari_db" ]]; then
        echo "❌ Safari cookies not found: $safari_db" >&2
        return 1
    fi

    python3 <<'PYEOF' >"$out"
import sys, struct
from pathlib import Path

DB = Path.home() / "Library/Containers/com.apple.Safari/Data/Library/Cookies/Cookies.binarycookies"

# Простой парсер binarycookies (формат Apple)
data = DB.read_bytes()
if data[:4] != b'cook':
    print("# bad magic", file=sys.stderr)
    sys.exit(1)

num_pages = struct.unpack(">I", data[4:8])[0]
page_sizes = []
offset = 8
for i in range(num_pages):
    page_sizes.append(struct.unpack(">I", data[offset:offset+4])[0])
    offset += 4

print("# Netscape HTTP Cookie File")
page_offset = offset
for page_size in page_sizes:
    page = data[page_offset:page_offset + page_size]
    page_offset += page_size

    if page[:4] != b'\\x00\\x00\\x01\\x00':
        continue
    num_cookies = struct.unpack("<I", page[4:8])[0]
    cookie_offsets = []
    for i in range(num_cookies):
        cookie_offsets.append(struct.unpack("<I", page[8 + i*4 : 12 + i*4])[0])

    for c_off in cookie_offsets:
        try:
            size = struct.unpack("<I", page[c_off:c_off+4])[0]
            flags = struct.unpack("<I", page[c_off+8:c_off+12])[0]
            url_off = struct.unpack("<I", page[c_off+16:c_off+20])[0]
            name_off = struct.unpack("<I", page[c_off+20:c_off+24])[0]
            path_off = struct.unpack("<I", page[c_off+24:c_off+28])[0]
            value_off = struct.unpack("<I", page[c_off+28:c_off+32])[0]
            expiry = struct.unpack("<d", page[c_off+40:c_off+48])[0]

            def read_str(start):
                end = page.index(b'\\x00', c_off + start)
                return page[c_off + start:end].decode('utf-8', errors='replace')

            domain = read_str(url_off)
            name = read_str(name_off)
            path = read_str(path_off)
            value = read_str(value_off)

            if 'google' not in domain.lower():
                continue

            secure = "TRUE" if flags & 1 else "FALSE"
            httponly = "TRUE" if flags & 4 else "FALSE"
            include_subdomains = "TRUE" if domain.startswith('.') else "FALSE"
            expiry_unix = int(978307200 + expiry)  # Apple epoch → Unix epoch

            print(f"{domain}\\t{include_subdomains}\\t{path}\\t{secure}\\t{expiry_unix}\\t{name}\\t{value}")
        except Exception as e:
            continue
PYEOF
}

# Если cookies stale (>2 часа) — re-extract
if [[ ! -f "$COOKIES_FILE" ]] || [[ $(find "$COOKIES_FILE" -mmin +120 2>/dev/null) ]]; then
    echo "→ Extracting fresh Safari cookies..."
    extract_safari_cookies "$COOKIES_FILE" || {
        echo "⚠️  Cookie extraction failed. Using existing cookies if any." >&2
    }
fi

# Парсим registry для получения списка sheet_id + gid
SHEETS_JSON=$(python3 - "$REGISTRY" << 'PYEOF'
import sys, yaml, json
reg = yaml.safe_load(open(sys.argv[1]))
result = []
for sheet_key, sheet_def in (reg.get('sheets') or {}).items():
    sheet_id = sheet_def.get('id')
    for tab in sheet_def.get('tabs', []):
        result.append({
            'sheet_key': sheet_key,
            'sheet_id': sheet_id,
            'gid': tab.get('gid'),
            'name': tab.get('name', '').replace(' ', '_').replace('(', '').replace(')', ''),
        })
print(json.dumps(result))
PYEOF
)

# Output dir со временной меткой
TIMESTAMP=$(date +%Y-%m-%d-%H%M)
OUT_DIR="${ARTVISION}/clients/${CLIENT}/orm/snapshots/${TIMESTAMP}"
mkdir -p "$OUT_DIR"

LATEST_LINK="${ARTVISION}/clients/${CLIENT}/orm/snapshots/latest"
PREV_LINK="${ARTVISION}/clients/${CLIENT}/orm/snapshots/prev"

CHANGES_REPORT="${OUT_DIR}/_changes.md"
echo "# Sheet Snapshot Changes — ${TIMESTAMP}" > "$CHANGES_REPORT"
echo "" >> "$CHANGES_REPORT"
echo "| Sheet | gid | Result | Δ vs previous |" >> "$CHANGES_REPORT"
echo "|-------|-----|--------|---------------|" >> "$CHANGES_REPORT"

# Для каждой вкладки — curl + сравнение MD5
echo "$SHEETS_JSON" | python3 -c "
import sys, json
for tab in json.loads(sys.stdin.read()):
    print(f\"{tab['sheet_key']}|{tab['sheet_id']}|{tab['gid']}|{tab['name']}\")
" | while IFS='|' read -r sheet_key sheet_id gid name; do
    out_file="${OUT_DIR}/${sheet_key}_${gid}.csv"
    url="https://docs.google.com/spreadsheets/d/${sheet_id}/export?format=csv&gid=${gid}"

    echo "→ ${sheet_key} / gid=${gid} (${name})"

    if curl -sL \
        --cookie "$COOKIES_FILE" \
        -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15" \
        -o "$out_file" \
        "$url"; then

        # Проверка что не HTML-redirect
        if head -1 "$out_file" | grep -qi "<HTML\|<!DOCTYPE"; then
            echo "  ❌ Got HTML (cookies expired?)"
            echo "| ${sheet_key} | ${gid} | ❌ HTML redirect | — |" >> "$CHANGES_REPORT"
            continue
        fi

        size=$(wc -l < "$out_file" | tr -d ' ')
        # Robust md5: try /sbin/md5 (BSD), fallback md5sum (Linux), fallback empty (just compare size)
        md5=""
        if command -v md5 >/dev/null 2>&1; then
            md5=$(md5 -q "$out_file" 2>/dev/null || true)
        elif command -v md5sum >/dev/null 2>&1; then
            md5=$(md5sum "$out_file" 2>/dev/null | awk '{print $1}' || true)
        fi

        # Сравнение с предыдущим snapshot если есть
        delta="—"
        if [[ -L "$PREV_LINK" ]] && [[ -f "${PREV_LINK}/${sheet_key}_${gid}.csv" ]]; then
            prev_md5=""
            if command -v md5 >/dev/null 2>&1; then
                prev_md5=$(md5 -q "${PREV_LINK}/${sheet_key}_${gid}.csv" 2>/dev/null || true)
            elif command -v md5sum >/dev/null 2>&1; then
                prev_md5=$(md5sum "${PREV_LINK}/${sheet_key}_${gid}.csv" 2>/dev/null | awk '{print $1}' || true)
            fi
            if [[ -n "$md5" && "$md5" == "$prev_md5" ]]; then
                delta="идентичен"
            else
                prev_size=$(wc -l < "${PREV_LINK}/${sheet_key}_${gid}.csv" | tr -d ' ')
                delta="строк: ${prev_size} → ${size}"
            fi
        fi

        echo "  ✅ ${size} строк, md5=${md5:0:8}"
        echo "| ${sheet_key} | ${gid} | ${size} строк, md5=${md5:0:8} | ${delta} |" >> "$CHANGES_REPORT"
    else
        echo "  ❌ curl failed"
        echo "| ${sheet_key} | ${gid} | ❌ curl failed | — |" >> "$CHANGES_REPORT"
    fi
done

# Обновляем символические ссылки latest → previous → current
if [[ -L "$LATEST_LINK" ]]; then
    rm -f "$PREV_LINK"
    mv "$LATEST_LINK" "$PREV_LINK"
fi
ln -sf "$OUT_DIR" "$LATEST_LINK"

echo ""
echo "✅ Snapshot saved: $OUT_DIR"
echo "📋 Changes report: $CHANGES_REPORT"
echo ""
cat "$CHANGES_REPORT"
