"""Stage 5: Aggregate verifications into a final verdict.

Verdict mapping (mirrors factcheck-v2.py thresholds so callers see the same
PASS / REVIEW / FAILED words):

    * FAILED  → at least one REFUTED claim, OR error rate > 30 %
    * REVIEW  → any UNVERIFIED claim, OR fraction of SUPPORTED < 50 %
    * PASS    → no REFUTED, no ERROR, ≥ 50 % SUPPORTED

This is intentionally conservative: a Loki run with sparse SUPPORTED claims
should NOT auto-greenlight a deploy. Phase 3 will tighten with SelfCheckGPT.
"""

from __future__ import annotations

from collections import Counter
from typing import Sequence

from .types import ClaimStatus, ClaimVerification


def aggregate(verifications: Sequence[ClaimVerification]) -> tuple[str, dict[str, int]]:
    counts = Counter(v.status.value for v in verifications)
    total = sum(counts.values())
    counts_dict = dict(counts)
    counts_dict["total"] = total

    if total == 0:
        return "REVIEW", counts_dict

    refuted = counts.get(ClaimStatus.REFUTED.value, 0)
    errors = counts.get(ClaimStatus.ERROR.value, 0)
    supported = counts.get(ClaimStatus.SUPPORTED.value, 0)
    unverified = counts.get(ClaimStatus.UNVERIFIED.value, 0)
    skipped = counts.get(ClaimStatus.SKIPPED.value, 0)

    actionable = total - skipped
    if actionable == 0:
        return "REVIEW", counts_dict

    if refuted > 0:
        return "FAILED", counts_dict
    if errors / max(actionable, 1) > 0.30:
        return "FAILED", counts_dict
    if unverified > 0:
        return "REVIEW", counts_dict
    if supported / max(actionable, 1) >= 0.50:
        return "PASS", counts_dict
    return "REVIEW", counts_dict
