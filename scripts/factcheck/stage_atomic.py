"""Stage 1: Atomic claim decomposition.

Adapts the Loki Decompose.py pattern (Libr-AI/OpenFactVerification, MIT)
but uses Llama-3.3-70B via Groq instead of GPT-4 to keep cost at $0.

Strategy:
    * If Groq available: chunk the document into ~2000-char windows,
      ask the LLM to emit JSON with {"claims": [{"text", "subject", ...}]}.
    * If Groq unavailable: fall back to a sentence-splitter so the pipeline
      still produces *some* structured output (degraded mode).

Why chunking: Llama-3.3-70B has 128k context but free Groq tier rate-limits
on tokens-per-minute. ~2000 char chunks keep us well below TPM caps and let
the model focus (we observed quality dips on >5000-char prompts in the pilot).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Iterable

from .groq_client import GroqClient, GroqError, GroqUnavailableError
from .types import AtomicClaim

logger = logging.getLogger(__name__)


CHUNK_CHAR_LIMIT = 2000
CHUNK_OVERLAP = 100
MAX_CHUNKS_PER_DOC = 25  # safety cap → ~50K chars worth of input


PROMPT_TEMPLATE = """Твоя задача — разбить русский (или смешанный с английским) документ на атомарные фактические утверждения для последующего фактчека.

Требования к каждому claim:
1. Само-достаточный: НЕ использовать "он", "она", "это", "компания" — везде полные имена/бренды.
2. Краткий: одна мысль, до 25 слов.
3. Содержит явный субъект, предикат и объект (subject + predicate + object).
4. Сохраняет числа, даты, проценты, бренды, URL, имена.
5. Игнорируй чисто декоративный текст (заголовки секций, "и т.д.", навигация).

Ответ — строго валидный JSON одной строкой вида:
{{"claims": [{{"text": "...", "subject": "...", "predicate": "...", "object": "...", "type": "fact|numeric|date|brand|url"}}, ...]}}

Если в фрагменте нет проверяемых фактов — верни {{"claims": []}}.

Фрагмент документа:
\"\"\"
{chunk}
\"\"\"

Output (JSON only, без markdown-обрамления, без комментариев):"""


SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+|\n{2,}")


def chunk_text(text: str, limit: int = CHUNK_CHAR_LIMIT, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks of roughly `limit` characters.

    Tries to break on paragraph or sentence boundaries.
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + limit, n)
        if end < n:
            # try to roll back to nearest sentence/paragraph boundary in last 25%
            window = text[start + int(limit * 0.75) : end]
            for sep in ("\n\n", ". ", "! ", "? ", "\n"):
                idx = window.rfind(sep)
                if idx != -1:
                    end = start + int(limit * 0.75) + idx + len(sep)
                    break
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return chunks[:MAX_CHUNKS_PER_DOC]


def _parse_llm_response(raw: str) -> list[dict]:
    """Parse JSON out of LLM response, tolerant to markdown fences."""
    text = raw.strip()
    # strip ```json ... ``` if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # try to locate the first {...} block
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return []
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return []
    claims = data.get("claims", []) if isinstance(data, dict) else []
    return [c for c in claims if isinstance(c, dict) and c.get("text")]


def _claim_from_dict(d: dict, source_span: str = "") -> AtomicClaim:
    return AtomicClaim(
        text=str(d.get("text", "")).strip(),
        source_span=source_span,
        subject=str(d.get("subject", "")).strip(),
        predicate=str(d.get("predicate", "")).strip(),
        object_value=str(d.get("object", d.get("object_value", ""))).strip(),
        claim_type=str(d.get("type", d.get("claim_type", "fact"))).strip().lower() or "fact",
        checkworthy=True,
    )


def _fallback_sentence_split(text: str) -> list[AtomicClaim]:
    """Degraded mode: each long-enough sentence becomes a claim."""
    claims: list[AtomicClaim] = []
    for sent in SENTENCE_SPLIT_RE.split(text):
        sent = sent.strip()
        if 20 <= len(sent) <= 350:
            claims.append(AtomicClaim(text=sent, source_span=sent, checkworthy=True))
    return claims


def extract_atomic_claims(
    text: str,
    *,
    client: GroqClient | None = None,
    max_chunks: int = MAX_CHUNKS_PER_DOC,
) -> tuple[list[AtomicClaim], list[str]]:
    """Run Stage 1.

    Returns (claims, errors). Errors are non-fatal; on Groq outage we degrade
    to sentence-splitting and add a note to errors.
    """
    errors: list[str] = []
    if not text or not text.strip():
        return [], errors

    if client is None:
        try:
            from .groq_client import get_default_client
            client = get_default_client()
        except Exception as exc:  # pragma: no cover - constructor is trivial
            errors.append(f"Groq client init failed: {exc}")
            client = None

    if client is None or not client.available:
        errors.append(
            "Groq API key not found (set GROQ_API_KEY or tokens.json -> groq.api_key) — "
            "falling back to sentence-split. Claims will be coarser; verification may underperform."
        )
        return _fallback_sentence_split(text), errors

    chunks = chunk_text(text)[:max_chunks]
    all_claims: list[AtomicClaim] = []
    seen: set[str] = set()

    for idx, chunk in enumerate(chunks):
        prompt = PROMPT_TEMPLATE.format(chunk=chunk)
        messages = [
            {"role": "system", "content": "Ты — точный экстрактор фактических утверждений."},
            {"role": "user", "content": prompt},
        ]
        try:
            raw = client.chat(messages, temperature=0.0, max_tokens=2048)
        except GroqUnavailableError as exc:
            errors.append(f"chunk {idx}: Groq unavailable — {exc}")
            break
        except GroqError as exc:
            errors.append(f"chunk {idx}: Groq error — {exc}")
            continue

        parsed = _parse_llm_response(raw)
        if not parsed:
            errors.append(f"chunk {idx}: empty/invalid JSON from LLM (response head: {raw[:120]!r})")
            continue

        for d in parsed:
            claim = _claim_from_dict(d, source_span=chunk[:200])
            key = claim.text.lower()
            if key and key not in seen and len(claim.text) >= 8:
                seen.add(key)
                all_claims.append(claim)

    if not all_claims and not errors:
        errors.append("LLM returned no claims for any chunk — using sentence-split fallback")
        return _fallback_sentence_split(text), errors

    return all_claims, errors
