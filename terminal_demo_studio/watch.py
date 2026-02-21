"""File-watching auto-render loop for ``tds watch``."""
from __future__ import annotations

import sys
import time
from collections.abc import Callable
from pathlib import Path


def run_watch(
    *,
    screenplay: Path,
    debounce_seconds: float,
    render_fn: Callable[[], None],
) -> None:
    """Poll *screenplay* and call *render_fn* when it changes.

    Uses simple ``stat().st_mtime`` polling — no external dependencies.
    The loop catches exceptions from *render_fn* so a broken render
    doesn't kill the watcher.

    Exits cleanly on ``KeyboardInterrupt`` (Ctrl+C).
    """
    screenplay_abs = screenplay.resolve()
    poll_interval = 0.25  # seconds
    last_mtime = 0.0

    try:
        last_mtime = screenplay_abs.stat().st_mtime
    except FileNotFoundError:
        print(f"watch: file not found: {screenplay_abs}", file=sys.stderr)
        raise SystemExit(1) from None

    print(f"Watching {screenplay_abs}", file=sys.stderr)
    print(f"Debounce: {int(debounce_seconds * 1000)}ms | Ctrl+C to stop", file=sys.stderr)

    try:
        while True:
            time.sleep(poll_interval)
            try:
                current_mtime = screenplay_abs.stat().st_mtime
            except FileNotFoundError:
                continue

            if current_mtime == last_mtime:
                continue

            # Debounce: wait then re-check (handles editors that write
            # multiple times when saving).
            time.sleep(debounce_seconds)
            try:
                final_mtime = screenplay_abs.stat().st_mtime
            except FileNotFoundError:
                continue

            if final_mtime == last_mtime:
                continue

            last_mtime = final_mtime
            print("\nChange detected — re-rendering …", file=sys.stderr)

            try:
                render_fn()
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                print(f"Render error: {exc}", file=sys.stderr)

    except KeyboardInterrupt:
        print("\nWatch stopped.", file=sys.stderr)
