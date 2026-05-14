"""Phase-2 acceptance tests for the Loki factcheck pipeline.

Scope (per artvision-data/TODO.md "Factcheck-OSS Phase 2"):
    Run the 5-stage Loki pipeline against three real KP files
    delivered to clients in May 2026, and assert:

        1. The parser returns a list of atomic claims (≥1 per real KP).
        2. The decomposition stage actually calls the Groq client
           (we use a FakeGroqClient and count chat() invocations).
        3. The pipeline result has the expected report structure
           (PipelineResult instance, valid verdict, populated counts,
            non-empty rendered markdown).

These tests intentionally use FakeGroqClient (no network) so they run
in CI / pre-commit hooks without the Groq API key. The opt-in live
smoke is in test_pipeline_loki.py::test_real_kp_smoke.

Test KPs:
    * clients/na-sklad/kp/index.html              (SEO КП, май 2026)
    * clients/zakvaski-rus/presale/kp/index.html  (Puratos B2B, май 2026)
    * clients/aleksandra-dental/presale/kp/aleksandra_kp.html
        (substitute for "dentix" — task spec allowed this fallback)
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import pytest

PKG_PARENT = Path(__file__).resolve().parents[2]
if str(PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(PKG_PARENT))

from factcheck import pipeline_loki  # noqa: E402
from factcheck.types import (  # noqa: E402
    AtomicClaim,
    ClaimStatus,
    PipelineResult,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Test data — 3 real KP files
# ---------------------------------------------------------------------------

CLIENTS_ROOT = Path("/Users/antonk/artvision-data/clients")

REAL_KP_FILES: dict[str, Path] = {
    "na-sklad": CLIENTS_ROOT / "na-sklad" / "kp" / "index.html",
    "zakvaski-rus": CLIENTS_ROOT / "zakvaski-rus" / "presale" / "kp" / "index.html",
    # Spec says "dentix or aleksandra-dental" — dentix client slot does not
    # exist in the repo (only dental-experts/dentalexpo). Fallback as instructed.
    "aleksandra-dental": (
        CLIENTS_ROOT
        / "aleksandra-dental"
        / "presale"
        / "kp"
        / "aleksandra_kp.html"
    ),
}


def _existing_kp_pairs() -> list[tuple[str, Path]]:
    """Return only KP files that actually exist on disk (skip missing)."""
    return [(name, path) for name, path in REAL_KP_FILES.items() if path.is_file()]


@pytest.fixture(params=_existing_kp_pairs(), ids=lambda p: p[0])
def real_kp(request) -> tuple[str, Path]:
    """Parametrised fixture — one execution per available real KP."""
    name, path = request.param
    if not path.is_file():
        pytest.skip(f"KP file missing on disk: {path}")
    return name, path


# ---------------------------------------------------------------------------
# Counting fake Groq client — lets us prove decomposition actually called it.
# ---------------------------------------------------------------------------


class CountingFakeGroqClient:
    """FakeGroqClient that returns canned claims AND records every call.

    We can't reuse conftest's FakeGroqClient because we want a stable
    payload for *every* chunk (real KPs are large enough to be split into
    multiple chunks, and we need each call to return something parseable).
    """

    CANNED_CLAIMS_JSON = json.dumps(
        {
            "claims": [
                {
                    "text": "Тариф Старт стоит 65 000 ₽/мес.",
                    "subject": "Тариф Старт",
                    "predicate": "стоит",
                    "object": "65 000 ₽/мес",
                    "type": "numeric",
                },
                {
                    "text": "Сайт https://example.com работает с 2018 года.",
                    "subject": "Сайт",
                    "predicate": "работает с",
                    "object": "2018 года",
                    "type": "url",
                },
                {
                    "text": "Команда опубликовала 47 материалов на vc.ru за 12 месяцев.",
                    "subject": "Команда",
                    "predicate": "опубликовала",
                    "object": "47 материалов на vc.ru за 12 месяцев",
                    "type": "fact",
                },
            ]
        },
        ensure_ascii=False,
    )

    def __init__(self) -> None:
        self.available: bool = True
        self.call_count: int = 0
        self.last_messages: list[dict[str, str]] | None = None

    def chat(self, messages: list[dict[str, str]], **kwargs) -> str:
        self.call_count += 1
        self.last_messages = messages
        return self.CANNED_CLAIMS_JSON


@pytest.fixture
def counting_groq() -> CountingFakeGroqClient:
    return CountingFakeGroqClient()


# ---------------------------------------------------------------------------
# (1) Parser returns claims list
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_pipeline_returns_claims_list(real_kp, counting_groq):
    """Pipeline must return a populated list[AtomicClaim] for each real KP."""
    name, path = real_kp

    result = pipeline_loki.run(
        str(path),
        no_http=True,
        groq_client=counting_groq,
    )

    assert isinstance(result, PipelineResult), (
        f"[{name}] expected PipelineResult, got {type(result).__name__}"
    )
    assert isinstance(result.claims, list), (
        f"[{name}] result.claims must be list, got {type(result.claims).__name__}"
    )
    assert len(result.claims) >= 1, (
        f"[{name}] expected ≥1 claim, got 0. Errors: {result.errors[:3]}"
    )
    # Every claim is an AtomicClaim with non-empty text
    for idx, claim in enumerate(result.claims):
        assert isinstance(claim, AtomicClaim), (
            f"[{name}] claim #{idx} is {type(claim).__name__}, expected AtomicClaim"
        )
        assert claim.text and claim.text.strip(), (
            f"[{name}] claim #{idx} has empty text"
        )


# ---------------------------------------------------------------------------
# (2) Decomposition stage actually calls Groq
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_decomposition_invokes_groq(real_kp, counting_groq):
    """Stage 1 (decomposition) must call client.chat() at least once."""
    name, path = real_kp

    pipeline_loki.run(
        str(path),
        no_http=True,
        groq_client=counting_groq,
    )

    assert counting_groq.call_count >= 1, (
        f"[{name}] expected ≥1 Groq chat() call, got {counting_groq.call_count}"
    )
    # Make sure the prompt actually contained KP content
    assert counting_groq.last_messages is not None
    user_msg = next(
        (m for m in counting_groq.last_messages if m.get("role") == "user"),
        None,
    )
    assert user_msg is not None, f"[{name}] no user message sent to LLM"
    assert "claims" in user_msg["content"].lower(), (
        f"[{name}] prompt missing decomposition instructions"
    )


# ---------------------------------------------------------------------------
# (3) Report structure
# ---------------------------------------------------------------------------


_VALID_VERDICTS = {"PASS", "REVIEW", "FAILED"}
_VALID_STATUSES = {s.value for s in ClaimStatus}
_REQUIRED_REPORT_HEADINGS = (
    "Factcheck Report (Loki pipeline)",
    "Pipeline:",
    "Summary",
    "VERDICT",
)


@pytest.mark.integration
def test_report_has_correct_structure(real_kp, counting_groq):
    """PipelineResult must expose verdict + counts + serialisable dict, and
    render_markdown must produce a report with all required sections."""
    name, path = real_kp

    result = pipeline_loki.run(
        str(path),
        no_http=True,
        groq_client=counting_groq,
    )

    # --- PipelineResult shape -------------------------------------------------
    assert result.verdict in _VALID_VERDICTS, (
        f"[{name}] verdict={result.verdict!r} not in {_VALID_VERDICTS}"
    )
    assert result.pipeline == "loki", (
        f"[{name}] pipeline tag should be 'loki', got {result.pipeline!r}"
    )
    assert result.elapsed_sec >= 0, (
        f"[{name}] elapsed_sec={result.elapsed_sec} must be non-negative"
    )

    # counts dict has total + at least one of the status keys
    assert "total" in result.counts, f"[{name}] counts missing 'total' key"
    assert result.counts["total"] == len(result.verifications), (
        f"[{name}] counts.total ({result.counts['total']}) != "
        f"len(verifications) ({len(result.verifications)})"
    )
    for status_key in result.counts:
        if status_key == "total":
            continue
        assert status_key in _VALID_STATUSES, (
            f"[{name}] unknown status key in counts: {status_key!r}"
        )

    # --- to_dict() produces JSON-serialisable structure ----------------------
    payload = result.to_dict()
    assert payload["pipeline"] == "loki"
    assert payload["verdict"] in _VALID_VERDICTS
    assert isinstance(payload["claims"], list)
    assert isinstance(payload["verifications"], list)
    # round-trip through json.dumps to catch non-serialisable values
    json.dumps(payload, ensure_ascii=False)

    # --- Markdown report has all required sections ---------------------------
    md = pipeline_loki.render_markdown(result, str(path))
    for heading in _REQUIRED_REPORT_HEADINGS:
        assert heading in md, (
            f"[{name}] markdown report missing heading {heading!r}\n"
            f"--- first 400 chars ---\n{md[:400]}"
        )


# ---------------------------------------------------------------------------
# Sanity: at least one of the 3 KP files is present in the repo
# (otherwise the parametrised tests are silently skipped)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_at_least_one_real_kp_available():
    """Guard: surface a clear failure if all three KP files vanished."""
    available = _existing_kp_pairs()
    assert available, (
        "None of the expected real KP files exist on disk. "
        "Update REAL_KP_FILES or restore the files. Looked at: "
        f"{[str(p) for p in REAL_KP_FILES.values()]}"
    )
