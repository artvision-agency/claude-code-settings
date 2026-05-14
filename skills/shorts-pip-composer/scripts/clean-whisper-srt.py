#!/usr/bin/env python3
"""
Clean Whisper SRT — apply Russian SEO/marketing terminology corrections.

Whisper small RU often mishears terms like "Click-True Rate" → should be "Click-Through Rate",
"шамонтаж" → "шиномонтаж", "SEO-вудачу" → "SEO-выдачу" etc.

Dictionary lives in ../templates/whisper-russian-corrections.json (auto-loaded).
"""
import argparse, json, pathlib, sys

DEFAULT_DICT = pathlib.Path(__file__).parent.parent / "templates" / "whisper-russian-corrections.json"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Source SRT/TXT/VTT")
    ap.add_argument("--output", required=True, help="Corrected file output")
    ap.add_argument("--dict", default=str(DEFAULT_DICT), help="Corrections JSON path")
    args = ap.parse_args()

    dict_path = pathlib.Path(args.dict)
    if not dict_path.exists():
        print(f"ERROR: dict not found {dict_path}", file=sys.stderr)
        sys.exit(1)

    corrections = json.loads(dict_path.read_text()).get("corrections", {})

    src = pathlib.Path(args.input).read_text()
    corrected = src
    applied = []
    for wrong, right in corrections.items():
        if wrong != right and wrong in corrected:
            count = corrected.count(wrong)
            corrected = corrected.replace(wrong, right)
            applied.append((wrong, right, count))

    pathlib.Path(args.output).write_text(corrected)
    print(f"✅ Applied {len(applied)} corrections to {args.output}")
    for w, r, c in applied:
        print(f"   {w!r} → {r!r} (×{c})")

if __name__ == "__main__":
    main()
