"""Per-stage unit tests — fast, deterministic, no network."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PKG_PARENT = Path(__file__).resolve().parents[2]
if str(PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(PKG_PARENT))

from factcheck.stage_aggregate import aggregate
from factcheck.stage_atomic import (
    _fallback_sentence_split,
    _parse_llm_response,
    chunk_text,
    extract_atomic_claims,
)
from factcheck.stage_normalize import normalize_claims
from factcheck.stage_source import _extract_first_url, resolve_source, resolve_sources
from factcheck.stage_verify import verify_claims
from factcheck.types import (
    AtomicClaim,
    ClaimSource,
    ClaimStatus,
    ClaimVerification,
)


# ---------------------------------------------------------------------------
# stage_atomic
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_chunk_text_short_returns_single_chunk():
    text = "Hello world."
    chunks = chunk_text(text)
    assert chunks == ["Hello world."]


@pytest.mark.unit
def test_chunk_text_splits_long_text_with_overlap():
    text = ("Sentence one. " * 200).strip()
    chunks = chunk_text(text, limit=500, overlap=50)
    assert len(chunks) > 1
    # No chunk wildly exceeds the limit (some slack for boundary search)
    assert all(len(c) <= 700 for c in chunks)


@pytest.mark.unit
def test_chunk_text_empty():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


@pytest.mark.unit
def test_parse_llm_response_clean_json():
    raw = '{"claims": [{"text": "Foo", "subject": "F", "type": "fact"}]}'
    out = _parse_llm_response(raw)
    assert len(out) == 1
    assert out[0]["text"] == "Foo"


@pytest.mark.unit
def test_parse_llm_response_strips_markdown_fence():
    raw = '```json\n{"claims": [{"text": "X"}]}\n```'
    out = _parse_llm_response(raw)
    assert len(out) == 1


@pytest.mark.unit
def test_parse_llm_response_handles_garbage():
    assert _parse_llm_response("not json at all") == []


@pytest.mark.unit
def test_fallback_sentence_split_picks_real_sentences():
    text = "Это первое предложение. Это второе предложение длиннее двадцати символов."
    claims = _fallback_sentence_split(text)
    assert len(claims) >= 1
    assert all(c.text for c in claims)


@pytest.mark.unit
def test_extract_atomic_with_fake_client(fake_groq_client):
    claims, errors = extract_atomic_claims(
        "Стом-Shop магазин. Тариф Старт стоит 65 000 ₽/мес.",
        client=fake_groq_client,
    )
    assert len(claims) >= 1
    assert errors == []


@pytest.mark.unit
def test_extract_atomic_no_client_falls_back():
    class NoKey:
        available = False

        def chat(self, *a, **kw):
            raise AssertionError("must not be called")

    text = "Это предложение длиннее двадцати символов одно. И это тоже второе тоже двадцати."
    claims, errors = extract_atomic_claims(text, client=NoKey())
    assert errors  # should have explanation
    assert len(claims) >= 1


# ---------------------------------------------------------------------------
# stage_normalize
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_normalize_dedupes_near_duplicates():
    raw = [
        AtomicClaim(text="Тариф Старт стоит 65 000 рублей в месяц"),
        AtomicClaim(text="Тариф Старт стоит 65000 рублей в месяц"),
        AtomicClaim(text="Тариф Рост стоит 95 000 рублей в месяц"),
    ]
    out = normalize_claims(raw)
    # Last one is genuinely different — must survive
    assert len(out) == 2


@pytest.mark.unit
def test_normalize_drops_too_short_or_too_long():
    raw = [
        AtomicClaim(text="Foo"),  # too short
        AtomicClaim(text="A" * 600),  # too long
        AtomicClaim(text="Это нормальное утверждение про метрику и долю."),
    ]
    out = normalize_claims(raw)
    assert len(out) == 1


@pytest.mark.unit
def test_normalize_drops_boilerplate():
    raw = [
        AtomicClaim(text="Свяжитесь с нами по телефону для подробностей."),
        AtomicClaim(text="ИП Иванов получил выручку 12 млн ₽ за 2024 год."),
    ]
    out = normalize_claims(raw)
    assert len(out) == 1
    assert "Иванов" in out[0].text


@pytest.mark.unit
def test_normalize_marks_opinion_non_checkworthy():
    raw = [
        AtomicClaim(text="Мы считаем что наш сервис лучший в индустрии сейчас."),
    ]
    out = normalize_claims(raw)
    assert len(out) == 1
    assert out[0].checkworthy is False


@pytest.mark.unit
def test_normalize_classifies_types():
    raw = [
        AtomicClaim(text="Сайт https://example.com работает с 2018 года."),
        AtomicClaim(text="Тариф Старт стоит 65000 рублей в месяц.", claim_type="fact"),
        AtomicClaim(text="ООО «Стом-Shop» зарегистрирован в реестре ИНН."),
    ]
    out = normalize_claims(raw)
    types = {c.claim_type for c in out}
    assert "url" in types
    assert "numeric" in types or "date" in types


# ---------------------------------------------------------------------------
# stage_source
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_extract_url_inline():
    assert _extract_first_url("see https://example.com/page for details") == "https://example.com/page"


@pytest.mark.unit
def test_extract_url_bare_domain():
    assert _extract_first_url("Зайдите на stomshop.pro чтобы узнать больше") == "https://stomshop.pro"


@pytest.mark.unit
def test_extract_url_none():
    assert _extract_first_url("No URLs here at all") is None


@pytest.mark.unit
def test_resolve_source_inline_url():
    claim = AtomicClaim(text="Сайт https://example.com работает с 2018 года.")
    _, src = resolve_source(claim)
    assert src.method == "http_head"
    assert src.url.startswith("https://example.com")


@pytest.mark.unit
def test_resolve_source_brand_map():
    claim = AtomicClaim(text="Стом-Shop предлагает скидки этой осенью.")
    _, src = resolve_source(claim, domain_map={"Стом-Shop": "https://stomshop.pro"})
    assert src.method == "http_head"
    assert src.url == "https://stomshop.pro"


@pytest.mark.unit
def test_resolve_source_crossref():
    claim = AtomicClaim(text="Тариф Старт стоит 65000 рублей за тестовый период.")
    sources = {"config.yaml": "tariff: Старт\nprice: 65000\nname: Тестовый"}
    _, src = resolve_source(claim, source_texts=sources)
    assert src.method == "crossref_doc"
    assert src.url == "config.yaml"


@pytest.mark.unit
def test_resolve_source_none_when_unknown():
    claim = AtomicClaim(text="Какой-то совершенно общий и обтекаемый тезис.")
    _, src = resolve_source(claim)
    assert src.method == "none"


@pytest.mark.unit
def test_resolve_sources_batch():
    claims = [
        AtomicClaim(text="Sample https://example.com link inside text."),
        AtomicClaim(text="Generic claim without anything verifiable here."),
    ]
    pairs = resolve_sources(claims)
    assert len(pairs) == 2


# ---------------------------------------------------------------------------
# stage_verify
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_verify_skips_non_checkworthy():
    claim = AtomicClaim(text="Some opinion text long enough.", checkworthy=False)
    src = ClaimSource(url="", method="none")
    out = verify_claims([(claim, src)], no_http=True)
    assert len(out) == 1
    assert out[0].status == ClaimStatus.SKIPPED


@pytest.mark.unit
def test_verify_crossref_supported():
    claim = AtomicClaim(text="Some checkworthy claim.")
    src = ClaimSource(url="config.yaml", method="crossref_doc", notes="2/3 hits")
    out = verify_claims([(claim, src)], no_http=True)
    assert out[0].status == ClaimStatus.SUPPORTED


@pytest.mark.unit
def test_verify_no_source_unverified():
    claim = AtomicClaim(text="Some claim text.")
    src = ClaimSource(url="", method="none")
    out = verify_claims([(claim, src)], no_http=True)
    assert out[0].status == ClaimStatus.UNVERIFIED


@pytest.mark.unit
def test_verify_url_no_http_returns_unverified():
    claim = AtomicClaim(text="Claim with URL.")
    src = ClaimSource(url="https://example.com", method="http_head")
    out = verify_claims([(claim, src)], no_http=True)
    assert out[0].status == ClaimStatus.UNVERIFIED


# ---------------------------------------------------------------------------
# stage_aggregate
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_aggregate_empty_is_review():
    verdict, counts = aggregate([])
    assert verdict == "REVIEW"
    assert counts["total"] == 0


@pytest.mark.unit
def test_aggregate_refuted_fails():
    c = AtomicClaim(text="x")
    verifications = [
        ClaimVerification(claim=c, status=ClaimStatus.REFUTED),
        ClaimVerification(claim=c, status=ClaimStatus.SUPPORTED),
    ]
    verdict, _ = aggregate(verifications)
    assert verdict == "FAILED"


@pytest.mark.unit
def test_aggregate_unverified_yields_review():
    c = AtomicClaim(text="x")
    verifications = [
        ClaimVerification(claim=c, status=ClaimStatus.SUPPORTED),
        ClaimVerification(claim=c, status=ClaimStatus.UNVERIFIED),
    ]
    verdict, _ = aggregate(verifications)
    assert verdict == "REVIEW"


@pytest.mark.unit
def test_aggregate_majority_supported_passes():
    c = AtomicClaim(text="x")
    verifications = [ClaimVerification(claim=c, status=ClaimStatus.SUPPORTED) for _ in range(5)]
    verdict, _ = aggregate(verifications)
    assert verdict == "PASS"


@pytest.mark.unit
def test_aggregate_high_error_rate_fails():
    c = AtomicClaim(text="x")
    verifications = [
        ClaimVerification(claim=c, status=ClaimStatus.ERROR) for _ in range(4)
    ] + [ClaimVerification(claim=c, status=ClaimStatus.SUPPORTED) for _ in range(2)]
    verdict, _ = aggregate(verifications)
    assert verdict == "FAILED"


@pytest.mark.unit
def test_aggregate_all_skipped_is_review():
    c = AtomicClaim(text="x")
    verifications = [
        ClaimVerification(claim=c, status=ClaimStatus.SKIPPED) for _ in range(3)
    ]
    verdict, _ = aggregate(verifications)
    assert verdict == "REVIEW"
