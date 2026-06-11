#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
shorts-daily-digest.py — ежедневный дайджест по YouTube Shorts канала @-Artvisionpro.

Собирает 4 блока (запрос Антона 27.05.2026):
  1. Очередь к публикации   — из ~/.claude/data/shorts-queue.tsv (ready / hold)
  2. Статус залитых вчера    — YouTube Data API: видео с publishedAt == вчера (MSK) + просмотры
  3. Предложение залить сегодня — топ-N ready из очереди + готовая команда
  4. Идеи новых видео        — топ по просмотрам за 90 дней (что заходит)

Вывод:
  - TG личка Антона (tg-send.sh anton)
  - Снимок в ~/.claude/data/shorts-digest-latest.txt (читается стартовым меню сессии)

Запуск: LaunchAgent pro.artvision.shorts-digest (09:00 ежедневно) или вручную.
Флаги: --no-tg (только снимок, без TG), --stdout (печать в консоль).
"""
import json, sys, os, urllib.request, datetime, subprocess

HOME = os.path.expanduser("~")
TOKENS = os.path.join(HOME, "artvision-data/tokens.json")
QUEUE = os.path.join(HOME, ".claude/data/shorts-queue.tsv")
SNAPSHOT = os.path.join(HOME, ".claude/data/shorts-digest-latest.txt")
TG_SEND = os.path.join(HOME, ".claude/scripts/tg-send.sh")
UPLOADS_PLAYLIST = "UUjscpShycpJCA5sRRuumijg"  # @-Artvisionpro uploads
CHANNEL_URL = "https://www.youtube.com/@-Artvisionpro/shorts"
MSK = datetime.timezone(datetime.timedelta(hours=3))


def api_key():
    return json.load(open(TOKENS))["youtube"]["api_key"]


def fetch_uploads(key):
    """Все загрузки канала: [{id,title,published(date),views}]"""
    items, page = [], ""
    while True:
        url = ("https://www.googleapis.com/youtube/v3/playlistItems"
               f"?part=snippet,contentDetails&maxResults=50&playlistId={UPLOADS_PLAYLIST}&key={key}")
        if page:
            url += f"&pageToken={page}"
        d = json.load(urllib.request.urlopen(url, timeout=30))
        if "error" in d:
            raise RuntimeError(d["error"].get("message", "API error"))
        for it in d.get("items", []):
            items.append({
                "id": it["contentDetails"]["videoId"],
                "title": it["snippet"].get("title", ""),
                "published": it["snippet"].get("publishedAt", "")[:10],
                "published_full": it["snippet"].get("publishedAt", ""),
            })
        page = d.get("nextPageToken")
        if not page:
            break
    # просмотры пачками по 50
    ids = [v["id"] for v in items]
    stats = {}
    for i in range(0, len(ids), 50):
        chunk = ",".join(ids[i:i+50])
        url = (f"https://www.googleapis.com/youtube/v3/videos?part=statistics&id={chunk}&key={key}")
        d = json.load(urllib.request.urlopen(url, timeout=30))
        for it in d.get("items", []):
            stats[it["id"]] = int(it.get("statistics", {}).get("viewCount", 0) or 0)
    for v in items:
        v["views"] = stats.get(v["id"], 0)
    return items


def read_queue():
    ready, hold = [], []
    if not os.path.exists(QUEUE):
        return ready, hold
    for line in open(QUEUE, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        path, title, status = parts[0], parts[1], parts[2]
        note = parts[3] if len(parts) > 3 else ""
        exists = os.path.exists(path)
        rec = {"path": path, "title": title, "note": note, "exists": exists}
        if status.strip() == "ready":
            ready.append(rec)
        elif status.strip() == "hold":
            hold.append(rec)
    return ready, hold


def build_digest():
    today = datetime.datetime.now(MSK).date()
    yesterday = today - datetime.timedelta(days=1)
    key = api_key()
    api_err = ""
    try:
        uploads = fetch_uploads(key)
        api_ok = True
    except Exception as e:
        uploads, api_ok = [], False
        api_err = str(e)

    L = []
    L.append(f"📹 ШОРТСЫ @-Artvisionpro — {today.strftime('%d.%m.%Y')}")
    L.append("")

    # Блок 2 — залито вчера
    if api_ok:
        y = [v for v in uploads if v["published"] == yesterday.isoformat()]
        L.append(f"▫️ Залито вчера ({yesterday.strftime('%d.%m')}): "
                 + (f"{len(y)} шт" if y else "ничего"))
        for v in y:
            L.append(f"   • {v['title'][:55]} — {v['views']} просм · youtu.be/{v['id']}")
        # последняя заливка
        if uploads:
            last = uploads[0]
            days = (today - datetime.date.fromisoformat(last["published"])).days
            L.append(f"   Всего на канале: {len(uploads)}. Последняя заливка: {last['published']} ({days} дн назад)")
    else:
        L.append(f"▫️ Залито вчера: ⚠️ YouTube API недоступен ({api_err[:60]})")
    L.append("")

    # Блок 1 — очередь
    ready, hold = read_queue()
    L.append(f"▫️ Очередь к публикации: {len(ready)} ready, {len(hold)} hold")
    for r in ready:
        mark = "" if r["exists"] else " ⚠️файл не найден"
        L.append(f"   ✅ {r['title']}{mark}")
    for h in hold:
        L.append(f"   ⏸ {h['title']} — {h['note'][:50]}")
    L.append("")

    # Блок 3 — предложение залить сегодня
    todo = [r for r in ready if r["exists"]]
    if todo:
        L.append("▫️ Залить сегодня?")
        for r in todo[:2]:
            L.append(f"   → {r['title']}")
        L.append("   Команда: открой Claude → «залей шортс из очереди»")
    else:
        L.append("▫️ Залить сегодня: очередь ready пуста — нужны новые ролики")
    L.append("")

    # Блок 4 — идеи (что заходит)
    if api_ok and uploads:
        recent = [v for v in uploads
                  if (today - datetime.date.fromisoformat(v["published"])).days <= 120]
        top = sorted(recent, key=lambda v: v["views"], reverse=True)[:5]
        L.append("▫️ Что заходит (топ просмотров, 120 дн) → идеи новых:")
        for v in top:
            L.append(f"   ★ {v['views']} — {v['title'][:50]}")
        L.append("   → делай продолжения зашедших тем + CTR-серию (CTR в SEO дал 744 просм)")
    L.append("")
    L.append(f"🔗 {CHANNEL_URL}")
    return "\n".join(L)


def main():
    no_tg = "--no-tg" in sys.argv
    to_stdout = "--stdout" in sys.argv
    text = build_digest()
    # снимок
    os.makedirs(os.path.dirname(SNAPSHOT), exist_ok=True)
    with open(SNAPSHOT, "w", encoding="utf-8") as f:
        f.write(text + f"\n\n# generated {datetime.datetime.now(MSK).strftime('%Y-%m-%d %H:%M MSK')}\n")
    if to_stdout:
        print(text)
    if not no_tg:
        import time
        last_err = None
        for _ in range(2):
            try:
                subprocess.run([TG_SEND, "anton", text], check=True,
                               capture_output=True, text=True, timeout=40)
                last_err = None
                break
            except Exception as e:
                last_err = e
                time.sleep(5)
        if last_err:
            sys.stderr.write(f"TG send failed after retries: {last_err}\n")
            sys.exit(1)


if __name__ == "__main__":
    main()
