from nv_engine.classify import BlockContent, draft_content


def test_marker_B_makes_image_prompt():
    c = draft_content(title="Метафора кредита", marker="B",
                       narration="Тех-долг это как кредит. Платишь потом.")
    assert isinstance(c, BlockContent)
    assert c.marker == "B"
    assert c.image_prompt and "Метафора кредита" in c.image_prompt
    assert c.slide_lines is None and c.diagram_spec is None


def test_marker_C_makes_slide_lines():
    c = draft_content(title="Определение", marker="C",
                      narration="Тех-долг это компромисс. Не плохой код. Это кредит.")
    assert c.marker == "C"
    assert c.slide_lines and len(c.slide_lines) >= 2
    assert all(len(line) <= 120 for line in c.slide_lines)
    assert c.image_prompt is None and c.diagram_spec is None


def test_marker_D_makes_diagram_spec():
    c = draft_content(title="Источники", marker="D",
                      narration="Хардкоды, тесты, CI/CD pipeline.")
    assert c.marker == "D"
    assert c.diagram_spec and "Источники" in c.diagram_spec
    assert c.image_prompt is None and c.slide_lines is None


def test_unknown_marker_defaults_to_C():
    c = draft_content(title="X", marker="Z", narration="Просто текст.")
    assert c.marker == "C"
    assert c.slide_lines
