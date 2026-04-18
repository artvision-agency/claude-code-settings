#!/usr/bin/env python3
"""Deploy HTML pages to VPS with factcheck validation.

Flow: factcheck -> scp -> post-deploy curl check -> URL sampling.

Usage:
    deploy-client-page.py -f clients/tvorim/kp/offer.html
    deploy-client-page.py -f page.html -r clients/tvorim/kp/page.html
    deploy-client-page.py -f page.html -r site/page.html --skip-factcheck
    deploy-client-page.py -f page.html --dry-run
"""

import argparse
import html.parser
import os
import random
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

VPS_HOST = "root@80.90.181.152"
VPS_WWW = "/var/www"
SITE_DOMAIN = "https://artvision.pro"
FACTCHECK_SCRIPT = "/Users/antonk/artvision-data/scripts/factcheck-v2.py"
CLIENTS_BASE = "/Users/antonk/artvision-data/clients"
MAX_URL_CHECKS = 10

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
BOLD = "\033[1m"
NC = "\033[0m"


def log_ok(msg: str) -> None:
    print(f"{GREEN}[OK]{NC} {msg}")


def log_info(msg: str) -> None:
    print(f"{BLUE}[INFO]{NC} {msg}")


def log_warn(msg: str) -> None:
    print(f"{YELLOW}[WARN]{NC} {msg}")


def log_err(msg: str) -> None:
    print(f"{RED}[ERR]{NC} {msg}")


def log_step(step: int, total: int, msg: str) -> None:
    print(f"\n{BOLD}[{step}/{total}]{NC} {msg}")


class URLExtractor(html.parser.HTMLParser):
    """Extract URLs from href and src attributes in HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        for attr, value in attrs:
            if attr in ("href", "src") and value:
                if value.startswith(("http://", "https://")):
                    self.urls.append(value)


def detect_remote_path(local_file: str) -> Optional[str]:
    """Auto-detect remote path from local file path if inside clients/ folder.

    Maps: clients/<name>/.../<file>.html -> clients/<name>/.../<file>.html
    """
    abs_path = os.path.abspath(local_file)
    if CLIENTS_BASE in abs_path:
        relative = abs_path.split(CLIENTS_BASE + "/")[1]
        return f"clients/{relative}"
    return None


def run_cmd(cmd: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    """Run a subprocess command with timeout."""
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def run_factcheck(filepath: str) -> tuple[bool, int, str]:
    """Run factcheck-v2.py on the file.

    Returns:
        (passed, critical_count, output)
    """
    if not os.path.exists(FACTCHECK_SCRIPT):
        return False, -1, f"Factcheck script not found: {FACTCHECK_SCRIPT}"

    try:
        result = run_cmd(
            ["python3", FACTCHECK_SCRIPT, "--standard", filepath],
            timeout=120,
        )
        output = result.stdout + result.stderr

        # Parse CRITICAL count from output
        critical_match = re.search(r"CRITICAL[:\s]+(\d+)", output, re.IGNORECASE)
        critical_count = int(critical_match.group(1)) if critical_match else 0

        # Check verdict
        if "FAILED" in output.upper() or critical_count > 0:
            return False, critical_count, output

        return True, critical_count, output

    except subprocess.TimeoutExpired:
        return False, -1, "Factcheck timed out after 120s"
    except Exception as e:
        return False, -1, f"Factcheck error: {e}"


def deploy_scp(local_file: str, remote_path: str) -> tuple[bool, str]:
    """SCP file to VPS."""
    full_remote = f"{VPS_HOST}:{VPS_WWW}/{remote_path}"

    # Ensure remote directory exists
    remote_dir = os.path.dirname(f"{VPS_WWW}/{remote_path}")
    try:
        run_cmd(["ssh", VPS_HOST, f"mkdir -p {remote_dir}"], timeout=15)
    except (subprocess.TimeoutExpired, Exception) as e:
        return False, f"Failed to create remote dir: {e}"

    try:
        result = run_cmd(["scp", local_file, full_remote], timeout=60)
        if result.returncode == 0:
            return True, full_remote
        return False, result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "SCP timed out after 60s"
    except Exception as e:
        return False, str(e)


def check_url_status(url: str) -> tuple[int, str]:
    """Curl -sI a URL, return (status_code, status_line)."""
    try:
        result = run_cmd(
            ["curl", "-sI", "-o", "/dev/null", "-w", "%{http_code}", url],
            timeout=15,
        )
        code = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
        return code, "OK" if code == 200 else f"HTTP {code}"
    except subprocess.TimeoutExpired:
        return 0, "TIMEOUT"
    except Exception as e:
        return 0, str(e)


def extract_urls_from_html(filepath: str) -> list[str]:
    """Extract external URLs from an HTML file."""
    try:
        with open(filepath, encoding="utf-8", errors="replace") as f:
            content = f.read()
        parser = URLExtractor()
        parser.feed(content)
        return parser.urls
    except Exception:
        return []


def print_summary(results: list[tuple[str, str, str]]) -> None:
    """Print a summary table of all checks."""
    print(f"\n{BOLD}{'=' * 70}")
    print(f"  DEPLOY SUMMARY")
    print(f"{'=' * 70}{NC}")

    col_step = 30
    col_status = 10
    col_detail = 28

    print(f"  {'Step':<{col_step}} {'Status':<{col_status}} {'Detail':<{col_detail}}")
    print(f"  {'-' * col_step} {'-' * col_status} {'-' * col_detail}")

    for step, status, detail in results:
        if status == "PASS":
            color = GREEN
        elif status == "SKIP":
            color = YELLOW
        elif status == "FAIL":
            color = RED
        else:
            color = NC
        detail_display = detail[:col_detail] if len(detail) > col_detail else detail
        print(f"  {step:<{col_step}} {color}{status:<{col_status}}{NC} {detail_display}")

    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deploy HTML pages to VPS with factcheck validation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "-f", "--file",
        required=True,
        help="Local HTML file path",
    )
    parser.add_argument(
        "-r", "--remote-path",
        help="Remote path under /var/www/ (auto-detected from clients/ path)",
    )
    parser.add_argument(
        "--skip-factcheck",
        action="store_true",
        help="Skip factcheck step",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without executing",
    )
    args = parser.parse_args()

    local_file = os.path.abspath(args.file)
    summary: list[tuple[str, str, str]] = []

    # Validate local file
    if not os.path.isfile(local_file):
        log_err(f"File not found: {local_file}")
        return 1

    # Determine remote path
    remote_path = args.remote_path
    if not remote_path:
        remote_path = detect_remote_path(local_file)
        if not remote_path:
            log_err(
                "Cannot auto-detect remote path. "
                "File is not in clients/ folder. Use -r to specify."
            )
            return 1
        log_info(f"Auto-detected remote path: {remote_path}")

    # Strip leading slash if present
    remote_path = remote_path.lstrip("/")

    deploy_url = f"{SITE_DOMAIN}/{remote_path}"
    total_steps = 3

    log_info(f"File:        {local_file}")
    log_info(f"Remote:      {VPS_HOST}:{VPS_WWW}/{remote_path}")
    log_info(f"URL:         {deploy_url}")
    log_info(f"Dry run:     {args.dry_run}")
    log_info(f"Factcheck:   {'skip' if args.skip_factcheck else 'enabled'}")
    print()

    if args.dry_run:
        log_info("[DRY RUN] Would run the following steps:")
        print()

    # --- Step 1: Factcheck ---
    log_step(1, total_steps, "Factcheck")

    if args.skip_factcheck:
        log_warn("Factcheck skipped by --skip-factcheck flag")
        summary.append(("Factcheck", "SKIP", "--skip-factcheck"))
    elif args.dry_run:
        log_info(f"[DRY RUN] python3 {FACTCHECK_SCRIPT} --standard {local_file}")
        summary.append(("Factcheck", "SKIP", "dry-run"))
    else:
        passed, critical_count, output = run_factcheck(local_file)
        if critical_count == -1:
            log_warn(f"Factcheck unavailable: {output.strip()}")
            summary.append(("Factcheck", "SKIP", "script not found"))
        elif passed:
            log_ok(f"Factcheck passed (CRITICAL: {critical_count})")
            summary.append(("Factcheck", "PASS", f"critical={critical_count}"))
        else:
            log_err(f"Factcheck FAILED (CRITICAL: {critical_count})")
            if output.strip():
                lines = output.strip().split("\n")
                for line in lines[-15:]:
                    print(f"    {line}")
            summary.append(("Factcheck", "FAIL", f"critical={critical_count}"))
            log_err("Deploy BLOCKED. Fix CRITICAL issues or use --skip-factcheck.")
            print_summary(summary)
            return 1

    # --- Step 2: SCP Deploy ---
    log_step(2, total_steps, "SCP Deploy")

    if args.dry_run:
        log_info(f"[DRY RUN] scp {local_file} {VPS_HOST}:{VPS_WWW}/{remote_path}")
        summary.append(("SCP Deploy", "SKIP", "dry-run"))
    else:
        success, detail = deploy_scp(local_file, remote_path)
        if success:
            log_ok(f"Deployed to {detail}")
            summary.append(("SCP Deploy", "PASS", remote_path))
        else:
            log_err(f"SCP failed: {detail}")
            summary.append(("SCP Deploy", "FAIL", detail[:40]))
            print_summary(summary)
            return 1

    # --- Step 3: Post-deploy checks ---
    log_step(3, total_steps, "Post-deploy verification")

    if args.dry_run:
        log_info(f"[DRY RUN] curl -sI {deploy_url}")
        urls = extract_urls_from_html(local_file)
        log_info(f"[DRY RUN] Would check {len(urls)} extracted URLs (max {MAX_URL_CHECKS})")
        summary.append(("Page check", "SKIP", "dry-run"))
        summary.append(("URL sampling", "SKIP", f"{len(urls)} URLs found"))
    else:
        # Check the deployed page itself
        code, status = check_url_status(deploy_url)
        if code == 200:
            log_ok(f"Page accessible: {deploy_url} -> {code}")
            summary.append(("Page check", "PASS", f"HTTP {code}"))
        else:
            log_warn(f"Page check: {deploy_url} -> {status}")
            summary.append(("Page check", "FAIL", status))

        # Extract and check URLs from HTML
        urls = extract_urls_from_html(local_file)
        if urls:
            sample = urls if len(urls) <= MAX_URL_CHECKS else random.sample(urls, MAX_URL_CHECKS)
            log_info(f"Checking {len(sample)}/{len(urls)} URLs from HTML...")

            ok_count = 0
            fail_count = 0
            for url in sample:
                url_code, url_status = check_url_status(url)
                short_url = url[:60] + "..." if len(url) > 60 else url
                if url_code == 200:
                    log_ok(f"  {short_url}")
                    ok_count += 1
                else:
                    log_warn(f"  {short_url} -> {url_status}")
                    fail_count += 1

            status_text = f"{ok_count} ok, {fail_count} fail"
            summary.append(("URL sampling", "PASS" if fail_count == 0 else "WARN", status_text))
        else:
            log_info("No external URLs found in HTML")
            summary.append(("URL sampling", "PASS", "no URLs"))

    print_summary(summary)

    # Final verdict
    has_fail = any(s[1] == "FAIL" for s in summary)
    if has_fail:
        log_err("Deploy completed with errors.")
        return 1

    log_ok(f"Deploy successful: {deploy_url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
