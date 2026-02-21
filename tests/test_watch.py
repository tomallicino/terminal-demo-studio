from __future__ import annotations

import threading
import time
from pathlib import Path

from terminal_demo_studio.watch import run_watch


def test_watch_detects_file_change(tmp_path: Path) -> None:
    """Verify run_watch calls render_fn when the screenplay is modified."""
    screenplay = tmp_path / "demo.yaml"
    screenplay.write_text("title: v1\n", encoding="utf-8")

    call_count = 0
    render_error: Exception | None = None

    def render_fn() -> None:
        nonlocal call_count
        call_count += 1

    def run() -> None:
        nonlocal render_error
        try:
            run_watch(
                screenplay=screenplay,
                debounce_seconds=0.1,
                render_fn=render_fn,
            )
        except Exception as exc:
            render_error = exc

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    # Allow watcher to initialise
    time.sleep(0.5)

    # Modify the file
    screenplay.write_text("title: v2\n", encoding="utf-8")

    # Wait for debounce + poll
    time.sleep(1.0)

    assert call_count >= 1, "render_fn should have been called after file change"


def test_watch_does_not_render_without_change(tmp_path: Path) -> None:
    """Verify run_watch does not call render_fn when the file is not modified."""
    screenplay = tmp_path / "demo.yaml"
    screenplay.write_text("title: v1\n", encoding="utf-8")

    call_count = 0

    def render_fn() -> None:
        nonlocal call_count
        call_count += 1

    thread = threading.Thread(
        target=run_watch,
        kwargs={
            "screenplay": screenplay,
            "debounce_seconds": 0.1,
            "render_fn": render_fn,
        },
        daemon=True,
    )
    thread.start()
    time.sleep(1.0)

    assert call_count == 0, "render_fn should not be called without file changes"


def test_watch_survives_render_error(tmp_path: Path) -> None:
    """Verify run_watch continues after render_fn raises."""
    screenplay = tmp_path / "demo.yaml"
    screenplay.write_text("title: v1\n", encoding="utf-8")

    call_count = 0

    def failing_render() -> None:
        nonlocal call_count
        call_count += 1
        raise RuntimeError("boom")

    thread = threading.Thread(
        target=run_watch,
        kwargs={
            "screenplay": screenplay,
            "debounce_seconds": 0.1,
            "render_fn": failing_render,
        },
        daemon=True,
    )
    thread.start()

    time.sleep(0.5)
    screenplay.write_text("title: v2\n", encoding="utf-8")
    time.sleep(1.0)

    # Write again — watcher should still be alive after the error
    screenplay.write_text("title: v3\n", encoding="utf-8")
    time.sleep(1.0)

    assert call_count >= 2, "render_fn should be called again after surviving an error"
