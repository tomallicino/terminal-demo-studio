from __future__ import annotations

import json
from pathlib import Path

from terminal_demo_studio.runtime.runner import run_autonomous_screenplay


def test_autonomous_runner_writes_event_log_and_summary(tmp_path: Path) -> None:
    screenplay = tmp_path / "demo.yaml"
    screenplay.write_text(
        """
title: Demo
output: demo
settings: {}
scenarios:
  - label: One
    execution_mode: autonomous_pty
    actions:
      - command: echo hello
      - wait_screen_regex: hello
""",
        encoding="utf-8",
    )

    result = run_autonomous_screenplay(screenplay_path=screenplay, output_dir=tmp_path)

    assert result.success is True
    assert result.events_path.exists()
    assert result.summary_path.exists()
    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    assert summary["success"] is True


def test_autonomous_runner_writes_failure_bundle(tmp_path: Path) -> None:
    screenplay = tmp_path / "demo.yaml"
    screenplay.write_text(
        """
title: Demo
output: demo
settings: {}
scenarios:
  - label: One
    execution_mode: autonomous_pty
    actions:
      - command: echo hello
      - assert_screen_regex: does-not-exist
""",
        encoding="utf-8",
    )

    result = run_autonomous_screenplay(screenplay_path=screenplay, output_dir=tmp_path)

    assert result.success is False
    assert result.failure_dir is not None
    assert (result.failure_dir / "screen.txt").exists()


def test_autonomous_runner_fails_on_interactive_key_action(tmp_path: Path) -> None:
    screenplay = tmp_path / "demo.yaml"
    screenplay.write_text(
        """
title: Demo
output: demo
settings: {}
scenarios:
  - label: One
    execution_mode: autonomous_pty
    actions:
      - key: Enter
""",
        encoding="utf-8",
    )

    result = run_autonomous_screenplay(screenplay_path=screenplay, output_dir=tmp_path)

    assert result.success is False
    assert result.failure_dir is not None
    reason = (result.failure_dir / "reason.txt").read_text(encoding="utf-8")
    assert "interactive input action" in reason
