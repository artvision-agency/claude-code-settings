"""Minimal Telethon-based E2E runner for Telegram bots.

Reads YAML scenarios from tests/e2e/scenarios/*.yaml and drives the bot
as a real user would.

Usage:
    python tests/e2e/runner.py tests/e2e/scenarios/flow_basic.yaml
    python tests/e2e/runner.py tests/e2e/scenarios/  # all files in dir

Env vars (required):
    TG_API_ID          — from my.telegram.org
    TG_API_HASH        — from my.telegram.org
    TG_SESSION         — path to Telethon session file
    TG_BOT_USERNAME    — e.g. @my_bot (without @ ok)

Scenario shapes supported:
    - send_command:  "/start"
    - send_text:     "Hello"
    - click_button:  "Button label"            # reply keyboard
    - click_callback: "Button label"           # inline keyboard
    - assert_contains:  substring
    - assert_matches:   regex
    - assert_keyboard:  ["Btn 1", "Btn 2"]     # checks inline/reply buttons
    - sleep:         seconds (float)
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from telethon import TelegramClient
from telethon.tl.custom.message import Message


@dataclass
class StepResult:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class ScenarioResult:
    name: str
    steps: list[StepResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(s.ok for s in self.steps)


def _env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        print(f"[ERROR] env var {name} is required", file=sys.stderr)
        sys.exit(2)
    return val


async def _wait_for_response(
    client: TelegramClient, bot: str, after_msg_id: int, timeout: float = 10.0
) -> Message | None:
    """Poll dialog for next message from bot after the given message id."""
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        async for msg in client.iter_messages(bot, limit=5):
            if msg.id > after_msg_id and msg.out is False:
                return msg
        await asyncio.sleep(0.3)
    return None


def _extract_keyboard_labels(msg: Message) -> list[str]:
    labels: list[str] = []
    if not msg.reply_markup:
        return labels
    rows = getattr(msg.reply_markup, "rows", [])
    for row in rows:
        for btn in getattr(row, "buttons", []):
            if hasattr(btn, "text"):
                labels.append(btn.text)
    return labels


async def _run_step(
    client: TelegramClient,
    bot: str,
    step: dict[str, Any],
    state: dict[str, Any],
) -> StepResult:
    kind = next(iter(step.keys()))
    value = step[kind]

    if kind == "send_command" or kind == "send_text":
        sent = await client.send_message(bot, str(value))
        state["last_sent_id"] = sent.id
        reply = await _wait_for_response(client, bot, sent.id)
        state["last_reply"] = reply
        return StepResult(name=f"{kind}: {value}", ok=reply is not None,
                          detail="no reply" if reply is None else f"reply id={reply.id}")

    if kind == "click_button":
        reply = state.get("last_reply")
        if reply is None:
            return StepResult(name=f"click_button: {value}", ok=False, detail="no prior reply")
        try:
            await reply.click(text=str(value))
        except Exception as exc:  # noqa: BLE001
            return StepResult(name=f"click_button: {value}", ok=False, detail=str(exc))
        next_reply = await _wait_for_response(client, bot, reply.id)
        state["last_reply"] = next_reply
        return StepResult(name=f"click_button: {value}", ok=next_reply is not None)

    if kind == "click_callback":
        reply = state.get("last_reply")
        if reply is None:
            return StepResult(name=f"click_callback: {value}", ok=False, detail="no prior reply")
        try:
            await reply.click(text=str(value))
        except Exception as exc:  # noqa: BLE001
            return StepResult(name=f"click_callback: {value}", ok=False, detail=str(exc))
        next_reply = await _wait_for_response(client, bot, reply.id)
        state["last_reply"] = next_reply
        return StepResult(name=f"click_callback: {value}", ok=next_reply is not None)

    if kind == "assert_contains":
        reply = state.get("last_reply")
        text = reply.message if reply else ""
        ok = str(value) in text
        return StepResult(name=f"assert_contains: {value}", ok=ok,
                          detail="" if ok else f"got: {text[:120]!r}")

    if kind == "assert_matches":
        reply = state.get("last_reply")
        text = reply.message if reply else ""
        ok = bool(re.search(str(value), text))
        return StepResult(name=f"assert_matches: {value}", ok=ok,
                          detail="" if ok else f"got: {text[:120]!r}")

    if kind == "assert_keyboard":
        reply = state.get("last_reply")
        expected: list[str] = list(value)
        actual = _extract_keyboard_labels(reply) if reply else []
        missing = [x for x in expected if x not in actual]
        ok = not missing
        return StepResult(name=f"assert_keyboard: {expected}", ok=ok,
                          detail="" if ok else f"missing: {missing}, got: {actual}")

    if kind == "sleep":
        await asyncio.sleep(float(value))
        return StepResult(name=f"sleep: {value}", ok=True)

    return StepResult(name=f"unknown: {kind}", ok=False, detail="unknown step kind")


async def run_scenario(client: TelegramClient, bot: str, path: Path) -> ScenarioResult:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    name = raw.get("name", path.stem)
    steps_spec: list[dict[str, Any]] = raw.get("steps", [])
    result = ScenarioResult(name=name)
    state: dict[str, Any] = {}
    for step in steps_spec:
        sr = await _run_step(client, bot, step, state)
        result.steps.append(sr)
        if not sr.ok:
            break
    return result


async def main(targets: list[str]) -> int:
    api_id = int(_env("TG_API_ID"))
    api_hash = _env("TG_API_HASH")
    session = _env("TG_SESSION")
    bot = _env("TG_BOT_USERNAME").lstrip("@")

    paths: list[Path] = []
    for t in targets:
        p = Path(t)
        if p.is_dir():
            paths.extend(sorted(p.glob("*.yaml")))
        elif p.is_file():
            paths.append(p)
    paths = [p for p in paths if not p.name.startswith("_")]

    if not paths:
        print("[ERROR] no scenarios found", file=sys.stderr)
        return 2

    async with TelegramClient(session, api_id, api_hash) as client:
        results: list[ScenarioResult] = []
        for path in paths:
            print(f"[RUN] {path}")
            r = await run_scenario(client, bot, path)
            results.append(r)
            for step in r.steps:
                mark = "OK " if step.ok else "FAIL"
                print(f"  {mark} {step.name}" + (f" — {step.detail}" if step.detail else ""))

    failed = [r for r in results if not r.ok]
    print("---")
    print(f"scenarios: {len(results)}, passed: {len(results) - len(failed)}, failed: {len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: runner.py <scenario.yaml | dir/>")
        sys.exit(2)
    sys.exit(asyncio.run(main(sys.argv[1:])))
