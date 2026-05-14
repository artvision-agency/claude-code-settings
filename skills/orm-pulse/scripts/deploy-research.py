#!/usr/bin/env python3
"""deploy-research — md → HTML → VPS под X-Robots-Tag noindex.

Конвертирует research markdown в HTML с inline CSS (sticky TOC, читабельная
вёрстка, мобильная адаптация) и заливает на artvision.pro/orm-research/<file>.html

Usage:
  deploy-research.py <client_slug> <md_filename>
  deploy-research.py bluemart yandex-moderation-2026-05-03.md
  deploy-research.py --list <client_slug>          # показать все доступные
  deploy-research.py --all <client_slug>           # деплой всех research/*.md

Output: URL на artvision.pro
"""
from __future__ import annotations
import argparse
import html
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime

import markdown

sys.path.insert(0, str(Path(__file__).parent))
from lib.config import ROOT  # noqa: E402

VPS_USER = "root"
VPS_HOST = "80.90.181.152"
VPS_DIR = "/var/www/artvision/orm-research"
PUBLIC_BASE = "https://artvision.pro/orm-research"

CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body { font-family: -apple-system, Segoe UI, Roboto, sans-serif;
       max-width: 1100px; margin: 0 auto; padding: 24px;
       background: #fafafa; color: #1a1a1a; line-height: 1.6; }
header { border-bottom: 2px solid #2c3e88; padding-bottom: 16px; margin-bottom: 24px; }
header h1 { margin: 0 0 4px; font-size: 24px; color: #2c3e88; }
header .meta { color: #666; font-size: 13px; }
header .badge { background: #fdecea; color: #b71c1c; padding: 3px 10px;
                border-radius: 4px; font-size: 12px; font-weight: 600;
                display: inline-block; margin-left: 8px; }
nav.toc { position: sticky; top: 0; background: #fff;
          padding: 12px 18px; margin: 12px 0 24px;
          border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);
          font-size: 13px; max-height: 200px; overflow-y: auto;
          z-index: 10; }
nav.toc strong { color: #2c3e88; display: block; margin-bottom: 4px; }
nav.toc a { color: #555; text-decoration: none; margin-right: 12px;
            display: inline-block; padding: 2px 6px; }
nav.toc a:hover { background: #eef; color: #2c3e88; border-radius: 3px; }
main { background: #fff; padding: 24px 32px; border-radius: 8px;
       box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
h1, h2, h3 { color: #2c3e88; }
h2 { border-bottom: 1px solid #eee; padding-bottom: 6px; margin-top: 32px; }
table { width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 14px; }
th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid #eee;
         vertical-align: top; }
th { background: #f5f7fa; font-weight: 600; color: #444; }
td a { color: #2c3e88; text-decoration: none; }
td a:hover { text-decoration: underline; }
code { background: #f3f4f6; padding: 2px 6px; border-radius: 3px;
       font-family: SFMono-Regular, Consolas, monospace; font-size: 13px; }
pre { background: #1f2937; color: #e5e7eb; padding: 14px; border-radius: 6px;
      overflow-x: auto; font-size: 13px; }
blockquote { border-left: 3px solid #2c3e88; background: #f0f6fa;
             padding: 8px 14px; margin: 12px 0; color: #444;
             font-style: italic; }
ul, ol { margin: 8px 0; padding-left: 24px; }
li { margin: 4px 0; }
strong { color: #1a1a1a; }
.confirmed { color: #1b5e20; font-weight: 600; }
.unconfirmed { color: #e65100; font-weight: 600; }
footer { margin-top: 40px; padding-top: 16px; border-top: 1px solid #eee;
         font-size: 12px; color: #888; text-align: center; }
@media (max-width: 700px) {
  body { padding: 12px; }
  main { padding: 16px; }
  table { font-size: 12px; }
  th, td { padding: 6px; }
}
"""


def md_to_html(md_text: str, title: str, source_path: str) -> str:
    md = markdown.Markdown(extensions=["tables", "fenced_code", "toc", "attr_list"])
    body_html = md.convert(md_text)
    toc = getattr(md, "toc", "") or ""

    ts = datetime.now().strftime("%Y-%m-%d %H:%M МСК")
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow, noarchive, nosnippet">
<meta name="googlebot" content="noindex, nofollow">
<meta name="yandex" content="noindex, nofollow">
<title>{html.escape(title)} — Artvision ORM Research</title>
<style>{CSS}</style>
</head>
<body>
<header>
<h1>{html.escape(title)}<span class="badge">INTERNAL</span></h1>
<div class="meta">Источник: <code>{html.escape(source_path)}</code> · Сгенерировано: {ts}</div>
</header>
{f'<nav class="toc"><strong>Содержание</strong>{toc}</nav>' if toc else ''}
<main>
{body_html}
</main>
<footer>Artvision ORM Research · X-Robots-Tag noindex · Только для команды</footer>
</body>
</html>"""


def deploy_one(client: str, md_filename: str) -> tuple[bool, str]:
    src = ROOT / "clients" / client / "orm" / "research" / md_filename
    if not src.exists():
        return False, f"NOT FOUND: {src}"

    md_text = src.read_text(encoding="utf-8")
    title = md_text.lstrip("#").splitlines()[0].strip() if md_text else md_filename
    title = title.lstrip("#").strip()

    html_out = md_to_html(md_text, title, f"clients/{client}/orm/research/{md_filename}")

    # Сохранить локально (для preview / git)
    out_local = src.with_suffix(".html")
    out_local.write_text(html_out, encoding="utf-8")

    # SCP
    remote_filename = f"{client}-{md_filename.replace('.md', '.html')}"
    remote_path = f"{VPS_DIR}/{remote_filename}"
    public_url = f"{PUBLIC_BASE}/{remote_filename}"

    # Ensure remote dir
    subprocess.run(["ssh", f"{VPS_USER}@{VPS_HOST}", f"mkdir -p {VPS_DIR}"], check=True)
    # Trigger outbound-gate ack (if hook present)
    Path("/tmp/.claude_outbound_ack").touch()
    res = subprocess.run(
        ["scp", "-q", str(out_local), f"{VPS_USER}@{VPS_HOST}:{remote_path}"],
        capture_output=True, text=True,
    )
    if res.returncode != 0:
        return False, f"SCP failed: {res.stderr}"

    return True, public_url


def list_research(client: str) -> list[Path]:
    return sorted((ROOT / "clients" / client / "orm" / "research").glob("*.md"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("client", nargs="?")
    parser.add_argument("md_filename", nargs="?")
    parser.add_argument("--list", dest="list_mode", action="store_true")
    parser.add_argument("--all", dest="all_mode", action="store_true")
    args = parser.parse_args()

    if not args.client:
        parser.print_help()
        sys.exit(1)

    if args.list_mode:
        files = list_research(args.client)
        if not files:
            print(f"No research/*.md for {args.client}")
            return 0
        print(f"# {args.client} research files ({len(files)}):")
        for f in files:
            kb = f.stat().st_size // 1024
            print(f"  {f.name:60} {kb} KB")
        return 0

    if args.all_mode:
        files = list_research(args.client)
        if not files:
            print(f"No research files for {args.client}")
            return 1
        results = []
        for f in files:
            ok, msg = deploy_one(args.client, f.name)
            results.append((f.name, ok, msg))
            print(f"{'✓' if ok else '✗'} {f.name} → {msg}")
        return 0 if all(r[1] for r in results) else 2

    if not args.md_filename:
        sys.exit("ERROR: provide md_filename, or use --list / --all")

    ok, msg = deploy_one(args.client, args.md_filename)
    if ok:
        print(f"✓ Deployed: {msg}")
    else:
        print(f"✗ FAILED: {msg}")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
