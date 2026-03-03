#!/usr/bin/env python3
"""Extract conversation from Claude Code session JSONL file.

Usage:
    python3 extract-session.py <session_id_or_number> [--full] [--last N]

    session_id_or_number: partial UUID, full UUID, or number from claude-sessions
    --full: show full messages (default: truncated to 500 chars)
    --last N: show only last N message pairs (default: all)
"""

import json
import sys
import os
from pathlib import Path

def find_session_file(query: str) -> str | None:
    """Find session JSONL by partial ID or number."""
    base = Path.home() / ".claude" / "projects"

    # Search all project dirs for matching JSONL
    all_sessions = []
    for jsonl in base.rglob("*.jsonl"):
        all_sessions.append(jsonl)

    # Sort by modification time (newest first)
    all_sessions.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    # Try as number (1-indexed)
    if query.isdigit():
        idx = int(query) - 1
        if 0 <= idx < len(all_sessions):
            return str(all_sessions[idx])

    # Try as partial UUID match
    for s in all_sessions:
        if query in s.stem:
            return str(s)

    return None


def extract_messages(filepath: str, full: bool = False, last_n: int = 0) -> list[dict]:
    """Extract human/assistant text messages from JSONL."""
    messages = []
    max_len = 10000 if full else 500

    with open(filepath) as f:
        for line in f:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_type = obj.get("type")
            if msg_type not in ("human", "assistant"):
                continue

            msg = obj.get("message", {})
            texts = []
            tool_uses = []

            if isinstance(msg, str):
                texts.append(msg)
            elif isinstance(msg, dict):
                for c in msg.get("content", []):
                    if isinstance(c, str):
                        texts.append(c)
                    elif isinstance(c, dict):
                        if c.get("type") == "text":
                            texts.append(c.get("text", ""))
                        elif c.get("type") == "tool_use":
                            tool_name = c.get("name", "unknown")
                            tool_uses.append(tool_name)
                        elif c.get("type") == "tool_result":
                            pass  # skip tool results for summary

            text = "\n".join(texts).strip()
            # Skip system reminders and empty
            if not text or text.startswith("<system-reminder>"):
                # But keep if there are tool uses
                if not tool_uses:
                    continue

            # Truncate if needed
            truncated = False
            if len(text) > max_len:
                text = text[:max_len] + "..."
                truncated = True

            role = "USER" if msg_type == "human" else "CLAUDE"
            entry = {"role": role, "text": text, "truncated": truncated}
            if tool_uses:
                entry["tools"] = tool_uses
            messages.append(entry)

    if last_n > 0:
        messages = messages[-last_n * 2:]

    return messages


def summarize(messages: list[dict]) -> dict:
    """Generate basic stats."""
    user_msgs = [m for m in messages if m["role"] == "USER"]
    claude_msgs = [m for m in messages if m["role"] == "CLAUDE"]
    all_tools = []
    for m in messages:
        all_tools.extend(m.get("tools", []))

    tool_counts = {}
    for t in all_tools:
        tool_counts[t] = tool_counts.get(t, 0) + 1

    return {
        "user_messages": len(user_msgs),
        "claude_messages": len(claude_msgs),
        "total_exchanges": len(messages),
        "tools_used": dict(sorted(tool_counts.items(), key=lambda x: -x[1])[:10]),
        "first_user_msg": user_msgs[0]["text"][:200] if user_msgs else "",
        "last_user_msg": user_msgs[-1]["text"][:200] if user_msgs else "",
        "last_claude_msg": claude_msgs[-1]["text"][:300] if claude_msgs else "",
    }


def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: extract-session.py <session_id_or_number> [--full] [--last N]")
        sys.exit(1)

    query = args[0]
    full = "--full" in args
    last_n = 0
    if "--last" in args:
        idx = args.index("--last")
        if idx + 1 < len(args):
            last_n = int(args[idx + 1])

    filepath = find_session_file(query)
    if not filepath:
        print(f"Session not found: {query}")
        sys.exit(1)

    file_size = os.path.getsize(filepath)
    print(f"Session file: {filepath}")
    print(f"Size: {file_size / 1024:.1f} KB")
    print("=" * 60)

    messages = extract_messages(filepath, full=full, last_n=last_n)
    stats = summarize(messages)

    print(f"\nSTATS: {stats['user_messages']} user msgs, {stats['claude_messages']} claude msgs")
    if stats['tools_used']:
        top_tools = ", ".join(f"{k}({v})" for k, v in list(stats['tools_used'].items())[:5])
        print(f"TOOLS: {top_tools}")
    print("=" * 60)

    print("\n--- CONVERSATION ---\n")
    for m in messages:
        prefix = m["role"]
        tools_str = f" [tools: {', '.join(m['tools'])}]" if m.get("tools") else ""
        text = m["text"]
        # Clean up system reminder noise
        if "<system-reminder>" in text:
            lines = [l for l in text.split("\n") if "<system-reminder>" not in l and "</system-reminder>" not in l]
            text = "\n".join(lines).strip()
        if not text and not tools_str:
            continue
        print(f"{prefix}{tools_str}:")
        print(text)
        print("---")


if __name__ == "__main__":
    main()
