"""Shared dataclasses for the Loki pipeline stages.

We deliberately mirror the shape of factcheck-v2.py's CheckResult / Severity
so that the orchestrator can convert pipeline output into the same report
format without callers needing to know which pipeline produced the data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ClaimStatus(str, Enum):
    """Outcome of verifying a single atomic claim."""

    SUPPORTED = "supported"      # evidence backs the claim
    REFUTED = "refuted"          # evidence contradicts the claim
    UNVERIFIED = "unverified"    # could not find evidence
    SKIPPED = "skipped"          # claim deemed not check-worthy
    ERROR = "error"              # technical failure during verification


@dataclass
class AtomicClaim:
    """One atomic, context-independent factual statement."""

    text: str                            # the claim itself
    source_span: str = ""                # original sentence/snippet from doc
    subject: str = ""                    # extracted entity ("Тариф Старт")
    predicate: str = ""                  # extracted relation ("стоит")
    object_value: str = ""               # extracted value ("65K/мес")
    claim_type: str = "fact"             # fact | numeric | date | url | brand
    checkworthy: bool = True             # set False after stage_normalize
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "source_span": self.source_span,
            "subject": self.subject,
            "predicate": self.predicate,
            "object_value": self.object_value,
            "claim_type": self.claim_type,
            "checkworthy": self.checkworthy,
            "metadata": self.metadata,
        }


@dataclass
class ClaimSource:
    """Candidate verification source for a claim."""

    url: str = ""
    method: str = "http_head"        # http_head | crossref_doc | none
    notes: str = ""


@dataclass
class ClaimVerification:
    """Result of stage_verify for a single claim."""

    claim: AtomicClaim
    status: ClaimStatus
    confidence: float = 0.0
    evidence: str = ""
    source: ClaimSource | None = None
    error: str = ""


@dataclass
class PipelineResult:
    """Final output of run_loki_pipeline — designed to plug into factcheck-v2 reports."""

    verdict: str                                    # PASS | REVIEW | FAILED
    claims: list[AtomicClaim] = field(default_factory=list)
    verifications: list[ClaimVerification] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    elapsed_sec: float = 0.0
    pipeline: str = "loki"
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "pipeline": self.pipeline,
            "claims": [c.to_dict() for c in self.claims],
            "verifications": [
                {
                    "claim": v.claim.text,
                    "status": v.status.value,
                    "confidence": v.confidence,
                    "evidence": v.evidence[:200],
                    "source": v.source.url if v.source else "",
                    "error": v.error,
                }
                for v in self.verifications
            ],
            "counts": self.counts,
            "elapsed_sec": self.elapsed_sec,
            "errors": self.errors,
        }
