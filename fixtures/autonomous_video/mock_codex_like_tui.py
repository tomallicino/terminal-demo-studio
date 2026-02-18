from __future__ import annotations

import sys
import termios
import tty


def _render(plan_ready: bool, patch_applied: bool) -> None:
    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stdout.write("Codex-like Mock TUI\n")
    sys.stdout.write("===================\n\n")
    sys.stdout.write("[x] Connected\n")
    sys.stdout.write(f"[{'x' if plan_ready else ' '}] Plan ready\n")
    sys.stdout.write(f"[{'x' if patch_applied else ' '}] Patch applied\n\n")
    sys.stdout.write("Controls: p=plan, a=apply patch, q=quit\n")
    sys.stdout.flush()


def main() -> int:
    fd = sys.stdin.fileno()
    previous = termios.tcgetattr(fd)
    plan_ready = False
    patch_applied = False

    try:
        tty.setraw(fd)
        _render(plan_ready=plan_ready, patch_applied=patch_applied)

        while True:
            char = sys.stdin.read(1)
            if not char:
                continue
            if char == "p":
                plan_ready = True
            elif char == "a" and plan_ready:
                patch_applied = True
            elif char in {"q", "\x03"}:
                break
            _render(plan_ready=plan_ready, patch_applied=patch_applied)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, previous)

    sys.stdout.write("\nSession complete\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
