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


from nv_engine.scriptgen import assign_markers


def test_markers_assigned_to_every_block(mini_lecture):
    blocks = assign_markers(build_blocks(_mini(mini_lecture)))
    assert all(b.marker in {"B", "C", "D"} for b in blocks)


def test_definition_block_is_C(mini_lecture):
    blocks = {b.title: b for b in assign_markers(build_blocks(_mini(mini_lecture)))}
    # "Новое определение" с маркером 🎯 -> слайд C
    assert blocks["Новое определение"].marker == "C"


def test_technical_pipeline_block_is_D(mini_lecture):
    blocks = {b.title: b for b in assign_markers(build_blocks(_mini(mini_lecture)))}
    # "Источники тех-долга" содержит CI/CD pipeline / архитектуру -> схема D
    assert blocks["Источники тех-долга"].marker == "D"


def test_default_marker_is_C_when_no_signal():
    from nv_engine.scriptgen import Block
    b = Block(title="Вступление", summary_body="Просто рассказ без сигналов.")
    b.narration = "Сегодня обзорная вводная часть."
    assert assign_markers([b])[0].marker == "C"


def test_block_without_segments_falls_back_to_summary():
    from nv_engine.inputs import RawInputs, Segment, SummarySection

    raw = RawInputs(
        duration=20.0,
        segments=[Segment(0.0, 10.0, "Кубернетес и докер деплой пайплайн.")],
        summary_sections=[
            SummarySection(title="Технический раздел", level=2,
                           body="- kubernetes\n- docker deploy pipeline"),
            SummarySection(title="Мотивация", level=2,
                           body="> Зачем это всё нужно команде."),
        ],
        speaker_notes_text=None,
    )
    by = {b.title: b for b in build_blocks(raw)}
    assert by["Мотивация"].narration
    assert "нужно" in by["Мотивация"].narration.lower()
    assert ">" not in by["Мотивация"].narration
    assert by["Мотивация"].start is None
