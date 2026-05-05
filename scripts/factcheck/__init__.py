"""Artvision Factcheck — Loki-style 5-stage pipeline (Phase 2 adoption).

This package adapts the Libr-AI/OpenFactVerification (Loki) architecture
into our factcheck-v2.py workflow as an opt-in alternative pipeline.

Default pipeline remains regex-based extraction in factcheck-v2.py.
This Loki pipeline is invoked only when CLI flag `--pipeline=loki` is set.

Architecture (5 stages):
    1. atomic     — split document into atomic claims via Llama-3.3-70B (Groq)
    2. normalize  — canonical form (dedupe, trim, fix references)
    3. source     — locate verification source for each claim
    4. verify     — HTTP HEAD + content match (reuses factcheck-v2 helpers)
    5. aggregate  — final verdict (PASS / REVIEW / FAILED)

See decisions/2026-05-05-factcheck-oss-adoption.md for rationale.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["pipeline_loki"]
