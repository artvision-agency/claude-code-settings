#!/usr/bin/env python3
"""
orm-pulse: orders-state — состояние заказов клиента.

Что это: каждая строка из Sheet заказчика → классификация по состоянию.
   ✅ опубликовано · ⏳ модерация · 📤 отдано исполнителю · 📝 согласовано не отдано · 💸 потрачен · ❌ не прошёл

+ темп публикаций/день за последнюю неделю (из history-csv reviews-tracker'а).

Usage: orders-state.py <client_slug>

Output:
  ~/artvision-data/clients/<slug>/orm/orders-state-{date}.md
  /tmp/orm-pulse/<slug>/orders-state.json
"""
import sys
import csv
import json
import re
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from difflib import SequenceMatcher
import yaml


def normalize(t):
    t = (t or "").lower().strip()
    for ch in ",.!?\"'`«»–—-()[]{};:":
        t = t.replace(ch, " ")
    return " ".join(t.split())[:120]


def sim(a, b):
    a, b = normalize(a), normalize(b)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def load_registry(slug):
    return yaml.safe_load((Path.home() / "artvision-data" / "clients" / slug / "orm" / "registry.yaml").read_text())


def load_sheet1(snapshots_dir):
    """Sheet1/апр26 — главный файл заказчика. Возвращает list[dict]."""
    paths = sorted(snapshots_dir.glob("sheet1_internal_*.csv"))
    if not paths:
        return []
    rows = []
    for p in paths:
        if "0.csv" not in p.name:  # gid=0 это март26 (старый), берём только апр26 + переделать
            pass
        with open(p, encoding='utf-8') as f:
            try:
                reader = csv.DictReader(f)
                for r in reader:
                    text = r.get("Текст отзыва", "").strip() or r.get("Текст", "").strip()
                    if not text:
                        continue
                    rows.append({
                        "sheet": p.stem,
                        "text": text,
                        "category": r.get("Категория товара", "").strip(),
                        "status": r.get("Статус", "").strip() or r.get("Статус размещения", "").strip(),
                        "author": r.get("Автор отзыва", "").strip(),
                        "date_заказа": r.get("Дата заказа", "").strip(),
                        "date_отзыва": r.get("Дата отзыва", "").strip(),
                    })
            except Exception:
                pass
    return rows


def load_sheet2_executors(snapshots_dir):
    """Sheet2 = тексты у okponrussia."""
    rows = []
    for p in snapshots_dir.glob("sheet2_*.csv"):
        with open(p, encoding='utf-8') as f:
            for r in csv.reader(f):
                if r and r[0].strip() and "Текст" not in r[0]:
                    rows.append({"text": r[0].strip(), "src": p.stem})
    return rows


def load_tg_corpus(slug):
    tg_dir = Path("/tmp/orm-pulse") / slug / "tg"
    corpus = ""
    if tg_dir.exists():
        for f in tg_dir.glob("*.md"):
            corpus += f.read_text(errors="ignore")
    return corpus


def classify(rows, executor_texts, tg_norm):
    """Каждая строка → одна из категорий."""
    state = {
        "published": [],          # размещён
        "moderation": [],         # ожидание модерации
        "given_to_okponrussia": [], # передан okp (по match)
        "given_to_kwork": [],     # упомянут в TG как kwork
        "given_internal_sheet": [], # «Согласовано, заказ размещён» (с датой) — внутренний учёт
        "approved_not_given": [], # «Текст согласован» — готов к отдаче
        "waiting_approval": [],   # «Ожидает согласования»
        "rejected": [],           # не прошёл модерацию
        "spent": [],              # потрачен
        "rework_pool": [],        # из вкладки «переделать»
        "uniq_failed": [],        # неуникальный текст
        "other": [],
    }

    for r in rows:
        text = r["text"]
        status = r["status"].lower()
        sheet = r["sheet"]

        if "переделать" in sheet.lower() or "470319558" in sheet:
            if "неуник" in status:
                state["uniq_failed"].append(r)
            else:
                state["rework_pool"].append(r)
            continue

        if "размещ" in status and "не прош" not in status and "согласов" not in status:
            state["published"].append(r)
            continue
        if "не прош" in status:
            state["rejected"].append(r); continue
        if "потрачен" in status:
            state["spent"].append(r); continue
        if "модерац" in status:
            state["moderation"].append(r); continue
        if "согласован" in status and "размещ" in status:
            # Match с okponrussia
            best = max((sim(text, e["text"]) for e in executor_texts), default=0.0)
            if best >= 0.6:
                state["given_to_okponrussia"].append({**r, "_match_score": round(best, 2)})
            else:
                # Возможно kwork
                sample = normalize(text)[:60]
                if sample and sample in tg_norm and "kwork" in tg_norm[max(0, tg_norm.find(sample)-200):tg_norm.find(sample)+200]:
                    state["given_to_kwork"].append(r)
                else:
                    state["given_internal_sheet"].append(r)
            continue
        if "текст согласован" in status:
            state["approved_not_given"].append(r); continue
        if "ожидает согласования" in status or "ожидание согласования" in status:
            state["waiting_approval"].append(r); continue

        state["other"].append(r)

    return state


def daily_pace(slug, days=7):
    """Темп публикаций/день из reviews-tracker history."""
    history_path = Path.home() / "artvision-data" / "clients" / slug / "orm" / "reviews-tracker" / "history.csv"
    if not history_path.exists():
        return None

    rows = list(csv.DictReader(open(history_path)))
    if len(rows) < 2:
        return None

    cutoff = datetime.now() - timedelta(days=days)
    recent = []
    for r in rows:
        try:
            ts = datetime.strptime(r["timestamp"], "%Y-%m-%d-%H%M")
            if ts >= cutoff:
                recent.append({
                    "ts": ts,
                    "total": int(r["total"]) if r["total"] else 0,
                    "rating": float(r["rating"]) if r["rating"] and r["rating"] != "None" else None,
                })
        except Exception:
            continue

    if len(recent) < 2:
        return None

    delta = recent[-1]["total"] - recent[0]["total"]
    period_days = max((recent[-1]["ts"] - recent[0]["ts"]).total_seconds() / 86400, 0.1)
    return {
        "delta_total": delta,
        "period_days": round(period_days, 2),
        "per_day": round(delta / period_days, 2),
        "from_total": recent[0]["total"],
        "to_total": recent[-1]["total"],
        "rating_now": recent[-1]["rating"],
    }


def load_qcomment_snapshot(slug):
    """Последний qcomment snapshot."""
    qc_dir = Path.home() / "artvision-data" / "clients" / slug / "orm" / "qcomment"
    if not qc_dir.exists():
        return None
    snaps = sorted(qc_dir.glob("snap-*.json"))
    if not snaps:
        return None
    try:
        return json.loads(snaps[-1].read_text())
    except Exception:
        return None


def format_kwork_executors(tg_corpus):
    """Извлечь названия kwork-исполнителей из TG."""
    # Известные ники из истории
    known = ["SMMDEAL", "seojob-rf", "polyaseo", "Internet_promo", "reputation_promotion",
             "social_boost", "otzyv_pro", "reputation_yandex", "ads_seo_yandex"]
    found = []
    for nick in known:
        c = tg_corpus.lower().count(nick.lower())
        if c > 0:
            found.append({"nick": nick, "mentions": c})
    return sorted(found, key=lambda x: -x["mentions"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("slug")
    args = parser.parse_args()

    registry = load_registry(args.slug)
    snapshots_dir = Path.home() / "artvision-data" / "clients" / args.slug / "orm" / "snapshots" / "latest"

    sheet1 = load_sheet1(snapshots_dir)
    executors = load_sheet2_executors(snapshots_dir)
    tg_corpus = load_tg_corpus(args.slug)
    tg_norm = normalize(tg_corpus)

    state = classify(sheet1, executors, tg_norm)
    pace = daily_pace(args.slug, days=7)
    kwork_exec = format_kwork_executors(tg_corpus)
    qc = load_qcomment_snapshot(args.slug)

    # Output
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M МСК")
    out_md = []
    out_md.append(f"# {registry.get('client_full_name', args.slug)} — состояние заказов")
    out_md.append("")
    out_md.append(f"> Сгенерировано: {timestamp} · `/orm-pulse {args.slug} orders-state`")
    out_md.append(f"> Источник: snapshots/latest + /tmp/orm-pulse/{args.slug}/tg/")
    out_md.append("")

    out_md.append("## Воронка состояний")
    out_md.append("")
    out_md.append("| Состояние | Кол-во | Что это |")
    out_md.append("|-----------|:------:|---------|")
    out_md.append(f"| ✅ Опубликовано | {len(state['published'])} | На reviews.yandex.ru |")
    out_md.append(f"| ⏳ На модерации Я | {len(state['moderation'])} | Биржа отдала, ждём |")
    out_md.append(f"| 📤 У okponrussia | {len(state['given_to_okponrussia'])} | Match с Sheet2 |")
    out_md.append(f"| 📤 У kwork | {len(state['given_to_kwork'])} | По упоминаниям в TG |")
    out_md.append(f"| 📋 Согл. + дата заказа (внутр.) | {len(state['given_internal_sheet'])} | Sheet говорит «отдано», но не подтверждено |")
    out_md.append(f"| 📝 Текст согласован — НЕ ОТДАН | **{len(state['approved_not_given'])}** | ⭐ можно раздать |")
    out_md.append(f"| ⏸ Ждёт согласования | {len(state['waiting_approval'])} | Юра/Антон должен утвердить |")
    out_md.append(f"| ❌ Не прошёл модерацию | {len(state['rejected'])} | Переписать |")
    out_md.append(f"| 💸 Потрачен | {len(state['spent'])} | Деньги ушли, отзыв не появился |")
    out_md.append(f"| 🔄 Банк переделать | {len(state['rework_pool'])} | Доработка |")
    out_md.append(f"| 🚫 Неуникальный (шинглы) | {len(state['uniq_failed'])} | Переписать |")
    out_md.append(f"| ? Другое/неклассиф. | {len(state['other'])} | Проверить статусы |")
    out_md.append("")

    if qc:
        out_md.append("## QComment (биржа qcomment.com — отдельный канал)")
        out_md.append("")
        balance = qc.get("balance", "?")
        total = qc.get("total_projects", 0)
        pending = qc.get("pending_review", 0)
        accepted = qc.get("accepted_total", 0)
        rejected = qc.get("rejected_total", 0)
        rework = qc.get("rework_total", 0)
        out_md.append(f"- **Баланс:** {balance} ₽")
        out_md.append(f"- **Проектов:** {total} (каждый = 1 слот для отзыва, тариф 183)")
        out_md.append(f"- ⏳ Ждут исполнителя или модерации: {total - pending - accepted - rejected - rework}")
        out_md.append(f"- 🚨 **Принять работу: {pending}** (auto-accept на 3-й день — НЕ пропустить!)")
        out_md.append(f"- ✅ Принято: {accepted}")
        out_md.append(f"- ❌ Отклонено: {rejected}")
        out_md.append(f"- 🔄 На доработке: {rework}")
        if pending > 0:
            out_md.append("")
            out_md.append("**Pending проекты:**")
            for gname, projs in qc.get("groups", {}).items():
                pending_projs = [p for p in projs if p.get("pending", 0) > 0]
                for p in pending_projs:
                    out_md.append(f"- [{p['project_id']}]({p['manage_url']}) — {gname} · {p['human_status']}")
        out_md.append("")
        out_md.append("📊 Дашборд: https://artvision.pro/qcomment/ (admin/111)")
        out_md.append("")

    if pace:
        out_md.append("## Темп публикаций")
        out_md.append("")
        out_md.append(f"- За последние {pace['period_days']} дней: **{pace['delta_total']:+d}** новых отзывов на reviews.yandex.ru")
        out_md.append(f"- **Темп: {pace['per_day']:.2f} публ/день**")
        target = 5.0
        gap = target - pace['per_day']
        if gap > 0:
            out_md.append(f"- 🎯 Цель 5/день · недобор: **{gap:.2f}/день** (×{(target/pace['per_day']):.1f} ускорение если темп >0)" if pace['per_day'] > 0 else f"- 🎯 Цель 5/день · темп ≈0, требует радикального ускорения")
        else:
            out_md.append(f"- ✅ Темп >5/день — план выполняется")
        out_md.append(f"- Рейтинг сейчас: **{pace['rating_now']}** (цель: расти)")
        out_md.append(f"- Total: {pace['from_total']} → {pace['to_total']}")
        out_md.append("")

    if kwork_exec:
        out_md.append("## Kwork-исполнители (упоминания в TG за период)")
        out_md.append("")
        out_md.append("| Ник | Упоминаний |")
        out_md.append("|-----|:----------:|")
        for e in kwork_exec:
            out_md.append(f"| {e['nick']} | {e['mentions']} |")
        out_md.append("")

    # Список «не отдано»
    if state["approved_not_given"]:
        out_md.append("## ⭐ Список «Текст согласован — НЕ отдан» (можно раздать)")
        out_md.append("")
        by_cat = Counter(r["category"] for r in state["approved_not_given"])
        out_md.append("По категориям:")
        for cat, n in by_cat.most_common():
            out_md.append(f"- {cat}: {n}")
        out_md.append("")

    md = "\n".join(out_md)

    # Save
    date = datetime.now().strftime("%Y-%m-%d")
    out_path = Path.home() / "artvision-data" / "clients" / args.slug / "orm" / f"orders-state-{date}.md"
    out_path.write_text(md)

    json_path = Path("/tmp/orm-pulse") / args.slug / "orders-state.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps({
        "state_counts": {k: len(v) for k, v in state.items()},
        "pace": pace,
        "kwork_executors": kwork_exec,
        "qcomment": {
            "balance": qc.get("balance") if qc else None,
            "total_projects": qc.get("total_projects") if qc else None,
            "pending_review": qc.get("pending_review") if qc else None,
            "accepted": qc.get("accepted_total") if qc else None,
            "rejected": qc.get("rejected_total") if qc else None,
            "rework": qc.get("rework_total") if qc else None,
        } if qc else None,
        "approved_not_given_full": state["approved_not_given"],
    }, ensure_ascii=False, indent=2))

    print(md)
    print(f"\n💾 {out_path}")
    print(f"💾 {json_path}")


if __name__ == "__main__":
    main()
