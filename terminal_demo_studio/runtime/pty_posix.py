from __future__ import annotations

import subprocess
from pathlib import Path

from terminal_demo_studio.runtime.shells import build_shell_command


def execute_command(command: str, cwd: Path, shell: str = "auto") -> tuple[str, int]:
    completed = subprocess.run(
        build_shell_command(command, shell),
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    output = f"{completed.stdout}{completed.stderr}"
    return output, completed.returncode
