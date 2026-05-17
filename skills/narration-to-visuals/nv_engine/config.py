"""Preset-driven path resolution for the script-gen stage.

Preset 'ai-course' encodes the layout:
  <project>/source/<lecture>/transcript.json   (input, canonical ASR)
  <project>/source/<lecture>/narration_script.md (artifact, review #1)
  <project>/course/<lecture>/summary.md        (input)
  <project>/course/<lecture>/speaker_notes.md  (optional input)
  <project>/.nv-work/<lecture>/                (intermediate, gitignored)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PRESETS = {
    "ai-course": {
        "transcript": "source/{lecture}/transcript.json",
        "summary": "course/{lecture}/summary.md",
        "speaker_notes": "course/{lecture}/speaker_notes.md",
        "narration_script": "source/{lecture}/narration_script.md",
        "work_dir": ".nv-work/{lecture}",
        "recording": "source/{lecture}/narration.mp4",
        "aligned": ".nv-work/{lecture}/aligned.json",
        "reconcile": ".nv-work/{lecture}/reconcile.md",
        "storyboard": ".nv-work/{lecture}/storyboard.json",
        "storyboard_md": ".nv-work/{lecture}/storyboard.md",
    }
}


@dataclass(frozen=True)
class LecturePaths:
    lecture: str
    transcript: Path
    summary: Path
    speaker_notes: Path | None
    narration_script: Path
    work_dir: Path
    recording: Path
    aligned: Path
    reconcile: Path
    storyboard: Path
    storyboard_md: Path


def resolve_paths(*, lecture: str, project_root: Path | str, preset: str = "ai-course") -> LecturePaths:
    if preset not in PRESETS:
        raise ValueError(f"unknown preset: {preset!r} (known: {sorted(PRESETS)})")
    tpl = PRESETS[preset]
    root = Path(project_root)

    def p(key: str) -> Path:
        return root / tpl[key].format(lecture=lecture)

    transcript = p("transcript")
    if not transcript.exists():
        raise FileNotFoundError(f"transcript not found for lecture {lecture!r}: {transcript}")

    sn = p("speaker_notes")
    return LecturePaths(
        lecture=lecture,
        transcript=transcript,
        summary=p("summary"),
        speaker_notes=sn if sn.exists() else None,
        narration_script=p("narration_script"),
        work_dir=p("work_dir"),
        recording=p("recording"),
        aligned=p("aligned"),
        reconcile=p("reconcile"),
        storyboard=p("storyboard"),
        storyboard_md=p("storyboard_md"),
    )
