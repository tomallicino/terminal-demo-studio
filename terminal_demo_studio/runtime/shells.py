from __future__ import annotations

import platform
import shutil


def build_shell_command(command: str, shell: str = "auto") -> list[str]:
    target = shell.lower()
    if target in {"pwsh", "powershell"}:
        return ["powershell", "-NoProfile", "-Command", command]
    if target == "cmd":
        return ["cmd", "/C", command]
    if target == "bash":
        return ["bash", "-lc", command]
    if target in {"zsh", "fish", "sh"}:
        return [target, "-lc", command]

    if platform.system() == "Windows":
        if shutil.which("powershell"):
            return ["powershell", "-NoProfile", "-Command", command]
        return ["cmd", "/C", command]

    if shutil.which("bash"):
        return ["bash", "-lc", command]
    if shutil.which("sh"):
        return ["sh", "-lc", command]
    raise RuntimeError("No supported shell found (expected bash/sh on POSIX)")
