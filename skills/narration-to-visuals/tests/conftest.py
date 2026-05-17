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
