from pathlib import Path

from nv_engine.align import AlignedTranscript, AlignedWord, FakeAligner, align_recording


def test_fake_aligner_perfect_read_uses_script_text():
    aligner = FakeAligner()  # recognized = script
    at = aligner.align(Path("x.mp4"), "привет мир тест")
    assert isinstance(at, AlignedTranscript)
    assert [w.word for w in at.words] == ["привет", "мир", "тест"]
    assert at.words[0].start == 0.0
    assert at.words[0].end == 0.5
    assert at.words[1].start == 0.5
    assert at.text == "привет мир тест"
    assert all(at.words[i].end <= at.words[i + 1].start
               for i in range(len(at.words) - 1))


def test_fake_aligner_can_override_recognized_text():
    aligner = FakeAligner(recognized_text="совсем другое")
    at = aligner.align(Path("x.mp4"), "ожидаемый скрипт")
    assert [w.word for w in at.words] == ["совсем", "другое"]


def test_align_recording_delegates_to_aligner():
    at = align_recording(recording=Path("a.mp4"), script_text="один два",
                          aligner=FakeAligner())
    assert isinstance(at, AlignedTranscript)
    assert len(at.words) == 2
