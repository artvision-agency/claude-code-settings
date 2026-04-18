#!/usr/bin/env python3
"""Extract long user prompts (>500 chars) from Claude session JSONL files.

Usage: extract-session-prompts.py <session.jsonl> <output.md> <timestamp>

Skips output if file already >10KB (already saved earlier).
"""
import json
import sys
import os

def main():
    if len(sys.argv) < 4:
        print("Usage: extract-session-prompts.py <session.jsonl> <output.md> <timestamp>", file=sys.stderr)
        sys.exit(1)

    session_file = sys.argv[1]
    output_file = sys.argv[2]
    timestamp = sys.argv[3]

    # Don't overwrite if file already >10KB (already saved earlier)
    if os.path.exists(output_file) and os.path.getsize(output_file) > 10000:
        sys.exit(0)

    messages = []
    try:
        with open(session_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue

                if obj.get("type") != "user":
                    continue

                msg = obj.get("message", {})
                content = msg.get("content", "") if isinstance(msg, dict) else ""
                text = ""

                if isinstance(content, list):
                    for b in content:
                        if isinstance(b, dict) and b.get("type") == "text":
                            t = b.get("text", "")
                            # Skip task notifications and system messages
                            if not t.startswith("<task-notification") and not t.startswith("This session is being continued"):
                                text += t
                elif isinstance(content, str):
                    if not content.startswith("<task-notification"):
                        text = content

                if len(text) > 500:
                    messages.append(text)
    except Exception as e:
        print(f"[extract-session-prompts] Error: {e}", file=sys.stderr)
        sys.exit(0)

    if not messages:
        sys.exit(0)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# Session Prompts\n")
        f.write(f"**Extracted:** {timestamp}\n")
        f.write(f"**Session:** {os.path.basename(session_file)}\n\n")
        for i, msg in enumerate(messages, 1):
            f.write(f"## Prompt #{i} ({len(msg)} chars)\n\n")
            f.write(msg[:20000])  # Cap at 20K per message
            if len(msg) > 20000:
                f.write(f"\n\n... [truncated from {len(msg)} chars]")
            f.write("\n\n---\n\n")

    print(f"[pre-compact] Saved {len(messages)} prompts to {output_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
