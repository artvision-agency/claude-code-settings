#!/usr/bin/env python3
"""executor-message — писать ТЗ/сообщения ИСПОЛНИТЕЛЯМ на биржах отзывов.

Внутренний ORM-tool. НЕ показывать заказчику (NDA, rules/orm.md).

Money-safety: write на биржу = деньги / сообщение исполнителю.
  По умолчанию --dry-run (печатает что будет отправлено, НИЧЕГО не шлёт).
  Реальная отправка — только флаг --commit (= CONFIRM Антона, security.md).

Команды:
  brief   --provider qcomment --slug blumart --platform yandex_maps [--count N --price P --kw a,b]
  msg     --provider qcomment --order <project_id> --text "..."
  rework  --provider qcomment --id <comment_id> --reason "..."
  reject  --provider qcomment --id <comment_id> --reason "..."
  list    --provider qcomment [--slug blumart]
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.exchanges import get_provider  # noqa: E402
from lib.brief_templates import build_brief  # noqa: E402


def _show(res) -> int:
    if res is None:
        return 0
    tag = "DRY-RUN (ничего не отправлено)" if res.dry_run else ("OK ОТПРАВЛЕНО" if res.ok else "ОШИБКА")
    print(f"\n=== {res.provider} · {res.action} · {tag} ===")
    print(res.preview)
    if res.error:
        print(f"\n❌ {res.error}", file=sys.stderr)
        return 1
    if not res.dry_run and res.response is not None:
        print(f"\nОтвет биржи: {res.response}")
    return 0 if res.ok else 1


def _confirm_commit(action: str) -> bool:
    print(f"\n⚠️  --commit: РЕАЛЬНАЯ операция «{action}» на бирже (деньги / сообщение исполнителю).")
    print("    Это CONFIRM-уровень. Продолжить? [введите 'да' для подтверждения]")
    return input("> ").strip().lower() in ("да", "yes", "y")


def cmd_brief(args) -> int:
    kw = [k.strip() for k in args.kw.split(",")] if args.kw else []
    brief = build_brief(args.slug, args.platform, count=args.count, price=args.price,
                        keywords=kw, tone=args.tone or "",
                        brand=args.brand or "", site=args.site or "", address=args.address or "")
    prov = get_provider(args.provider, slug=args.slug)
    if args.commit and not _confirm_commit("create_order"):
        print("Отменено.")
        return 0
    return _show(prov.create_order(brief, commit=args.commit))


def cmd_msg(args) -> int:
    prov = get_provider(args.provider, slug=args.slug)
    if args.commit and not _confirm_commit("message"):
        print("Отменено.")
        return 0
    return _show(prov.message(args.order, args.text, commit=args.commit))


def cmd_rework(args) -> int:
    prov = get_provider(args.provider, slug=args.slug)
    if args.commit and not _confirm_commit("rework"):
        print("Отменено.")
        return 0
    return _show(prov.rework(args.id, args.reason, commit=args.commit))


def cmd_reject(args) -> int:
    prov = get_provider(args.provider, slug=args.slug)
    if args.commit and not _confirm_commit("reject"):
        print("Отменено.")
        return 0
    return _show(prov.reject(args.id, args.reason, commit=args.commit))


def cmd_list(args) -> int:
    prov = get_provider(args.provider, slug=args.slug)
    try:
        orders = prov.list_orders()
    except NotImplementedError as e:
        print(f"ℹ️  {e}")
        return 0
    print(f"Заказов/проектов: {len(orders)}")
    for o in orders[:50]:
        if isinstance(o, dict):
            print(f"  • id={o.get('id')} title={o.get('title')!r} status={o.get('status')}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Писать ТЗ/сообщения исполнителям бирж отзывов")
    ap.add_argument("--commit", action="store_true",
                    help="РЕАЛЬНО отправить (деньги/сообщение). Без флага = dry-run.")
    ap.add_argument("--provider", default="qcomment", choices=["qcomment", "turbotext"])
    ap.add_argument("--slug", default="blumart", help="клиент (config.yaml)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("brief", help="создать заказ с ТЗ")
    p.add_argument("--platform", required=True)
    p.add_argument("--count", type=int)
    p.add_argument("--price", type=int)
    p.add_argument("--kw", default="")
    p.add_argument("--tone", default="")
    p.add_argument("--brand", default="", help="название (если нет config.yaml)")
    p.add_argument("--site", default="")
    p.add_argument("--address", default="")
    p.set_defaults(func=cmd_brief)

    p = sub.add_parser("msg", help="сообщение исполнителям заказа")
    p.add_argument("--order", required=True)
    p.add_argument("--text", required=True)
    p.set_defaults(func=cmd_msg)

    p = sub.add_parser("rework", help="на доработку с причиной")
    p.add_argument("--id", required=True)
    p.add_argument("--reason", required=True)
    p.set_defaults(func=cmd_rework)

    p = sub.add_parser("reject", help="отклонить с причиной")
    p.add_argument("--id", required=True)
    p.add_argument("--reason", required=True)
    p.set_defaults(func=cmd_reject)

    p = sub.add_parser("list", help="список заказов (read-only)")
    p.set_defaults(func=cmd_list)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
