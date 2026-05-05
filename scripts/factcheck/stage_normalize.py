"""Stage 2: Claim normalization.

Cleans up atomic claims:
    * Strips whitespace, normalises punctuation.
    * Removes near-duplicates (case-insensitive Jaccard on token bags).
    * Drops boilerplate (single-token, navigation phrases, pure numbers).
    * Marks claims as `checkworthy=False` if they look like opinion/CTA
      ("свяжитесь с нами", "наша миссия — …") so verifier skips them.

This is a deterministic, dependency-free pass — no LLM needed. The Loki
CheckWorthy step would normally use the LLM for this, but for our HTML
KP/landing texts a heuristic filter works well enough at zero cost.
"""

from __future__ import annotations

import re
from typing import Iterable

from .types import AtomicClaim


_BOILERPLATE_PATTERNS = [
    re.compile(r"^\s*(свяжитесь|обратитесь|напишите|позвоните)\b", re.IGNORECASE),
    re.compile(r"^\s*(подробнее|читать дальше|узнать больше|оставить заявку)\b", re.IGNORECASE),
    re.compile(r"^\s*(menu|меню|навигация|контакты|footer|header)\s*$", re.IGNORECASE),
    re.compile(r"^\s*наш[аиоеу]?\s+(миссия|видение|команда)\b", re.IGNORECASE),
]


_OPINION_MARKERS = re.compile(
    r"\b(мы\s+считаем|по\s+нашему\s+мнению|на\s+наш\s+взгляд|believe|think|imho)\b",
    re.IGNORECASE,
)


_NUMERIC_TOKEN = re.compile(r"\d")
_BRAND_TOKEN = re.compile(r"[A-ZА-Я][a-zа-я]+|\b[A-Z]{2,}\b")
_URL_TOKEN = re.compile(r"https?://|www\.|\b\w+\.(?:ru|com|pro|net|org|io)\b")


def _tokens(text: str) -> set[str]:
    # Collapse intra-number whitespace ("65 000" → "65000") so that
    # near-dedupe treats the two stylistic forms as equal tokens.
    collapsed = re.sub(r"(?<=\d)[\s ](?=\d)", "", text)
    return {w.lower() for w in re.findall(r"[A-Za-zА-Яа-яЁё0-9]{3,}", collapsed)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = a & b
    union = a | b
    return len(inter) / len(union)


def _classify_type(text: str, current: str) -> str:
    if _URL_TOKEN.search(text):
        return "url"
    if re.search(r"\d{1,2}[./]\d{1,2}[./]\d{2,4}|\b\d{4}\s*(?:год|г\.|year)\b", text, re.IGNORECASE):
        return "date"
    if _NUMERIC_TOKEN.search(text):
        return "numeric"
    if _BRAND_TOKEN.search(text):
        return "brand"
    return current or "fact"


def normalize_claims(
    claims: Iterable[AtomicClaim],
    *,
    dedupe_threshold: float = 0.85,
    min_length: int = 10,
    max_length: int = 400,
) -> list[AtomicClaim]:
    """Apply Stage 2 to the output of stage_atomic.

    The function is pure (no I/O) so it is trivial to test.
    """
    cleaned: list[AtomicClaim] = []
    seen_tokens: list[set[str]] = []

    for c in claims:
        text = re.sub(r"\s+", " ", (c.text or "")).strip().strip("•-—–·*")
        if not text:
            continue

        # length guards
        if len(text) < min_length or len(text) > max_length:
            continue

        # boilerplate
        if any(p.search(text) for p in _BOILERPLATE_PATTERNS):
            continue

        # mostly punctuation / numbers only?
        word_chars = sum(1 for ch in text if ch.isalpha())
        if word_chars < 5:
            continue

        # near-duplicate
        toks = _tokens(text)
        if any(_jaccard(toks, prev) >= dedupe_threshold for prev in seen_tokens):
            continue

        seen_tokens.append(toks)

        new_claim = AtomicClaim(
            text=text,
            source_span=c.source_span,
            subject=re.sub(r"\s+", " ", c.subject).strip(),
            predicate=re.sub(r"\s+", " ", c.predicate).strip(),
            object_value=re.sub(r"\s+", " ", c.object_value).strip(),
            claim_type=_classify_type(text, c.claim_type),
            checkworthy=not bool(_OPINION_MARKERS.search(text)),
            metadata=dict(c.metadata),
        )
        cleaned.append(new_claim)

    return cleaned
