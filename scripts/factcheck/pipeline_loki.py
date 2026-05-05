"""Loki-style 5-stage factcheck pipeline orchestrator.

Public entry-point: ``run(html_file, source_paths=None, no_http=False, ...)``.

The orchestrator is stateless and side-effect free aside from network calls
in Stage 4. Heavy work is delegated to stage_* modules. This makes each
stage independently testable and replaceable (e.g. swapping Llama-3.3 for
Claude or MiniCheck later).

Usage from factcheck-v2.py:

    from factcheck.pipeline_loki import run as run_loki
    result = run_loki(args.html_file, source_paths=args.source, no_http=args.no_http)
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Sequence

from .stage_aggregate import aggregate
from .stage_atomic import extract_atomic_claims
from .stage_normalize import normalize_claims
from .stage_source import resolve_sources
from .stage_verify import verify_claims
from .types import PipelineResult

logger = logging.getLogger(__name__)


def _read_html_text(html_file: str) -> str:
    """Strip HTML to visible text — re-uses bs4 if available, falls back to regex."""
    raw = Path(html_file).read_text(encoding="utf-8", errors="replace")
    try:
        from bs4 import BeautifulSoup, Comment  # type: ignore
        soup = BeautifulSoup(raw, "html.parser")
        for tag in soup.find_all(["script", "style", "noscript"]):
            tag.decompose()
        for c in soup.find_all(string=lambda t: isinstance(t, Comment)):
            c.extract()
        return soup.get_text(separator="\n", strip=True)
    except Exception:
        import re

        text = re.sub(r"<script[^>]*>.*?</script>", " ", raw, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", text).strip()


def _load_source_texts(source_paths: Sequence[str] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    if not source_paths:
        return out
    for sp in source_paths:
        p = Path(sp)
        if p.is_file():
            try:
                out[p.name] = p.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                logger.warning("could not read source %s: %s", sp, exc)
    return out


def _build_domain_map(source_texts: dict[str, str]) -> dict[str, str]:
    """Pull domains/brands from optional config.yaml content."""
    domain_map: dict[str, str] = {}
    for fname, content in source_texts.items():
        if not (fname.endswith(".yaml") or fname.endswith(".yml")):
            continue
        try:
            import yaml  # type: ignore
            cfg = yaml.safe_load(content) or {}
        except Exception:
            continue
        if not isinstance(cfg, dict):
            continue
        for key in ("site", "domain", "url", "website", "brand_url"):
            v = cfg.get(key)
            if isinstance(v, str) and v.strip():
                u = v.strip()
                if not u.startswith("http"):
                    u = "https://" + u.lstrip("/")
                brand = cfg.get("brand") or cfg.get("name") or cfg.get("company") or fname
                domain_map[str(brand).strip()] = u
                break
    return domain_map


def run(
    html_file: str,
    source_paths: Sequence[str] | None = None,
    *,
    no_http: bool = False,
    max_chunks: int | None = None,
    groq_client=None,
) -> PipelineResult:
    """Execute the 5-stage Loki-style pipeline on a single HTML document."""
    started = time.monotonic()

    text = _read_html_text(html_file)

    # Stage 1
    atomic_kwargs = {} if max_chunks is None else {"max_chunks": max_chunks}
    claims, atomic_errors = extract_atomic_claims(text, client=groq_client, **atomic_kwargs)

    # Stage 2
    normalized = normalize_claims(claims)

    # Stage 3
    source_texts = _load_source_texts(source_paths)
    domain_map = _build_domain_map(source_texts)
    pairs = resolve_sources(normalized, domain_map=domain_map, source_texts=source_texts)

    # Stage 4
    verifications = verify_claims(pairs, no_http=no_http)

    # Stage 5
    verdict, counts = aggregate(verifications)

    elapsed = time.monotonic() - started

    return PipelineResult(
        verdict=verdict,
        claims=normalized,
        verifications=verifications,
        counts=counts,
        elapsed_sec=round(elapsed, 3),
        pipeline="loki",
        errors=list(atomic_errors),
    )


def render_markdown(result: PipelineResult, html_file: str) -> str:
    """Pretty-print the pipeline result as a markdown report (factcheck-v2 compatible)."""
    lines: list[str] = []
    lines.append(f"# Factcheck Report (Loki pipeline) -- {Path(html_file).name}")
    lines.append(f"**Pipeline:** loki (Llama-3.3-70B via Groq)")
    lines.append(f"**Elapsed:** {result.elapsed_sec}s")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Total claims: {result.counts.get('total', 0)}")
    lines.append(f"- Supported:   {result.counts.get('supported', 0)}")
    lines.append(f"- Unverified:  {result.counts.get('unverified', 0)}")
    lines.append(f"- Refuted:     {result.counts.get('refuted', 0)}")
    lines.append(f"- Skipped:     {result.counts.get('skipped', 0)}")
    lines.append(f"- Errors:      {result.counts.get('error', 0)}")
    lines.append("")
    if result.errors:
        lines.append("## Pipeline notes")
        for e in result.errors[:10]:
            lines.append(f"- {e}")
        if len(result.errors) > 10:
            lines.append(f"- _... and {len(result.errors) - 10} more_")
        lines.append("")

    lines.append("## Sample claims (first 30)")
    lines.append("")
    lines.append("| # | Status | Type | Claim | Source |")
    lines.append("|---|--------|------|-------|--------|")
    for i, v in enumerate(result.verifications[:30], 1):
        text = v.claim.text.replace("|", "/").replace("\n", " ")[:120]
        src = (v.source.url if v.source else "")[:60]
        lines.append(f"| {i} | {v.status.value} | {v.claim.claim_type} | {text} | {src} |")
    if len(result.verifications) > 30:
        lines.append(f"| ... | _and {len(result.verifications) - 30} more_ | | | |")
    lines.append("")

    lines.append("---")
    if result.verdict == "FAILED":
        lines.append(f"**VERDICT: FAILED** -- refuted/error claims detected. DO NOT DEPLOY.")
    elif result.verdict == "REVIEW":
        lines.append(f"**VERDICT: REVIEW** -- some claims unverified. Manual check recommended.")
    else:
        lines.append(f"**VERDICT: PASSED** -- no refutations found.")
    lines.append("")
    return "\n".join(lines)
