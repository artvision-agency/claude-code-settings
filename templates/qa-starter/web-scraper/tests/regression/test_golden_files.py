"""Golden-file regression: последний успешный прогон сериализуется в
`regression/golden/<name>.golden.json`. При новых прогонах сравниваем
через `deepdiff` — если сайт перестроил вёрстку и парсер сломался, diff
покажет конкретные поля.

Обновление: `PYTEST_GOLDEN_UPDATE=1 pytest tests/regression`
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from deepdiff import DeepDiff

from tests.unit.test_parsers import parse_product

FIXTURES = Path(__file__).parents[1] / "integration" / "fixtures"


def _load_html_cases() -> list[Path]:
    return sorted(FIXTURES.glob("*.html"))


@pytest.mark.regression
@pytest.mark.parametrize("html_path", _load_html_cases(), ids=lambda p: p.stem)
def test_golden_matches(html_path: Path, golden_dir: Path, golden_update: bool):
    html = html_path.read_text(encoding="utf-8")
    current = parse_product(html)

    golden_path = golden_dir / f"{html_path.stem}.golden.json"

    if golden_update or not golden_path.exists():
        golden_path.write_text(
            json.dumps(current, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        pytest.skip(f"Golden updated: {golden_path.name}")

    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    diff = DeepDiff(golden, current, ignore_order=True)
    assert not diff, f"Regression in {html_path.name}:\n{diff.pretty()}"
