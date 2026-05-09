#!/usr/bin/env python3
"""
audit-session-tools.py — анализ использованных и пропущенных инструментов в сессии.

Парсит JSONL-транскрипт активной сессии Claude Code, извлекает все вызовы
Agent (subagent_type), Skill, Bash (скрипты/CLI), сравнивает с реестром
доступных инструментов и показывает: что использовано, что пропущено, рекомендации.

Использование:
    python3 ~/.claude/scripts/audit-session-tools.py [sessionId]
    # без аргумента → берёт самую свежую сессию из ~/.claude/projects/-Users-antonk/
"""

from __future__ import annotations
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_DIR = Path.home() / ".claude" / "projects" / "-Users-antonk"
SKILLS_DIR = Path.home() / ".claude" / "skills"
AGENTS_DIR = Path.home() / ".claude" / "agents"
COMMANDS_DIR = Path.home() / ".claude" / "commands"
SCRIPTS_DIR = Path.home() / ".claude" / "scripts"
RECAPS_DIR = Path.home() / "artvision-data" / "sync" / "recaps"


def latest_session_id() -> str | None:
    if not PROJECT_DIR.exists():
        return None
    jsonls = sorted(PROJECT_DIR.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not jsonls:
        return None
    return jsonls[0].stem


def list_registry(d: Path, pattern: str = "*") -> set[str]:
    if not d.exists():
        return set()
    return {p.stem if p.is_file() else p.name for p in d.glob(pattern)}


def parse_transcript(jsonl_path: Path) -> dict:
    agents = Counter()
    skills = Counter()
    bash_scripts = Counter()
    bash_cli_tools = Counter()
    agent_descriptions = defaultdict(list)
    skill_args = defaultdict(list)
    total_tool_uses = 0

    if not jsonl_path.exists():
        return {"error": f"{jsonl_path} not found"}

    with jsonl_path.open() as f:
        for line in f:
            try:
                entry = json.loads(line)
            except Exception:
                continue
            msg = entry.get("message") or {}
            content = msg.get("content")
            if not isinstance(content, list):
                continue
            for item in content:
                if not isinstance(item, dict):
                    continue
                if item.get("type") != "tool_use":
                    continue
                total_tool_uses += 1
                name = item.get("name", "")
                inp = item.get("input") or {}

                if name == "Agent":
                    sub = inp.get("subagent_type", "general-purpose")
                    agents[sub] += 1
                    desc = inp.get("description", "")[:80]
                    agent_descriptions[sub].append(desc)
                elif name == "Skill":
                    skill_name = inp.get("skill", "")
                    skills[skill_name] += 1
                    args = (inp.get("args") or "")[:80]
                    skill_args[skill_name].append(args)
                elif name == "Bash":
                    cmd = inp.get("command", "")
                    # extract script paths
                    for m in re.finditer(r"~/\.claude/scripts/[\w/\.-]+", cmd):
                        bash_scripts[m.group(0)] += 1
                    for m in re.finditer(r"~/artvision-data/scripts/[\w/\.-]+", cmd):
                        bash_scripts[m.group(0)] += 1
                    # CLI tools (first word)
                    first = cmd.strip().split()[0] if cmd.strip() else ""
                    if first in {"playwright", "curl", "scp", "ssh", "git", "python3",
                                 "node", "npm", "gh", "jq", "rsync", "sed", "awk", "grep",
                                 "find", "wc", "cat", "head", "tail"}:
                        bash_cli_tools[first] += 1
                    if "python3" in cmd and ("playwright" in cmd or "from playwright" in cmd):
                        bash_cli_tools["playwright(py)"] += 1
                    if "factcheck-v2" in cmd:
                        bash_scripts["factcheck-v2.py"] += 1

    return {
        "total_tool_uses": total_tool_uses,
        "agents": dict(agents),
        "agent_descriptions": dict(agent_descriptions),
        "skills": dict(skills),
        "skill_args": dict(skill_args),
        "bash_scripts": dict(bash_scripts),
        "bash_cli_tools": dict(bash_cli_tools),
    }


def main():
    sid = sys.argv[1] if len(sys.argv) > 1 else latest_session_id()
    if not sid:
        print("ERR: session not found")
        sys.exit(1)
    jsonl = PROJECT_DIR / f"{sid}.jsonl"
    data = parse_transcript(jsonl)
    if "error" in data:
        print(f"ERR: {data['error']}")
        sys.exit(1)

    available_skills = list_registry(SKILLS_DIR, "*")
    available_agents = list_registry(AGENTS_DIR, "*.md")
    available_commands = list_registry(COMMANDS_DIR, "*.md")
    available_scripts = list_registry(SCRIPTS_DIR, "*.py") | list_registry(SCRIPTS_DIR, "*.sh")

    used_skills = set(data["skills"].keys())
    used_agents = set(data["agents"].keys())
    used_scripts = {Path(s).name for s in data["bash_scripts"].keys()}

    # Recap
    recap_file = RECAPS_DIR / f"{sid}.md"
    recap_goal = "—"
    if recap_file.exists():
        for line in recap_file.read_text().splitlines():
            if line.strip().startswith("Составить") or line.strip().startswith("- Make") or "Цель сессии" in line:
                continue
            if line.strip() and not line.startswith("#") and not line.startswith("**") and not line.startswith("<!--"):
                recap_goal = line.strip()[:120]
                break

    # Output
    print(f"\n{'='*72}")
    print(f"  SESSION TOOLS AUDIT — {sid[:8]}")
    print(f"{'='*72}\n")
    print(f"📋 Цель: {recap_goal}")
    print(f"🔢 Всего tool_use: {data['total_tool_uses']}\n")

    # USED
    print("✅ ИСПОЛЬЗОВАНО\n")
    print(f"Subagent-агенты ({sum(data['agents'].values())} вызовов):")
    for agent, n in sorted(data["agents"].items(), key=lambda x: -x[1]):
        print(f"  • {agent} ×{n}")
    print()
    print(f"Skills ({sum(data['skills'].values())} вызовов):")
    for skill, n in sorted(data["skills"].items(), key=lambda x: -x[1]):
        print(f"  • {skill} ×{n}")
    print()
    print(f"CLI / scripts:")
    for tool, n in sorted(data["bash_cli_tools"].items(), key=lambda x: -x[1])[:15]:
        print(f"  • {tool} ×{n}")
    if data["bash_scripts"]:
        print(f"\nScript-файлы:")
        for s, n in data["bash_scripts"].items():
            print(f"  • {s} ×{n}")

    # NOT USED
    relevant_skills_skipped = [s for s in available_skills if s not in used_skills
                               and not s.startswith(".")
                               and ":" not in s]
    print(f"\n❌ НЕ ИСПОЛЬЗОВАНО (релевантные skills, всего {len(relevant_skills_skipped)} из {len(available_skills)}):")
    # show first 20
    for s in sorted(relevant_skills_skipped)[:25]:
        print(f"  • {s}")
    if len(relevant_skills_skipped) > 25:
        print(f"  ... +{len(relevant_skills_skipped)-25} more")

    print(f"\n📊 Покрытие:")
    print(f"  • Skills: {len(used_skills)}/{len(available_skills)} ({100*len(used_skills)//max(len(available_skills),1)}%)")
    print(f"  • Agents: {len(used_agents)}/{len(available_agents)}")
    print(f"  • Scripts: {len(used_scripts)}/{len(available_scripts)}")

    print(f"\n{'='*72}")
    print(f"  Анализ JSONL: {jsonl}")
    print(f"{'='*72}")


if __name__ == "__main__":
    main()
