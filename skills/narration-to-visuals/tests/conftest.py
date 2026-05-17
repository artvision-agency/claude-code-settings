from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def mini_lecture() -> Path:
    return FIXTURES / "lecture-mini"


@pytest.fixture
def nonotes_lecture() -> Path:
    return FIXTURES / "lecture-nonotes"


@pytest.fixture
def mini_script_text(mini_lecture) -> str:
    from nv_engine.script_doc import parse_script_md
    md = (mini_lecture / "narration_script.md").read_text(encoding="utf-8")
    parsed = parse_script_md(md)
    return " ".join(b.narration for b in parsed.blocks)
