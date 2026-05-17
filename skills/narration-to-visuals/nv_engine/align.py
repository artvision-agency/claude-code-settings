"""Alignment model + a deterministic FakeAligner for tests.

The real engine (stable-ts) lives in align_stable.py behind the same
Aligner protocol so this module has zero heavy dependencies and is fully
unit-testable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

_WORD = re.compile(r"\S+")


@dataclass(frozen=True)
class AlignedWord:
    word: str
    start: float
    end: float


@dataclass(frozen=True)
class AlignedTranscript:
    words: list[AlignedWord]
    text: str


@runtime_checkable
class Aligner(Protocol):
    def align(self, audio_path: Path, script_text: str) -> AlignedTranscript:
        ...


class FakeAligner:
    """Deterministic aligner for tests. Each word gets 1/wps seconds,
    laid back-to-back from 0. If recognized_text is None the recording is
    assumed a perfect read of the script."""

    def __init__(self, recognized_text: str | None = None, wps: float = 2.0):
        self._recognized = recognized_text
        self._step = 1.0 / wps

    def align(self, audio_path: Path, script_text: str) -> AlignedTranscript:
        text = self._recognized if self._recognized is not None else script_text
        tokens = _WORD.findall(text)
        words: list[AlignedWord] = []
        t = 0.0
        for tok in tokens:
            words.append(AlignedWord(word=tok, start=round(t, 3),
                                     end=round(t + self._step, 3)))
            t += self._step
        return AlignedTranscript(words=words, text=" ".join(tokens))


def align_recording(*, recording: Path, script_text: str,
                     aligner: Aligner) -> AlignedTranscript:
    return aligner.align(recording, script_text)
