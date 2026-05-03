#!/usr/bin/env python3
"""
asana-skill-comment.py — постит в закрытые Asana-задачи комментарий с аудитом
использованных/пропущенных скиллов из текущей сессии.

Источники task_gid:
  1. tool_use вызовы Asana MCP в JSONL транскрипте — собираем все task_gid
  2. Поле "Связанные задачи" в recap.md (ссылки asana.com/0/.../X)

Не дублируем — если в комментарии задачи уже есть метка [skill-audit:<sid>] — skip.

Использование:
  python3 asana-skill-comment.py [sessionId]

Без аргумента — берёт самую свежую сессию.
"""

from __future__ import annotations
import json
import os
import re
import sys
import urllib.request
import urllib.error
from collections import Counter
from pathlib import Path

PROJECT_DIR = Path.home() / ".claude" / "projects" / "-Users-antonk"
RECAPS_DIR = Path.home() / "artvision-data" / "sync" / "recaps"
TOKENS = Path.home() / "artvision-data" / "tokens.json"


def asana_pat() -> str | None:
    try:
        d = json.loads(TOKENS.read_text())
        return d.get("asana", {}).get("token")
    except Exception:
        return None


def latest_session_id() -> str | None:
    if not PROJECT_DIR.exists():
        return None
    jsonls = sorted(PROJECT_DIR.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return jsonls[0].stem if jsonls else None


def parse_session(sid: str) -> dict:
    jsonl = PROJECT_DIR / f"{sid}.jsonl"
    if not jsonl.exists():
        return {"task_gids": set(), "skills": Counter(), "agents": Counter()}

    task_gids: set[str] = set()
    skills = Counter()
    agents = Counter()
    goal = ""

    with jsonl.open() as f:
        for line in f:
            try:
                e = json.loads(line)
            except Exception:
                continue
            content = (e.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for item in content:
                if not isinstance(item, dict):
                    continue
                if item.get("type") != "tool_use":
                    continue
                name = item.get("name", "")
                inp = item.get("input") or {}
                if name.startswith("mcp__asana__"):
                    # extract task_gid from various asana tools
                    for k in ("task_gid", "task_id"):
                        v = inp.get(k)
                        if v and re.match(r"^\d{10,}$", str(v)):
                            task_gids.add(str(v))
                    # update_task and similar may include parent_task_gid
                    if "parent" in inp and re.match(r"^\d{10,}$", str(inp.get("parent", ""))):
                        task_gids.add(str(inp["parent"]))
                elif name == "Skill":
                    sn = inp.get("skill", "")
                    if sn:
                        skills[sn] += 1
                elif name == "Agent":
                    sub = inp.get("subagent_type", "general-purpose")
                    agents[sub] += 1

    # also scan recap for asana.com/0/.../X links
    recap = RECAPS_DIR / f"{sid}.md"
    if recap.exists():
        text = recap.read_text(errors="replace")
        for m in re.finditer(r"app\.asana\.com/\d+/\d+/(\d{10,})", text):
            task_gids.add(m.group(1))
        # extract goal
        gm = re.search(r"## Цель сессии\s*\n+(.+?)(?:\n\n|\n##)", text, re.S)
        if gm:
            goal = gm.group(1).strip()[:300]

    return {
        "task_gids": task_gids,
        "skills": dict(skills),
        "agents": dict(agents),
        "goal": goal,
    }


def asana_get_story(pat: str, task_gid: str, marker: str) -> bool:
    """Returns True if task already has a story containing the marker."""
    url = f"https://app.asana.com/api/1.0/tasks/{task_gid}/stories?opt_fields=text&limit=50"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {pat}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        for st in data.get("data", []):
            if marker in (st.get("text") or ""):
                return True
    except Exception:
        pass
    return False


def asana_post_story(pat: str, task_gid: str, text: str) -> bool:
    url = f"https://app.asana.com/api/1.0/tasks/{task_gid}/stories"
    body = json.dumps({"data": {"text": text}}).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {pat}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status in (200, 201)
    except urllib.error.HTTPError as e:
        sys.stderr.write(f"Asana POST {task_gid}: HTTP {e.code} {e.read()[:200]}\n")
        return False
    except Exception as e:
        sys.stderr.write(f"Asana POST {task_gid}: {e}\n")
        return False


def render_comment(sid: str, info: dict) -> str:
    skills = info["skills"]
    agents = info["agents"]
    goal = info.get("goal", "") or "—"

    lines = [f"🔍 Skill audit (session {sid[:8]})", "", f"Цель: {goal[:200]}", ""]
    if skills:
        lines.append("✅ Skills вызваны:")
        for s, n in sorted(skills.items(), key=lambda x: -x[1]):
            lines.append(f"  • {s} ×{n}")
    else:
        lines.append("⚠️ Skill tool ни разу не вызван")
    lines.append("")
    if agents:
        lines.append("Агенты:")
        for a, n in sorted(agents.items(), key=lambda x: -x[1])[:8]:
            lines.append(f"  • {a} ×{n}")
    lines.append("")
    lines.append(f"[skill-audit:{sid}]")
    return "\n".join(lines)


def main():
    pat = asana_pat()
    if not pat:
        print("ERR: no asana token in tokens.json")
        sys.exit(1)

    sid = sys.argv[1] if len(sys.argv) > 1 else latest_session_id()
    if not sid:
        print("ERR: session not found")
        sys.exit(1)

    info = parse_session(sid)
    task_gids = info["task_gids"]
    if not task_gids:
        print(f"No Asana tasks in session {sid[:8]} — skip")
        return

    comment = render_comment(sid, info)
    marker = f"[skill-audit:{sid}]"
    posted = 0
    skipped = 0
    for gid in task_gids:
        if asana_get_story(pat, gid, marker):
            skipped += 1
            continue
        if asana_post_story(pat, gid, comment):
            posted += 1

    print(f"Asana skill-audit comments: posted={posted} skipped(dup)={skipped} of {len(task_gids)} tasks")


if __name__ == "__main__":
    main()
