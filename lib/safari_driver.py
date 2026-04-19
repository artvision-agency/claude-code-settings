#!/usr/bin/env python3
"""Shared Safari automation driver for Claude Code skills.

Wraps AppleScript + JavaScript execution for tab-targeted browser automation.
Used by: youtube-history, youtube-publish, (future) gmail-export, linkedin-scraper.

Design:
- SafariTab represents a specific tab matched by URL substring
- JS is safely escaped via json.dumps (fixes CRITICAL-class injection)
- All AppleScript calls check returncode
- Timeouts are explicit to prevent hangs
"""
from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass


@dataclass
class AppleScriptError(RuntimeError):
    """Raised when osascript fails (returncode != 0 or empty stdout)."""
    stderr: str
    returncode: int

    def __str__(self) -> str:
        return f"osascript rc={self.returncode}: {self.stderr.strip()}"


def run_applescript(script: str, timeout: float = 15.0) -> str:
    """Execute AppleScript and return stdout. Raises on osascript failure."""
    try:
        r = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise AppleScriptError(stderr=f"timeout after {timeout}s", returncode=-1) from e
    if r.returncode != 0:
        raise AppleScriptError(stderr=r.stderr, returncode=r.returncode)
    return r.stdout.strip()


class SafariTab:
    """Represents a Safari tab matched by URL substring.

    Example:
        tab = SafariTab(url_match="/feed/history",
                       open_url="https://www.youtube.com/feed/history")
        tab.ensure()
        result = tab.run_js("return document.title;")
    """

    def __init__(self, url_match: str, open_url: str | None = None):
        """
        Args:
            url_match: substring to find an existing tab (case-sensitive)
            open_url: URL to open if no matching tab found (fallback to url_match if None)
        """
        if not url_match:
            raise ValueError("url_match cannot be empty")
        self.url_match = url_match
        self.open_url = open_url or url_match

    def ensure(self, wait_load: float = 3.0) -> None:
        """Find an existing tab matching url_match, or open a new one.

        Does NOT change the front window — runs JS directly in the matched tab.
        """
        script = f'''tell application "Safari"
            set foundIt to false
            repeat with w in windows
                repeat with t in tabs of w
                    if URL of t contains {json.dumps(self.url_match)} then
                        set foundIt to true
                        exit repeat
                    end if
                end repeat
                if foundIt then exit repeat
            end repeat
            if not foundIt then
                if (count of windows) is 0 then
                    make new document with properties {{URL:{json.dumps(self.open_url)}}}
                else
                    tell front window to set current tab to (make new tab with properties {{URL:{json.dumps(self.open_url)}}})
                end if
            end if
        end tell'''
        run_applescript(script)
        if wait_load > 0:
            time.sleep(wait_load)

    def run_js(self, js: str, timeout: float = 15.0) -> str:
        """Execute JavaScript inside the matched tab.

        JS is wrapped in an IIFE and safely quoted via json.dumps to
        prevent AppleScript injection when js contains quotes/newlines.
        """
        # Wrap JS in IIFE so `return` works at the top level
        if not js.lstrip().startswith("("):
            js = f"(function(){{ {js} }})();"

        quoted_js = json.dumps(js)
        quoted_match = json.dumps(self.url_match)
        script = f'''tell application "Safari"
            set resultValue to ""
            repeat with w in windows
                repeat with t in tabs of w
                    if URL of t contains {quoted_match} then
                        set resultValue to (do JavaScript {quoted_js} in t)
                        exit repeat
                    end if
                end repeat
                if resultValue is not "" then exit repeat
            end repeat
            return resultValue
        end tell'''
        return run_applescript(script, timeout=timeout)

    def scroll(self, iterations: int = 5, delta_px: int = 1500, pause: float = 1.5) -> None:
        """Scroll the tab down repeatedly to trigger infinite-scroll loading."""
        for _ in range(iterations):
            self.run_js(f"window.scrollBy(0, {delta_px});")
            time.sleep(pause)

    def current_url(self) -> str:
        """Return the current URL of the matched tab."""
        quoted_match = json.dumps(self.url_match)
        script = f'''tell application "Safari"
            repeat with w in windows
                repeat with t in tabs of w
                    if URL of t contains {quoted_match} then
                        return URL of t
                    end if
                end repeat
            end repeat
            return ""
        end tell'''
        return run_applescript(script)


if __name__ == "__main__":
    # Self-test: try opening a simple page
    import sys
    tab = SafariTab(url_match="example.com", open_url="https://example.com/")
    try:
        tab.ensure()
        title = tab.run_js("return document.title;")
        print(f"OK — opened tab, title: {title}")
    except AppleScriptError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
