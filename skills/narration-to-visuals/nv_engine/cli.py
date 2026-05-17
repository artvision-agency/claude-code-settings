"""CLI: `python -m nv_engine <lecture> [--project-root P] [--preset NAME] [--force]`.

Stage 'script' (Plan 1) or 'storyboard' (Plan 2). Prints the REVIEW GATE 1 instruction so the
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
    parser.add_argument("--stage", choices=["script", "storyboard", "render"],
                         default="script")
    args = parser.parse_args(argv)

    if args.stage == "script":
        try:
            res = run_script_gen(
                lecture=args.lecture, project_root=args.project_root,
                preset=args.preset, force=args.force,
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

    # stage == "storyboard"
    if args.stage == "storyboard":
        import os
        from nv_engine.pipeline import run_storyboard

        if os.environ.get("NV_FAKE_ALIGNER") == "1":
            from nv_engine.align import FakeAligner
            aligner = FakeAligner()
        else:
            from nv_engine.align_stable import make_stable_aligner
            try:
                aligner = make_stable_aligner(model="small")
            except RuntimeError as e:
                print(str(e), file=sys.stderr)
                return 2
        try:
            res = run_storyboard(
                lecture=args.lecture, project_root=args.project_root,
                preset=args.preset, aligner=aligner, force=args.force,
            )
        except (FileNotFoundError, ValueError) as e:
            print(str(e), file=sys.stderr)
            return 2
        if not res.created:
            print(f"storyboard.json already exists: {res.storyboard_path}\n"
                  f"Use --force to regenerate (will overwrite author edits).")
            return 0
        print(
            f"STORYBOARD done: {res.block_count} blocks, "
            f"{res.deviations} deviation(s)\n"
            f"Written: {res.storyboard_path}\n"
            f"\n=== REVIEW GATE 2 ===\n"
            f"STOP. Author must review/edit the storyboard "
            f"(markers, content, deviations) before asset generation. "
            f"GENERATE/RENDER is Plan 3 — do not proceed."
        )
        return 0

    # stage == "render"
    import os
    from nv_engine.pipeline import run_render

    if os.environ.get("NV_FAKE_ASSETS") == "1":
        from nv_engine.assets import FakeImageGenerator
        image_generator = FakeImageGenerator()
    else:
        from nv_engine.assets_fal import make_fal_generator
        try:
            image_generator = make_fal_generator()
        except RuntimeError as e:
            print(str(e), file=sys.stderr)
            return 2
    if os.environ.get("NV_FAKE_RENDER") == "1":
        from nv_engine.render import FakeRunner
        runner = FakeRunner()
    else:
        from nv_engine.render import SubprocessRunner
        runner = SubprocessRunner()

    try:
        res = run_render(
            lecture=args.lecture, project_root=args.project_root,
            preset=args.preset, image_generator=image_generator,
            runner=runner, force=args.force,
        )
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(str(e), file=sys.stderr)
        return 2
    if not res.created:
        print(f"visualized.mp4 already exists: {res.video_path}\n"
              f"Use --force to re-render.")
        return 0
    print(
        f"RENDER done: {res.video_path}\n"
        f"Images: generated {res.generated_images}, cached "
        f"{res.cached_images}, cost ${res.cost_usd:.3f}\n"
        f"Report: {res.report_path}\n"
        f"Pipeline complete — no further gate."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
