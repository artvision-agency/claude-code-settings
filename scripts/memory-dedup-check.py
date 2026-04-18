#!/usr/bin/env python3
"""Helper для pre-memory-write.sh: ищет похожие memory-файлы по frontmatter."""
import os
import re
import sys
from difflib import SequenceMatcher

FM = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
THRESHOLD_FM = 0.45        # frontmatter name+description
THRESHOLD_NAME_CORE = 0.65  # basename после удаления префикса (feedback_, reference_, ...)

TYPE_PREFIXES = ("feedback_", "trend_", "project_", "reference_", "user_",
                 "personal_", "client_", "product_", "architecture_",
                 "motivation_", "google_", "tvorim_", "allen_")


def strip_prefix(stem: str) -> str:
    for p in TYPE_PREFIXES:
        if stem.startswith(p):
            return stem[len(p):]
    return stem


def parse_fm(text: str) -> dict[str, str]:
    m = FM.search(text)
    if not m:
        return {}
    out = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip()
    return out


def main() -> None:
    memory_dir = os.environ.get("MEMORY_DIR", "")
    new_content = os.environ.get("NEW_CONTENT", "")
    new_basename = os.environ.get("BASENAME", "")

    if not (memory_dir and new_content and new_basename):
        return

    new_fm = parse_fm(new_content)
    new_key = (new_fm.get("name", "") + " " + new_fm.get("description", "")).strip()
    if not new_key:
        new_key = new_content[:200]

    similar = []
    try:
        entries = os.listdir(memory_dir)
    except FileNotFoundError:
        return

    new_stem = new_basename.rsplit(".", 1)[0]
    new_core = strip_prefix(new_stem)

    for f in entries:
        if not f.endswith(".md") or f in ("MEMORY.md", "README.md") or f == new_basename:
            continue
        try:
            with open(os.path.join(memory_dir, f), encoding="utf-8") as fh:
                t = fh.read()
        except Exception:
            continue
        fm = parse_fm(t)
        old_key = (fm.get("name", "") + " " + fm.get("description", "")).strip()

        old_stem = f.rsplit(".", 1)[0]
        old_core = strip_prefix(old_stem)
        name_sim = SequenceMatcher(None, new_core.lower(), old_core.lower()).ratio()
        fm_sim = SequenceMatcher(None, new_key.lower(), old_key.lower()).ratio() if old_key else 0.0

        score = max(name_sim, fm_sim)
        if name_sim >= THRESHOLD_NAME_CORE or fm_sim >= THRESHOLD_FM:
            similar.append((score, f, fm.get("description", "")[:80], name_sim, fm_sim))

    similar.sort(reverse=True)
    if similar:
        print(f"⚠️  pre-memory-write: создаётся {new_basename} — похожие:", file=sys.stderr)
        for score, f, desc, ns, fs in similar[:3]:
            print(f"    [name:{ns:.2f} fm:{fs:.2f}] {f} — {desc}", file=sys.stderr)
        print("   → рассмотреть Edit существующего вместо Write нового", file=sys.stderr)


if __name__ == "__main__":
    main()
