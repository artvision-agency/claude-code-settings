#!/usr/bin/env python3
"""qcomment-accept-pending — list/accept/reject pending comments через API.

API docs: https://qcomment.com/api (wiki6 = requests, wiki7 = revision).

Usage:
    qcomment-accept-pending.py list                  # показать все pending
    qcomment-accept-pending.py accept <comment_id>   # принять
    qcomment-accept-pending.py accept --all          # принять все
    qcomment-accept-pending.py reject <comment_id> --reason "почему"
    qcomment-accept-pending.py rework <comment_id> --reason "на доработку"

Without LK qcomment.com — only api_code from tokens.json/qcomment.api_code.
"""
from __future__ import annotations
import argparse
import json
import sys
import urllib.request
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.config import ROOT  # noqa: E402

TOKENS_PATH = ROOT / "tokens.json"


def load_api_code() -> tuple[str, str]:
    cfg = json.load(open(TOKENS_PATH))["qcomment"]
    return cfg["api_code"], cfg.get("api_base", "https://qcomment.com/api")


def api_post(api_base: str, endpoint: str, **params) -> dict | list:
    api_code, _ = load_api_code()
    params.setdefault("apicode", api_code)
    params.setdefault("result", "json")
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(f"{api_base}/{endpoint}", data=data, method="POST")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def list_pending() -> list[dict]:
    """GET /api/requests — все pending по всем проектам."""
    _, base = load_api_code()
    resp = api_post(base, "requests")
    if not isinstance(resp, dict):
        return []
    pending = []
    for key, c in resp.items():
        if key.startswith("comment_") and str(c.get("status", "")) == "0":
            pending.append(c)
    return pending


def revision(comment_id: str, operation: int, reason: str = "") -> dict:
    """POST /api/revision — accept/rework/reject.

    operation: 0 = оплатить (default), 1 = на доработку, 2 = отклонить.
    """
    _, base = load_api_code()
    params = {"comment_id": comment_id, "operation": operation}
    if operation in (1, 2):
        if not reason:
            raise ValueError("reason обязателен для rework/reject")
        params["reason"] = reason
    return api_post(base, "revision", **params)


def cmd_list(args) -> int:
    pending = list_pending()
    if not pending:
        print("✅ Нет pending (всё принято / нет работ на проверке)")
        return 0
    print(f"📋 Pending: {len(pending)} коммент(а/ов)\n")
    for c in pending:
        cid = c.get("id")
        pid = c.get("project_id")
        msg = (c.get("message") or "").strip().replace("\r", "").replace("\n", " ")[:120]
        uniq = c.get("uniq", "?")
        robot = c.get("robot_find", "?")
        name = c.get("name", "")
        date = c.get("date", "")
        url = c.get("url", "")
        print(f"  • id={cid}  project={pid}  date={date}")
        print(f"    name={name!r}  uniq={uniq}%  robot_find={robot}  url={url}")
        print(f"    text: {msg}")
        print()
    print(f"Принять все:     {sys.argv[0]} accept --all")
    print(f"Принять один:    {sys.argv[0]} accept {pending[0].get('id')}")
    print(f"Отклонить:       {sys.argv[0]} reject <id> --reason \"причина\"")
    return 0


def _live_match(slug: str, comment: dict) -> bool:
    """Проверка что отзыв реально опубликован — найден в live-reviews-history.

    Rule: ~/.claude/rules/qcomment-accept-only-published.md
    Прецедент 2026-05-11: принял 2 коммента со статусом «На проверке» вслепую.
    """
    from pathlib import Path
    import glob as _glob
    pattern = f"/Users/antonk/artvision-data/clients/{slug}/orm/live-reviews*/*.json"
    files = sorted(_glob.glob(pattern), key=lambda p: Path(p).stat().st_mtime, reverse=True)
    if not files:
        return False
    # Самый свежий
    try:
        data = json.loads(Path(files[0]).read_text())
    except Exception:
        return False
    items = data.get("items", []) if isinstance(data, dict) else []
    name_target = (comment.get("name") or "").lower().strip()
    text_target = (comment.get("message") or "").lower().strip()[:60]
    for it in items:
        author = (it.get("author") or "").lower()
        text = (it.get("text") or "").lower()
        if name_target and name_target in author:
            return True
        if text_target and len(text_target) > 20 and text_target in text:
            return True
    return False


def cmd_accept(args) -> int:
    # Slug для live-check (default blumart, можно через --slug)
    slug = getattr(args, "slug", None) or "blumart"
    require_live = not getattr(args, "force", False)

    if args.all:
        pending = list_pending()
        if not pending:
            print("✅ Нечего принимать")
            return 0
        print(f"📋 Pending: {len(pending)}")

        # Q-RULE: проверка published перед accept
        # ~/.claude/rules/qcomment-accept-only-published.md
        if require_live:
            print(f"🔎 Проверяю что опубликованы (live-reviews snapshot)...")
            checked = []
            for c in pending:
                if _live_match(slug, c):
                    checked.append(c)
                    print(f"  ✓ {c['id']}: найден в live → можно принять")
                else:
                    print(f"  ⚠️  {c['id']}: НЕ найден в live snapshot → SKIP (используй --force чтобы принять вслепую)", file=sys.stderr)
            pending = checked
            if not pending:
                print("\n🛑 Ни один коммент не подтверждён published. Подсказки:")
                print("   1. Запусти свежий crawl: playwright-full-crawl.py blumart")
                print("   2. ИЛИ примени --force (только если на скрине статус «Опубликован»)")
                print("   3. Подожди 24-48ч пока Яндекс закончит модерацию")
                return 0

        print(f"\n🚀 Accepting {len(pending)} verified comments...")
        ok, fail = 0, 0
        for c in pending:
            cid = c["id"]
            try:
                r = revision(cid, operation=0)
                print(f"  ✓ {cid}: {r}")
                ok += 1
            except Exception as e:
                print(f"  ✗ {cid}: {e}", file=sys.stderr)
                fail += 1
        print(f"\nDone: {ok} accepted, {fail} failed")
        return 0 if fail == 0 else 1

    if not args.comment_id:
        print("Usage: accept <comment_id> | accept --all", file=sys.stderr)
        return 2

    # Single accept: тоже проверка published
    if require_live:
        pending = list_pending()
        target = next((c for c in pending if c.get("id") == args.comment_id), None)
        if target and not _live_match(slug, target):
            print(f"⚠️ {args.comment_id} НЕ найден в live snapshot.")
            print(f"   Используй --force чтобы принять вслепую (только если на скрине «Опубликован»)")
            return 3

    try:
        r = revision(args.comment_id, operation=0)
        print(f"✓ Accepted: {r}")
        return 0
    except Exception as e:
        print(f"✗ Failed: {e}", file=sys.stderr)
        return 1


def cmd_reject(args) -> int:
    if not args.comment_id or not args.reason:
        print("Usage: reject <comment_id> --reason \"причина\"", file=sys.stderr)
        return 2
    try:
        r = revision(args.comment_id, operation=2, reason=args.reason)
        print(f"✓ Rejected: {r}")
        return 0
    except Exception as e:
        print(f"✗ Failed: {e}", file=sys.stderr)
        return 1


def cmd_rework(args) -> int:
    if not args.comment_id or not args.reason:
        print("Usage: rework <comment_id> --reason \"причина\"", file=sys.stderr)
        return 2
    try:
        r = revision(args.comment_id, operation=1, reason=args.reason)
        print(f"✓ Sent to rework: {r}")
        return 0
    except Exception as e:
        print(f"✗ Failed: {e}", file=sys.stderr)
        return 1


def main() -> int:
    ap = argparse.ArgumentParser(description="qcomment accept/reject pending via API")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="показать все pending")

    p_acc = sub.add_parser("accept", help="принять (default operation=0)")
    p_acc.add_argument("comment_id", nargs="?")
    p_acc.add_argument("--all", action="store_true", help="принять все pending")
    p_acc.add_argument("--force", action="store_true",
                       help="принять БЕЗ проверки published в live (используй ТОЛЬКО если на скрине статус «Опубликован»)")
    p_acc.add_argument("--slug", default="blumart", help="клиент (default: blumart)")

    p_rej = sub.add_parser("reject", help="отклонить (operation=2)")
    p_rej.add_argument("comment_id")
    p_rej.add_argument("--reason", required=True)

    p_rew = sub.add_parser("rework", help="на доработку (operation=1)")
    p_rew.add_argument("comment_id")
    p_rew.add_argument("--reason", required=True)

    args = ap.parse_args()
    return {
        "list": cmd_list,
        "accept": cmd_accept,
        "reject": cmd_reject,
        "rework": cmd_rework,
    }[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
