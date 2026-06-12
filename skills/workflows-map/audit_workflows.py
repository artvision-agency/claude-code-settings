#!/usr/bin/env python3
"""Инвентарь named workflows + сверка CORRIDOR_MAP combine.js ↔ существующие .js.
Exit 0 = всё ок; Exit 2 = есть broken corridor (corridor → несуществующий .js).
Usage: audit_workflows.py [workflows_dir]
"""
import sys, os, re

WF_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(
    "~/artvision-data/.claude/workflows")


def meta_field(text, field):
    m = re.search(field + r"\s*:\s*'([^']*)'", text)
    return m.group(1) if m else ""


def main():
    if not os.path.isdir(WF_DIR):
        print(f"ERROR: нет папки {WF_DIR}"); sys.exit(1)
    files = sorted(f for f in os.listdir(WF_DIR) if f.endswith(".js"))
    names = {f[:-3] for f in files}

    print(f"# Инвентарь workflows ({WF_DIR}) — {len(files)} шт.\n")
    print("| workflow.js | meta.name | описание (кратко) |")
    print("|---|---|---|")
    for f in files:
        txt = open(os.path.join(WF_DIR, f), errors="ignore").read()
        nm = meta_field(txt, "name")
        desc = meta_field(txt, "description")[:70]
        print(f"| {f} | {nm} | {desc} |")

    # Сверка CORRIDOR_MAP combine.js
    combine = os.path.join(WF_DIR, "combine.js")
    broken = []
    if os.path.exists(combine):
        ct = open(combine, errors="ignore").read()
        corridors = set(re.findall(r"corridor:\s*'([a-z0-9-]+)'", ct))
        print(f"\n# Сверка CORRIDOR_MAP combine.js ↔ файлы ({len(corridors)} коридоров)\n")
        print("| corridor | статус |")
        print("|---|---|")
        for c in sorted(corridors):
            if c == "manual":
                print(f"| {c} | OK (спец, без файла) |"); continue
            if c in names:
                print(f"| {c} | OK ({c}.js) |")
            else:
                print(f"| {c} | BROKEN — нет {c}.js |"); broken.append(c)
    else:
        print("\n⚠️ combine.js не найден — сверка пропущена")

    print("\n# Итог")
    if broken:
        print(f"BROKEN corridors ({len(broken)}): {', '.join(broken)} — EXEC throw при боевом combine!")
        sys.exit(2)
    print("Все corridor → существующий .js или manual. OK.")


if __name__ == "__main__":
    main()
