"""CLI: `python -m nv_engine <lecture> [--project-root P] [--preset NAME] [--force]`.

Runs SCRIPT-GEN only (Plan 1). Prints the REVIEW GATE 1 instruction so the
SKILL.md workflow halts for author review.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from nv_engine.pipeline import run_script_gen


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="narration-to-visuals")
    parser.add_argument("lecture")
    parser.add_argument("--project-root", default=".", type=Path)
    parser.add_argument("--preset", default="ai-course")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    try:
        res = run_script_gen(
            lecture=args.lecture,
            project_root=args.project_root,
            preset=args.preset,
            force=args.force,
        )
    except (FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2

    if not res.created:
        print(
            f"narration_script.md already exists: {res.script_path}\n"
            f"Use --force to regenerate (will overwrite author edits)."
        )
        return 0

    print(
        f"SCRIPT-GEN done: {res.block_count} blocks\n"
        f"Draft written: {res.script_path}\n"
        f"Brief: {res.brief_path}\n"
        f"\n=== REVIEW GATE 1 ===\n"
        f"STOP. Author must read and edit narration_script.md "
        f"(text + [B/C/D:] markers) before recording. Do not proceed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
