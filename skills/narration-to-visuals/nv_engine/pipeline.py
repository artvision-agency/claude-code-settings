"""SCRIPT-GEN orchestration: inputs -> blocks -> markers -> draft artifact.

Idempotent: if narration_script.md already exists and force is False, skip
(the author may have edited it on review gate #1 — never clobber).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from nv_engine.config import resolve_paths
from nv_engine.inputs import load_inputs
from nv_engine.script_doc import render_script_md, validate_script_md
from nv_engine.scriptgen import assign_markers, build_blocks


@dataclass(frozen=True)
class ScriptGenResult:
    created: bool
    script_path: Path
    brief_path: Path
    block_count: int


def run_script_gen(
    *, lecture: str, project_root: Path, preset: str = "ai-course", force: bool = False
) -> ScriptGenResult:
    paths = resolve_paths(lecture=lecture, project_root=project_root, preset=preset)
    paths.work_dir.mkdir(parents=True, exist_ok=True)
    brief_path = paths.work_dir / "script_brief.json"

    if paths.narration_script.exists() and not force:
        return ScriptGenResult(
            created=False,
            script_path=paths.narration_script,
            brief_path=brief_path,
            block_count=0,
        )

    raw = load_inputs(
        transcript=paths.transcript,
        summary=paths.summary,
        speaker_notes=paths.speaker_notes,
    )
    blocks = assign_markers(build_blocks(raw))

    brief = {
        "lecture": lecture,
        "duration": raw.duration,
        "has_speaker_notes": raw.speaker_notes_text is not None,
        "blocks": [
            {
                "title": b.title,
                "marker": b.marker,
                "start": b.start,
                "end": b.end,
                "narration": b.narration,
            }
            for b in blocks
        ],
    }
    brief_path.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    md = render_script_md(lecture=lecture, blocks=blocks)
    validate_script_md(md)  # самопроверка перед записью
    paths.narration_script.parent.mkdir(parents=True, exist_ok=True)
    paths.narration_script.write_text(md, encoding="utf-8")

    return ScriptGenResult(
        created=True,
        script_path=paths.narration_script,
        brief_path=brief_path,
        block_count=len(blocks),
    )


# --- Plan 2: storyboard stage ----------------------------------------------

from nv_engine.align import Aligner, align_recording  # noqa: E402
from nv_engine.classify import draft_content  # noqa: E402
from nv_engine.reconcile import reconcile_blocks, render_reconcile_md  # noqa: E402
from nv_engine.script_doc import parse_script_md, validate_script_md  # noqa: E402
from nv_engine.segment import map_blocks_to_timeline  # noqa: E402
from nv_engine.storyboard import (  # noqa: E402
    build_storyboard,
    render_storyboard_json,
    render_storyboard_md,
    validate_storyboard_json,
)


@dataclass(frozen=True)
class StoryboardResult:
    created: bool
    storyboard_path: Path
    block_count: int
    deviations: int


def run_storyboard(*, lecture: str, project_root: Path, aligner: Aligner,
                   preset: str = "ai-course", threshold: float = 0.2,
                   force: bool = False) -> StoryboardResult:
    paths = resolve_paths(lecture=lecture, project_root=project_root,
                          preset=preset)
    if not paths.narration_script.exists():
        raise FileNotFoundError(
            f"narration_script.md missing for {lecture!r}: "
            f"{paths.narration_script} — run the script stage and approve it first"
        )
    if not paths.recording.exists():
        raise FileNotFoundError(
            f"narration.mp4 missing for {lecture!r}: {paths.recording} — "
            f"record yourself reading the approved narration_script.md first"
        )
    paths.work_dir.mkdir(parents=True, exist_ok=True)

    if paths.storyboard.exists() and not force:
        return StoryboardResult(created=False,
                                storyboard_path=paths.storyboard,
                                block_count=0, deviations=0)

    md = paths.narration_script.read_text(encoding="utf-8")
    validate_script_md(md)
    parsed = parse_script_md(md)
    script_text = " ".join(b.narration for b in parsed.blocks)

    aligned = align_recording(recording=paths.recording,
                              script_text=script_text, aligner=aligner)
    paths.aligned.write_text(
        json.dumps({"text": aligned.text,
                    "words": [{"word": w.word, "start": w.start,
                               "end": w.end} for w in aligned.words]},
                   ensure_ascii=False, indent=2),
        encoding="utf-8")

    spans = map_blocks_to_timeline(parsed_script=parsed, aligned=aligned)
    recs = reconcile_blocks(spans=spans, threshold=threshold)
    paths.reconcile.write_text(render_reconcile_md(recs), encoding="utf-8")

    contents = [draft_content(title=s.title, marker=s.marker,
                              narration=s.narration) for s in spans]
    sb = build_storyboard(lecture=lecture, spans=spans, recs=recs,
                          contents=contents)
    sb_json = render_storyboard_json(sb)
    validate_storyboard_json(sb_json)
    paths.storyboard.write_text(sb_json, encoding="utf-8")
    paths.storyboard_md.write_text(render_storyboard_md(sb), encoding="utf-8")

    return StoryboardResult(created=True, storyboard_path=paths.storyboard,
                            block_count=len(sb.blocks),
                            deviations=sum(1 for r in recs if r.deviation))
