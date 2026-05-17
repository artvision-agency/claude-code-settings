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
