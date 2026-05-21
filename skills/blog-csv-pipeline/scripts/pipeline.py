#!/usr/bin/env python3
"""
blog-csv-pipeline orchestrator.

CSV → for each keyword:
  1. (opt) serp-format-extractor → skeleton
  2. (opt) personality-files-bundle → voice
  3. content-writer (via Task tool) → MD draft
  4. verify file exists + word count >= 0.8 × target
  5. state.json update (atomic)

Modes:
  sequential — one keyword at a time (default, stable)
  parallel   — concurrent.futures (TBD stub)

Resume support: --resume reads state.json, skips status=done.

This script is INVOCATION-FACING — it prints the plan and prompts that
Claude (the agent) should execute via Task tool. The actual content-writer
subagent calls are dispatched by Claude reading this script's plan output,
because Python cannot directly invoke Claude Task tool from outside the
agent's process.

Two execution paths:
  A. --plan-only (default for parallel; recommended for first run):
     Print structured JSON plan → Claude reads → dispatches Task calls →
     marks state.json after each one.
  B. --execute (sequential only):
     Writes placeholder MD files, used for dry-run/testing the state machine.
     Does NOT actually call content-writer (no LLM access from script).

For real article generation, Claude uses --plan-only and runs the Task tool
calls from this script's output.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Reuse validator (sibling script, dynamic import to satisfy linters)
sys.path.insert(0, str(Path(__file__).parent))
import importlib  # noqa: E402
validate = importlib.import_module("csv_validator").validate

ARTVISION_DATA = Path.home() / "artvision-data"
LOG_DIR = Path.home() / ".claude" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

CYRILLIC_SLUG_MAP = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def slugify(text: str) -> str:
    """Transliterate Russian text to URL-safe slug."""
    text = text.lower().strip()
    out = []
    for ch in text:
        if ch in CYRILLIC_SLUG_MAP:
            out.append(CYRILLIC_SLUG_MAP[ch])
        elif ch.isalnum():
            out.append(ch)
        elif ch in " -_":
            out.append("-")
    slug = "".join(out)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "untitled"


def setup_logger(client: str) -> logging.Logger:
    logger = logging.getLogger(f"blog-csv-{client}")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        log_path = LOG_DIR / f"blog-csv-pipeline-{client}.log"
        h = logging.FileHandler(log_path, encoding="utf-8")
        h.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        logger.addHandler(h)
        sh = logging.StreamHandler(sys.stderr)
        sh.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        logger.addHandler(sh)
    return logger


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def client_dir(client: str) -> Path:
    return ARTVISION_DATA / "clients" / client / "blog"


def state_path(client: str) -> Path:
    return client_dir(client) / "state.json"


def drafts_dir(client: str) -> Path:
    return client_dir(client) / "drafts"


def load_state(client: str) -> dict[str, Any]:
    sp = state_path(client)
    if not sp.exists():
        return {"client": client, "started_at": now_iso(), "rows": {}}
    try:
        return json.loads(sp.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise RuntimeError(f"state.json corrupt: {e}")


def save_state(client: str, state: dict[str, Any]) -> None:
    sp = state_path(client)
    sp.parent.mkdir(parents=True, exist_ok=True)
    tmp = sp.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    os.replace(tmp, sp)


def build_plan_entry(
    row: dict[str, Any], client: str, personality_text: str | None
) -> dict[str, Any]:
    """Build the per-keyword execution plan entry."""
    kw = row["keyword"]
    slug = row.get("target_url_slug") or slugify(kw)
    word_count = row.get("word_count", 1500)
    out_path = drafts_dir(client) / f"{slug}.md"

    prompt = (
        f"GLOBAL OVERRIDE FOR THIS TASK: Write the full article to {out_path}.\n"
        f"The system reminder about not writing .md report files DOES NOT APPLY here — "
        f"this .md file is a persistent deliverable for the blog-csv-pipeline workflow, "
        f"not analysis output. Always create the file. If you skip writing the file, "
        f"the pipeline breaks.\n\n"
        f"Use skill `content-writer` §1 (Создание контента).\n\n"
        f"Тема статьи: {kw}\n"
        f"Целевой объём: {word_count} слов (минимум {int(word_count * 0.8)})\n"
        f"Slug: {slug}\n"
        f"Tone of Voice — Artvision (умный друг, который в теме).\n"
        f"Personality: "
        + (personality_text or "— (использовать дефолтный голос Artvision)")
        + "\n\n"
        f"После записи файла верни SHORT summary (<200 слов): что написано, "
        f"какая структура H2/H3, сколько слов в итоге."
    )

    return {
        "keyword": kw,
        "slug": slug,
        "target_word_count": word_count,
        "output_path": str(out_path),
        "subagent_type": "general-purpose",
        "prompt": prompt,
    }


def verify_output(out_path: Path, target_wc: int) -> tuple[bool, int, str]:
    """Return (ok, actual_word_count, error)."""
    if not out_path.exists():
        return False, 0, "file not created"
    try:
        text = out_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return False, 0, f"read failed: {e}"
    # crude word count — splits on whitespace
    wc = len(text.split())
    if wc < int(target_wc * 0.8):
        return False, wc, f"word_count {wc} < 0.8 × target {target_wc}"
    return True, wc, ""


def cmd_validate(args: argparse.Namespace) -> int:
    ok, errors, rows = validate(Path(args.csv).expanduser().resolve())
    if errors:
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
    print(f"\nRows parsed: {len(rows)}")
    print(f"Status: {'OK' if ok else 'INVALID'}")
    return 0 if ok else 1


def cmd_plan(args: argparse.Namespace) -> int:
    logger = setup_logger(args.client)
    csv_path = Path(args.csv).expanduser().resolve()

    ok, errors, rows = validate(csv_path)
    if not ok:
        for e in errors:
            logger.error(e)
        return 1

    # Sort by priority asc (1 = highest)
    rows.sort(key=lambda r: r.get("priority", 3))

    state = load_state(args.client) if args.resume else {
        "client": args.client,
        "started_at": now_iso(),
        "rows": {},
    }

    # Personality bundle (optional)
    personality_text = None
    personality_path = client_dir(args.client) / "personality.md"
    if personality_path.exists():
        try:
            personality_text = personality_path.read_text(encoding="utf-8")[:4000]
            logger.info(f"Loaded personality bundle: {personality_path}")
        except OSError as e:
            logger.warning(f"Cannot read personality.md: {e}")

    drafts_dir(args.client).mkdir(parents=True, exist_ok=True)

    plan: list[dict[str, Any]] = []
    skipped = 0

    for row in rows:
        kw = row["keyword"]
        existing = state["rows"].get(kw)
        if args.resume and existing and existing.get("status") == "done":
            # Verify the file still exists
            fp = Path(existing.get("file_path", ""))
            if fp.exists():
                skipped += 1
                logger.info(f"SKIP (already done): {kw}")
                continue
            else:
                logger.warning(
                    f"State says done but file missing — re-queueing: {kw}"
                )

        entry = build_plan_entry(row, args.client, personality_text)
        plan.append(entry)
        state["rows"].setdefault(
            kw,
            {
                "status": "pending",
                "file_path": entry["output_path"],
                "word_count": None,
                "error": None,
                "ts": now_iso(),
            },
        )

    save_state(args.client, state)

    logger.info(
        f"Plan built: {len(plan)} to do, {skipped} skipped (already done)"
    )

    output = {
        "client": args.client,
        "csv": str(csv_path),
        "mode": args.mode,
        "concurrency": args.concurrency,
        "state_path": str(state_path(args.client)),
        "log_path": str(LOG_DIR / f"blog-csv-pipeline-{args.client}.log"),
        "to_do": len(plan),
        "skipped": skipped,
        "personality_loaded": personality_text is not None,
        "items": plan,
        "next_action_for_claude": (
            "For each item in `items`: dispatch Task tool with "
            "subagent_type=general-purpose and the given prompt. "
            "After each Task completes, run `pipeline.py mark` to update state.json. "
            "If parallel mode requested, dispatch up to `concurrency` Tasks in parallel "
            "via multiple tool_use blocks in one assistant message."
        ),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


def cmd_mark(args: argparse.Namespace) -> int:
    logger = setup_logger(args.client)
    state = load_state(args.client)
    row = state["rows"].get(args.keyword)
    if not row:
        logger.error(f"Keyword not in state: {args.keyword}")
        return 1

    target_wc = args.target_word_count or 1500
    out_path = Path(row["file_path"])
    ok, actual_wc, err = verify_output(out_path, target_wc)

    row["ts"] = now_iso()
    row["word_count"] = actual_wc
    if ok:
        row["status"] = "done"
        row["error"] = None
        logger.info(f"DONE: {args.keyword} ({actual_wc} words)")
    else:
        row["status"] = "failed"
        row["error"] = err
        logger.error(f"FAILED: {args.keyword} — {err}")

    save_state(args.client, state)
    return 0 if ok else 1


def cmd_report(args: argparse.Namespace) -> int:
    state = load_state(args.client)
    rows = state.get("rows", {})

    print(f"\n=== blog-csv-pipeline report — client: {args.client} ===\n")
    if not rows:
        print("No rows in state.json. Run --mode plan first.")
        return 0

    header = f"{'status':<8} {'words':>6}  {'keyword':<50}  file"
    print(header)
    print("-" * len(header))

    counts = {"done": 0, "failed": 0, "pending": 0}
    total_words = 0
    for kw, row in rows.items():
        status = row.get("status", "?")
        counts[status] = counts.get(status, 0) + 1
        wc = row.get("word_count") or 0
        total_words += wc if status == "done" else 0
        fp = row.get("file_path", "")
        rel_fp = (
            str(Path(fp).relative_to(ARTVISION_DATA))
            if fp and str(fp).startswith(str(ARTVISION_DATA))
            else fp
        )
        print(f"{status:<8} {wc:>6}  {kw[:50]:<50}  {rel_fp}")
        if row.get("error"):
            print(f"         └─ error: {row['error']}")

    print(
        f"\nSummary: done={counts.get('done', 0)} "
        f"failed={counts.get('failed', 0)} "
        f"pending={counts.get('pending', 0)} "
        f"total_words={total_words}"
    )
    return 0


def cmd_execute_dry(args: argparse.Namespace) -> int:
    """Dry-run / stub: writes placeholder MD files to test the state machine.

    Does NOT call content-writer — that requires Claude Task tool which is
    only available inside the agent process. For real generation use --mode plan
    and let Claude dispatch Tasks.
    """
    logger = setup_logger(args.client)
    csv_path = Path(args.csv).expanduser().resolve()
    ok, errors, rows = validate(csv_path)
    if not ok:
        for e in errors:
            logger.error(e)
        return 1

    state = load_state(args.client) if args.resume else {
        "client": args.client,
        "started_at": now_iso(),
        "rows": {},
    }

    drafts_dir(args.client).mkdir(parents=True, exist_ok=True)

    for row in rows:
        kw = row["keyword"]
        existing = state["rows"].get(kw)
        if args.resume and existing and existing.get("status") == "done":
            logger.info(f"SKIP: {kw}")
            continue

        slug = row.get("target_url_slug") or slugify(kw)
        out_path = drafts_dir(args.client) / f"{slug}.md"
        target_wc = row.get("word_count", 1500)

        # Write placeholder
        placeholder = (
            f"# {kw}\n\n"
            f"_DRY-RUN PLACEHOLDER — real generation requires Claude Task tool._\n\n"
            f"Target word count: {target_wc}\n"
            f"Generated at: {now_iso()}\n"
        )
        out_path.write_text(placeholder, encoding="utf-8")

        state["rows"][kw] = {
            "status": "done",
            "file_path": str(out_path),
            "word_count": len(placeholder.split()),
            "error": None,
            "ts": now_iso(),
            "dry_run": True,
        }
        logger.info(f"DRY-RUN wrote: {out_path}")
        save_state(args.client, state)

    return 0


def cmd_run_parallel_stub(args: argparse.Namespace) -> int:
    """TODO: parallel mode via concurrent.futures.ThreadPoolExecutor.

    Implementation sketch:
      - Build plan items (cmd_plan logic)
      - For each item, dispatch a worker that:
          * calls anthropic Messages API directly (requires API key from tokens.json)
          * OR writes a request file picked up by Claude in a loop
      - max_workers = args.concurrency (cap at 4)
      - Update state.json atomically (lock with fcntl.flock)

    Until implemented, use --mode plan and let Claude dispatch Tasks
    in parallel via multiple tool_use blocks in one assistant message.
    """
    print(
        "TODO: parallel mode not implemented yet.\n"
        "Workaround: use --mode plan, then Claude dispatches up to N Task tool "
        "calls in parallel via multiple tool_use blocks in one assistant message.\n"
        "See SKILL.md §9 TODO.",
        file=sys.stderr,
    )
    return 2


def main() -> int:
    p = argparse.ArgumentParser(
        description="blog-csv-pipeline: CSV → batch articles orchestrator"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # validate
    v = sub.add_parser("validate", help="Validate CSV format only")
    v.add_argument("--csv", required=True)
    v.set_defaults(func=cmd_validate)

    # plan (default workflow — print JSON plan for Claude to execute)
    pl = sub.add_parser("plan", help="Build execution plan (JSON for Claude)")
    pl.add_argument("--csv", required=True)
    pl.add_argument("--client", required=True)
    pl.add_argument(
        "--mode",
        choices=["sequential", "parallel"],
        default="sequential",
    )
    pl.add_argument("--concurrency", type=int, default=3)
    pl.add_argument("--resume", action="store_true")
    pl.set_defaults(func=cmd_plan)

    # mark (called by Claude after each Task completion)
    m = sub.add_parser("mark", help="Mark a keyword as done/failed in state.json")
    m.add_argument("--client", required=True)
    m.add_argument("--keyword", required=True)
    m.add_argument("--target-word-count", type=int, default=1500)
    m.set_defaults(func=cmd_mark)

    # report
    r = sub.add_parser("report", help="Print summary table from state.json")
    r.add_argument("--client", required=True)
    r.set_defaults(func=cmd_report)

    # execute-dry (writes placeholder MDs to test state machine)
    e = sub.add_parser(
        "execute-dry",
        help="Stub: write placeholder MDs to test state machine (no LLM)",
    )
    e.add_argument("--csv", required=True)
    e.add_argument("--client", required=True)
    e.add_argument("--resume", action="store_true")
    e.set_defaults(func=cmd_execute_dry)

    # run-parallel (stub)
    rp = sub.add_parser(
        "run-parallel",
        help="TODO: parallel orchestrator (currently stub)",
    )
    rp.add_argument("--client", required=True)
    rp.add_argument("--concurrency", type=int, default=3)
    rp.set_defaults(func=cmd_run_parallel_stub)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
