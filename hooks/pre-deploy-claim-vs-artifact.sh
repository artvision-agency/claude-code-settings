#!/usr/bin/env bash
# pre-deploy-claim-vs-artifact.sh — PreToolUse(Bash) hook
#
# Блокирует deploy/scp клиентского HTML-аудита, если в файле заявлены
# инструменты сбора данных (Screaming Frog, SEMrush, Keys.so, Lighthouse,
# NAP-каталоги) с конкретными числами, но реальных артефактов в
# clients/<name>/seo/<date>/ либо нет, либо pipeline-summary.md помечает
# их как failed.
#
# Прецеденты:
#   - 04.05.2026 Wave 2 AdvertMed — заявлено 8 шагов методологии, реально 4
#   - 09.05.2026 spb-kursy v3 — заявлено «Screaming Frog 2 799 ссылок»,
#                                 реально SF упал, sf-out папки не было
#
# Bypass: CLAIM_ARTIFACT_FORCE=1 <команда>
#
# Trigger:
#   Bash command содержит scp / safe-deploy-html.sh с путём *.html
#   ИЛИ путь /var/www/artvision/kp/<slug>/index.html
#
# Логика:
#   1. Извлечь локальный HTML-файл из команды
#   2. Из пути файла определить клиента (presales/<slug>/ или clients/<slug>/)
#   3. Найти связанную папку clients/<slug>/seo/<latest_date>/
#   4. Прочитать pipeline-summary.md (если есть) и собрать список failed/skipped инструментов
#   5. Прочитать HTML, найти упоминания инструментов в #tools / #pages блоках
#      с числами (паттерн: «<инструмент>...<число> <единица>» или таблица tools-grid)
#   6. Для каждого упоминания — есть ли соответствующий артефакт?
#   7. Если расхождение → exit 2 + понятное сообщение
#
# Exit codes: 0 = пропуск, 2 = блок (deploy не выполняется)

set -uo pipefail

# 0. Bypass
[ "${CLAIM_ARTIFACT_FORCE:-0}" = "1" ] && exit 0

# 1. Read JSON stdin
INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

TOOL_NAME=$(printf '%s' "$INPUT" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("tool_name",""))' 2>/dev/null)
[ "$TOOL_NAME" != "Bash" ] && exit 0

CMD=$(printf '%s' "$INPUT" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("tool_input",{}).get("command",""))' 2>/dev/null)
[ -z "$CMD" ] && exit 0

# 2. Trigger: deploy команда с *.html
case "$CMD" in
    *safe-deploy-html.sh*) ;;
    *scp*\.html*) ;;
    *) exit 0 ;;
esac

# 3. Локальный HTML файл + slug клиента (через python — sed на macOS капризен)
EXTRACTED=$(printf '%s' "$CMD" | python3 -c '
import sys, re
cmd = sys.stdin.read()
# Все *.html пути в команде, кроме /var/www
paths = [p for p in re.findall(r"/[A-Za-z0-9_./-]+\.html", cmd) if "/var/www" not in p]
if not paths:
    sys.exit(0)
html = paths[0]
# slug из presales/<slug>/  или  clients/<slug>/
m = re.search(r"/(?:presales|clients)/([^/]+)/", html)
if not m:
    sys.exit(0)
print(html)
print(m.group(1))
' 2>/dev/null)

[ -z "$EXTRACTED" ] && exit 0
HTML_PATH=$(printf '%s\n' "$EXTRACTED" | sed -n '1p')
CLIENT_SLUG=$(printf '%s\n' "$EXTRACTED" | sed -n '2p')
[ -z "$HTML_PATH" ] || [ -z "$CLIENT_SLUG" ] && exit 0
[ ! -f "$HTML_PATH" ] && exit 0

# 5. Найти папку seo/<latest_date>/
SEO_BASE="$HOME/artvision-data/clients/$CLIENT_SLUG/seo"
[ ! -d "$SEO_BASE" ] && exit 0  # нет SEO-папки — клиент без аудита, не наш кейс

LATEST_SEO=$(ls -t "$SEO_BASE" 2>/dev/null | head -1)
[ -z "$LATEST_SEO" ] && exit 0
SEO_DIR="$SEO_BASE/$LATEST_SEO"

# 6. Сбор claims из HTML и проверка
RESULT=$(python3 - "$HTML_PATH" "$SEO_DIR" <<'PYEOF'
import sys, re, os
html_path, seo_dir = sys.argv[1], sys.argv[2]
try:
    with open(html_path, encoding='utf-8') as f:
        html = f.read()
except Exception:
    sys.exit(0)

# Только если в HTML есть блок #tools (раздел «Чем просканировали»)
if 'id="tools"' not in html and 'scan-tool' not in html:
    sys.exit(0)

issues = []

# Проверка артефактов
sf_out = os.path.join(seo_dir, 'sf-out')
sf_csv_exists = os.path.exists(os.path.join(sf_out, 'internal_all.csv')) or \
                os.path.exists(os.path.join(sf_out, 'internal_html.csv'))
sf_url_count = 0
if sf_csv_exists:
    for cand in ('internal_all.csv', 'internal_html.csv'):
        p = os.path.join(sf_out, cand)
        if os.path.exists(p):
            try:
                with open(p) as f:
                    sf_url_count = sum(1 for _ in f) - 1  # минус header
                break
            except Exception:
                pass

semrush_dir = os.path.join(seo_dir, 'semrush')
semrush_files = []
if os.path.isdir(semrush_dir):
    semrush_files = [f for f in os.listdir(semrush_dir) if f.endswith('.json')]

keysso_dir = os.path.join(seo_dir, 'keys-so')
keysso_files = []
if os.path.isdir(keysso_dir):
    keysso_files = [f for f in os.listdir(keysso_dir) if f.endswith('.json')]

# 1. Screaming Frog claim
sf_pattern = re.search(r'(Screaming\s*Frog|sf\s*crawl|sf-out)[^<]*?(\d[\d\s]*)\s*(ссыл|URL|url|стран)', html)
if sf_pattern:
    claimed = sf_pattern.group(2).replace(' ', '').strip()
    try:
        claimed_n = int(claimed)
        if not sf_csv_exists:
            issues.append(f"❌ Screaming Frog: заявлено «{claimed_n} ссылок/URL», но {sf_out} НЕ существует / нет CSV")
        elif sf_url_count > 0 and abs(claimed_n - sf_url_count) > max(50, sf_url_count * 0.3):
            issues.append(f"⚠️  Screaming Frog: заявлено «{claimed_n}», в CSV реально {sf_url_count} URL (расхождение >30%)")
    except ValueError:
        pass

# 2. SEMrush claim
sem_pattern = re.search(r'SEMrush[^<]{0,200}?(\d[\d\s]*)\s*(стран|URL|page)', html, re.IGNORECASE)
if sem_pattern and not semrush_files:
    issues.append(f"❌ SEMrush: заявлены страницы/данные, но {semrush_dir} пуст / не существует")

# 3. Keys.so claim
keysso_pattern = re.search(r'Keys\.so|кейссо', html, re.IGNORECASE)
if keysso_pattern and not keysso_files:
    # Допускается «Pending — заберём в первую неделю»
    pending_keyword = re.search(r'Keys\.so[^<]{0,300}(Pending|pending|оформля|зарегистр|первой\s*недел)', html, re.IGNORECASE)
    if not pending_keyword:
        issues.append(f"❌ Keys.so: упомянут как источник, но {keysso_dir} пуст и нет пометки 'Pending'")

# 4. Pipeline-summary check (если есть)
ps = os.path.join(seo_dir, 'pipeline-summary.md')
if os.path.exists(ps):
    try:
        with open(ps) as f:
            ps_text = f.read()
        # Если в summary failed/skipped, и инструмент упомянут в HTML
        for line in ps_text.splitlines():
            if 'failed' in line.lower():
                if 'Screaming Frog' in line and re.search(r'Screaming\s*Frog', html, re.IGNORECASE):
                    if not sf_csv_exists:
                        issues.append(f"❌ pipeline-summary.md: 'Screaming Frog crawl | failed', а в HTML заявлен")
                if 'SEMrush' in line and re.search(r'SEMrush', html):
                    if not semrush_files:
                        issues.append(f"❌ pipeline-summary.md: 'SEMrush | failed', а в HTML заявлен")
    except Exception:
        pass

if issues:
    print("BLOCK")
    for i in issues:
        print("  " + i)
PYEOF
)

if printf '%s' "$RESULT" | grep -q '^BLOCK'; then
    {
        echo ""
        echo "🚫 BLOCKED: pre-deploy-claim-vs-artifact"
        echo ""
        echo "  HTML: $HTML_PATH"
        echo "  SEO-папка: $SEO_DIR"
        echo ""
        echo "  Заявка в HTML #tools НЕ подтверждена реальными артефактами:"
        printf '%s\n' "$RESULT" | grep -v '^BLOCK'
        echo ""
        echo "  Действия:"
        echo "    A) Запустить недостающий инструмент:"
        echo "       sf <url> --output-folder $SEO_DIR/sf-out"
        echo "       python3 ~/artvision-data/scripts/semrush_top_pages.py --domain <X>"
        echo "    Б) Убрать заявку из #tools блока"
        echo "    В) Заменить число на 'Pending — заберём в первую неделю'"
        echo ""
        echo "  Прецеденты:"
        echo "    04.05.2026 — AdvertMed Wave 2 (8 шагов заявлено, 4 реально)"
        echo "    09.05.2026 — spb-kursy v3 (2799 SF выдумано)"
        echo ""
        echo "  Bypass: CLAIM_ARTIFACT_FORCE=1 $0"
        echo "  Decision: ~/artvision-data/decisions/2026-05-09-top-pages-required-in-audit.md"
        echo ""
    } >&2
    exit 2
fi

exit 0
