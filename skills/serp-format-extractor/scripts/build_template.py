#!/usr/bin/env python3
"""
build_template.py — STUB.

Goal: Aggregate 3 parse_dom.py outputs into a single JSON template (recommended structure).

TODO:
1. Read 3 per-URL JSON files (output from parse_dom.py)
2. Compute median (not mean — resistant to outliers):
   - total_target_words = median(total_word_count)
   - intro_length_words = median(intro_word_count)
   - section.word_count_target = median per matched H2 topic
3. Section matching across 3 articles:
   - Lemma-based fuzzy match (use pymorphy3 if available, else lowercase + Levenshtein)
   - "Что такое имплантация" ≈ "Что это" ≈ "Определение" → cluster into single recommended H2
4. Schema recommendations: union of all top-3, plus YMYL defaults (Article + FAQPage for info)
5. FAQ recommendation: present if 2+/3 top-3 have FAQ block
6. Confidence flag:
   - "high" if 3 valid competitors (no Wikipedia/Reddit)
   - "medium" if 2 valid
   - "low" if <2 — output warning, require manual verification
7. Output JSON in format described in SKILL.md (recommended_structure + top_3_analysis)

Args (planned):
    --input file1.json file2.json file3.json
    --keyword "..."
    --region spb (optional, passes through to output)
    --out template.json

Median rationale: see memory feedback_no_single_snapshot_conclusions.md +
SKILL.md "Числа в JSON — median (устойчивее к outlier'ам), не mean".

Exit codes:
    0 = success
    1 = <2 valid inputs (low confidence)
    2 = invalid input JSON
"""

import sys


def main() -> int:
    sys.stderr.write(
        "STUB: build_template.py not yet implemented.\n"
        "For now: run parse_dom.py on each URL manually, then manually synthesize.\n"
        "\n"
        "Example manual workflow:\n"
        "  python3 parse_dom.py --html top1.html --out a1.json\n"
        "  python3 parse_dom.py --html top2.html --out a2.json\n"
        "  python3 parse_dom.py --html top3.html --out a3.json\n"
        "  # then median synthesis manually or via jq\n"
        "\n"
        "TODO list see docstring at top of file.\n"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
