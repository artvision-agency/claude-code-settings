"""Stage 3: Source resolution.

For each normalized atomic claim, decide *how* it can be verified:

    1. If the claim contains a URL → use that URL (method=http_head).
    2. If the claim mentions a known brand/domain → resolve to the brand's
       canonical URL via the optional `domain_map` argument.
    3. If a `source_documents` set is provided → check whether the claim's
       distinctive tokens appear in any source doc (method=crossref_doc).
    4. Otherwise → method=none (Stage 4 will mark it UNVERIFIED).

This stage is pure (no network, no LLM). The expensive HTTP work happens
in Stage 4 so we can decide *what* to fetch only after deduping.
"""

from __future__ import annotations

import re
from dataclasses import replace
from typing import Mapping, Sequence

from .types import AtomicClaim, ClaimSource


URL_RE = re.compile(r"https?://[^\s)\]\"<>]+", re.IGNORECASE)
BARE_DOMAIN_RE = re.compile(
    r"\b((?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+(?:ru|com|pro|net|org|io|info|me))\b",
    re.IGNORECASE,
)


def _extract_first_url(text: str) -> str | None:
    m = URL_RE.search(text)
    if m:
        return m.group(0).rstrip(".,;")
    m = BARE_DOMAIN_RE.search(text)
    if m:
        return f"https://{m.group(1)}"
    return None


def _distinctive_tokens(text: str) -> list[str]:
    return [
        w
        for w in re.findall(r"[A-ZА-ЯЁ][A-Za-zА-Яа-яЁё0-9-]{3,}|\b\d{2,}[%а-яa-z]*", text)
        if not w.lower() in {"http", "https", "www"}
    ][:6]


def resolve_source(
    claim: AtomicClaim,
    *,
    domain_map: Mapping[str, str] | None = None,
    source_texts: Mapping[str, str] | None = None,
) -> tuple[AtomicClaim, ClaimSource]:
    """Return claim (possibly enriched in metadata) and a ClaimSource.

    `domain_map` example: {"yandex": "https://yandex.ru", "stomshop": "https://stomshop.pro"}
    `source_texts`        : {"config.yaml": "...", "context-log.md": "..."} — already-loaded sources.
    """
    text = claim.text

    # 1. inline URL / bare domain
    url = _extract_first_url(text)
    if url:
        return claim, ClaimSource(url=url, method="http_head", notes="inline url")

    # 2. brand → canonical
    if domain_map:
        lowered = text.lower()
        for brand, brand_url in domain_map.items():
            if brand and brand.lower() in lowered:
                return claim, ClaimSource(url=brand_url, method="http_head", notes=f"brand:{brand}")

    # 3. crossref against source documents
    if source_texts:
        toks = _distinctive_tokens(text)
        if toks:
            for fname, content in source_texts.items():
                low = content.lower()
                hits = sum(1 for t in toks if t.lower() in low)
                if hits >= max(2, len(toks) // 2):
                    new_meta = dict(claim.metadata)
                    new_meta["crossref_hits"] = hits
                    new_meta["crossref_source"] = fname
                    return (
                        replace(claim, metadata=new_meta),
                        ClaimSource(url=fname, method="crossref_doc", notes=f"{hits}/{len(toks)} tokens"),
                    )

    # 4. nothing found
    return claim, ClaimSource(url="", method="none", notes="no source resolved")


def resolve_sources(
    claims: Sequence[AtomicClaim],
    *,
    domain_map: Mapping[str, str] | None = None,
    source_texts: Mapping[str, str] | None = None,
) -> list[tuple[AtomicClaim, ClaimSource]]:
    return [
        resolve_source(c, domain_map=domain_map, source_texts=source_texts)
        for c in claims
    ]
