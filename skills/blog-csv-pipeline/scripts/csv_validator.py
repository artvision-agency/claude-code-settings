#!/usr/bin/env python3
"""
CSV validator for blog-csv-pipeline.

Usage:
    python3 csv_validator.py <path-to-csv>

Exit codes:
    0 — valid
    1 — invalid (errors printed to stderr)
    2 — file not found / IO error
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

REQUIRED_COLUMNS = ["keyword"]
OPTIONAL_COLUMNS = ["priority", "target_url_slug", "word_count"]
ALL_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS

CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9\-]*[a-z0-9]$")


def validate(csv_path: Path) -> tuple[bool, list[str], list[dict]]:
    """Return (ok, errors, rows). Rows are normalized dicts."""
    errors: list[str] = []
    rows: list[dict] = []

    if not csv_path.exists():
        return False, [f"CSV file not found: {csv_path}"], []

    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []

            # Header check
            missing = [c for c in REQUIRED_COLUMNS if c not in headers]
            if missing:
                errors.append(f"Missing required columns: {missing}")
                return False, errors, []

            unknown = [c for c in headers if c not in ALL_COLUMNS]
            if unknown:
                errors.append(
                    f"Unknown columns (will be ignored): {unknown}. "
                    f"Allowed: {ALL_COLUMNS}"
                )

            seen_keywords: set[str] = set()

            for idx, raw in enumerate(reader, start=2):  # line 1 = header
                kw = (raw.get("keyword") or "").strip()
                if not kw:
                    errors.append(f"Line {idx}: empty keyword")
                    continue

                kw_lower = kw.lower()
                if kw_lower in seen_keywords:
                    errors.append(f"Line {idx}: duplicate keyword '{kw}'")
                    continue
                seen_keywords.add(kw_lower)

                # Priority
                priority_raw = (raw.get("priority") or "").strip()
                priority = 3
                if priority_raw:
                    try:
                        priority = int(priority_raw)
                        if not 1 <= priority <= 5:
                            errors.append(
                                f"Line {idx}: priority={priority} not in 1..5"
                            )
                    except ValueError:
                        errors.append(
                            f"Line {idx}: priority '{priority_raw}' is not an integer"
                        )

                # Slug
                slug = (raw.get("target_url_slug") or "").strip()
                if slug:
                    if CYRILLIC_RE.search(slug):
                        errors.append(
                            f"Line {idx}: target_url_slug '{slug}' contains "
                            f"Cyrillic — use transliteration"
                        )
                    elif not SLUG_RE.match(slug):
                        errors.append(
                            f"Line {idx}: target_url_slug '{slug}' must be "
                            f"lowercase a-z, 0-9, hyphens; cannot start/end with hyphen"
                        )

                # Word count
                wc_raw = (raw.get("word_count") or "").strip()
                word_count = 1500
                if wc_raw:
                    try:
                        word_count = int(wc_raw)
                        if word_count < 300:
                            errors.append(
                                f"Line {idx}: word_count={word_count} too small (<300)"
                            )
                        elif word_count > 10000:
                            errors.append(
                                f"Line {idx}: word_count={word_count} too large (>10000)"
                            )
                    except ValueError:
                        errors.append(
                            f"Line {idx}: word_count '{wc_raw}' is not an integer"
                        )

                rows.append(
                    {
                        "line": idx,
                        "keyword": kw,
                        "priority": priority,
                        "target_url_slug": slug,
                        "word_count": word_count,
                    }
                )

    except (OSError, UnicodeDecodeError) as e:
        return False, [f"Failed to read CSV: {e}"], []

    # Filter out non-fatal warnings (unknown columns) from blocking errors
    fatal = [e for e in errors if not e.startswith("Unknown columns")]
    ok = not fatal
    return ok, errors, rows


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: csv_validator.py <path-to-csv>", file=sys.stderr)
        return 2

    csv_path = Path(sys.argv[1]).expanduser().resolve()
    ok, errors, rows = validate(csv_path)

    if errors:
        for e in errors:
            print(f"  - {e}", file=sys.stderr)

    print(f"\nCSV: {csv_path}")
    print(f"Rows parsed: {len(rows)}")
    print(f"Status: {'OK' if ok else 'INVALID'}")

    if ok and rows:
        print(f"\nFirst 3 rows (normalized):")
        for r in rows[:3]:
            print(
                f"  • [{r['priority']}] {r['keyword']} → "
                f"{r['target_url_slug'] or '(auto-slug)'} "
                f"({r['word_count']} слов)"
            )

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
