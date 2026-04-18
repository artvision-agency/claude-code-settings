#!/usr/bin/env python3
"""Dashboard Builder -- scaffolding tool for multi-screen client dashboards.

Automates the workflow: template -> data injection -> factcheck -> deploy -> index.

Usage examples:
    # List existing screens for a client
    dashboard-builder.py --client mirbir --list

    # Build a new screen from data file
    dashboard-builder.py -c mirbir -s 1 --title "Overview" --data-file data.json

    # Build with custom template
    dashboard-builder.py -c mirbir -s 2 --title "Competitors" --template custom.html

    # Build and deploy
    dashboard-builder.py -c mirbir -s 3 --title "Traffic" --data-file traffic.json --deploy

Base path: /Users/antonk/artvision-data/
VPS deploy: via deploy_pages.py (scp to artvision.pro)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_PATH = Path("/Users/antonk/artvision-data")
CLIENTS_DIR = BASE_PATH / "clients"
FACTCHECK_SCRIPT = Path("/Users/antonk/.claude/scripts/factcheck-v2.py")
DEPLOY_SCRIPT = BASE_PATH / "scripts" / "deploy_pages.py"


# ---------------------------------------------------------------------------
# Built-in minimal template (dark theme, responsive)
# ---------------------------------------------------------------------------

BUILTIN_TEMPLATE = """\
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<title>{{TITLE}} -- {{CLIENT}}</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0f1117;--surface:#1a1d27;--surface2:#242836;
  --border:#2d3348;--text:#e4e6f0;--text-muted:#8b8fa3;
  --accent:#6366f1;--accent-light:#818cf8;--success:#22c55e;
  --warning:#f59e0b;--danger:#ef4444;
  --radius:12px;--shadow:0 4px 24px rgba(0,0,0,.35);
}
html{font-size:16px;scroll-behavior:smooth}
body{
  font-family:'Inter','Segoe UI',system-ui,-apple-system,sans-serif;
  background:var(--bg);color:var(--text);
  line-height:1.6;min-height:100vh;
}
a{color:var(--accent-light);text-decoration:none}
a:hover{text-decoration:underline}

/* --- Header --- */
.dash-header{
  background:var(--surface);border-bottom:1px solid var(--border);
  padding:1.25rem 2rem;display:flex;align-items:center;
  justify-content:space-between;flex-wrap:wrap;gap:1rem;
}
.dash-header h1{font-size:1.35rem;font-weight:700;letter-spacing:-.02em}
.dash-header .meta{color:var(--text-muted);font-size:.85rem}

/* --- Navigation --- */
.dash-nav{
  background:var(--surface);border-bottom:1px solid var(--border);
  padding:.6rem 2rem;display:flex;gap:.5rem;flex-wrap:wrap;
  overflow-x:auto;
}
.dash-nav a{
  padding:.4rem .9rem;border-radius:6px;font-size:.85rem;
  color:var(--text-muted);transition:all .15s;white-space:nowrap;
}
.dash-nav a:hover,.dash-nav a.active{
  background:var(--accent);color:#fff;text-decoration:none;
}

/* --- Content area --- */
.dash-content{
  max-width:1280px;margin:0 auto;padding:2rem;
}

/* --- Cards & sections --- */
.card{
  background:var(--surface);border:1px solid var(--border);
  border-radius:var(--radius);padding:1.5rem;margin-bottom:1.5rem;
  box-shadow:var(--shadow);
}
.card h2{font-size:1.15rem;margin-bottom:1rem;color:var(--accent-light)}
.card h3{font-size:1rem;margin-bottom:.75rem;color:var(--text)}

/* --- Tables --- */
table{width:100%;border-collapse:collapse;font-size:.9rem}
th,td{padding:.65rem .9rem;text-align:left;border-bottom:1px solid var(--border)}
th{color:var(--text-muted);font-weight:600;font-size:.8rem;text-transform:uppercase;letter-spacing:.04em}
tr:hover td{background:var(--surface2)}

/* --- KPI row --- */
.kpi-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem;margin-bottom:1.5rem}
.kpi{
  background:var(--surface2);border-radius:var(--radius);padding:1.25rem;
  text-align:center;border:1px solid var(--border);
}
.kpi .value{font-size:1.8rem;font-weight:700;color:var(--accent-light)}
.kpi .label{font-size:.8rem;color:var(--text-muted);margin-top:.25rem}

/* --- Footer --- */
.dash-footer{
  text-align:center;padding:2rem;color:var(--text-muted);
  font-size:.75rem;border-top:1px solid var(--border);margin-top:2rem;
}

/* --- Responsive --- */
@media(max-width:768px){
  .dash-header{padding:1rem}
  .dash-content{padding:1rem}
  .dash-nav{padding:.5rem 1rem}
  .kpi-row{grid-template-columns:repeat(auto-fit,minmax(140px,1fr))}
  .kpi .value{font-size:1.4rem}
}
@media(max-width:480px){
  .kpi-row{grid-template-columns:1fr 1fr}
}
</style>
</head>
<body>

<header class="dash-header">
  <div>
    <h1>{{TITLE}}</h1>
    <div class="meta">{{CLIENT}} &middot; {{DATE}}</div>
  </div>
  <div class="meta">Artvision Agency</div>
</header>

<nav class="dash-nav">
{{NAV}}
</nav>

<main class="dash-content">
{{CONTENT}}
</main>

<footer class="dash-footer">
  &copy; {{YEAR}} Artvision Agency &middot; artvision.pro &middot; Dashboard powered by Artvision Flow
</footer>

</body>
</html>
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def dashboards_dir(client: str) -> Path:
    """Return the dashboards directory for a client."""
    return CLIENTS_DIR / client / "dashboards"


def discover_screens(client: str) -> list[Path]:
    """Find all screen-*.html files for a client, sorted by number."""
    ddir = dashboards_dir(client)
    if not ddir.exists():
        return []
    screens = sorted(ddir.glob("screen-*.html"))
    return screens


def extract_screen_title(path: Path) -> str:
    """Extract <title> content from an HTML file."""
    try:
        text = path.read_text(encoding="utf-8")
        match = re.search(r"<title>(.*?)</title>", text, re.IGNORECASE)
        if match:
            title = match.group(1).split(" -- ")[0].strip()
            return title
    except OSError:
        pass
    return path.stem


def extract_screen_number(path: Path) -> str:
    """Extract screen number from filename like screen-3.html."""
    match = re.search(r"screen-(\w+)", path.stem)
    return match.group(1) if match else path.stem


def build_nav_html(screens: list[Path], active_screen: str | None = None) -> str:
    """Build navigation links for all screens."""
    if not screens:
        return '  <a href="index.html" class="active">Index</a>'
    lines: list[str] = ['  <a href="index.html">Index</a>']
    for screen_path in screens:
        num = extract_screen_number(screen_path)
        title = extract_screen_title(screen_path)
        filename = screen_path.name
        css_class = ' class="active"' if num == active_screen else ""
        lines.append(f'  <a href="{filename}"{css_class}>{title}</a>')
    return "\n".join(lines)


def render_template(
    template: str,
    *,
    title: str,
    client: str,
    content: str,
    nav: str,
    date: str | None = None,
) -> str:
    """Replace placeholders in template with actual values."""
    now = datetime.now()
    replacements: dict[str, str] = {
        "{{TITLE}}": title,
        "{{CLIENT}}": client,
        "{{DATE}}": date or now.strftime("%d.%m.%Y"),
        "{{YEAR}}": str(now.year),
        "{{NAV}}": nav,
        "{{CONTENT}}": content,
    }
    result = template
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)
    return result


def data_to_content(data: dict[str, Any]) -> str:
    """Convert a JSON data structure into HTML content sections.

    Supports these top-level keys in the JSON:
      - kpis: list of {value, label} dicts -> KPI cards row
      - sections: list of {title, type, ...} dicts:
          type="table" -> {headers: [...], rows: [[...]]}
          type="text"  -> {text: "..."}
          type="html"  -> {html: "..."} (raw HTML)
          type="list"  -> {items: ["..."]}
      - content: raw HTML string (fallback)

    Args:
        data: Parsed JSON data dictionary.

    Returns:
        HTML string for the content area.
    """
    parts: list[str] = []

    # KPIs
    kpis = data.get("kpis")
    if kpis and isinstance(kpis, list):
        parts.append('<div class="kpi-row">')
        for kpi in kpis:
            value = kpi.get("value", "---")
            label = kpi.get("label", "")
            parts.append(
                f'  <div class="kpi">\n'
                f'    <div class="value">{value}</div>\n'
                f'    <div class="label">{label}</div>\n'
                f'  </div>'
            )
        parts.append("</div>")

    # Sections
    sections = data.get("sections")
    if sections and isinstance(sections, list):
        for section in sections:
            sec_title = section.get("title", "")
            sec_type = section.get("type", "text")
            parts.append('<div class="card">')
            if sec_title:
                parts.append(f"  <h2>{sec_title}</h2>")

            if sec_type == "table":
                headers = section.get("headers", [])
                rows = section.get("rows", [])
                parts.append("  <table>")
                if headers:
                    parts.append("    <thead><tr>")
                    for h in headers:
                        parts.append(f"      <th>{h}</th>")
                    parts.append("    </tr></thead>")
                parts.append("    <tbody>")
                for row in rows:
                    parts.append("    <tr>")
                    for cell in row:
                        parts.append(f"      <td>{cell}</td>")
                    parts.append("    </tr>")
                parts.append("    </tbody>")
                parts.append("  </table>")

            elif sec_type == "html":
                parts.append(f'  {section.get("html", "")}')

            elif sec_type == "list":
                items = section.get("items", [])
                parts.append("  <ul>")
                for item in items:
                    parts.append(f"    <li>{item}</li>")
                parts.append("  </ul>")

            else:  # text
                text = section.get("text", "")
                parts.append(f"  <p>{text}</p>")

            parts.append("</div>")

    # Fallback: raw content key
    raw_content = data.get("content")
    if raw_content and isinstance(raw_content, str):
        parts.append(f'<div class="card">\n  {raw_content}\n</div>')

    if not parts:
        parts.append(
            '<div class="card">\n'
            "  <h2>Content placeholder</h2>\n"
            "  <p>Replace this section with dashboard data.</p>\n"
            "</div>"
        )

    return "\n\n".join(parts)


def build_index(client: str) -> Path:
    """Scan screen files and build/update index.html."""
    ddir = dashboards_dir(client)
    screens = discover_screens(client)
    nav = build_nav_html(screens)
    now = datetime.now()

    items_html: list[str] = []
    for screen_path in screens:
        num = extract_screen_number(screen_path)
        title = extract_screen_title(screen_path)
        size_kb = screen_path.stat().st_size / 1024
        mtime = datetime.fromtimestamp(screen_path.stat().st_mtime).strftime(
            "%d.%m.%Y %H:%M"
        )
        items_html.append(
            f"    <tr>\n"
            f'      <td><a href="{screen_path.name}">{num}</a></td>\n'
            f'      <td><a href="{screen_path.name}">{title}</a></td>\n'
            f"      <td>{size_kb:.1f} KB</td>\n"
            f"      <td>{mtime}</td>\n"
            f"    </tr>"
        )

    content = (
        '<div class="card">\n'
        f"  <h2>Dashboard Screens ({len(screens)})</h2>\n"
        "  <table>\n"
        "    <thead><tr>\n"
        "      <th>#</th><th>Screen</th><th>Size</th><th>Updated</th>\n"
        "    </tr></thead>\n"
        "    <tbody>\n"
        + "\n".join(items_html)
        + "\n    </tbody>\n"
        "  </table>\n"
        "</div>"
    )

    if not items_html:
        content = (
            '<div class="card">\n'
            "  <h2>No screens yet</h2>\n"
            "  <p>Use <code>dashboard-builder.py -c "
            f'{client} -s 1 --title "..."</code> to create the first screen.</p>\n'
            "</div>"
        )

    index_html = render_template(
        BUILTIN_TEMPLATE,
        title="Dashboard Index",
        client=client,
        content=content,
        nav=nav.replace(' class="active"', ""),
        date=now.strftime("%d.%m.%Y"),
    )

    index_path = ddir / "index.html"
    index_path.write_text(index_html, encoding="utf-8")
    return index_path


def run_factcheck(html_path: Path) -> int:
    """Run factcheck-v2.py on the generated HTML. Returns exit code."""
    if not FACTCHECK_SCRIPT.exists():
        print(f"[WARN] factcheck script not found: {FACTCHECK_SCRIPT}")
        return 0
    print(f"\n--- Running factcheck on {html_path.name} ---")
    result = subprocess.run(
        [sys.executable, str(FACTCHECK_SCRIPT), str(html_path), "--quick"],
        capture_output=False,
    )
    return result.returncode


def run_deploy(client: str, html_path: Path) -> int:
    """Deploy via deploy_pages.py scp."""
    if not DEPLOY_SCRIPT.exists():
        print(f"[ERROR] deploy script not found: {DEPLOY_SCRIPT}")
        return 1
    remote_path = f"{client}-dashboard/"
    print(f"\n--- Deploying {html_path.name} to {remote_path} ---")
    result = subprocess.run(
        [
            sys.executable,
            str(DEPLOY_SCRIPT),
            "scp",
            str(html_path),
            "--remote-path",
            remote_path,
            "--execute",
        ],
        capture_output=False,
    )
    return result.returncode


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Build multi-screen client dashboard HTML pages.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s -c mirbir --list\n"
            "  %(prog)s -c mirbir -s 1 --title 'Overview'\n"
            '  %(prog)s -c mirbir -s 2 --title "Competitors" '
            "--data-file competitors.json\n"
            "  %(prog)s -c mirbir -s 3 --title Traffic --deploy\n"
        ),
    )
    parser.add_argument(
        "-c", "--client", required=True,
        help="Client folder name (e.g. mirbir, raduga)",
    )
    parser.add_argument(
        "-s", "--screen", help="Screen number or name (e.g. 1, overview)"
    )
    parser.add_argument("--title", help="Screen title")
    parser.add_argument(
        "--template",
        help="Path to HTML template (default: clients/<client>/dashboards/template.html)",
    )
    parser.add_argument("--data-file", help="JSON file with data for the screen")
    parser.add_argument(
        "--deploy", action="store_true", help="Deploy to VPS after build",
    )
    parser.add_argument(
        "--list", action="store_true", help="List existing screens for client",
    )
    parser.add_argument(
        "--no-factcheck", action="store_true", help="Skip factcheck step",
    )
    parser.add_argument(
        "--index-only", action="store_true",
        help="Only rebuild index.html, do not create a screen",
    )
    return parser.parse_args()


def cmd_list(client: str) -> None:
    """List existing screens for a client."""
    screens = discover_screens(client)
    ddir = dashboards_dir(client)
    if not screens:
        print(f"No screens found for '{client}' in {ddir}")
        return
    print(f"Dashboard screens for '{client}' ({ddir}):\n")
    print(f"  {'#':<6} {'Title':<40} {'Size':>8}  {'Updated'}")
    print(f"  {'---':<6} {'---':<40} {'---':>8}  {'---'}")
    for path in screens:
        num = extract_screen_number(path)
        title = extract_screen_title(path)
        size_kb = path.stat().st_size / 1024
        mtime = datetime.fromtimestamp(path.stat().st_mtime).strftime(
            "%d.%m.%Y %H:%M"
        )
        print(f"  {num:<6} {title:<40} {size_kb:>6.1f}KB  {mtime}")
    index = ddir / "index.html"
    if index.exists():
        print(f"\n  Index: {index}")


def cmd_build(args: argparse.Namespace) -> int:
    """Build a screen HTML file. Returns 0 on success, 1 on failure."""
    client = args.client
    screen = args.screen
    title = args.title or f"Screen {screen}"
    ddir = dashboards_dir(client)

    # Ensure directory exists
    ddir.mkdir(parents=True, exist_ok=True)

    # Resolve template
    template_text: str
    if args.template:
        tpl_path = Path(args.template)
        if not tpl_path.is_absolute():
            tpl_path = BASE_PATH / tpl_path
        if not tpl_path.exists():
            print(f"[ERROR] Template not found: {tpl_path}")
            return 1
        template_text = tpl_path.read_text(encoding="utf-8")
    else:
        client_tpl = ddir / "template.html"
        if client_tpl.exists():
            template_text = client_tpl.read_text(encoding="utf-8")
            print(f"Using client template: {client_tpl}")
        else:
            template_text = BUILTIN_TEMPLATE
            print("Using built-in template")

    # Load data
    content_html = ""
    if args.data_file:
        data_path = Path(args.data_file)
        if not data_path.is_absolute():
            data_path = BASE_PATH / data_path
        if not data_path.exists():
            print(f"[ERROR] Data file not found: {data_path}")
            return 1
        try:
            with open(data_path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[ERROR] Failed to read data file: {exc}")
            return 1
        content_html = data_to_content(data)
    else:
        content_html = (
            '<div class="card">\n'
            f"  <h2>{title}</h2>\n"
            "  <p>Content placeholder -- replace with actual data.</p>\n"
            "</div>"
        )

    # Discover existing screens for nav (include the one being built)
    existing_screens = discover_screens(client)
    output_path = ddir / f"screen-{screen}.html"

    # Build nav (temporarily include new screen if not yet on disk)
    temp_screens = list(existing_screens)
    if output_path not in temp_screens:
        temp_screens.append(output_path)
        temp_screens.sort()

    nav_html = build_nav_html(temp_screens, active_screen=str(screen))

    # Render
    final_html = render_template(
        template_text,
        title=title,
        client=client,
        content=content_html,
        nav=nav_html,
    )

    # Write output
    output_path.write_text(final_html, encoding="utf-8")
    size_kb = output_path.stat().st_size / 1024
    print(f"\n[OK] Built: {output_path} ({size_kb:.1f} KB)")

    # Factcheck
    if not args.no_factcheck:
        fc_code = run_factcheck(output_path)
        if fc_code != 0:
            print("[WARN] Factcheck found issues. Fix before deploying.")

    # Update index
    index_path = build_index(client)
    print(f"[OK] Index updated: {index_path}")

    # Deploy
    if args.deploy:
        deploy_code = run_deploy(client, output_path)
        if deploy_code != 0:
            print("[ERROR] Deploy failed for screen file")
            return 1
        deploy_code = run_deploy(client, index_path)
        if deploy_code != 0:
            print("[ERROR] Deploy failed for index")
            return 1
        print(f"[OK] Deployed to https://artvision.pro/{client}-dashboard/")

    return 0


def main() -> int:
    """Entry point."""
    args = parse_args()

    # Validate client dir exists (or will be created)
    client_dir = CLIENTS_DIR / args.client
    if not client_dir.exists():
        print(f"[WARN] Client directory does not exist: {client_dir}")
        print("       It will be created on build.")

    if args.list:
        cmd_list(args.client)
        return 0

    if args.index_only:
        ddir = dashboards_dir(args.client)
        if not ddir.exists():
            print(f"[ERROR] No dashboards dir: {ddir}")
            return 1
        index_path = build_index(args.client)
        print(f"[OK] Index rebuilt: {index_path}")
        return 0

    if not args.screen:
        print("[ERROR] --screen is required for building. Use --list to see existing.")
        return 1

    return cmd_build(args)


if __name__ == "__main__":
    sys.exit(main())
