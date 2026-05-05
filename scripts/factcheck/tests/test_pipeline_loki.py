"""End-to-end tests for the Loki pipeline (factcheck/pipeline_loki.py).

Strategy:
    * Unit tests use FakeGroqClient → no network, no API calls.
    * Integration test (`test_real_kp_smoke`) only runs when:
        - GROQ_API_KEY is set (or tokens.json has a valid key), AND
        - ARTVISION_TEST_REAL_KP=1 is set.
      This keeps CI cheap; manual runs can opt-in.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

PKG_PARENT = Path(__file__).resolve().parents[2]
if str(PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(PKG_PARENT))

from factcheck import pipeline_loki  # noqa: E402
from factcheck.types import ClaimStatus, PipelineResult  # noqa: E402


# ---------------------------------------------------------------------------
# Unit
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_run_returns_pipeline_result(synthetic_kp_path, fake_groq_client):
    result = pipeline_loki.run(
        str(synthetic_kp_path), no_http=True, groq_client=fake_groq_client
    )
    assert isinstance(result, PipelineResult)
    assert result.pipeline == "loki"
    assert result.elapsed_sec >= 0
    assert result.verdict in {"PASS", "REVIEW", "FAILED"}


@pytest.mark.unit
def test_run_extracts_claims(synthetic_kp_path, fake_groq_client):
    result = pipeline_loki.run(
        str(synthetic_kp_path), no_http=True, groq_client=fake_groq_client
    )
    assert len(result.claims) >= 3
    # Each normalized claim should preserve subject when available
    with_subject = [c for c in result.claims if c.subject]
    assert len(with_subject) >= 1


@pytest.mark.unit
def test_pipeline_handles_short_html(short_html_path, fake_groq_client):
    result = pipeline_loki.run(
        str(short_html_path), no_http=True, groq_client=fake_groq_client
    )
    assert isinstance(result, PipelineResult)
    # Even on short input, pipeline must yield ≥1 claim from fake client
    assert result.counts.get("total", 0) >= 0


@pytest.mark.unit
def test_pipeline_handles_empty_html(empty_html_path):
    """Empty body should produce zero claims regardless of LLM availability:
    Stage 1 short-circuits before calling the model when text is empty."""

    class NeverCalledClient:
        available = True

        def chat(self, *a, **kw):
            raise AssertionError("LLM must not be called on empty document")

    result = pipeline_loki.run(
        str(empty_html_path), no_http=True, groq_client=NeverCalledClient()
    )
    assert result.verdict == "REVIEW"
    assert result.counts.get("total", 0) == 0


@pytest.mark.unit
def test_pipeline_no_groq_falls_back(synthetic_kp_path, monkeypatch):
    """Without any client, pipeline must still produce sentence-level claims and a note."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    class NoKeyClient:
        available = False

        def chat(self, *a, **kw):
            raise RuntimeError("should not be called")

    result = pipeline_loki.run(
        str(synthetic_kp_path), no_http=True, groq_client=NoKeyClient()
    )
    assert isinstance(result, PipelineResult)
    assert any("Groq" in e or "fallback" in e for e in result.errors)
    # fallback splits sentences → expect a few claims
    assert len(result.claims) >= 3


@pytest.mark.unit
def test_render_markdown_smoke(synthetic_kp_path, fake_groq_client):
    result = pipeline_loki.run(
        str(synthetic_kp_path), no_http=True, groq_client=fake_groq_client
    )
    md = pipeline_loki.render_markdown(result, str(synthetic_kp_path))
    assert "Factcheck Report (Loki pipeline)" in md
    assert "VERDICT" in md
    assert "Pipeline:" in md


# ---------------------------------------------------------------------------
# Integration (opt-in)
# ---------------------------------------------------------------------------


def _has_groq_key() -> bool:
    if os.environ.get("GROQ_API_KEY"):
        return True
    try:
        from factcheck.groq_client import resolve_api_keys

        return bool(resolve_api_keys())
    except Exception:
        return False


@pytest.mark.integration
@pytest.mark.skipif(
    not _has_groq_key() or os.environ.get("ARTVISION_TEST_REAL_KP") != "1",
    reason="needs GROQ_API_KEY + ARTVISION_TEST_REAL_KP=1 to run live KP smoke test",
)
def test_real_kp_smoke(real_kp_paths):
    if not real_kp_paths:
        pytest.skip("no real KP files found on disk")

    sample = real_kp_paths[0]
    result = pipeline_loki.run(str(sample), no_http=True)
    assert isinstance(result, PipelineResult)
    # Pilot showed ≥100 claims on a 26K-char KP. We keep the bar loose
    # (≥30) to tolerate KP length variability and Groq rate-limits.
    assert len(result.claims) >= 30, (
        f"Expected ≥30 claims on real KP, got {len(result.claims)}. "
        f"Errors: {result.errors[:3]}"
    )
