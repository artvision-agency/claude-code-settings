#!/usr/bin/env python3
"""
Artvision Factcheck Autofix -- automated factcheck -> fix -> re-check loop.

Runs factcheck-v2.py on an HTML file, parses CRITICAL/WARNING issues,
attempts automatic fixes (broken URLs, missing images, broken anchors),
and re-runs until CRITICAL == 0 or max rounds reached.

Usage:
    python3 factcheck-autofix.py -f <html_file> [options]

Options:
    -f, --file          HTML file to check (required)
    -n, --max-rounds    Max fix rounds (default: 5)
    --auto-fix-urls     Automatically fix broken URLs
    --dry-run           Show what would be fixed without changing
    --factcheck-args    Extra args to pass to factcheck-v2.py

Exit codes:
    0 = all CRITICAL issues resolved (PASS)
    1 = CRITICAL issues remain after max rounds
    2 = script error
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FACTCHECK_SCRIPT = Path(__file__).parent / "factcheck-v2.py"
PYTHON = sys.executable

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


class IssueSeverity(Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"


class IssueType(Enum):
    BROKEN_URL = "broken_url"
    HTTP_ERROR = "http_error"
    MISSING_IMAGE = "missing_image"
    BROKEN_ANCHOR = "broken_anchor"
    EMPTY_IMAGE_SRC = "empty_image_src"
    PLACEHOLDER_TEXT = "placeholder_text"
    MISSING_TITLE = "missing_title"
    OTHER = "other"


@dataclass
class Issue:
    severity: IssueSeverity
    check: str
    details: str
    issue_type: IssueType = IssueType.OTHER
    url: str = ""
    fixed: bool = False
    fix_description: str = ""


@dataclass
class RoundResult:
    round_num: int
    criticals: int
    warnings: int
    fixed: int
    issues: list[Issue] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
DIM = "\033[2m"
RESET = "\033[0m"


def print_header(text: str) -> None:
    """Print a bold header line."""
    print(f"\n{BOLD}{CYAN}{'=' * 60}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 60}{RESET}")


def print_round_summary(results: list[RoundResult]) -> None:
    """Print a summary table of all rounds."""
    print(f"\n{BOLD}Summary:{RESET}")
    print(f"{'Round':<8} {'CRITICALs':<12} {'WARNINGs':<12} {'Fixed':<8} {'Status'}")
    print("-" * 55)
    for r in results:
        if r.criticals == 0:
            status = f"{GREEN}PASS{RESET}"
        else:
            status = f"{RED}FAIL{RESET}"
        crit_color = GREEN if r.criticals == 0 else RED
        warn_color = GREEN if r.warnings == 0 else YELLOW
        print(
            f"  {r.round_num:<6} "
            f"{crit_color}{r.criticals:<12}{RESET}"
            f"{warn_color}{r.warnings:<12}{RESET}"
            f"{r.fixed:<8} "
            f"{status}"
        )


# ---------------------------------------------------------------------------
# Factcheck runner
# ---------------------------------------------------------------------------


def run_factcheck(
    html_file: Path,
    extra_args: list[str] | None = None,
) -> tuple[str, int]:
    """Run factcheck-v2.py and return (stdout, exit_code)."""
    cmd = [PYTHON, str(FACTCHECK_SCRIPT), "--standard", str(html_file)]
    if extra_args:
        cmd.extend(extra_args)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,
    )
    output = result.stdout + result.stderr
    return output, result.returncode


# ---------------------------------------------------------------------------
# Output parser
# ---------------------------------------------------------------------------

# Matches table rows like: | FAIL | Link URL | FAILED: https://example.com/page -- Connection error |
# or: | FAIL | Image URL | HTTP 404: https://example.com/img.jpg |
# or: | WARN | ... | ... |
TABLE_ROW_RE = re.compile(
    r"^\|\s*(FAIL|WARN|PASS|INFO)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|$",
    re.MULTILINE,
)

# Extract URL from details like "FAILED: https://..." or "HTTP 404: https://..."
URL_IN_DETAILS_RE = re.compile(
    r"(?:FAILED|HTTP \d{3}):\s*(https?://\S+)"
)

# Summary line: - CRITICAL: N
CRITICAL_COUNT_RE = re.compile(r"^- CRITICAL:\s*(\d+)", re.MULTILINE)
WARNING_COUNT_RE = re.compile(r"^- Warnings:\s*(\d+)", re.MULTILINE)

# Verdict line
VERDICT_RE = re.compile(r"\*\*VERDICT:\s*(PASSED|FAILED|REVIEW)\*\*")


def parse_factcheck_output(output: str) -> tuple[list[Issue], int, int]:
    """Parse factcheck-v2.py output into structured issues.

    Returns:
        Tuple of (issues, critical_count, warning_count).
    """
    issues: list[Issue] = []

    # Extract counts from summary
    crit_match = CRITICAL_COUNT_RE.search(output)
    warn_match = WARNING_COUNT_RE.search(output)
    critical_count = int(crit_match.group(1)) if crit_match else 0
    warning_count = int(warn_match.group(1)) if warn_match else 0

    # Parse table rows
    for match in TABLE_ROW_RE.finditer(output):
        status_str, check, details = match.group(1), match.group(2).strip(), match.group(3).strip()

        if status_str == "FAIL":
            severity = IssueSeverity.CRITICAL
        elif status_str == "WARN":
            severity = IssueSeverity.WARNING
        else:
            continue  # skip PASS and INFO

        issue_type = _classify_issue(check, details)
        url = ""
        url_match = URL_IN_DETAILS_RE.search(details)
        if url_match:
            url = url_match.group(1)

        issues.append(Issue(
            severity=severity,
            check=check,
            details=details,
            issue_type=issue_type,
            url=url,
        ))

    return issues, critical_count, warning_count


def _classify_issue(check: str, details: str) -> IssueType:
    """Classify an issue by its check name and details."""
    check_lower = check.lower()
    details_lower = details.lower()

    if "url" in check_lower:
        if "failed:" in details_lower:
            return IssueType.BROKEN_URL
        if re.match(r"http \d{3}", details_lower):
            return IssueType.HTTP_ERROR
        return IssueType.BROKEN_URL

    if "anchor" in check_lower:
        return IssueType.BROKEN_ANCHOR

    if "empty image src" in check_lower or "empty image" in details_lower:
        return IssueType.EMPTY_IMAGE_SRC

    if "missing" in check_lower and "image" in check_lower:
        return IssueType.MISSING_IMAGE

    if "placeholder" in check_lower or "placeholder" in details_lower:
        return IssueType.PLACEHOLDER_TEXT

    if "title" in check_lower and "missing" in details_lower:
        return IssueType.MISSING_TITLE

    return IssueType.OTHER


# ---------------------------------------------------------------------------
# Fixers
# ---------------------------------------------------------------------------


def check_url_with_curl(url: str, timeout: int = 10) -> tuple[int, str]:
    """Check URL via curl, return (status_code, final_url_after_redirects).

    Returns (0, "") on connection failure.
    """
    try:
        result = subprocess.run(
            [
                "curl", "-sI", "-o", "/dev/null",
                "-w", "%{http_code} %{url_effective}",
                "-L",  # follow redirects
                "--max-time", str(timeout),
                "--max-redirs", "5",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=timeout + 5,
        )
        parts = result.stdout.strip().split(" ", 1)
        status = int(parts[0]) if parts[0].isdigit() else 0
        final_url = parts[1] if len(parts) > 1 else url
        return status, final_url
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, ValueError):
        return 0, ""


def try_url_alternatives(broken_url: str) -> Optional[str]:
    """Try common URL mutations to find a working alternative.

    Strategies:
    - Follow redirects (the URL itself may redirect)
    - Try www / non-www variants
    - Try https / http variants
    - Try removing trailing path segments
    """
    # First, try the URL itself with redirect following
    status, final_url = check_url_with_curl(broken_url)
    if 200 <= status < 400 and final_url and final_url != broken_url:
        return final_url

    from urllib.parse import urlparse, urlunparse

    parsed = urlparse(broken_url)

    alternatives: list[str] = []

    # www / non-www
    if parsed.hostname and parsed.hostname.startswith("www."):
        alt_host = parsed.hostname[4:]
        alternatives.append(urlunparse(parsed._replace(netloc=alt_host)))
    elif parsed.hostname:
        alt_host = f"www.{parsed.hostname}"
        alternatives.append(urlunparse(parsed._replace(netloc=alt_host)))

    # https / http swap
    if parsed.scheme == "https":
        alternatives.append(urlunparse(parsed._replace(scheme="http")))
    elif parsed.scheme == "http":
        alternatives.append(urlunparse(parsed._replace(scheme="https")))

    # Try parent paths (remove last segment)
    path_parts = parsed.path.rstrip("/").split("/")
    if len(path_parts) > 2:
        parent_path = "/".join(path_parts[:-1]) + "/"
        alternatives.append(urlunparse(parsed._replace(path=parent_path)))

    # Try root
    if parsed.path and parsed.path != "/":
        alternatives.append(urlunparse(parsed._replace(path="/", query="", fragment="")))

    for alt in alternatives:
        alt_status, _ = check_url_with_curl(alt)
        if 200 <= alt_status < 400:
            return alt

    return None


def find_local_image_alternatives(
    html_file: Path,
    image_path: str,
) -> Optional[str]:
    """Look for an image file at common alternative paths relative to the HTML file."""
    html_dir = html_file.parent
    img_name = Path(image_path).name
    img_stem = Path(image_path).stem
    img_suffixes = [".jpg", ".jpeg", ".png", ".webp", ".svg", ".gif"]

    # Search directories relative to the HTML file
    search_dirs = [
        html_dir,
        html_dir / "img",
        html_dir / "images",
        html_dir / "assets",
        html_dir / "assets" / "img",
        html_dir / "static",
        html_dir / "media",
    ]

    for search_dir in search_dirs:
        if not search_dir.is_dir():
            continue

        # Exact name match
        candidate = search_dir / img_name
        if candidate.is_file():
            return str(candidate.relative_to(html_dir))

        # Same stem, different extension
        for ext in img_suffixes:
            candidate = search_dir / f"{img_stem}{ext}"
            if candidate.is_file():
                return str(candidate.relative_to(html_dir))

    return None


def fix_broken_anchor(html_content: str, details: str) -> tuple[str, Optional[str]]:
    """Attempt to fix broken anchor references in HTML.

    Returns (new_content, fix_description) or (original_content, None) if unfixable.
    """
    # Pattern: "Broken #anchor-name -- not found in document"
    anchor_match = re.search(r'href="#([^"]+)".*not found', details, re.IGNORECASE)
    if not anchor_match:
        # Try extracting from details like: "#some-id not found in document"
        anchor_match = re.search(r"#(\S+)\s+", details)
    if not anchor_match:
        return html_content, None

    broken_id = anchor_match.group(1)

    # Check if a similar ID exists (case-insensitive or with common variations)
    id_pattern = re.compile(r'id\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
    existing_ids = id_pattern.findall(html_content)

    # Try fuzzy match: lowercase comparison, dash/underscore swap
    normalized_broken = broken_id.lower().replace("-", "_")
    for existing_id in existing_ids:
        normalized_existing = existing_id.lower().replace("-", "_")
        if normalized_broken == normalized_existing and existing_id != broken_id:
            new_content = html_content.replace(f'href="#{broken_id}"', f'href="#{existing_id}"')
            if new_content != html_content:
                return new_content, f'Fixed anchor #{broken_id} -> #{existing_id}'

    return html_content, None


# ---------------------------------------------------------------------------
# Main fix loop
# ---------------------------------------------------------------------------


def apply_fixes(
    html_file: Path,
    issues: list[Issue],
    auto_fix_urls: bool,
    dry_run: bool,
) -> tuple[str, int]:
    """Apply fixes for parsed issues.

    Returns:
        Tuple of (html_content_after_fixes, number_of_fixes_applied).
    """
    content = html_file.read_text(encoding="utf-8")
    original_content = content
    fixes_applied = 0

    for issue in issues:
        if issue.severity != IssueSeverity.CRITICAL:
            continue

        if issue.issue_type in (IssueType.BROKEN_URL, IssueType.HTTP_ERROR) and issue.url:
            if not auto_fix_urls:
                continue

            print(f"  {DIM}Checking alternatives for: {issue.url[:80]}...{RESET}")
            alternative = try_url_alternatives(issue.url)

            if alternative:
                if dry_run:
                    print(f"  {YELLOW}[DRY-RUN]{RESET} Would replace:")
                    print(f"    {RED}- {issue.url[:100]}{RESET}")
                    print(f"    {GREEN}+ {alternative[:100]}{RESET}")
                    issue.fixed = True
                    issue.fix_description = f"Would replace with {alternative}"
                    fixes_applied += 1
                else:
                    new_content = content.replace(issue.url, alternative)
                    if new_content != content:
                        content = new_content
                        issue.fixed = True
                        issue.fix_description = f"Replaced with {alternative}"
                        fixes_applied += 1
                        print(f"  {GREEN}Fixed:{RESET} {issue.url[:60]} -> {alternative[:60]}")
                    else:
                        print(f"  {YELLOW}URL not found in HTML (may be encoded differently){RESET}")
            else:
                # URL is completely dead -- comment it out or remove the link
                # We remove the href but keep the text
                link_pattern = re.compile(
                    r'<a\s+[^>]*href\s*=\s*["\']'
                    + re.escape(issue.url)
                    + r'["\'][^>]*>(.*?)</a>',
                    re.DOTALL | re.IGNORECASE,
                )
                match = link_pattern.search(content)
                if match:
                    link_text = match.group(1)
                    if dry_run:
                        print(f"  {YELLOW}[DRY-RUN]{RESET} Would remove dead link, keep text: {link_text[:60]}")
                        issue.fixed = True
                        issue.fix_description = f"Would remove dead link, keep text"
                        fixes_applied += 1
                    else:
                        # Replace <a href="dead">text</a> with <span>text</span>
                        content = content[:match.start()] + f"<span>{link_text}</span>" + content[match.end():]
                        issue.fixed = True
                        issue.fix_description = f"Removed dead link, kept text as <span>"
                        fixes_applied += 1
                        print(f"  {GREEN}Removed dead link:{RESET} {issue.url[:60]} (kept text)")
                else:
                    print(f"  {RED}No fix found:{RESET} {issue.url[:60]} -- no alternative, not a simple <a> tag")

        elif issue.issue_type == IssueType.MISSING_IMAGE:
            # Try to find image at alternative local paths
            img_match = re.search(r'src\s*=\s*["\']([^"\']+)["\']', issue.details)
            if img_match:
                img_src = img_match.group(1)
            else:
                # Try to extract path from details text
                path_match = re.search(r"Not found:\s*(\S+)", issue.details)
                img_src = path_match.group(1) if path_match else ""

            if img_src:
                alternative = find_local_image_alternatives(html_file, img_src)
                if alternative:
                    if dry_run:
                        print(f"  {YELLOW}[DRY-RUN]{RESET} Would replace image: {img_src} -> {alternative}")
                        issue.fixed = True
                        issue.fix_description = f"Would replace with {alternative}"
                        fixes_applied += 1
                    else:
                        new_content = content.replace(img_src, alternative)
                        if new_content != content:
                            content = new_content
                            issue.fixed = True
                            issue.fix_description = f"Replaced with {alternative}"
                            fixes_applied += 1
                            print(f"  {GREEN}Fixed image:{RESET} {img_src} -> {alternative}")

        elif issue.issue_type == IssueType.BROKEN_ANCHOR:
            new_content, fix_desc = fix_broken_anchor(content, issue.details)
            if fix_desc:
                if dry_run:
                    print(f"  {YELLOW}[DRY-RUN]{RESET} {fix_desc}")
                    issue.fixed = True
                    issue.fix_description = fix_desc
                    fixes_applied += 1
                else:
                    content = new_content
                    issue.fixed = True
                    issue.fix_description = fix_desc
                    fixes_applied += 1
                    print(f"  {GREEN}Fixed:{RESET} {fix_desc}")

        elif issue.issue_type == IssueType.EMPTY_IMAGE_SRC:
            # Remove <img> tags with empty src to avoid browser errors
            empty_img_re = re.compile(r'<img\s+[^>]*src\s*=\s*["\']["\'][^>]*/?\s*>', re.IGNORECASE)
            match = empty_img_re.search(content)
            if match:
                if dry_run:
                    print(f"  {YELLOW}[DRY-RUN]{RESET} Would remove <img> with empty src")
                    issue.fixed = True
                    issue.fix_description = "Would remove empty src img"
                    fixes_applied += 1
                else:
                    content = content[:match.start()] + f"<!-- removed empty img -->" + content[match.end():]
                    issue.fixed = True
                    issue.fix_description = "Removed <img> with empty src"
                    fixes_applied += 1
                    print(f"  {GREEN}Removed empty src img{RESET}")

    # Write changes if not dry-run and something changed
    if not dry_run and content != original_content:
        html_file.write_text(content, encoding="utf-8")

    return content, fixes_applied


def get_issue_fingerprints(issues: list[Issue]) -> set[str]:
    """Create a set of fingerprints for issues to detect stale loops."""
    return {f"{i.severity.value}:{i.check}:{i.url or i.details[:50]}" for i in issues}


def main(argv: list[str] | None = None) -> int:
    """Entry point for the autofix loop."""
    parser = argparse.ArgumentParser(
        description="Artvision Factcheck Autofix -- automated fix loop",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "-f", "--file",
        required=True,
        help="HTML file to check (required)",
    )
    parser.add_argument(
        "-n", "--max-rounds",
        type=int,
        default=5,
        help="Maximum fix rounds (default: 5)",
    )
    parser.add_argument(
        "--auto-fix-urls",
        action="store_true",
        help="Automatically fix broken URLs (verify with curl, find alternatives)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be fixed without changing the file",
    )
    parser.add_argument(
        "--factcheck-args",
        nargs=argparse.REMAINDER,
        default=[],
        help="Extra arguments to pass to factcheck-v2.py",
    )

    args = parser.parse_args(argv)
    html_file = Path(args.file).resolve()

    # Validate inputs
    if not html_file.is_file():
        print(f"{RED}ERROR:{RESET} File not found: {html_file}", file=sys.stderr)
        return 2

    if not FACTCHECK_SCRIPT.is_file():
        print(
            f"{RED}ERROR:{RESET} factcheck-v2.py not found at: {FACTCHECK_SCRIPT}",
            file=sys.stderr,
        )
        return 2

    print_header(f"Factcheck Autofix: {html_file.name}")
    print(f"  File: {html_file}")
    print(f"  Max rounds: {args.max_rounds}")
    print(f"  Auto-fix URLs: {args.auto_fix_urls}")
    print(f"  Dry run: {args.dry_run}")

    # Create backup before any modifications
    backup_path = html_file.with_suffix(html_file.suffix + ".bak")
    if not args.dry_run:
        shutil.copy2(html_file, backup_path)
        print(f"  Backup: {backup_path}")
    else:
        print(f"  {YELLOW}[DRY-RUN] No backup created{RESET}")

    round_results: list[RoundResult] = []
    previous_fingerprints: set[str] = set()
    stale_count = 0

    for round_num in range(1, args.max_rounds + 1):
        print(f"\n{BOLD}--- Round {round_num}/{args.max_rounds} ---{RESET}")

        # Step 1: Run factcheck
        print(f"  Running factcheck-v2.py --standard ...")
        output, exit_code = run_factcheck(html_file, args.factcheck_args or None)

        # Step 2: Parse output
        issues, critical_count, warning_count = parse_factcheck_output(output)

        # Show verdict from factcheck
        verdict_match = VERDICT_RE.search(output)
        verdict = verdict_match.group(1) if verdict_match else "UNKNOWN"
        verdict_color = GREEN if verdict == "PASSED" else (YELLOW if verdict == "REVIEW" else RED)
        print(f"  Verdict: {verdict_color}{verdict}{RESET}  "
              f"(CRITICALs: {critical_count}, WARNINGs: {warning_count})")

        # Step 3: Check if we are done
        if critical_count == 0:
            round_results.append(RoundResult(
                round_num=round_num,
                criticals=critical_count,
                warnings=warning_count,
                fixed=0,
                issues=issues,
            ))
            print(f"\n{GREEN}{BOLD}PASS{RESET} -- No CRITICAL issues. ", end="")
            if warning_count > 0:
                print(f"{YELLOW}{warning_count} warning(s) remain for manual review.{RESET}")
            else:
                print("Clean.")
            print_round_summary(round_results)
            return 0

        # Step 4: Detect stale loop (same issues persisting)
        current_fingerprints = get_issue_fingerprints(issues)
        if current_fingerprints == previous_fingerprints:
            stale_count += 1
        else:
            stale_count = 0
        previous_fingerprints = current_fingerprints

        if stale_count >= 2:
            round_results.append(RoundResult(
                round_num=round_num,
                criticals=critical_count,
                warnings=warning_count,
                fixed=0,
                issues=issues,
            ))
            print(f"\n{RED}{BOLD}STUCK{RESET} -- Same issues persist after {stale_count} rounds. Stopping.")
            print(f"\n{BOLD}Remaining CRITICAL issues:{RESET}")
            for issue in issues:
                if issue.severity == IssueSeverity.CRITICAL:
                    print(f"  {RED}[CRITICAL]{RESET} {issue.check}: {issue.details[:100]}")
            print_round_summary(round_results)
            return 1

        # Step 5: Show issues found
        critical_issues = [i for i in issues if i.severity == IssueSeverity.CRITICAL]
        print(f"  Found {len(critical_issues)} CRITICAL issue(s) to fix:")
        for issue in critical_issues:
            type_label = issue.issue_type.value.replace("_", " ")
            print(f"    {RED}[{type_label}]{RESET} {issue.details[:90]}")

        # Step 6: Apply fixes
        print(f"\n  Applying fixes...")
        _, fixes_applied = apply_fixes(
            html_file=html_file,
            issues=issues,
            auto_fix_urls=args.auto_fix_urls,
            dry_run=args.dry_run,
        )

        round_results.append(RoundResult(
            round_num=round_num,
            criticals=critical_count,
            warnings=warning_count,
            fixed=fixes_applied,
            issues=issues,
        ))

        if fixes_applied == 0:
            print(f"\n  {YELLOW}No automatic fixes available for remaining issues.{RESET}")
            print(f"\n{BOLD}Remaining CRITICAL issues (manual fix required):{RESET}")
            for issue in issues:
                if issue.severity == IssueSeverity.CRITICAL and not issue.fixed:
                    print(f"  {RED}[CRITICAL]{RESET} {issue.check}: {issue.details[:100]}")
            print_round_summary(round_results)
            return 1

        print(f"  Applied {fixes_applied} fix(es) this round.")

        if args.dry_run:
            print(f"\n  {YELLOW}[DRY-RUN] No changes written. Stopping after analysis.{RESET}")
            print_round_summary(round_results)
            return 0 if critical_count == fixes_applied else 1

    # Exhausted max rounds
    print(f"\n{RED}{BOLD}MAX ROUNDS REACHED{RESET} -- {args.max_rounds} rounds completed.")
    print(f"Remaining CRITICAL issues:")
    for issue in issues:
        if issue.severity == IssueSeverity.CRITICAL and not issue.fixed:
            print(f"  {RED}[CRITICAL]{RESET} {issue.check}: {issue.details[:100]}")
    print_round_summary(round_results)
    return 1


if __name__ == "__main__":
    sys.exit(main())
