#!/usr/bin/env python3
"""
pre-deploy-formula-consistency.py
PreToolUse hook: блокирует scp HTML если коэффициент платежа К/мес в шапке
противоречит данным таблицы (платёж / кредит).
Прецедент: IPOTEKA c052407c — «6.0 К/мес × млн» в шапке, таблицы дают 5.83 К/мес.
Bypass: FORMULA_CONSISTENCY_SKIP=1
"""

import json
import math
import os
import re
import sys
import logging

LOG_PATH = os.path.expanduser("~/.claude/logs/pre-deploy-formula-consistency.log")
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("formula-verify")

TOLERANCE = 0.05  # 5% tolerance for rounding differences


def parse_number(raw: str) -> float | None:
    """Parse Russian-formatted number: '5.83', '58 000', '6,0'."""
    raw = raw.strip().replace("\xa0", "").replace(" ", "").replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


def parse_price_mln(raw: str) -> float | None:
    """Parse price in millions: '6.5М', '6,5 млн', '6500000'."""
    raw = raw.strip().replace("\xa0", "").replace(" ", "")
    m = re.match(r"([0-9]+[.,][0-9]+|[0-9]+)\s*[Мм](?:лн)?$", raw)
    if m:
        return float(m.group(1).replace(",", "."))
    m = re.match(r"^([0-9]{7,10})$", raw.replace("_", ""))
    if m:
        return float(m.group(1)) / 1_000_000
    return None


def extract_headline_k(html: str) -> list[float]:
    """
    Extract K coefficient from headline formulas like:
    '6.0 К/мес × млн', '5.83 К/мес/млн', '6,0 тыс/мес на млн'
    Returns list of K values found.
    """
    results = []
    patterns = [
        r"([0-9]+[.,][0-9]+|[0-9]+)\s*[Кк]/мес\s*[×x*/]\s*млн",
        r"([0-9]+[.,][0-9]+|[0-9]+)\s*[Кк]\s*/\s*мес",
        r"([0-9]+[.,][0-9]+|[0-9]+)\s*тыс\.?\s*/\s*мес.*(?:млн|миллион)",
    ]
    for pat in patterns:
        for m in re.finditer(pat, html, re.IGNORECASE):
            val = parse_number(m.group(1))
            if val and 1.0 <= val <= 20.0:
                results.append(val)
    return results


def extract_table_payments(html: str) -> list[tuple[float, float]]:
    """
    Extract (monthly_payment_K, credit_mln) pairs from HTML tables.
    Looks for patterns like:
    - <td>35 000</td> ... <td>6 000 000</td>
    - data-payment="35000" data-loan="6000000"
    Returns list of (payment_k, loan_mln) tuples.
    """
    results = []

    # Pattern 1: adjacent table cells with numeric values
    # Find all td/th values as sequence
    cells = re.findall(r"<t[dh][^>]*>\s*([0-9][0-9\s.,]{2,12}[0-9])\s*</t[dh]>", html)
    numeric_cells = []
    for cell in cells:
        clean = cell.replace("\xa0", "").replace(" ", "").replace(",", ".")
        try:
            val = float(clean)
            numeric_cells.append(val)
        except ValueError:
            continue

    # Sliding window: find payment (20K-300K) adjacent to loan (1M-50M)
    # Only forward order: payment then loan (not reversed — reversed creates false pairs)
    # Also skip if the previous cell was already used as loan (avoid overlapping pairs)
    used_as_loan: set[int] = set()
    for i in range(len(numeric_cells) - 1):
        if i in used_as_loan:
            continue
        a, b = numeric_cells[i], numeric_cells[i + 1]
        if 20_000 <= a <= 300_000 and 1_000_000 <= b <= 50_000_000:
            results.append((a / 1000, b / 1_000_000))  # → (K, mln)
            used_as_loan.add(i + 1)  # mark loan cell as consumed

    # Pattern 2: data attributes
    for m in re.finditer(
        r'data-(?:payment|platezh)=["\']([0-9]+)["\'][^>]*data-(?:loan|kredit)=["\']([0-9]+)["\']',
        html,
        re.IGNORECASE,
    ):
        pay = float(m.group(1)) / 1000
        loan = float(m.group(2)) / 1_000_000
        if 20 <= pay <= 300 and 1 <= loan <= 50:
            results.append((pay, loan))

    return results


def compute_k_from_pair(payment_k: float, loan_mln: float) -> float | None:
    """K = payment_k / loan_mln (thousands per month per million)."""
    if loan_mln <= 0:
        return None
    return payment_k / loan_mln


def extract_html_path(command: str) -> str | None:
    m = re.search(r"(\S+\.html)", command)
    return m.group(1) if m else None


def main() -> int:
    if os.environ.get("FORMULA_CONSISTENCY_SKIP") == "1":
        print("[formula-verify] SKIP via FORMULA_CONSISTENCY_SKIP=1", file=sys.stderr)
        return 0

    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return 0

    command = data.get("tool_input", {}).get("command", "")

    if not re.search(r"\bscp\b|\bcp\b", command):
        return 0
    if ".html" not in command:
        return 0

    html_path = extract_html_path(command)
    if not html_path or not os.path.isfile(html_path):
        return 0

    log.info("Checking formula consistency in %s", html_path)

    try:
        with open(html_path, encoding="utf-8", errors="replace") as f:
            html = f.read()
    except OSError:
        return 0

    headline_ks = list(dict.fromkeys(extract_headline_k(html)))  # deduplicate preserving order
    if not headline_ks:
        log.info("No K/мес coefficient in headline — PASS")
        return 0

    table_pairs = extract_table_payments(html)
    if not table_pairs:
        log.info("No payment table pairs found — cannot verify formula")
        return 0

    # Compute actual K from table pairs
    actual_ks = []
    for pay_k, loan_mln in table_pairs:
        k = compute_k_from_pair(pay_k, loan_mln)
        if k:
            actual_ks.append(k)

    if not actual_ks:
        return 0

    actual_k_avg = sum(actual_ks) / len(actual_ks)
    log.info("Headline K=%s, Table K_avg=%.3f (n=%d)", headline_ks, actual_k_avg, len(actual_ks))

    criticals = []
    warnings = []

    for hk in headline_ks:
        deviation = abs(hk - actual_k_avg) / actual_k_avg if actual_k_avg else 1.0
        if deviation > TOLERANCE * 2:  # >10% → critical
            criticals.append(
                f"CRITICAL: K={hk:.2f} К/мес×млн в шапке, "
                f"таблица даёт {actual_k_avg:.2f} (отклонение {deviation * 100:.1f}%)"
            )
        elif deviation > TOLERANCE:  # 5-10% → warn
            warnings.append(
                f"WARN: K={hk:.2f} К/мес×млн в шапке, "
                f"таблица даёт {actual_k_avg:.2f} (отклонение {deviation * 100:.1f}%)"
            )

    if criticals:
        print("\n[pre-deploy-formula-consistency] BLOCKED — коэффициент K/мес не совпадает с таблицей:", file=sys.stderr)
        for msg in criticals:
            print(f"  {msg}", file=sys.stderr)
        for msg in warnings:
            print(f"  {msg}", file=sys.stderr)
        print("\nИсправь коэффициент K или таблицу. Bypass: FORMULA_CONSISTENCY_SKIP=1", file=sys.stderr)
        log.error("BLOCK: formula mismatch in %s", html_path)
        return 2

    if warnings:
        print("\n[pre-deploy-formula-consistency] WARN — небольшое расхождение K/мес:", file=sys.stderr)
        for msg in warnings:
            print(f"  {msg}", file=sys.stderr)
        print("Проверь вручную или: FORMULA_CONSISTENCY_SKIP=1", file=sys.stderr)
        log.warning("WARN: formula warnings in %s", html_path)
        return 1

    log.info("PASS: formula K consistent in %s", html_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
