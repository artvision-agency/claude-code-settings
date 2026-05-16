from nv_engine.cleaning import clean_segment_text, is_offtopic_segment
from nv_engine.inputs import Segment


def test_removes_filler_words():
    assert clean_segment_text("Эээ, ну, как бы, понимаете, тех-долг это компромисс.") == \
        "Тех-долг это компромисс."


def test_collapses_repeated_spaces_and_trims():
    assert clean_segment_text("  Логи   это   основа.  ") == "Логи это основа."


def test_offtopic_segment_detected():
    # реплики про чат/организацию — оффтопик
    assert is_offtopic_segment(Segment(9.0, 12.0, "Сейчас, секунду, кто-то пишет в чат."))
    assert is_offtopic_segment(Segment(0.0, 3.0, "Подождите, люди ещё подключаются."))


def test_substantive_segment_not_offtopic():
    assert not is_offtopic_segment(
        Segment(12.0, 28.0, "Технический долг это осознанный компромисс.")
    )


def test_empty_after_cleaning_returns_empty():
    assert clean_segment_text("Эээ, ну, как бы.") == ""
