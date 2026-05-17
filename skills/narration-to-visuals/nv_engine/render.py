"""RENDER step: invoke Remotion to produce visualized.mp4.

The actual `npx remotion render` is heavy (Node + Chromium), so it is
behind a Runner protocol: FakeRunner for tests, SubprocessRunner for
real use. render_video builds the command, runs it, and asserts the
output exists.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Protocol


class RenderError(RuntimeError):
    pass


class Runner(Protocol):
    def run(self, cmd: list[str], cwd: Path) -> int:
        ...


class FakeRunner:
    """Test runner: records the command, optionally writes a stub mp4."""

    def __init__(self, returncode: int = 0, write_output: bool = True):
        self._rc = returncode
        self._write = write_output
        self.last_cmd: list[str] = []
        self.last_cwd: Path | None = None

    def run(self, cmd: list[str], cwd: Path) -> int:
        self.last_cmd = cmd
        self.last_cwd = cwd
        if self._write and self._rc == 0:
            # output path is the token right before "--props" (stable
            # contract: `npx remotion render <entry> <comp> <out> --props ...`)
            out = Path(cmd[cmd.index("--props") - 1])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"\x00FAKEMP4")
        return self._rc


class SubprocessRunner:
    def run(self, cmd: list[str], cwd: Path) -> int:  # pragma: no cover
        return subprocess.run(cmd, cwd=str(cwd), check=False).returncode


def render_video(*, props_path: Path, remotion_dir: Path, out_path: Path,
                 runner: Runner) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Remotion v4 CLI: npx remotion render <entry> <composition-id> <out> [opts]
    cmd = ["npx", "remotion", "render", "src/index.ts", "Main",
           str(out_path), "--props", str(props_path)]
    rc = runner.run(cmd, remotion_dir)
    if rc != 0:
        raise RenderError(f"remotion render failed (exit {rc})")
    if not out_path.exists():
        raise RenderError(f"remotion render produced no output: {out_path}")
