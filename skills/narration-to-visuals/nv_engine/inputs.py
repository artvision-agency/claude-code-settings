"""Load and structurally parse the three inputs of the script-gen stage."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Segment:
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class SummarySection:
    title: str          # текст заголовка ## / ###
    level: int           # 2 для ##, 3 для ###
    body: str            # markdown-тело секции (до следующего заголовка)


@dataclass(frozen=True)
class RawInputs:
    duration: float
    segments: list[Segment]
    summary_sections: list[SummarySection]
    speaker_notes_text: str | None


_HEADING = re.compile(r"^(#{2,3})\s+(.*\S)\s*$", re.MULTILINE)


def _parse_transcript(path: Path) -> tuple[float, list[Segment]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    segs = [
        Segment(start=float(s["start"]), end=float(s["end"]), text=str(s["text"]).strip())
        for s in data.get("segments", [])
    ]
    return float(data.get("duration", 0.0)), segs


def _parse_summary(path: Path) -> list[SummarySection]:
    text = path.read_text(encoding="utf-8")
    matches = list(_HEADING.finditer(text))
    sections: list[SummarySection] = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append(
            SummarySection(
                title=m.group(2).strip(),
                level=len(m.group(1)),
                body=text[start:end].strip(),
            )
        )
    return sections


def load_inputs(*, transcript: Path, summary: Path, speaker_notes: Path | None) -> RawInputs:
    duration, segments = _parse_transcript(transcript)
    summary_sections = _parse_summary(summary) if summary.exists() else []
    sn_text = (
        speaker_notes.read_text(encoding="utf-8")
        if speaker_notes is not None and speaker_notes.exists()
        else None
    )
    return RawInputs(
        duration=duration,
        segments=segments,
        summary_sections=summary_sections,
        speaker_notes_text=sn_text,
    )
