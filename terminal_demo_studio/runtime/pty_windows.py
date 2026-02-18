from __future__ import annotations

from pathlib import Path

from terminal_demo_studio.runtime.pty_posix import execute_command as _execute


def execute_command(command: str, cwd: Path, shell: str = "auto") -> tuple[str, int]:
    # ConPTY implementation can replace this adapter later; use shell abstraction now.
    return _execute(command, cwd=cwd, shell=shell)
