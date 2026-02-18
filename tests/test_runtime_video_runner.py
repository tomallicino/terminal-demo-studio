from __future__ import annotations

import json
import os
import subprocess
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
        output_gif: Path | None,
        playback_mode: str,
        redaction_mode: str = "off",
    ) -> None:
        _ = inputs
        _ = labels
        _ = playback_mode
        _ = redaction_mode
        output_mp4.write_text("mp4", encoding="utf-8")
        if output_gif is not None:
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


def test_run_shell_command_times_out(monkeypatch: object, tmp_path: Path) -> None:
    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(
            cmd=["sh", "-lc", "echo hello"],
            timeout=1.0,
            output="partial",
            stderr="error",
        )

    monkeypatch.setattr(video_runner.subprocess, "run", fake_run)
    output, exit_code = video_runner._run_shell_command(
        "echo hello",
        cwd=tmp_path,
        shell="auto",
        timeout_seconds=1.0,
    )

    assert exit_code == 124
    assert "timed out" in output
    assert "partial" in output


def test_video_runner_redacts_sensitive_values_in_failure_bundle(
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
      - command: echo hello
""",
        encoding="utf-8",
    )

    secret = "sk-testsupersecretvalue123456"
    monkeypatch.setenv("OPENAI_API_KEY", secret)

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
        _ = value
        raise RuntimeError(f"secret leaked: {secret}")

    monkeypatch.setattr(video_runner, "_send_text", fake_send_text)
    monkeypatch.setattr(video_runner, "_send_key", lambda **_: None)
    monkeypatch.setattr(video_runner, "_get_screen_text", lambda **_: secret)
    monkeypatch.setattr(video_runner, "compose_split_screen", lambda **_: None)

    result = video_runner.run_autonomous_video_screenplay(
        screenplay_path=screenplay,
        output_dir=tmp_path,
    )

    assert result.success is False
    assert result.failure_dir is not None
    reason = (result.failure_dir / "reason.txt").read_text(encoding="utf-8")
    screen = (result.failure_dir / "screen.txt").read_text(encoding="utf-8")
    step = json.loads((result.failure_dir / "step.json").read_text(encoding="utf-8"))
    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))

    assert secret not in reason
    assert secret not in screen
    assert secret not in step["reason"]
    assert secret not in summary["reason"]
    assert "[REDACTED]" in reason


def test_start_kitty_uses_socket_only_remote_control(
    monkeypatch: object, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}

    class _Proc:
        pass

    def fake_popen(cmd: object, **kwargs: object) -> _Proc:
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return _Proc()

    monkeypatch.setattr(video_runner.subprocess, "Popen", fake_popen)

    log_file = tmp_path / "kitty.log"
    log_file.write_text("", encoding="utf-8")
    _ = video_runner._start_kitty(
        socket_target="unix:/tmp/test-kitty.sock",
        env=dict(os.environ),
        cwd=tmp_path,
        log_file=log_file,
    )

    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert "allow_remote_control=socket-only" in cmd


def test_video_runner_cleans_private_socket_dir(monkeypatch: object, tmp_path: Path) -> None:
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
      - command: echo ok
""",
        encoding="utf-8",
    )

    socket_dir = tmp_path / "kitty-private-socket"

    def fake_mkdtemp(*, prefix: str) -> str:
        if prefix.startswith("terminal-demo-studio-kitty-"):
            socket_dir.mkdir(parents=True, exist_ok=True)
            return str(socket_dir)
        raise AssertionError(f"Unexpected mkdtemp prefix: {prefix}")

    monkeypatch.setattr(video_runner.tempfile, "mkdtemp", fake_mkdtemp)
    monkeypatch.setattr(video_runner, "missing_local_video_dependencies", lambda: [])
    monkeypatch.setattr(video_runner, "_start_xvfb", lambda **_: object())
    monkeypatch.setattr(video_runner, "_start_kitty", lambda **_: object())
    monkeypatch.setattr(video_runner, "_start_ffmpeg_recording", lambda **_: object())
    monkeypatch.setattr(video_runner, "_wait_for_kitty_ready", lambda **_: None)
    monkeypatch.setattr(video_runner, "_stop_ffmpeg", lambda proc: None)
    monkeypatch.setattr(video_runner, "_stop_process", lambda proc, timeout_seconds=5.0: None)
    monkeypatch.setattr(video_runner, "_send_text", lambda **_: None)
    monkeypatch.setattr(video_runner, "_send_key", lambda **_: None)
    monkeypatch.setattr(video_runner, "_get_screen_text", lambda **_: "ok")

    def fake_compose(
        *,
        inputs: list[Path],
        labels: list[str],
        output_mp4: Path,
        output_gif: Path | None,
        playback_mode: str,
        redaction_mode: str = "off",
    ) -> None:
        _ = inputs
        _ = labels
        _ = playback_mode
        _ = redaction_mode
        output_mp4.write_text("mp4", encoding="utf-8")
        if output_gif is not None:
            output_gif.write_text("gif", encoding="utf-8")

    monkeypatch.setattr(video_runner, "compose_split_screen", fake_compose)

    result = video_runner.run_autonomous_video_screenplay(
        screenplay_path=screenplay,
        output_dir=tmp_path,
        keep_temp=True,
    )

    assert result.success is True
    assert not socket_dir.exists()


def test_wait_target_does_not_pass_if_only_present_before_action(
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
      - input: "TOKEN"
        wait_for: "TOKEN"
        wait_mode: "line"
        wait_timeout: "100ms"
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
    monkeypatch.setattr(video_runner, "_get_screen_text", lambda **_: "TOKEN")
    monkeypatch.setattr(video_runner, "compose_split_screen", lambda **_: None)

    result = video_runner.run_autonomous_video_screenplay(
        screenplay_path=screenplay,
        output_dir=tmp_path,
    )

    assert result.success is False
    assert result.failure_dir is not None
    reason = (result.failure_dir / "reason.txt").read_text(encoding="utf-8")
    assert "already present before action" in reason


def test_video_runner_auto_approves_agent_prompts_when_enabled(
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
    agent_prompts:
      allow_regex: "Press enter to confirm or esc to cancel"
    actions:
      - command: codex -a on-request -s workspace-write
        wait_for: "DONE"
        wait_mode: "screen"
        wait_timeout: "500ms"
""",
        encoding="utf-8",
    )

    screens = iter(
        [
            "",  # baseline
            "Press enter to confirm or esc to cancel",
            "Press enter to confirm or esc to cancel",
            "DONE",
            "DONE",
        ]
    )
    sent_keys: list[str] = []

    monkeypatch.setattr(video_runner, "missing_local_video_dependencies", lambda: [])
    monkeypatch.setattr(video_runner, "_start_xvfb", lambda **_: object())
    monkeypatch.setattr(video_runner, "_start_kitty", lambda **_: object())
    monkeypatch.setattr(video_runner, "_start_ffmpeg_recording", lambda **_: object())
    monkeypatch.setattr(video_runner, "_wait_for_kitty_ready", lambda **_: None)
    monkeypatch.setattr(video_runner, "_stop_ffmpeg", lambda proc: None)
    monkeypatch.setattr(video_runner, "_stop_process", lambda proc, timeout_seconds=5.0: None)
    monkeypatch.setattr(video_runner, "_send_text", lambda **_: None)

    def fake_send_key(*, socket_target: str, env: dict[str, str], token: str) -> None:
        _ = socket_target
        _ = env
        sent_keys.append(video_runner._normalize_key_token(token))

    monkeypatch.setattr(video_runner, "_send_key", fake_send_key)
    monkeypatch.setattr(video_runner, "_get_screen_text", lambda **_: next(screens))
    monkeypatch.setattr(video_runner, "compose_split_screen", lambda **_: None)

    result = video_runner.run_autonomous_video_screenplay(
        screenplay_path=screenplay,
        output_dir=tmp_path,
        agent_prompt_mode="approve",
    )

    assert result.success is True
    assert sent_keys.count("enter") >= 2
    events = result.events_path.read_text(encoding="utf-8")
    assert "agent_prompt" in events


def test_video_runner_auto_denies_agent_prompts_when_enabled(
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
      - command: codex -a on-request -s workspace-write
        wait_for: "CANCELLED"
        wait_mode: "screen"
        wait_timeout: "500ms"
""",
        encoding="utf-8",
    )

    screens = iter(
        [
            "",  # baseline
            "Press enter to confirm or esc to cancel",
            "CANCELLED",
            "CANCELLED",
        ]
    )
    sent_keys: list[str] = []

    monkeypatch.setattr(video_runner, "missing_local_video_dependencies", lambda: [])
    monkeypatch.setattr(video_runner, "_start_xvfb", lambda **_: object())
    monkeypatch.setattr(video_runner, "_start_kitty", lambda **_: object())
    monkeypatch.setattr(video_runner, "_start_ffmpeg_recording", lambda **_: object())
    monkeypatch.setattr(video_runner, "_wait_for_kitty_ready", lambda **_: None)
    monkeypatch.setattr(video_runner, "_stop_ffmpeg", lambda proc: None)
    monkeypatch.setattr(video_runner, "_stop_process", lambda proc, timeout_seconds=5.0: None)
    monkeypatch.setattr(video_runner, "_send_text", lambda **_: None)

    def fake_send_key(*, socket_target: str, env: dict[str, str], token: str) -> None:
        _ = socket_target
        _ = env
        sent_keys.append(video_runner._normalize_key_token(token))

    monkeypatch.setattr(video_runner, "_send_key", fake_send_key)
    monkeypatch.setattr(video_runner, "_get_screen_text", lambda **_: next(screens))
    monkeypatch.setattr(video_runner, "compose_split_screen", lambda **_: None)

    result = video_runner.run_autonomous_video_screenplay(
        screenplay_path=screenplay,
        output_dir=tmp_path,
        agent_prompt_mode="deny",
    )

    assert result.success is True
    assert "esc" in sent_keys


def test_video_runner_fails_fast_when_manual_prompt_blocks_wait(
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
      - command: codex -a on-request -s workspace-write
        wait_for: "DONE"
        wait_mode: "screen"
        wait_timeout: "500ms"
""",
        encoding="utf-8",
    )

    screens = [
        "",
        "Press enter to confirm or esc to cancel",
        "Press enter to confirm or esc to cancel",
    ]
    index = {"value": 0}

    monkeypatch.setattr(video_runner, "missing_local_video_dependencies", lambda: [])
    monkeypatch.setattr(video_runner, "_start_xvfb", lambda **_: object())
    monkeypatch.setattr(video_runner, "_start_kitty", lambda **_: object())
    monkeypatch.setattr(video_runner, "_start_ffmpeg_recording", lambda **_: object())
    monkeypatch.setattr(video_runner, "_wait_for_kitty_ready", lambda **_: None)
    monkeypatch.setattr(video_runner, "_stop_ffmpeg", lambda proc: None)
    monkeypatch.setattr(video_runner, "_stop_process", lambda proc, timeout_seconds=5.0: None)
    monkeypatch.setattr(video_runner, "_send_text", lambda **_: None)
    monkeypatch.setattr(video_runner, "_send_key", lambda **_: None)

    def fake_get_screen_text(**_: object) -> str:
        current = screens[min(index["value"], len(screens) - 1)]
        index["value"] += 1
        return current

    monkeypatch.setattr(video_runner, "_get_screen_text", fake_get_screen_text)
    monkeypatch.setattr(video_runner, "compose_split_screen", lambda **_: None)

    result = video_runner.run_autonomous_video_screenplay(
        screenplay_path=screenplay,
        output_dir=tmp_path,
    )

    assert result.success is False
    assert result.failure_dir is not None
    reason = (result.failure_dir / "reason.txt").read_text(encoding="utf-8")
    assert "interactive approval prompt detected while agent prompt automation is manual" in reason


def test_video_runner_allows_explicit_manual_wait_for_prompt(
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
      - command: codex -a on-request -s workspace-write
        wait_for: "Press enter to confirm or esc to cancel"
        wait_mode: "screen"
        wait_timeout: "500ms"
""",
        encoding="utf-8",
    )

    screens = [
        "",
        "Press enter to confirm or esc to cancel",
        "Press enter to confirm or esc to cancel",
    ]
    index = {"value": 0}

    monkeypatch.setattr(video_runner, "missing_local_video_dependencies", lambda: [])
    monkeypatch.setattr(video_runner, "_start_xvfb", lambda **_: object())
    monkeypatch.setattr(video_runner, "_start_kitty", lambda **_: object())
    monkeypatch.setattr(video_runner, "_start_ffmpeg_recording", lambda **_: object())
    monkeypatch.setattr(video_runner, "_wait_for_kitty_ready", lambda **_: None)
    monkeypatch.setattr(video_runner, "_stop_ffmpeg", lambda proc: None)
    monkeypatch.setattr(video_runner, "_stop_process", lambda proc, timeout_seconds=5.0: None)
    monkeypatch.setattr(video_runner, "_send_text", lambda **_: None)
    monkeypatch.setattr(video_runner, "_send_key", lambda **_: None)

    def fake_get_screen_text(**_: object) -> str:
        current = screens[min(index["value"], len(screens) - 1)]
        index["value"] += 1
        return current

    monkeypatch.setattr(video_runner, "_get_screen_text", fake_get_screen_text)
    monkeypatch.setattr(video_runner, "compose_split_screen", lambda **_: None)

    result = video_runner.run_autonomous_video_screenplay(
        screenplay_path=screenplay,
        output_dir=tmp_path,
    )

    assert result.success is True


def test_video_runner_rejects_unsafe_cli_approve_override(
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
      - command: codex -a on-request -s workspace-write
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(video_runner, "missing_local_video_dependencies", lambda: [])

    result = video_runner.run_autonomous_video_screenplay(
        screenplay_path=screenplay,
        output_dir=tmp_path,
        agent_prompt_mode="approve",
    )

    assert result.success is False
    assert result.failure_dir is not None
    reason = (result.failure_dir / "reason.txt").read_text(encoding="utf-8")
    assert "approve mode requires a non-empty allow_regex" in reason
    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    assert summary["failed_action"] == "policy_lint"


def test_video_runner_rejects_unbounded_approve_allow_regex(
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
    agent_prompts:
      mode: approve
      allow_regex: ".*"
    actions:
      - command: codex -a on-request -s workspace-write
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(video_runner, "missing_local_video_dependencies", lambda: [])

    result = video_runner.run_autonomous_video_screenplay(
        screenplay_path=screenplay,
        output_dir=tmp_path,
    )

    assert result.success is False
    assert result.failure_dir is not None
    reason = (result.failure_dir / "reason.txt").read_text(encoding="utf-8")
    assert "allow_regex is too broad" in reason


def test_video_runner_approve_respects_allowed_command_prefixes(
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
    agent_prompts:
      mode: approve
      allow_regex: "Press enter to confirm or esc to cancel"
      allowed_command_prefixes:
        - "mkdir "
    actions:
      - command: codex -a on-request -s workspace-write
        wait_for: "DONE"
        wait_mode: "screen"
        wait_timeout: "500ms"
""",
        encoding="utf-8",
    )

    screens = iter(
        [
            "",
            "Press enter to confirm or esc to cancel\n$ mkdir -p /tmp/demo",
            "DONE",
            "DONE",
        ]
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
    monkeypatch.setattr(video_runner, "_get_screen_text", lambda **_: next(screens))
    monkeypatch.setattr(video_runner, "compose_split_screen", lambda **_: None)

    result = video_runner.run_autonomous_video_screenplay(
        screenplay_path=screenplay,
        output_dir=tmp_path,
    )

    assert result.success is True


def test_video_runner_rejects_prompt_when_prefix_not_allowed(
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
    agent_prompts:
      mode: approve
      allow_regex: "Press enter to confirm or esc to cancel"
      allowed_command_prefixes:
        - "mkdir "
    actions:
      - command: codex -a on-request -s workspace-write
        wait_for: "DONE"
        wait_mode: "screen"
        wait_timeout: "500ms"
""",
        encoding="utf-8",
    )

    screens = iter(
        [
            "",
            "Press enter to confirm or esc to cancel\\n$ rm -rf /tmp/demo",
            "Press enter to confirm or esc to cancel\\n$ rm -rf /tmp/demo",
        ]
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
    monkeypatch.setattr(video_runner, "_get_screen_text", lambda **_: next(screens))
    monkeypatch.setattr(video_runner, "compose_split_screen", lambda **_: None)

    result = video_runner.run_autonomous_video_screenplay(
        screenplay_path=screenplay,
        output_dir=tmp_path,
    )

    assert result.success is False
    assert result.failure_dir is not None
    reason = (result.failure_dir / "reason.txt").read_text(encoding="utf-8")
    assert "allowed_command_prefixes" in reason


def test_extract_prompt_command_candidates_parses_prompt_shell_lines() -> None:
    commands = video_runner._extract_prompt_command_candidates(
        "Approve?\n$ mkdir -p /tmp/demo\n$ cat README.md\n"
    )

    assert commands == ["mkdir -p /tmp/demo", "cat README.md"]


def test_matches_allowed_command_prefixes_requires_all_commands() -> None:
    screen_text = "Approve?\n$ mkdir -p /tmp/demo\n$ rm -rf /tmp/demo\n"

    assert video_runner._matches_allowed_command_prefixes(
        screen_text,
        ("mkdir ", "cat "),
    ) is False
