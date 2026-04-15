#!/bin/bash
# PostToolUse (Bash): Playwright скриншоты КП на 3 breakpoints после scp в clients/*/kp/
# Триггер: scp ... clients/*/kp/*.html ... srv | 80.90.181.152
# Цель: визуально ловить асимметрию/обрезы/горизонт-скролл сразу после деплоя

set -u
COMMAND="${CLAUDE_BASH_COMMAND:-$1}"

# Триггер: scp + clients/*/kp/ + (srv|80.90.181.152)
echo "$COMMAND" | grep -qE "scp.*clients/[^/]+/kp/[^/[:space:]]+\.html" || exit 0
echo "$COMMAND" | grep -qE "(srv:|80\.90\.181\.152)" || exit 0

# Извлекаем путь к локальному HTML
LOCAL=$(echo "$COMMAND" | grep -oE "[^[:space:]]*clients/[^/]+/kp/[^/[:space:]]+\.html" | head -1)
[ -z "$LOCAL" ] && exit 0

# clients/<client>/kp/<file>.html
CLIENT=$(echo "$LOCAL" | sed -E 's|.*clients/([^/]+)/kp/.*|\1|')
FILE=$(basename "$LOCAL")
URL="https://artvision.pro/${CLIENT}/kp/${FILE}"

OUT_DIR="/tmp/kp-shots/${CLIENT}-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUT_DIR"

echo ""
echo "📸 [POST-SCP] Скриншоты KP на 3 breakpoints → $URL"

python3 - "$URL" "$OUT_DIR" <<'PYEOF' &
import sys, os
url, out = sys.argv[1], sys.argv[2]
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print(f"⚠️ playwright не установлен: pip install playwright && playwright install chromium")
    sys.exit(0)

bps = [("desktop", 1440, 900), ("tablet", 768, 1024), ("mobile", 375, 812)]
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for name, w, h in bps:
        ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=1)
        page = ctx.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=20000)
            path = os.path.join(out, f"{name}.jpg")
            page.screenshot(path=path, full_page=False, type="jpeg", quality=70)
            print(f"  ✅ {name} ({w}x{h}): {path}")
        except Exception as e:
            print(f"  ⚠️ {name}: {e}")
        finally:
            ctx.close()
    browser.close()
PYEOF

# Не блокируем — фоновый процесс. Сообщение Claude увидит при следующем сообщении пользователя.
echo "  ⏳ скриншоты в фоне → $OUT_DIR/{desktop,tablet,mobile}.jpg"
echo "  → проверь визуально после готовности (Read tool на JPG)"
echo ""

exit 0
