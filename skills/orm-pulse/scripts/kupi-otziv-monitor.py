#!/usr/bin/env python3
"""kupi-otziv-monitor — снапшот аккаунта kupi-otziv.ru через cookie-session.

Что делает:
1. Использует сохранённые cookies (раз настроенная сессия Антона)
2. Pull /kabinet/finance/ + /kabinet/projects/ + /kabinet/notifications/
3. Парсит embedded Pinia stores (Bitrix Vue3 — JS preload)
4. Сохраняет snapshot в clients/<slug>/orm/kupi-otziv/snap-<date>.json

Usage:
  # Setup один раз: сохранить cookies из браузера
  kupi-otziv-monitor.py <client> --setup-cookies <cookies.txt>

  # Pull snapshot (после setup)
  kupi-otziv-monitor.py <client>

Структура snapshot:
  - user: id, name, email, registered
  - balance: value, billing_id
  - billing_history: операции
  - projects: список с briefs
  - orderlist / tasklist
  - notifications

Cookies path: tokens.json/kupi-otziv.cookies_file
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path
from datetime import datetime
from urllib.request import Request, build_opener, HTTPCookieProcessor
from http.cookiejar import MozillaCookieJar
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from lib.config import ROOT  # noqa: E402

TOKENS_PATH = ROOT / "tokens.json"
BASE = "https://kupi-otziv.ru"

# Bitrix-страницы для двухстадийного fetch.
# Из них вытаскиваем <script src="/bitrix/templates/.../*.data.php?...">
# и грузим уже эти api endpoints (с актуальным cache-buster c=...).
PINIA_PAGES = {
    "kabinet": f"{BASE}/kabinet/",
    "kabinet_finance": f"{BASE}/kabinet/finance/",
    "kabinet_projects_planning": f"{BASE}/kabinet/projects/planning/",
    "kabinet_notifications": f"{BASE}/kabinet/notifications/",
    "kabinet_profile": f"{BASE}/kabinet/profile/",
}

# Регулярка для извлечения api-endpoints из HTML
API_SCRIPT_PATTERN = re.compile(
    r'src="(/bitrix/templates/kabinet/components/[^"]+\.(?:data|php)\.php\?[^"]*)"'
)

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15"


def load_kupi_otziv_config() -> dict:
    if not TOKENS_PATH.exists():
        sys.exit("ERROR: tokens.json not found")
    with open(TOKENS_PATH, encoding="utf-8") as f:
        tokens = json.load(f)
    cfg = tokens.get("kupi-otziv") or tokens.get("kupi_otziv") or {}
    if not cfg.get("cookies_file"):
        sys.exit(
            "ERROR: tokens.json missing kupi-otziv.cookies_file\n"
            "Setup: 1) В Safari открыть kupi-otziv.ru/kabinet/, залогиниться\n"
            "       2) Экспортировать cookies в Netscape-формате\n"
            "       3) Сохранить путь в tokens.json под kupi-otziv.cookies_file"
        )
    return cfg


def make_opener(cookies_path: Path):
    cj = MozillaCookieJar(str(cookies_path))
    cj.load(ignore_discard=True, ignore_expires=True)
    opener = build_opener(HTTPCookieProcessor(cj))
    opener.addheaders = [
        ("User-Agent", USER_AGENT),
        ("Accept", "text/html,application/xhtml+xml"),
    ]
    return opener


def fetch(opener, url: str) -> str:
    req = Request(url)
    with opener.open(req, timeout=20) as r:
        return r.read().decode("utf-8", errors="replace")


# Pinia preload — формат `const xxxStoreData = {...}` или `const xxxStoreData = [...]`
# Парсим сбалансированными скобками + json5-relax для одинарных кавычек
def extract_pinia_blocks(html: str) -> dict:
    blocks: dict[str, Any] = {}
    pattern = re.compile(r"const\s+(\w+StoreData)\s*=\s*([\[{])", re.MULTILINE)
    for m in pattern.finditer(html):
        name = m.group(1)
        start = m.end() - 1  # включая открывающую скобку
        depth = 0
        in_str = False
        str_ch = ""
        i = start
        while i < len(html):
            ch = html[i]
            if in_str:
                if ch == "\\":
                    i += 2
                    continue
                if ch == str_ch:
                    in_str = False
            else:
                if ch in "\"'":
                    in_str = True
                    str_ch = ch
                elif ch in "[{":
                    depth += 1
                elif ch in "]}":
                    depth -= 1
                    if depth == 0:
                        snippet = html[start:i + 1]
                        try:
                            value = parse_json5_relaxed(snippet)
                            blocks[name] = value
                        except Exception as e:
                            blocks[name] = {"_parse_error": str(e), "_snippet_head": snippet[:200]}
                        break
            i += 1
    return blocks


def parse_json5_relaxed(s: str) -> Any:
    """Конвертация JS-литерала с одинарными кавычками в JSON.

    Bitrix отдаёт строки в одинарных кавычках. JSON требует двойных.
    Простой подход: replace ' → ", при этом избегая апострофов в значениях.
    Для kupi-otziv формат стабильный — попробуем напрямую.
    """
    # Шаг 1: одинарные → двойные (rough)
    converted = s.replace("'", '"')
    try:
        return json.loads(converted)
    except json.JSONDecodeError:
        # Fallback: ничего не вернёт — строка может содержать апострофы внутри
        # Пробуем регексп для замены key:'value' → "key":"value"
        # Простейший случай: уже почти всё ок после первой замены
        raise


def parse_user(blocks: dict) -> dict:
    u = blocks.get("userStoreData", {})
    if isinstance(u, dict):
        return {
            "id": u.get("ID"),
            "login": u.get("LOGIN"),
            "name": f"{u.get('LAST_NAME', '')} {u.get('NAME', '')}".strip(),
            "email": u.get("EMAIL"),
            "phone": u.get("PHONE_NUMBER"),
            "billing_id": u.get("KABINET_USER_BILLING_ID"),
            "registered_unix": u.get("DATE_REGISTER", 0),
        }
    return {}


def parse_billing(blocks: dict) -> dict:
    b = blocks.get("billingStoreData", {})
    if isinstance(b, dict):
        return {
            "billing_id": b.get("ID"),
            "value_rub": b.get("UF_VALUE", "0.00"),
            "active": b.get("UF_ACTIVE") == "1",
        }
    return {}


def parse_history(blocks: dict) -> list:
    """historyBillingData[] — список операций."""
    h = blocks.get("historyBillingStoreData") or blocks.get("historybillingdata") or []
    if not isinstance(h, list):
        return []
    return [
        {
            "id": x.get("ID"),
            "operation": x.get("UF_OPERATION"),
            "value": x.get("UF_VALUE"),
            "publish_unix": x.get("UF_PUBLISH_DATE"),
            "project_id": x.get("UF_PROJECT_ID"),
            "task_id": x.get("UF_TASK_ID"),
        }
        for x in h
    ]


def parse_projects(blocks: dict) -> list:
    """briefListStoreData — список проектов."""
    p = blocks.get("briefListStoreData") or []
    if not isinstance(p, list):
        return []
    return [
        {
            "id": x.get("ID"),
            "name": x.get("UF_NAME"),
            "ext_key": x.get("UF_EXT_KEY"),
            "status": x.get("UF_STATUS"),
            "publish_unix": x.get("UF_PUBLISH_DATE"),
        }
        for x in p
    ]


def parse_orderlist(blocks: dict) -> list:
    o = blocks.get("orderListStoreData") or []
    return o if isinstance(o, list) else []


def parse_tasklist(blocks: dict) -> list:
    t = blocks.get("taskListStoreData") or []
    return t if isinstance(t, list) else []


def extract_api_urls(html: str) -> list[str]:
    """Извлечь URLs api-endpoints (включая cache-buster) из HTML страницы."""
    return list(set(API_SCRIPT_PATTERN.findall(html)))


def build_snapshot(opener) -> dict:
    snap: dict = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "pages": {},
        "api_endpoints": [],
        "user": {},
        "balance": {},
        "billing_history": [],
        "projects": [],
        "orderlist": [],
        "tasklist": [],
        "errors": [],
    }
    all_blocks: dict[str, Any] = {}
    api_urls_seen: set[str] = set()

    for label, url in PINIA_PAGES.items():
        try:
            html = fetch(opener, url)
            # Stage 1: extract pinia from page itself (rare)
            blocks = extract_pinia_blocks(html)
            # Stage 2: find api-endpoints with cache-buster
            api_urls = extract_api_urls(html)
            for api_url in api_urls:
                full_api = f"{BASE}{api_url}" if api_url.startswith("/") else api_url
                if full_api in api_urls_seen:
                    continue
                api_urls_seen.add(full_api)
                try:
                    api_html = fetch(opener, full_api)
                    api_blocks = extract_pinia_blocks(api_html)
                    blocks.update(api_blocks)
                except Exception as e:
                    snap["errors"].append(f"api {api_url}: {e}")
            snap["pages"][label] = {
                "status": "ok",
                "blocks_count": len(blocks),
                "api_endpoints_found": len(api_urls),
            }
            all_blocks.update(blocks)
        except Exception as e:
            snap["pages"][label] = {"status": "error", "error": str(e)}
            snap["errors"].append(f"{label}: {e}")
    snap["api_endpoints"] = sorted(api_urls_seen)

    snap["user"] = parse_user(all_blocks)
    snap["balance"] = parse_billing(all_blocks)
    snap["billing_history"] = parse_history(all_blocks)
    snap["projects"] = parse_projects(all_blocks)
    snap["orderlist"] = parse_orderlist(all_blocks)
    snap["tasklist"] = parse_tasklist(all_blocks)
    snap["_blocks_found"] = sorted(all_blocks.keys())
    return snap


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: kupi-otziv-monitor.py <client_slug>")
    client = sys.argv[1]

    cfg = load_kupi_otziv_config()
    cookies_path = Path(cfg["cookies_file"]).expanduser()
    if not cookies_path.exists():
        sys.exit(f"ERROR: cookies file not found: {cookies_path}")

    out_dir = ROOT / "clients" / client / "orm" / "kupi-otziv"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"→ kupi-otziv-monitor for {client}")
    opener = make_opener(cookies_path)
    snap = build_snapshot(opener)

    stamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    snap_path = out_dir / f"snap-{stamp}.json"
    snap_path.write_text(json.dumps(snap, ensure_ascii=False, indent=2))
    print(f"✓ Snapshot: {snap_path}")

    # History CSV
    history_path = out_dir / "history.csv"
    if not history_path.exists():
        history_path.write_text("timestamp,balance,projects,orders,tasks,history_ops,errors\n")
    with open(history_path, "a", encoding="utf-8") as f:
        f.write(
            f"{snap['ts']},{snap['balance'].get('value_rub', '?')},"
            f"{len(snap['projects'])},{len(snap['orderlist'])},"
            f"{len(snap['tasklist'])},{len(snap['billing_history'])},"
            f"{len(snap['errors'])}\n"
        )

    # Console output
    print(f"\n{'='*60}")
    print(f"USER:     {snap['user'].get('name', '?')} · {snap['user'].get('email', '?')}")
    print(f"BALANCE:  {snap['balance'].get('value_rub', '?')} ₽")
    print(f"PROJECTS: {len(snap['projects'])} (statuses: {sorted(set(p.get('status', '?') for p in snap['projects']))})")
    print(f"ORDERS:   {len(snap['orderlist'])}")
    print(f"TASKS:    {len(snap['tasklist'])}")
    print(f"HISTORY:  {len(snap['billing_history'])} операций")
    if snap["errors"]:
        print(f"⚠️  ERRORS: {len(snap['errors'])}")
        for e in snap["errors"][:3]:
            print(f"   - {e}")
    print("="*60)
    return 0


if __name__ == "__main__":
    main()
