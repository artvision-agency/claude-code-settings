"""CLI tests — verify backwards-compatibility of factcheck-v2.py argparse.

We import factcheck-v2.py via importlib (it is not a package) and exercise:
    1. parse_args without --pipeline → defaults to 'regex' (existing behaviour)
    2. parse_args with --pipeline=loki → branch resolved
    3. main() with regex on synthetic file still produces a report
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

V2_PATH = Path("/Users/antonk/.claude/scripts/factcheck-v2.py")


def _load_v2():
    spec = importlib.util.spec_from_file_location("factcheck_v2_cli", V2_PATH)
    if spec is None or spec.loader is None:
        pytest.skip("factcheck-v2.py not found")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["factcheck_v2_cli"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.unit
def test_v2_default_pipeline_is_regex(synthetic_kp_path):
    v2 = _load_v2()
    ns = v2.parse_args([str(synthetic_kp_path)])
    assert ns.pipeline == "regex"
    assert ns.mode == "standard"


@pytest.mark.unit
def test_v2_pipeline_loki_recognized(synthetic_kp_path):
    v2 = _load_v2()
    ns = v2.parse_args([str(synthetic_kp_path), "--pipeline", "loki"])
    assert ns.pipeline == "loki"


@pytest.mark.unit
def test_v2_pipeline_invalid_choice_rejected(synthetic_kp_path):
    v2 = _load_v2()
    with pytest.raises(SystemExit):
        v2.parse_args([str(synthetic_kp_path), "--pipeline", "nonsense"])


@pytest.mark.unit
def test_v2_regex_main_still_works(synthetic_kp_path, tmp_path, capsys):
    """Smoke: existing regex pipeline still produces a non-empty report."""
    v2 = _load_v2()
    report_file = tmp_path / "out.md"
    rc = v2.main([str(synthetic_kp_path), "--quick", "--no-http", "--report", str(report_file)])
    # quick mode finds no CRITICAL on synthetic html → exit 0
    assert rc == 0
    assert report_file.is_file()
    body = report_file.read_text(encoding="utf-8")
    assert "Factcheck Report" in body
    assert "VERDICT" in body
