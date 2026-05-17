"""Real aligner adapter over stable-ts (import name: stable_whisper).

Heavy + needs ffmpeg, so it is isolated here behind a factory with a
guard import. Unit tests use FakeAligner; this is exercised only when
stable_whisper is installed (integration). It satisfies the Aligner
protocol from align.py.
"""

from __future__ import annotations

from pathlib import Path

from nv_engine.align import AlignedTranscript, AlignedWord


class StableTsAligner:
    def __init__(self, model_obj):
        self._model = model_obj

    def align(self, audio_path: Path, script_text: str) -> AlignedTranscript:
        result = self._model.align(str(audio_path), script_text, language="ru")
        words: list[AlignedWord] = []
        for seg in result.segments:
            for w in seg.words:
                words.append(AlignedWord(
                    word=str(w.word).strip(),
                    start=float(w.start),
                    end=float(w.end),
                ))
        return AlignedTranscript(words=words,
                                 text=" ".join(w.word for w in words))


def make_stable_aligner(*, model: str = "small") -> StableTsAligner:
    try:
        import stable_whisper  # noqa: PLC0415
    except ImportError as e:  # pragma: no cover - exercised via monkeypatch
        raise RuntimeError(
            "stable-ts not installed. `pip install stable-ts` "
            "(needs ffmpeg) to run the storyboard stage."
        ) from e
    return StableTsAligner(stable_whisper.load_model(model))
