#!/usr/bin/env python3
"""
parse_dom.py — DOM extraction from a single HTML file/string.

Extracts:
- H1, H2 cascade with word counts per H2 section
- H3 nesting (count per H2)
- Total word count + intro length (first paragraph after H1)
- Image count + alt-density
- FAQ block presence (FAQPage schema OR <details>/accordion patterns)
- Schema.org JSON-LD types
- External/internal links count

Input:  --html <file.html>  OR  --url <url>  (via WebFetch externally)
Output: JSON to --out <file.json>  (stdout if not provided)

Usage:
    python3 parse_dom.py --html article.html --out section-1.json
    python3 parse_dom.py --html article.html             # stdout
    cat article.html | python3 parse_dom.py --stdin      # pipe

Tested with BeautifulSoup 4.14 (already installed system-wide).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    from bs4 import BeautifulSoup, Tag
except ImportError:
    sys.stderr.write("ERROR: BeautifulSoup4 not installed. Run: pip3 install beautifulsoup4\n")
    sys.exit(2)


WORD_RE = re.compile(r"\b[\w\-']+\b", re.UNICODE)


def count_words(text: str) -> int:
    """Count words (Unicode-aware, supports Cyrillic)."""
    if not text:
        return 0
    return len(WORD_RE.findall(text))


def text_until_next_heading(start_tag: Tag, stop_levels: tuple[str, ...] = ("h2", "h1")) -> str:
    """Collect text from siblings of start_tag until next heading at stop_levels."""
    chunks: list[str] = []
    for sibling in start_tag.find_all_next():
        if isinstance(sibling, Tag) and sibling.name in stop_levels:
            break
        if isinstance(sibling, Tag) and sibling.name in ("script", "style", "noscript"):
            continue
        # Only direct text inside this sibling (no recursion into next heading section)
        if isinstance(sibling, Tag) and sibling.name not in ("h2", "h3", "h4", "h5", "h6"):
            text = sibling.get_text(" ", strip=True)
            if text:
                chunks.append(text)
    return " ".join(chunks)


def extract_jsonld_types(soup: BeautifulSoup) -> list[str]:
    """Extract @type values from all JSON-LD blocks."""
    types: list[str] = []
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.get_text()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            continue
        # Can be dict, list, or @graph
        candidates = []
        if isinstance(data, list):
            candidates = data
        elif isinstance(data, dict):
            if "@graph" in data and isinstance(data["@graph"], list):
                candidates = data["@graph"]
            else:
                candidates = [data]
        for item in candidates:
            if isinstance(item, dict):
                t = item.get("@type")
                if isinstance(t, str):
                    types.append(t)
                elif isinstance(t, list):
                    types.extend(x for x in t if isinstance(x, str))
    # Dedupe, preserve order
    seen: set[str] = set()
    unique = []
    for t in types:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique


def detect_faq(soup: BeautifulSoup, schemas: list[str]) -> dict[str, Any]:
    """Detect FAQ presence via schema OR DOM patterns."""
    has_faq_schema = "FAQPage" in schemas

    # DOM patterns: <details>, classes containing 'faq'/'accordion', itemtype FAQPage
    details = soup.find_all("details")
    faq_classes = soup.find_all(class_=re.compile(r"faq|accordion|qa-item|question", re.I))
    itemtype_faq = soup.find_all(attrs={"itemtype": re.compile(r"FAQPage|Question", re.I)})

    has_dom_faq = bool(details) or len(faq_classes) >= 3 or bool(itemtype_faq)

    # Count distinct questions
    question_count = 0
    if has_faq_schema:
        # Try to count Question entries in JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
            except (json.JSONDecodeError, ValueError, TypeError):
                continue
            items = data if isinstance(data, list) else [data]
            for d in items:
                if isinstance(d, dict) and d.get("@type") == "FAQPage":
                    main = d.get("mainEntity", [])
                    if isinstance(main, list):
                        question_count = max(question_count, len(main))
    if not question_count:
        question_count = len(details) or len(faq_classes)

    return {
        "present": has_faq_schema or has_dom_faq,
        "via_schema": has_faq_schema,
        "via_dom": has_dom_faq,
        "question_count": question_count,
    }


def extract_h2_sections(soup: BeautifulSoup) -> list[dict[str, Any]]:
    """Extract H2 sections with word count + H3 count per section."""
    sections: list[dict[str, Any]] = []
    h2s = soup.find_all("h2")
    for h2 in h2s:
        title = h2.get_text(" ", strip=True)
        if not title:
            continue
        # Collect text until next H2 (or H1)
        body_text = text_until_next_heading(h2, stop_levels=("h2", "h1"))
        word_count = count_words(body_text)

        # Count H3 between this H2 and next H2
        h3_count = 0
        has_image = False
        for sibling in h2.find_all_next():
            if isinstance(sibling, Tag) and sibling.name in ("h2", "h1"):
                break
            if isinstance(sibling, Tag):
                if sibling.name == "h3":
                    h3_count += 1
                if sibling.name == "img":
                    has_image = True

        sections.append({
            "h2": title,
            "word_count": word_count,
            "h3_count": h3_count,
            "has_image": has_image,
        })
    return sections


def extract_intro_length(soup: BeautifulSoup) -> int:
    """Word count of text between H1 and first H2."""
    h1 = soup.find("h1")
    if not h1:
        # Fallback: first <p> in <body>
        body = soup.find("body") or soup
        first_p = body.find("p")
        return count_words(first_p.get_text(" ", strip=True)) if first_p else 0
    intro_text = text_until_next_heading(h1, stop_levels=("h2",))
    return count_words(intro_text)


def extract_links(soup: BeautifulSoup, base_host: str | None = None) -> dict[str, int]:
    """Count internal vs external links."""
    internal = 0
    external = 0
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue
        if href.startswith("/") or href.startswith("./") or href.startswith("../"):
            internal += 1
            continue
        try:
            parsed = urlparse(href)
        except ValueError:
            continue
        if not parsed.netloc:
            internal += 1
            continue
        if base_host and parsed.netloc.replace("www.", "") == base_host.replace("www.", ""):
            internal += 1
        else:
            external += 1
    return {"internal": internal, "external": external}


def extract_images(soup: BeautifulSoup) -> dict[str, Any]:
    """Image count + alt-density."""
    imgs = soup.find_all("img")
    total = len(imgs)
    with_alt = sum(1 for img in imgs if img.get("alt", "").strip())
    return {
        "total": total,
        "with_alt": with_alt,
        "alt_density": round(with_alt / total, 2) if total else 0.0,
    }


def analyze_html(html: str, source_url: str | None = None) -> dict[str, Any]:
    """Main analysis entry point."""
    # Strip scripts/styles before word counting (keep ld+json scripts for schemas)
    soup = BeautifulSoup(html, "html.parser")

    # Save JSON-LD before stripping
    schemas = extract_jsonld_types(soup)

    # Strip noise tags (but keep structure)
    for tag in soup.find_all(["style", "noscript"]):
        tag.decompose()
    # Keep <script type="application/ld+json"> already extracted; remove others
    for tag in soup.find_all("script"):
        if tag.get("type") != "application/ld+json":
            tag.decompose()

    h1_tag = soup.find("h1")
    h1_text = h1_tag.get_text(" ", strip=True) if h1_tag else ""

    title_tag = soup.find("title")
    title = title_tag.get_text(" ", strip=True) if title_tag else ""

    sections = extract_h2_sections(soup)
    intro_words = extract_intro_length(soup)

    # Total word count from <body>
    body = soup.find("body") or soup
    total_words = count_words(body.get_text(" ", strip=True))

    base_host = None
    if source_url:
        try:
            base_host = urlparse(source_url).netloc
        except ValueError:
            pass

    return {
        "source_url": source_url,
        "title": title,
        "h1": h1_text,
        "total_word_count": total_words,
        "intro_word_count": intro_words,
        "h2_count": len(sections),
        "h3_count_total": sum(s["h3_count"] for s in sections),
        "sections": sections,
        "images": extract_images(soup),
        "links": extract_links(soup, base_host=base_host),
        "schemas": schemas,
        "faq": detect_faq(soup, schemas),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Parse HTML and extract SEO structure (H1/H2/H3, word count, images, FAQ, schemas)."
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--html", type=str, help="Path to HTML file")
    src.add_argument("--stdin", action="store_true", help="Read HTML from stdin")

    parser.add_argument("--url", type=str, default=None, help="Source URL (for link classification)")
    parser.add_argument("--out", type=str, default=None, help="Output JSON path (default: stdout)")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")

    args = parser.parse_args()

    if args.html:
        path = Path(args.html).expanduser()
        if not path.exists():
            sys.stderr.write(f"ERROR: file not found: {path}\n")
            return 2
        html = path.read_text(encoding="utf-8", errors="replace")
    else:
        html = sys.stdin.read()

    if not html.strip():
        sys.stderr.write("ERROR: empty HTML input\n")
        return 2

    result = analyze_html(html, source_url=args.url)

    indent = 2 if args.pretty else None
    out_json = json.dumps(result, ensure_ascii=False, indent=indent)

    if args.out:
        out_path = Path(args.out).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(out_json, encoding="utf-8")
        sys.stderr.write(f"OK: wrote {out_path} ({len(out_json)} chars)\n")
    else:
        print(out_json)

    return 0


if __name__ == "__main__":
    sys.exit(main())
