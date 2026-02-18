from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from terminal_demo_studio.adapters import get_adapter
from terminal_demo_studio.artifacts import (
    RunLayout,
    create_run_layout,
    write_manifest,
    write_summary,
)
from terminal_demo_studio.editor import compose_split_screen
from terminal_demo_studio.models import Action, Screenplay, load_screenplay
from terminal_demo_studio.runtime.events import RuntimeEvent, append_event
from terminal_demo_studio.runtime.shells import build_shell_command
from terminal_demo_studio.runtime.waits import (
    duration_to_seconds,
    evaluate_wait_condition,
    wait_stable,
)

PlaybackMode = Literal["sequential", "simultaneous"]
_DEFAULT_WAIT_TIMEOUT_SECONDS = 20.0


@dataclass(slots=True)
class AutonomousVideoRunResult:
    success: bool
    run_layout: RunLayout
    run_dir: Path
    events_path: Path
    summary_path: Path
    failure_dir: Path | None
    mp4_path: Path | None
    gif_path: Path | None


def _binary_exists(name: str) -> bool:
    return shutil.which(name) is not None


def missing_local_video_dependencies() -> list[str]:
    missing: list[str] = []
    required = {
        "kitty": "kitty",
        "kitten": "kitten",
        "Xvfb": "xvfb",
        "ffmpeg": "ffmpeg",
        "ffprobe": "ffprobe",
    }
    for binary, label in required.items():
        if not _binary_exists(binary):
            missing.append(label)
    return missing


def _platform_family() -> str:
    system = platform.system().lower()
    if "windows" in system:
        return "windows"
    if "darwin" in system:
        return "macos"
    return "linux"


def format_local_video_dependency_help(missing: list[str]) -> str:
    if not missing:
        return ""
    family = _platform_family()
    missing_set = set(missing)
    commands_by_family: dict[str, list[str]] = {
        "linux": [
            "sudo apt-get update && sudo apt-get install -y kitty xvfb ffmpeg",
        ],
        "macos": [
            "brew install kitty ffmpeg",
            "brew install --cask xquartz",
            "Then run: /opt/X11/bin/Xvfb :99 -screen 0 1440x900x24",
        ],
        "windows": [
            "Use Docker mode for autonomous_video on Windows (local Xvfb is not supported).",
        ],
    }
    install_steps = " | ".join(commands_by_family.get(family, []))
    return (
        "Missing local autonomous_video dependencies: "
        f"{', '.join(sorted(missing_set))}. "
        f"Suggested fix: {install_steps}"
    )


def _action_name(action: Action) -> str:
    for key in [
        "command",
        "type",
        "input",
        "key",
        "hotkey",
        "wait_for",
        "wait_screen_regex",
        "wait_line_regex",
        "wait_stable",
        "assert_screen_regex",
        "assert_not_screen_regex",
        "expect_exit_code",
        "sleep",
    ]:
        value = getattr(action, key)
        if value is not None:
            return key
    return "unknown"


def _run_shell_command(command: str, cwd: Path, shell: str) -> tuple[str, int]:
    completed = subprocess.run(
        build_shell_command(command, shell),
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    return f"{completed.stdout}{completed.stderr}", completed.returncode


def _xvfb_display_id(index: int) -> str:
    return f":{140 + (os.getpid() % 400) + index}"


def _start_xvfb(
    *,
    display: str,
    width: int,
    height: int,
    log_file: Path,
) -> subprocess.Popen[str]:
    with log_file.open("a", encoding="utf-8") as handle:
        return subprocess.Popen(
            [
                "Xvfb",
                display,
                "-screen",
                "0",
                f"{width}x{height}x24",
                "-nolisten",
                "tcp",
            ],
            stdout=handle,
            stderr=handle,
            text=True,
        )


def _start_kitty(
    *,
    socket_target: str,
    env: dict[str, str],
    cwd: Path,
    log_file: Path,
) -> subprocess.Popen[str]:
    with log_file.open("a", encoding="utf-8") as handle:
        return subprocess.Popen(
            [
                "kitty",
                "--listen-on",
                socket_target,
                "-o",
                "allow_remote_control=yes",
                "-o",
                "disable_ligatures=never",
            ],
            cwd=cwd,
            env=env,
            stdout=handle,
            stderr=handle,
            text=True,
        )


def _start_ffmpeg_recording(
    *,
    display: str,
    width: int,
    height: int,
    framerate: int,
    output_path: Path,
    env: dict[str, str],
    log_file: Path,
) -> subprocess.Popen[str]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as handle:
        return subprocess.Popen(
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "x11grab",
                "-framerate",
                str(framerate),
                "-video_size",
                f"{width}x{height}",
                "-i",
                f"{display}.0",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(output_path),
            ],
            env=env,
            stdout=handle,
            stderr=handle,
            stdin=subprocess.PIPE,
            text=True,
        )


def _run_kitten(
    *,
    socket_target: str,
    env: dict[str, str],
    args: list[str],
    timeout: float = 10.0,
) -> str:
    completed = subprocess.run(
        ["kitten", "@", "--to", socket_target, *args],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "kitten call failed"
        raise RuntimeError(message)
    return completed.stdout


def _wait_for_kitty_ready(
    *, socket_target: str, env: dict[str, str], timeout_seconds: float
) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error = "kitty remote control not ready"
    while time.monotonic() < deadline:
        try:
            _run_kitten(socket_target=socket_target, env=env, args=["ls"], timeout=2.0)
            return
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            time.sleep(0.15)
    raise RuntimeError(last_error)


def _send_text(*, socket_target: str, env: dict[str, str], value: str) -> None:
    _run_kitten(socket_target=socket_target, env=env, args=["send-text", value], timeout=5.0)


def _normalize_key_token(value: str) -> str:
    token = value.strip()
    if "+" in token:
        parts = [part.strip().lower() for part in token.split("+") if part.strip()]
        return "+".join(parts)
    normalized_map = {
        "enter": "enter",
        "return": "enter",
        "tab": "tab",
        "up": "up",
        "down": "down",
        "left": "left",
        "right": "right",
        "esc": "esc",
        "escape": "esc",
        "backspace": "backspace",
        "space": "space",
    }
    lowered = token.lower()
    if lowered in normalized_map:
        return normalized_map[lowered]
    return token


def _send_key(*, socket_target: str, env: dict[str, str], token: str) -> None:
    _run_kitten(
        socket_target=socket_target,
        env=env,
        args=["send-key", _normalize_key_token(token)],
        timeout=5.0,
    )


def _get_screen_text(*, socket_target: str, env: dict[str, str], adapter_name: str) -> str:
    text = _run_kitten(socket_target=socket_target, env=env, args=["get-text"], timeout=5.0)
    adapter = get_adapter(adapter_name)
    return adapter.normalize_output(text)


def _resolve_wait_patterns(action: Action) -> tuple[str | None, str | None]:
    wait_screen_regex = action.wait_screen_regex
    wait_line_regex = action.wait_line_regex
    if action.wait_for:
        if action.wait_mode == "line":
            wait_line_regex = action.wait_for
        else:
            wait_screen_regex = action.wait_for
    return wait_screen_regex, wait_line_regex


def _poll_wait_condition(
    *,
    socket_target: str,
    env: dict[str, str],
    adapter_name: str,
    wait_screen_regex: str | None,
    wait_line_regex: str | None,
    timeout_seconds: float,
) -> tuple[bool, str, str]:
    deadline = time.monotonic() + timeout_seconds
    last_text = ""
    last_reason = "wait condition did not match"

    while True:
        last_text = _get_screen_text(
            socket_target=socket_target,
            env=env,
            adapter_name=adapter_name,
        )
        ok, reason = evaluate_wait_condition(
            last_text,
            wait_screen_regex=wait_screen_regex,
            wait_line_regex=wait_line_regex,
        )
        if ok:
            return True, "", last_text
        last_reason = reason
        if time.monotonic() >= deadline:
            return False, last_reason, last_text
        time.sleep(0.12)


def _write_failure_bundle(
    *,
    run_layout: RunLayout,
    screen_text: str,
    reason: str,
    step_index: int | None,
    action: str | None,
    scenario: str | None,
    log_path: Path | None,
) -> Path:
    failure_dir = run_layout.failure_dir
    failure_dir.mkdir(parents=True, exist_ok=True)
    (failure_dir / "screen.txt").write_text(screen_text, encoding="utf-8")
    (failure_dir / "reason.txt").write_text(reason, encoding="utf-8")
    if step_index is not None:
        payload = {
            "scenario": scenario,
            "step_index": step_index,
            "action": action,
            "reason": reason,
        }
        (failure_dir / "step.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    if log_path is not None and log_path.exists():
        (failure_dir / "video_runner.log").write_text(
            log_path.read_text(encoding="utf-8"), encoding="utf-8"
        )
    return failure_dir


def _stop_process(proc: subprocess.Popen[str] | None, timeout_seconds: float = 5.0) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=timeout_seconds)


def _stop_ffmpeg(ffmpeg_proc: subprocess.Popen[str] | None) -> None:
    if ffmpeg_proc is None or ffmpeg_proc.poll() is not None:
        return
    if ffmpeg_proc.stdin is not None:
        try:
            ffmpeg_proc.stdin.write("q\n")
            ffmpeg_proc.stdin.flush()
        except Exception:  # noqa: BLE001
            pass
    try:
        ffmpeg_proc.wait(timeout=6.0)
    except subprocess.TimeoutExpired:
        _stop_process(ffmpeg_proc)


def run_autonomous_video_screenplay(
    *,
    screenplay_path: Path,
    output_dir: Path | None = None,
    screenplay: Screenplay | None = None,
    keep_temp: bool = False,
    produce_mp4: bool = True,
    produce_gif: bool = True,
    playback_mode: PlaybackMode = "sequential",
) -> AutonomousVideoRunResult:
    if not produce_mp4 and not produce_gif:
        raise ValueError("At least one output type must be enabled")

    missing = missing_local_video_dependencies()
    if missing:
        raise RuntimeError(format_local_video_dependency_help(missing))

    loaded = screenplay if screenplay is not None else load_screenplay(screenplay_path)
    run_layout = create_run_layout(
        screenplay_path=screenplay_path,
        output_dir=output_dir,
        lane="autonomous_video",
    )
    write_manifest(
        run_layout,
        screenplay_path=screenplay_path,
        command="tds render",
        mode="autonomous_video",
    )

    events_path = run_layout.runtime_dir / "events.jsonl"
    summary_path = run_layout.summary_path
    log_path = run_layout.runtime_dir / "video_runner.log"
    log_path.write_text("", encoding="utf-8")
    working_dir = screenplay_path.resolve().parent

    success = True
    failure_reason = ""
    failure_dir: Path | None = None
    failed_step_index: int | None = None
    failed_action: str | None = None
    failed_scenario: str | None = None
    last_screen_snapshot = ""
    scene_videos: list[Path] = []
    scene_labels: list[str] = []

    for command in loaded.preinstall:
        output, exit_code = _run_shell_command(command, cwd=working_dir, shell="auto")
        append_event(
            events_path,
            RuntimeEvent(
                scenario="preinstall",
                step_index=-1,
                action="setup",
                status="ok" if exit_code == 0 else "failed",
                detail=command,
                exit_code=exit_code,
            ),
        )
        if exit_code != 0:
            success = False
            failure_reason = f"preinstall command failed: {command}\n{output}".strip()
            failed_step_index = -1
            failed_action = "setup"
            failed_scenario = "preinstall"
            break

    if success:
        for scenario_index, scenario in enumerate(loaded.scenarios):
            for setup_cmd in scenario.setup:
                output, exit_code = _run_shell_command(
                    setup_cmd,
                    cwd=working_dir,
                    shell=scenario.shell,
                )
                append_event(
                    events_path,
                    RuntimeEvent(
                        scenario=scenario.label,
                        step_index=-1,
                        action="setup",
                        status="ok" if exit_code == 0 else "failed",
                        detail=setup_cmd,
                        exit_code=exit_code,
                    ),
                )
                if exit_code != 0:
                    success = False
                    failure_reason = f"setup command failed: {setup_cmd}\n{output}".strip()
                    failed_step_index = -1
                    failed_action = "setup"
                    failed_scenario = scenario.label
                    break
            if not success:
                break

            display = _xvfb_display_id(scenario_index)
            # Keep socket path short enough for unix domain socket limits.
            socket_name = f"terminal-demo-studio-kitty-{os.getpid()}-{scenario_index}.sock"
            socket_path = Path(tempfile.gettempdir()) / socket_name
            socket_target = f"unix:{socket_path}"
            scene_video = run_layout.scenes_dir / f"scene_{scenario_index}.mp4"
            xvfb_proc: subprocess.Popen[str] | None = None
            kitty_proc: subprocess.Popen[str] | None = None
            ffmpeg_proc: subprocess.Popen[str] | None = None
            env = os.environ.copy()
            env["DISPLAY"] = display

            try:
                xvfb_proc = _start_xvfb(
                    display=display,
                    width=loaded.settings.width,
                    height=loaded.settings.height,
                    log_file=log_path,
                )
                time.sleep(0.3)
                kitty_proc = _start_kitty(
                    socket_target=socket_target,
                    env=env,
                    cwd=working_dir,
                    log_file=log_path,
                )
                _wait_for_kitty_ready(
                    socket_target=socket_target,
                    env=env,
                    timeout_seconds=10.0,
                )
                ffmpeg_proc = _start_ffmpeg_recording(
                    display=display,
                    width=loaded.settings.width,
                    height=loaded.settings.height,
                    framerate=loaded.settings.framerate,
                    output_path=scene_video,
                    env=env,
                    log_file=log_path,
                )
                time.sleep(0.25)

                for step_index, raw_action in enumerate(scenario.actions):
                    action = (
                        raw_action if isinstance(raw_action, Action) else Action(command=raw_action)
                    )
                    action_name = _action_name(action)
                    detail = ""
                    step_status = "ok"

                    try:
                        if action.expect_exit_code is not None:
                            raise RuntimeError(
                                "expect_exit_code is not supported in autonomous_video; "
                                "use screen assertions instead"
                            )

                        command_text = action.command or action.type
                        if command_text:
                            detail = command_text
                            _send_text(socket_target=socket_target, env=env, value=command_text)
                            _send_key(socket_target=socket_target, env=env, token="enter")

                        if action.input:
                            detail = action.input
                            _send_text(socket_target=socket_target, env=env, value=action.input)

                        if action.key:
                            detail = action.key
                            _send_key(socket_target=socket_target, env=env, token=action.key)

                        if action.hotkey:
                            detail = action.hotkey
                            _send_key(socket_target=socket_target, env=env, token=action.hotkey)

                        if action.sleep:
                            wait_stable(action.sleep)
                        if action.wait_stable:
                            wait_stable(action.wait_stable)

                        wait_screen_regex, wait_line_regex = _resolve_wait_patterns(action)
                        if wait_screen_regex or wait_line_regex:
                            timeout_seconds = (
                                duration_to_seconds(action.wait_timeout)
                                if action.wait_timeout
                                else _DEFAULT_WAIT_TIMEOUT_SECONDS
                            )
                            ok, message, last_screen_snapshot = _poll_wait_condition(
                                socket_target=socket_target,
                                env=env,
                                adapter_name=scenario.adapter,
                                wait_screen_regex=wait_screen_regex,
                                wait_line_regex=wait_line_regex,
                                timeout_seconds=timeout_seconds,
                            )
                            if not ok:
                                raise RuntimeError(message)
                        else:
                            last_screen_snapshot = _get_screen_text(
                                socket_target=socket_target,
                                env=env,
                                adapter_name=scenario.adapter,
                            )

                        if action.assert_screen_regex and not re.search(
                            action.assert_screen_regex,
                            last_screen_snapshot,
                            re.MULTILINE,
                        ):
                            raise RuntimeError(
                                f"assert_screen_regex failed: {action.assert_screen_regex}"
                            )
                        if action.assert_not_screen_regex and re.search(
                            action.assert_not_screen_regex,
                            last_screen_snapshot,
                            re.MULTILINE,
                        ):
                            raise RuntimeError(
                                f"assert_not_screen_regex failed: {action.assert_not_screen_regex}"
                            )
                    except Exception as exc:  # noqa: BLE001
                        step_status = "failed"
                        success = False
                        failure_reason = str(exc)
                        failed_step_index = step_index
                        failed_action = action_name
                        failed_scenario = scenario.label

                    append_event(
                        events_path,
                        RuntimeEvent(
                            scenario=scenario.label,
                            step_index=step_index,
                            action=action_name,
                            status=step_status,
                            detail=detail,
                            exit_code=None,
                        ),
                    )

                    if not success:
                        break

                time.sleep(0.2)
                _stop_ffmpeg(ffmpeg_proc)
                ffmpeg_proc = None
                scene_videos.append(scene_video)
                scene_labels.append(scenario.label)
            except Exception as exc:  # noqa: BLE001
                success = False
                failure_reason = str(exc)
                failed_step_index = failed_step_index if failed_step_index is not None else -1
                failed_action = failed_action or "scenario_bootstrap"
                failed_scenario = failed_scenario or scenario.label
            finally:
                _stop_ffmpeg(ffmpeg_proc)
                _stop_process(kitty_proc)
                _stop_process(xvfb_proc)
                if socket_path.exists():
                    socket_path.unlink(missing_ok=True)

            if not success:
                break

    final_mp4: Path | None = None
    final_gif: Path | None = None

    if success:
        output_stem = Path(loaded.output).stem
        final_mp4 = run_layout.media_dir / f"{output_stem}.mp4"
        final_gif = run_layout.media_dir / f"{output_stem}.gif"

        if keep_temp:
            temp_dir = run_layout.run_dir / "tmp"
            temp_dir.mkdir(parents=True, exist_ok=True)
        else:
            temp_dir = Path(tempfile.mkdtemp(prefix="terminal-demo-studio-autonomous-video-"))

        try:
            target_mp4 = final_mp4 if produce_mp4 else temp_dir / f"{output_stem}.discard.mp4"
            target_gif = final_gif if produce_gif else temp_dir / f"{output_stem}.discard.gif"
            compose_split_screen(
                inputs=scene_videos,
                labels=scene_labels,
                output_mp4=target_mp4,
                output_gif=target_gif,
                playback_mode=playback_mode,
            )
        except Exception as exc:  # noqa: BLE001
            success = False
            failure_reason = str(exc)
            failed_step_index = failed_step_index if failed_step_index is not None else -1
            failed_action = failed_action or "compose"
            failed_scenario = failed_scenario or "compose"
        finally:
            if not keep_temp:
                shutil.rmtree(temp_dir, ignore_errors=True)

    if not success:
        failure_dir = _write_failure_bundle(
            run_layout=run_layout,
            screen_text=last_screen_snapshot,
            reason=failure_reason,
            step_index=failed_step_index,
            action=failed_action,
            scenario=failed_scenario,
            log_path=log_path,
        )
        final_mp4 = None
        final_gif = None

    write_summary(
        run_layout,
        {
            "run_id": run_layout.run_id,
            "lane": "autonomous_video",
            "status": "success" if success else "failed",
            "screenplay": str(screenplay_path.resolve()),
            "events": str(events_path),
            "media": {
                "mp4": str(final_mp4)
                if success and produce_mp4 and final_mp4 is not None
                else None,
                "gif": str(final_gif)
                if success and produce_gif and final_gif is not None
                else None,
            },
            "failed_scenario": failed_scenario,
            "failed_step_index": failed_step_index,
            "failed_action": failed_action,
            "reason": "" if success else failure_reason,
            "failure_dir": str(failure_dir) if failure_dir is not None else None,
        },
    )

    return AutonomousVideoRunResult(
        success=success,
        run_layout=run_layout,
        run_dir=run_layout.run_dir,
        events_path=events_path,
        summary_path=summary_path,
        failure_dir=failure_dir,
        mp4_path=final_mp4 if success and produce_mp4 else None,
        gif_path=final_gif if success and produce_gif else None,
    )
