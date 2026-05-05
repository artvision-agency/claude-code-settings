"""Stage 4: Verification.

Reuses the HTTP session helpers from factcheck-v2.py (when available) and
falls back to a simple urllib HEAD-or-GET check otherwise. The point is to
keep verification deterministic and cheap — heavyweight LLM-based evidence
extraction is intentionally OUT OF SCOPE for Phase 2 (see decision-doc).

What we actually verify per claim:
    * method=http_head        → URL responds 2xx/3xx → SUPPORTED
                                   non-2xx                  → REFUTED
                                   network error            → ERROR
    * method=crossref_doc     → already proven by Stage 3 → SUPPORTED
    * method=none             → UNVERIFIED (we couldn't even pick a source)
"""

from __future__ import annotations

import urllib.error
import urllib.request
from typing import Sequence

from .types import AtomicClaim, ClaimSource, ClaimStatus, ClaimVerification

DEFAULT_TIMEOUT = 5
USER_AGENT = "Artvision-Factcheck-Loki/0.1 (+https://artvision.pro)"


def _try_factcheck_v2_session():
    """Return a configured `requests.Session` if factcheck-v2 helpers are importable."""
    try:
        # Allow re-using the production HTTP session (retries, UA, timeout).
        import importlib.util
        import sys
        from pathlib import Path

        v2_path = Path("/Users/antonk/.claude/scripts/factcheck-v2.py")
        if not v2_path.is_file():
            return None
        # Avoid module-name clash with our package
        spec = importlib.util.spec_from_file_location("_factcheck_v2_compat", v2_path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules.setdefault("_factcheck_v2_compat", module)
        spec.loader.exec_module(module)
        if getattr(module, "HAS_REQUESTS", False):
            return module.make_http_session()
    except Exception:
        return None
    return None


def _stdlib_head(url: str, timeout: int = DEFAULT_TIMEOUT) -> tuple[int | None, str]:
    """HEAD via stdlib; returns (status, error)."""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, ""
    except urllib.error.HTTPError as exc:
        if exc.code == 405:
            # Try GET as a last resort
            req_get = urllib.request.Request(url, method="GET", headers={"User-Agent": USER_AGENT})
            try:
                with urllib.request.urlopen(req_get, timeout=timeout) as resp:
                    return resp.status, ""
            except Exception as inner:
                return None, str(inner)[:120]
        return exc.code, f"HTTP {exc.code}: {exc.reason}"
    except (urllib.error.URLError, TimeoutError) as exc:
        return None, str(exc)[:120]
    except Exception as exc:  # pragma: no cover - defensive
        return None, str(exc)[:120]


def _check_url(url: str, *, no_http: bool, session) -> tuple[ClaimStatus, float, str, str]:
    """Return (status, confidence, evidence, error)."""
    if no_http:
        return ClaimStatus.UNVERIFIED, 0.0, "", "HTTP disabled (--no-http)"

    if session is not None:
        try:
            from importlib import import_module
            mod = import_module("_factcheck_v2_compat")
            result = mod.head_check(session, url)
            status_code = result.get("status")
            err = result.get("error") or ""
        except Exception as exc:
            status_code, err = _stdlib_head(url)
            if status_code is None and not err:
                err = str(exc)[:120]
    else:
        status_code, err = _stdlib_head(url)

    if err:
        return ClaimStatus.ERROR, 0.0, "", err
    if status_code is None:
        return ClaimStatus.ERROR, 0.0, "", "no status returned"
    if 200 <= status_code < 400:
        return ClaimStatus.SUPPORTED, 0.7, f"HTTP {status_code} OK", ""
    if status_code in (404, 410):
        return ClaimStatus.REFUTED, 0.9, f"HTTP {status_code}", ""
    return ClaimStatus.UNVERIFIED, 0.3, f"HTTP {status_code}", ""


def verify_claims(
    pairs: Sequence[tuple[AtomicClaim, ClaimSource]],
    *,
    no_http: bool = False,
) -> list[ClaimVerification]:
    """Run Stage 4 across all (claim, source) pairs."""
    session = None if no_http else _try_factcheck_v2_session()
    results: list[ClaimVerification] = []

    for claim, source in pairs:
        if not claim.checkworthy:
            results.append(
                ClaimVerification(
                    claim=claim,
                    status=ClaimStatus.SKIPPED,
                    confidence=0.0,
                    evidence="claim marked non-checkworthy by stage_normalize",
                    source=source,
                )
            )
            continue

        if source.method == "crossref_doc":
            results.append(
                ClaimVerification(
                    claim=claim,
                    status=ClaimStatus.SUPPORTED,
                    confidence=0.6,
                    evidence=f"cross-referenced in {source.url} ({source.notes})",
                    source=source,
                )
            )
            continue

        if source.method == "http_head" and source.url:
            status, conf, evidence, err = _check_url(
                source.url, no_http=no_http, session=session,
            )
            results.append(
                ClaimVerification(
                    claim=claim,
                    status=status,
                    confidence=conf,
                    evidence=evidence,
                    source=source,
                    error=err,
                )
            )
            continue

        # method=none or empty url → unverified
        results.append(
            ClaimVerification(
                claim=claim,
                status=ClaimStatus.UNVERIFIED,
                confidence=0.0,
                evidence="",
                source=source,
                error="no source resolved",
            )
        )

    return results
