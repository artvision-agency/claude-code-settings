from nv_engine.config import resolve_paths
from nv_engine.inputs import SummarySection, load_inputs


def test_load_inputs_mini(mini_lecture, tmp_path, monkeypatch):
    # mini_lecture лежит как .../lecture-mini/{transcript,summary,speaker_notes}
    # Соберём ad-hoc LecturePaths напрямую вместо пресета:
    from nv_engine.inputs import RawInputs

    raw = load_inputs(
        transcript=mini_lecture / "transcript.json",
        summary=mini_lecture / "summary.md",
        speaker_notes=mini_lecture / "speaker_notes.md",
    )
    assert isinstance(raw, RawInputs)
    # сегменты транскрипта
    assert len(raw.segments) == 6
    assert raw.segments[0].start == 1.0
    assert "Началось" in raw.segments[0].text
    assert raw.duration == 95.0
    # секции summary (## заголовки)
    titles = [s.title for s in raw.summary_sections]
    assert "О чём лекция" in titles
    assert "Источники тех-долга" in titles
    assert all(isinstance(s, SummarySection) for s in raw.summary_sections)
    # speaker_notes присутствует как сырой текст
    assert raw.speaker_notes_text is not None
    assert "Speaker notes" in raw.speaker_notes_text


def test_load_inputs_without_speaker_notes(nonotes_lecture):
    raw = load_inputs(
        transcript=nonotes_lecture / "transcript.json",
        summary=nonotes_lecture / "summary.md",
        speaker_notes=None,
    )
    assert raw.speaker_notes_text is None
    assert len(raw.segments) == 2
    assert [s.title for s in raw.summary_sections] == ["О чём лекция", "Главная мысль"]
