#!/usr/bin/env python3
"""
post-deploy-curl.py — проверка всех ресурсов HTML после деплоя.

Использование:
    python3 post-deploy-curl.py <html_file_or_url> [--base BASE_URL] [--max-fail 5]

Выходные коды:
    0 — все ресурсы доступны
    1 — превышен порог FAIL (по умолчанию 5)
    2 — ошибка парсинга/сети

Проверяет href/src/action в:
    <a>, <img>, <link>, <script>, <source>, <iframe>, <form>
"""
from __future__ import annotations

import argparse
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

URL_ATTR_PATTERN = re.compile(
    r'(?:href|src|action|data-src)\s*=\s*["\']([^"\']+)["\']',
    re.IGNORECASE,
)

SKIP_SCHEMES = {"mailto", "tel", "javascript", "data", "sms", "#"}


def extract_urls(html: str, base: str | None) -> list[str]:
    urls = set()
    for match in URL_ATTR_PATTERN.finditer(html):
        raw = match.group(1).strip()
        if not raw or raw.startswith("#"):
            continue
        scheme = raw.split(":", 1)[0].lower() if ":" in raw else ""
        if scheme in SKIP_SCHEMES:
            continue
        if raw.startswith("//"):
            raw = "https:" + raw
        if not raw.startswith(("http://", "https://")):
            if not base:
                continue
            raw = urljoin(base, raw)
        urls.add(raw)
    return sorted(urls)


def check_url(url: str, timeout: int = 10) -> tuple[str, int, str]:
    try:
        req = Request(url, method="HEAD", headers={"User-Agent": "combine-post-deploy/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            return (url, resp.status, "")
    except HTTPError as exc:
        if exc.code in (405, 501):
            try:
                req = Request(url, method="GET", headers={"User-Agent": "combine-post-deploy/1.0"})
                with urlopen(req, timeout=timeout) as resp:
                    return (url, resp.status, "")
            except Exception as e2:
                return (url, 0, f"{type(e2).__name__}: {e2}")
        return (url, exc.code, exc.reason or "")
    except URLError as exc:
        return (url, 0, f"URLError: {exc.reason}")
    except Exception as exc:
        return (url, 0, f"{type(exc).__name__}: {exc}")


def load_html(source: str) -> tuple[str, str | None]:
    if source.startswith(("http://", "https://")):
        req = Request(source, headers={"User-Agent": "combine-post-deploy/1.0"})
        with urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace"), source
    path = Path(source)
    if not path.exists():
        print(f"ERROR: file not found: {source}", file=sys.stderr)
        sys.exit(2)
    return path.read_text(encoding="utf-8", errors="replace"), None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="HTML file path or URL")
    ap.add_argument("--base", help="Base URL for relative links (required for file input)")
    ap.add_argument("--max-fail", type=int, default=5, help="Fail threshold (default 5)")
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    html, auto_base = load_html(args.source)
    base = args.base or auto_base

    urls = extract_urls(html, base)
    if not args.quiet:
        print(f"[post-deploy-curl] Found {len(urls)} URLs to check", file=sys.stderr)

    if not urls:
        return 0

    fails: list[tuple[str, int, str]] = []
    passes = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(check_url, u): u for u in urls}
        for fut in as_completed(futures):
            url, code, err = fut.result()
            ok = 200 <= code < 400
            if ok:
                passes += 1
                if not args.quiet:
                    print(f"  OK  {code} {url}")
            else:
                fails.append((url, code, err))
                print(f"  FAIL {code or '---'} {url} {err}", file=sys.stderr)

    print(
        f"[post-deploy-curl] PASS={passes} FAIL={len(fails)} "
        f"threshold={args.max_fail}",
        file=sys.stderr,
    )

    if len(fails) >= args.max_fail:
        print("VERDICT: FAIL — rollback recommended", file=sys.stderr)
        return 1
    if fails:
        print("VERDICT: WARNING — some resources failed, review manually", file=sys.stderr)
    else:
        print("VERDICT: PASS", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
