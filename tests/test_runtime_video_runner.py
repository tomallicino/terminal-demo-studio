from __future__ import annotations

import json
from pathlib import Path

import pytest

from terminal_demo_studio.runtime import video_runner


def _write_video_screenplay(path: Path) -> None:
    path.write_text(
        """
title: Demo
output: demo
settings: {}
scenarios:
  - label: One
    execution_mode: autonomous_video
    actions:
      - command: python3 mock.py
      - wait_for: Connected
        wait_mode: screen
        wait_timeout: 500ms
      - key: p
      - wait_for: Plan ready
        wait_mode: screen
        wait_timeout: 500ms
      - key: a
      - wait_for: Patch applied
        wait_mode: screen
        wait_timeout: 500ms
      - sleep: 100ms
""",
        encoding="utf-8",
    )


def test_video_runner_success_writes_summary_and_media(monkeypatch: object, tmp_path: Path) -> None:
    screenplay = tmp_path / "demo.yaml"
    _write_video_screenplay(screenplay)

    state = {"launched": False, "plan": False, "patch": False}

    monkeypatch.setattr(video_runner, "missing_local_video_dependencies", lambda: [])
    monkeypatch.setattr(video_runner, "_start_xvfb", lambda **_: object())
    monkeypatch.setattr(video_runner, "_start_kitty", lambda **_: object())
    monkeypatch.setattr(video_runner, "_start_ffmpeg_recording", lambda **_: object())
    monkeypatch.setattr(video_runner, "_wait_for_kitty_ready", lambda **_: None)
    monkeypatch.setattr(video_runner, "_stop_ffmpeg", lambda proc: None)
    monkeypatch.setattr(video_runner, "_stop_process", lambda proc, timeout_seconds=5.0: None)

    def fake_send_text(*, socket_target: str, env: dict[str, str], value: str) -> None:
        _ = socket_target
        _ = env
        if value.startswith("python3"):
            state["launched"] = True

    def fake_send_key(*, socket_target: str, env: dict[str, str], token: str) -> None:
        _ = socket_target
        _ = env
        key = video_runner._normalize_key_token(token)
        if key == "p":
            state["plan"] = True
        if key == "a" and state["plan"]:
            state["patch"] = True

    def fake_get_screen_text(*, socket_target: str, env: dict[str, str], adapter_name: str) -> str:
        _ = socket_target
        _ = env
        _ = adapter_name
        lines: list[str] = []
        if state["launched"]:
            lines.append("Connected")
        if state["plan"]:
            lines.append("Plan ready")
        if state["patch"]:
            lines.append("Patch applied")
        return "\n".join(lines)

    monkeypatch.setattr(video_runner, "_send_text", fake_send_text)
    monkeypatch.setattr(video_runner, "_send_key", fake_send_key)
    monkeypatch.setattr(video_runner, "_get_screen_text", fake_get_screen_text)

    def fake_compose(
        *,
        inputs: list[Path],
        labels: list[str],
        output_mp4: Path,
        output_gif: Path,
        playback_mode: str,
    ) -> None:
        _ = inputs
        _ = labels
        _ = playback_mode
        output_mp4.write_text("mp4", encoding="utf-8")
        output_gif.write_text("gif", encoding="utf-8")

    monkeypatch.setattr(video_runner, "compose_split_screen", fake_compose)

    result = video_runner.run_autonomous_video_screenplay(
        screenplay_path=screenplay,
        output_dir=tmp_path,
    )

    assert result.success is True
    assert result.mp4_path is not None
    assert result.gif_path is not None
    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    assert summary["lane"] == "autonomous_video"
    assert summary["status"] == "success"


def test_video_runner_fails_when_wait_condition_never_matches(
    monkeypatch: object, tmp_path: Path
) -> None:
    screenplay = tmp_path / "demo.yaml"
    screenplay.write_text(
        """
title: Demo
output: demo
settings: {}
scenarios:
  - label: One
    execution_mode: autonomous_video
    actions:
      - command: python3 mock.py
      - key: p
      - wait_for: Plan ready
        wait_mode: screen
        wait_timeout: 100ms
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(video_runner, "missing_local_video_dependencies", lambda: [])
    monkeypatch.setattr(video_runner, "_start_xvfb", lambda **_: object())
    monkeypatch.setattr(video_runner, "_start_kitty", lambda **_: object())
    monkeypatch.setattr(video_runner, "_start_ffmpeg_recording", lambda **_: object())
    monkeypatch.setattr(video_runner, "_wait_for_kitty_ready", lambda **_: None)
    monkeypatch.setattr(video_runner, "_stop_ffmpeg", lambda proc: None)
    monkeypatch.setattr(video_runner, "_stop_process", lambda proc, timeout_seconds=5.0: None)
    monkeypatch.setattr(video_runner, "_send_text", lambda **_: None)
    monkeypatch.setattr(video_runner, "_send_key", lambda **_: None)
    monkeypatch.setattr(video_runner, "_get_screen_text", lambda **_: "Connected")
    monkeypatch.setattr(video_runner, "compose_split_screen", lambda **_: None)

    result = video_runner.run_autonomous_video_screenplay(
        screenplay_path=screenplay,
        output_dir=tmp_path,
    )

    assert result.success is False
    assert result.failure_dir is not None
    reason = (result.failure_dir / "reason.txt").read_text(encoding="utf-8")
    assert "Plan ready" in reason


def test_video_runner_requires_local_dependencies(monkeypatch: object, tmp_path: Path) -> None:
    screenplay = tmp_path / "demo.yaml"
    _write_video_screenplay(screenplay)

    monkeypatch.setattr(video_runner, "missing_local_video_dependencies", lambda: ["kitty"])

    with pytest.raises(RuntimeError, match="Missing local autonomous_video dependencies"):
        video_runner.run_autonomous_video_screenplay(
            screenplay_path=screenplay, output_dir=tmp_path
        )
