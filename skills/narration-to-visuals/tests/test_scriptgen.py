from nv_engine.inputs import load_inputs
from nv_engine.scriptgen import build_blocks


def _mini(mini_lecture):
    return load_inputs(
        transcript=mini_lecture / "transcript.json",
        summary=mini_lecture / "summary.md",
        speaker_notes=mini_lecture / "speaker_notes.md",
    )


def test_blocks_follow_summary_h2_sections(mini_lecture):
    blocks = build_blocks(_mini(mini_lecture))
    titles = [b.title for b in blocks]
    # H2-секции summary становятся блоками (## уровня 2)
    assert "О чём лекция" in titles
    assert "Новое определение" in titles
    assert "Источники тех-долга" in titles
    assert "Как продать рефакторинг бизнесу" in titles


def test_offtopic_segments_excluded_from_block_text(mini_lecture):
    blocks = build_blocks(_mini(mini_lecture))
    joined = " ".join(b.narration for b in blocks)
    assert "пишет в чат" not in joined
    assert "Эээ" not in joined


def test_each_block_has_time_anchor(mini_lecture):
    blocks = build_blocks(_mini(mini_lecture))
    timed = [b for b in blocks if b.start is not None]
    assert timed, "хотя бы один блок должен получить тайм-якорь из транскрипта"
    for b in timed:
        assert b.start is not None and b.end is not None
        assert b.end >= b.start


def test_definition_segment_maps_to_definition_block(mini_lecture):
    blocks = build_blocks(_mini(mini_lecture))
    by_title = {b.title: b for b in blocks}
    assert "компромисс" in by_title["Новое определение"].narration.lower()
