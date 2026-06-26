#!/usr/bin/env python3
"""
creative_standard.py — каталог стандартов рекламных креативов (0 LLM-токенов).

Зачем: стандарты (ракурс/линза, тип баннера, gen-промпт) живут как ДАННЫЕ в catalog.yaml,
а не пересказываются из памяти Claude каждый раз. ad-creative/figma читают по вызову.

Команды:
  list [--type lens|banner]      — показать стандарты
  get <id>                       — полные параметры одного (gen_prompt для генерации)
  add --id X --name "..." --type lens --image <path> --when "a;b" --gen "..." [--source "..."]
                                 — добавить стандарт (копирует картинку в refs/, дописывает yaml)

Каталог: artvision-data/knowledge/marketing/ad-creative-standards/catalog.yaml
"""
import sys, argparse, shutil
from pathlib import Path
import yaml

BASE = Path.home() / "artvision-data" / "knowledge" / "marketing" / "ad-creative-standards"
CAT = BASE / "catalog.yaml"


def load():
    return yaml.safe_load(CAT.read_text(encoding="utf-8")) if CAT.exists() else {"version": 1, "standards": []}


def save(d):
    CAT.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), encoding="utf-8")


def cmd_list(a):
    d = load()
    for s in d["standards"]:
        if a.type and s.get("type") != a.type:
            continue
        print(f"  [{s['id']}] ({s.get('type')}) {s['name']}")
        print(f"       когда: {', '.join(s.get('when_to_apply', []))}")


def cmd_get(a):
    d = load()
    s = next((x for x in d["standards"] if x["id"] == a.id), None)
    if not s:
        print(f"нет стандарта '{a.id}'"); return 1
    print(yaml.safe_dump(s, allow_unicode=True, sort_keys=False))


def cmd_add(a):
    d = load()
    if any(x["id"] == a.id for x in d["standards"]):
        print(f"⚠️ '{a.id}' уже есть"); return 1
    ref = ""
    if a.image:
        (BASE / "refs").mkdir(parents=True, exist_ok=True)
        dst = BASE / "refs" / f"{a.id}{Path(a.image).suffix}"
        shutil.copy(a.image, dst); ref = f"refs/{dst.name}"
    d["standards"].append({
        "id": a.id, "name": a.name, "type": a.type, "ref_image": ref,
        "source": a.source or "", "description": a.desc or "",
        "when_to_apply": [w.strip() for w in (a.when or "").split(";") if w.strip()],
        "gen_prompt": a.gen or "", "notes": a.notes or "",
    })
    save(d); print(f"✅ добавлен стандарт '{a.id}' (всего {len(d['standards'])})")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")
    pl = sub.add_parser("list"); pl.add_argument("--type")
    pg = sub.add_parser("get"); pg.add_argument("id")
    pa = sub.add_parser("add")
    for f in ["id", "name", "type", "image", "when", "gen", "source", "desc", "notes"]:
        pa.add_argument(f"--{f}")
    a = p.parse_args()
    return {"list": cmd_list, "get": cmd_get, "add": cmd_add}.get(a.cmd, lambda _: (print(__doc__), 1)[1])(a) or 0


if __name__ == "__main__":
    sys.exit(main())
