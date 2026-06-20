#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build-sessions-index.py — единый searchable индекс всех сессий Claude Code.

Сканирует ~/.claude/projects/-Users-antonk/*.jsonl → для каждой сессии извлекает:
  sessionId · дата · cwd · первый запрос (тема) · есть ли recap/handover · кол-во сообщений.
Пишет:
  ~/artvision-data/sync/SESSIONS-INDEX.md  — markdown таблица (последние сверху)
  ~/artvision-data/sync/sessions-index.jsonl — машиночитаемо (для grep/поиска)

Поиск:  grep -i "<тема>" ~/artvision-data/sync/SESSIONS-INDEX.md
        python3 build-sessions-index.py --search "<тема>"
"""
import json, os, glob, sys, datetime

PROJ = os.path.expanduser("~/.claude/projects/-Users-antonk")
RECAPS = os.path.expanduser("~/artvision-data/sync/recaps")
HANDOVERS = os.path.expanduser("~/.claude/handovers/.pending")
OUT_MD = os.path.expanduser("~/artvision-data/sync/SESSIONS-INDEX.md")
OUT_JSONL = os.path.expanduser("~/artvision-data/sync/sessions-index.jsonl")

def first_user_text(path, maxlen=120):
    """Первый осмысленный пользовательский запрос (не команда/не системное)."""
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                m = o.get("message", {})
                if m.get("role") != "user":
                    continue
                c = m.get("content")
                if isinstance(c, list):
                    c = " ".join(p.get("text", "") for p in c if isinstance(p, dict) and p.get("type") == "text")
                if not isinstance(c, str):
                    continue
                t = c.strip().replace("\n", " ")
                # пропустить служебное/навигацию
                if not t or t.startswith("<") or t.startswith("/") or t.lower() in (
                        "go", "го", "uj", "да", "1", "туду", "синк", "sync", "done?", "пщ", "pgo"):
                    continue
                if "command-name" in t or "local-command" in t or "system-reminder" in t:
                    continue
                return t[:maxlen]
    except Exception:
        pass
    return ""

def session_cwd(path):
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                if o.get("cwd"):
                    return o["cwd"]
    except Exception:
        pass
    return ""

def msg_count(path):
    try:
        return sum(1 for _ in open(path, encoding="utf-8", errors="ignore"))
    except Exception:
        return 0

def build():
    rows = []
    for path in glob.glob(os.path.join(PROJ, "*.jsonl")):
        sid = os.path.basename(path)[:-6]
        mt = os.path.getmtime(path)
        date = datetime.datetime.fromtimestamp(mt).strftime("%Y-%m-%d %H:%M")
        topic = first_user_text(path)
        cwd = session_cwd(path)
        n = msg_count(path)
        has_recap = os.path.exists(os.path.join(RECAPS, sid + ".md"))
        has_ho = os.path.exists(os.path.join(HANDOVERS, sid))
        rows.append({"sid": sid, "mt": mt, "date": date, "topic": topic,
                     "cwd": cwd.replace(os.path.expanduser("~"), "~"), "n": n,
                     "recap": has_recap, "handover_pending": has_ho})
    rows.sort(key=lambda r: -r["mt"])
    # jsonl
    with open(OUT_JSONL, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    # markdown
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(f"# SESSIONS INDEX — все сессии Claude Code\n\n")
        f.write(f"> Авто-индекс {len(rows)} сессий. Обновлён: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}.\n")
        f.write(f"> Поиск: `grep -i \"<тема>\" {OUT_MD}` или `python3 ~/.claude/scripts/build-sessions-index.py --search \"<тема>\"`.\n")
        f.write(f"> Полный лог сессии: `~/.claude/projects/-Users-antonk/<sessionId>.jsonl` · resume: `claude --resume <sessionId>`.\n\n")
        f.write("| Дата | Тема (первый запрос) | cwd | msgs | recap | sessionId |\n")
        f.write("|------|----------------------|-----|-----:|:-----:|-----------|\n")
        for r in rows:
            rc = "✅" if r["recap"] else ""
            topic = (r["topic"] or "—").replace("|", "/")
            f.write(f"| {r['date']} | {topic} | {r['cwd']} | {r['n']} | {rc} | `{r['sid'][:8]}` |\n")
    return len(rows)

def search(q):
    q = q.lower()
    if not os.path.exists(OUT_JSONL):
        build()
    hits = []
    for line in open(OUT_JSONL, encoding="utf-8"):
        r = json.loads(line)
        if q in (r.get("topic", "") + " " + r.get("cwd", "")).lower():
            hits.append(r)
    for r in hits[:40]:
        print(f"{r['date']}  {r['sid'][:8]}  {r['cwd']:30}  {r['topic']}")
    print(f"\nнайдено: {len(hits)} | resume: claude --resume <sessionId>")

if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--search":
        search(sys.argv[2])
    else:
        n = build()
        print(f"✅ индекс построен: {n} сессий → {OUT_MD} + {OUT_JSONL}")
