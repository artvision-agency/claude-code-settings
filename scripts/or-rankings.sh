#!/usr/bin/env bash
# or-rankings.sh — БЕСПЛАТНО тянет каталог моделей OpenRouter (GET /api/v1/models, без ключа, без MCP)
# и выдаёт топ по цене/контексту + список FREE-моделей. Ноль overhead (запускается по требованию).
# Источник правды: openrouter.ai/api/v1/models (public, no-auth). Правило: service-knowledge-base.md
# Usage:
#   or-rankings.sh            — сводка в stdout + полный каталог в файл
#   or-rankings.sh free       — только бесплатные модели (pricing=0)
#   or-rankings.sh cheap      — топ-20 самых дешёвых платных (по prompt-цене)
#   or-rankings.sh ctx        — топ-20 по размеру контекста
set -euo pipefail

MODE="${1:-summary}"
OUT_DIR="$HOME/artvision-data/knowledge/services/openrouter"
DATE="$(date +%Y-%m-%d)"
OUT_FILE="$OUT_DIR/models-catalog-$DATE.md"
API="https://openrouter.ai/api/v1/models"

mkdir -p "$OUT_DIR"

TMP_JSON="$(mktemp)"
trap 'rm -f "$TMP_JSON"' EXIT
curl -sS --fail --max-time 30 "$API" -o "$TMP_JSON" || { echo "ERROR: не удалось получить $API"; exit 1; }

python3 - "$MODE" "$OUT_FILE" "$DATE" "$TMP_JSON" <<'PYEOF'
import sys, json
mode, out_file, date, json_path = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
with open(json_path) as jf:
    data = json.load(jf).get("data", [])

def price(m, key):
    try: return float(m.get("pricing", {}).get(key, 0) or 0)
    except (TypeError, ValueError): return 0.0

rows = []
for m in data:
    rows.append({
        "id": m.get("id", "?"),
        "ctx": m.get("context_length", 0) or 0,
        "p_in": price(m, "prompt"),      # $ за токен
        "p_out": price(m, "completion"),
    })

free = [r for r in rows if r["p_in"] == 0 and r["p_out"] == 0]
paid = [r for r in rows if r["p_in"] > 0 or r["p_out"] > 0]

def fmt_price(p):  # $/токен -> $/1M токенов
    return f"${p*1_000_000:.2f}/1M" if p else "FREE"

def table(items):
    out = ["| Модель | Контекст | Вход | Выход |", "|---|---|---|---|"]
    for r in items:
        out.append(f"| `{r['id']}` | {r['ctx']:,} | {fmt_price(r['p_in'])} | {fmt_price(r['p_out'])} |")
    return "\n".join(out)

# Полный каталог -> файл
with open(out_file, "w") as f:
    f.write(f"# OpenRouter — каталог моделей (срез {date})\n\n")
    f.write(f"> Источник: openrouter.ai/api/v1/models (public, no-auth). Всего моделей: {len(rows)}, из них FREE: {len(free)}.\n\n")
    f.write(f"## Бесплатные модели ({len(free)})\n\n{table(sorted(free, key=lambda r:-r['ctx']))}\n\n")
    f.write(f"## Все платные ({len(paid)}) — по возрастанию цены входа\n\n{table(sorted(paid, key=lambda r:r['p_in']))}\n")

# stdout по режиму
print(f"OpenRouter каталог {date}: всего {len(rows)} моделей, FREE {len(free)}. Полный -> {out_file}\n")
if mode == "free":
    print(f"# Бесплатные модели ({len(free)})\n")
    print(table(sorted(free, key=lambda r:-r['ctx'])))
elif mode == "cheap":
    print("# Топ-20 самых дешёвых платных (по цене входа)\n")
    print(table(sorted(paid, key=lambda r:r['p_in'])[:20]))
elif mode == "ctx":
    print("# Топ-20 по размеру контекста\n")
    print(table(sorted(rows, key=lambda r:-r['ctx'])[:20]))
else:  # summary
    print(f"# Бесплатные топ-10 по контексту\n")
    print(table(sorted(free, key=lambda r:-r['ctx'])[:10]))
    print(f"\n# Дешёвые платные топ-10\n")
    print(table(sorted(paid, key=lambda r:r['p_in'])[:10]))
PYEOF
