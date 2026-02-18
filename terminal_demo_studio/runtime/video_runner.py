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
from terminal_demo_studio.models import Action, AgentPromptPolicy, Screenplay, load_screenplay
from terminal_demo_studio.prompt_policy import (
    lint_agent_prompt_policy,
    resolve_merged_agent_prompt_policy,
)
from terminal_demo_studio.redaction import (
    MediaRedactionMode,
    resolve_media_redaction_mode,
)
from terminal_demo_studio.runtime.events import RuntimeEvent, append_event
from terminal_demo_studio.runtime.shells import build_shell_command
from terminal_demo_studio.runtime.waits import (
    duration_to_seconds,
    evaluate_wait_condition,
    wait_stable,
)

PlaybackMode = Literal["sequential", "simultaneous"]
AgentPromptMode = Literal["auto", "manual", "approve", "deny"]
_DEFAULT_WAIT_TIMEOUT_SECONDS = 20.0
_DEFAULT_SETUP_TIMEOUT_SECONDS = 120.0
_MANUAL_AGENT_PROMPT_REASON = (
    "interactive approval prompt detected while agent prompt automation is manual; "
    "set --agent-prompts approve|deny or configure agent_prompts.mode"
)
_REDACTED_TOKEN = "[REDACTED]"
_SENSITIVE_VALUE_ENV_NAMES = (
    "OPENAI_API_KEY",
    "OPENAI_ORGANIZATION",
    "OPENAI_BASE_URL",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "GITHUB_TOKEN",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
)
_SENSITIVE_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
)


@dataclass(slots=True)
class RuntimeAgentPromptPolicy:
    mode: Literal["approve", "deny"]
    prompt_regex: str
    allow_regex: str | None
    allowed_command_prefixes: tuple[str, ...]
    max_rounds: int
    approve_key: str
    deny_key: str


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


def _setup_timeout_seconds() -> float:
    raw = os.environ.get("TDS_SETUP_TIMEOUT_SECONDS", str(_DEFAULT_SETUP_TIMEOUT_SECONDS)).strip()
    try:
        parsed = float(raw)
    except ValueError:
        return _DEFAULT_SETUP_TIMEOUT_SECONDS
    if parsed <= 0:
        return _DEFAULT_SETUP_TIMEOUT_SECONDS
    return parsed


def _sensitive_values() -> list[str]:
    values: list[str] = []
    for name in _SENSITIVE_VALUE_ENV_NAMES:
        value = os.environ.get(name)
        if value and len(value) >= 6:
            values.append(value)
    return values


def _redact_sensitive_text(value: str) -> str:
    redacted = value
    for secret in _sensitive_values():
        redacted = redacted.replace(secret, _REDACTED_TOKEN)
    for pattern in _SENSITIVE_PATTERNS:
        redacted = pattern.sub(_REDACTED_TOKEN, redacted)
    return redacted


def _coerce_agent_prompt_mode(value: str) -> AgentPromptMode:
    normalized = value.strip().lower()
    if normalized in {"auto", "manual", "approve", "deny"}:
        return normalized  # type: ignore[return-value]
    return "auto"


def _env_agent_prompt_mode() -> Literal["manual", "approve", "deny"] | None:
    raw = os.environ.get("TDS_AGENT_PROMPTS")
    if raw is None:
        return None
    mode = _coerce_agent_prompt_mode(raw)
    if mode == "auto":
        return None
    return mode


def _allow_unbounded_approve_from_env() -> bool:
    raw = os.environ.get("TDS_ALLOW_UNSAFE_APPROVE", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _resolve_merged_agent_prompt_policy(
    *,
    screenplay_policy: AgentPromptPolicy | None,
    scenario_policy: AgentPromptPolicy | None,
    override_mode: AgentPromptMode,
) -> AgentPromptPolicy:
    env_mode = _env_agent_prompt_mode()
    return resolve_merged_agent_prompt_policy(
        screenplay_policy=screenplay_policy,
        scenario_policy=scenario_policy,
        override_mode=override_mode,
        env_mode=env_mode,
    )


def _resolve_agent_prompt_policy(policy: AgentPromptPolicy) -> RuntimeAgentPromptPolicy | None:
    if policy.mode == "manual":
        return None

    return RuntimeAgentPromptPolicy(
        mode=policy.mode,
        prompt_regex=policy.prompt_regex,
        allow_regex=policy.allow_regex,
        allowed_command_prefixes=tuple(policy.allowed_command_prefixes),
        max_rounds=policy.max_rounds,
        approve_key=policy.approve_key,
        deny_key=policy.deny_key,
    )


def _resolve_prompt_detection_regex(policy: AgentPromptPolicy) -> str:
    return policy.prompt_regex


def _extract_prompt_command_candidates(screen_text: str) -> list[str]:
    command_lines = re.findall(r"(?m)^\s*\$\s+(.+)$", screen_text)
    return [line.strip() for line in command_lines if line.strip()]


def _matches_allowed_command_prefixes(screen_text: str, prefixes: tuple[str, ...]) -> bool:
    if not prefixes:
        return True
    commands = _extract_prompt_command_candidates(screen_text)
    if not commands:
        return False
    return all(
        any(command.startswith(prefix) for prefix in prefixes)
        for command in commands
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


def _run_shell_command(
    command: str,
    cwd: Path,
    shell: str,
    *,
    timeout_seconds: float,
) -> tuple[str, int]:
    try:
        completed = subprocess.run(
            build_shell_command(command, shell),
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        if isinstance(exc.stdout, bytes):
            stdout = exc.stdout.decode("utf-8", errors="replace")
        else:
            stdout = exc.stdout or ""
        if isinstance(exc.stderr, bytes):
            stderr = exc.stderr.decode("utf-8", errors="replace")
        else:
            stderr = exc.stderr or ""
        partial_output = f"{stdout}{stderr}"
        output = (
            f"Command timed out after {timeout_seconds:.1f}s: {command}\n{partial_output}".strip()
        )
        return output, 124
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
                "allow_remote_control=socket-only",
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
    baseline_text: str | None = None,
    scenario: str | None = None,
    step_index: int | None = None,
    events_path: Path | None = None,
    prompt_policy: RuntimeAgentPromptPolicy | None = None,
    prompt_detection_regex: str | None = None,
) -> tuple[bool, str, str]:
    deadline = time.monotonic() + timeout_seconds
    last_text = ""
    last_reason = "wait condition did not match"
    prompts_handled = 0
    baseline_matches = False
    if baseline_text is not None:
        baseline_matches, _ = evaluate_wait_condition(
            baseline_text,
            wait_screen_regex=wait_screen_regex,
            wait_line_regex=wait_line_regex,
        )

    while True:
        last_text = _get_screen_text(
            socket_target=socket_target,
            env=env,
            adapter_name=adapter_name,
        )
        if prompt_policy and re.search(prompt_policy.prompt_regex, last_text, re.MULTILINE):
            prompts_handled += 1
            if prompts_handled > prompt_policy.max_rounds:
                return (
                    False,
                    (
                        "agent prompt remained unresolved after "
                        f"{prompt_policy.max_rounds} automated rounds"
                    ),
                    last_text,
                )

            decision = prompt_policy.mode
            if decision == "approve" and prompt_policy.allow_regex:
                if not re.search(prompt_policy.allow_regex, last_text, re.MULTILINE):
                    return (
                        False,
                        (
                            "agent prompt did not match allow_regex; "
                            "refusing automated approval"
                        ),
                        last_text,
                    )
            if decision == "approve" and prompt_policy.allowed_command_prefixes:
                if not _matches_allowed_command_prefixes(
                    last_text, prompt_policy.allowed_command_prefixes
                ):
                    return (
                        False,
                        (
                            "agent prompt command did not match "
                            "allowed_command_prefixes; refusing automated approval"
                        ),
                        last_text,
                    )

            key = prompt_policy.approve_key if decision == "approve" else prompt_policy.deny_key
            _send_key(socket_target=socket_target, env=env, token=key)
            if events_path is not None and scenario is not None and step_index is not None:
                append_event(
                    events_path,
                    RuntimeEvent(
                        scenario=scenario,
                        step_index=step_index,
                        action="agent_prompt",
                        status="ok",
                        detail=_redact_sensitive_text(
                            f"{decision} round {prompts_handled} ({key})"
                        ),
                        exit_code=None,
                    ),
                )
            time.sleep(0.2)
            continue

        ok, reason = evaluate_wait_condition(
            last_text,
            wait_screen_regex=wait_screen_regex,
            wait_line_regex=wait_line_regex,
        )
        if ok and baseline_matches and baseline_text is not None and last_text == baseline_text:
            ok = False
            reason = "wait target already present before action; waiting for screen update"
        if ok:
            return True, "", last_text
        if (
            prompt_policy is None
            and prompt_detection_regex
            and re.search(prompt_detection_regex, last_text, re.MULTILINE)
        ):
            return False, _MANUAL_AGENT_PROMPT_REASON, last_text
        last_reason = reason
        if time.monotonic() >= deadline:
            return False, last_reason, last_text
        time.sleep(0.12)


def _drain_agent_prompts(
    *,
    socket_target: str,
    env: dict[str, str],
    adapter_name: str,
    scenario: str,
    step_index: int,
    events_path: Path,
    prompt_policy: RuntimeAgentPromptPolicy | None,
) -> str:
    last_text = _get_screen_text(
        socket_target=socket_target,
        env=env,
        adapter_name=adapter_name,
    )
    if prompt_policy is None:
        return last_text

    for round_index in range(prompt_policy.max_rounds):
        if not re.search(prompt_policy.prompt_regex, last_text, re.MULTILINE):
            return last_text
        if prompt_policy.mode == "approve" and prompt_policy.allow_regex:
            if not re.search(prompt_policy.allow_regex, last_text, re.MULTILINE):
                raise RuntimeError("agent prompt did not match allow_regex; refusing approval")
        if prompt_policy.mode == "approve" and prompt_policy.allowed_command_prefixes:
            if not _matches_allowed_command_prefixes(
                last_text, prompt_policy.allowed_command_prefixes
            ):
                raise RuntimeError(
                    "agent prompt command did not match allowed_command_prefixes; "
                    "refusing approval"
                )
        key = (
            prompt_policy.approve_key
            if prompt_policy.mode == "approve"
            else prompt_policy.deny_key
        )
        _send_key(socket_target=socket_target, env=env, token=key)
        append_event(
            events_path,
            RuntimeEvent(
                scenario=scenario,
                step_index=step_index,
                action="agent_prompt",
                status="ok",
                detail=_redact_sensitive_text(
                    f"{prompt_policy.mode} round {round_index + 1} ({key})"
                ),
                exit_code=None,
            ),
        )
        time.sleep(0.2)
        last_text = _get_screen_text(
            socket_target=socket_target,
            env=env,
            adapter_name=adapter_name,
        )

    if re.search(prompt_policy.prompt_regex, last_text, re.MULTILINE):
        raise RuntimeError(
            f"agent prompt remained unresolved after {prompt_policy.max_rounds} automated rounds"
        )
    return last_text


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
    redacted_screen = _redact_sensitive_text(screen_text)
    redacted_reason = _redact_sensitive_text(reason)
    (failure_dir / "screen.txt").write_text(redacted_screen, encoding="utf-8")
    (failure_dir / "reason.txt").write_text(redacted_reason, encoding="utf-8")
    if step_index is not None:
        payload = {
            "scenario": scenario,
            "step_index": step_index,
            "action": action,
            "reason": redacted_reason,
        }
        (failure_dir / "step.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    if log_path is not None and log_path.exists():
        (failure_dir / "video_runner.log").write_text(
            _redact_sensitive_text(log_path.read_text(encoding="utf-8")), encoding="utf-8"
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
    agent_prompt_mode: AgentPromptMode = "auto",
    media_redaction_mode: MediaRedactionMode = "auto",
) -> AutonomousVideoRunResult:
    if not produce_mp4 and not produce_gif:
        raise ValueError("At least one output type must be enabled")

    missing = missing_local_video_dependencies()
    if missing:
        raise RuntimeError(format_local_video_dependency_help(missing))

    loaded = screenplay if screenplay is not None else load_screenplay(screenplay_path)
    resolved_redaction_mode = resolve_media_redaction_mode(
        screenplay=loaded,
        override_mode=media_redaction_mode,
    )
    resolved_agent_prompt_mode = _coerce_agent_prompt_mode(agent_prompt_mode)
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
    setup_timeout_seconds = _setup_timeout_seconds()
    scenario_prompt_modes: dict[str, str] = {}
    scenario_prompt_warnings: dict[str, list[str]] = {}

    for command in loaded.preinstall:
        output, exit_code = _run_shell_command(
            command,
            cwd=working_dir,
            shell="auto",
            timeout_seconds=setup_timeout_seconds,
        )
        append_event(
            events_path,
            RuntimeEvent(
                scenario="preinstall",
                step_index=-1,
                action="setup",
                status="ok" if exit_code == 0 else "failed",
                detail=_redact_sensitive_text(command),
                exit_code=exit_code,
            ),
        )
        if exit_code != 0:
            success = False
            failure_reason = _redact_sensitive_text(
                f"preinstall command failed: {command}\n{output}".strip()
            )
            failed_step_index = -1
            failed_action = "setup"
            failed_scenario = "preinstall"
            break

    if success:
        for scenario_index, scenario in enumerate(loaded.scenarios):
            merged_prompt_policy = _resolve_merged_agent_prompt_policy(
                screenplay_policy=loaded.agent_prompts,
                scenario_policy=scenario.agent_prompts,
                override_mode=resolved_agent_prompt_mode,
            )
            scenario_prompt_modes[scenario.label] = merged_prompt_policy.mode
            lint_result = lint_agent_prompt_policy(
                merged_prompt_policy,
                allow_unbounded_approve=_allow_unbounded_approve_from_env(),
            )
            policy_errors = lint_result.errors
            policy_warnings = lint_result.warnings
            if policy_warnings:
                scenario_prompt_warnings[scenario.label] = policy_warnings
                for warning in policy_warnings:
                    append_event(
                        events_path,
                        RuntimeEvent(
                            scenario=scenario.label,
                            step_index=-1,
                            action="policy_lint",
                            status="warning",
                            detail=_redact_sensitive_text(warning),
                            exit_code=None,
                        ),
                    )
            if policy_errors:
                for error in policy_errors:
                    append_event(
                        events_path,
                        RuntimeEvent(
                            scenario=scenario.label,
                            step_index=-1,
                            action="policy_lint",
                            status="failed",
                            detail=_redact_sensitive_text(error),
                            exit_code=None,
                        ),
                    )
                success = False
                failure_reason = _redact_sensitive_text(
                    "agent prompt policy lint failed: " + "; ".join(policy_errors)
                )
                failed_step_index = -1
                failed_action = "policy_lint"
                failed_scenario = scenario.label
                break

            prompt_policy = _resolve_agent_prompt_policy(merged_prompt_policy)
            prompt_detection_regex = _resolve_prompt_detection_regex(
                merged_prompt_policy,
            )
            for setup_cmd in scenario.setup:
                output, exit_code = _run_shell_command(
                    setup_cmd,
                    cwd=working_dir,
                    shell=scenario.shell,
                    timeout_seconds=setup_timeout_seconds,
                )
                append_event(
                    events_path,
                    RuntimeEvent(
                        scenario=scenario.label,
                        step_index=-1,
                        action="setup",
                        status="ok" if exit_code == 0 else "failed",
                        detail=_redact_sensitive_text(setup_cmd),
                        exit_code=exit_code,
                    ),
                )
                if exit_code != 0:
                    success = False
                    failure_reason = _redact_sensitive_text(
                        f"setup command failed: {setup_cmd}\n{output}".strip()
                    )
                    failed_step_index = -1
                    failed_action = "setup"
                    failed_scenario = scenario.label
                    break
            if not success:
                break

            display = _xvfb_display_id(scenario_index)
            # Use a private temp directory per scenario so the kitty control socket
            # is not exposed in a shared /tmp namespace.
            socket_dir = Path(tempfile.mkdtemp(prefix="terminal-demo-studio-kitty-"))
            socket_path = socket_dir / "kitty.sock"
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
                    baseline_screen = ""
                    interaction_triggered = False

                    try:
                        baseline_screen = _get_screen_text(
                            socket_target=socket_target,
                            env=env,
                            adapter_name=scenario.adapter,
                        )

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
                            interaction_triggered = True

                        if action.input:
                            detail = action.input
                            _send_text(socket_target=socket_target, env=env, value=action.input)
                            interaction_triggered = True

                        if action.key:
                            detail = action.key
                            _send_key(socket_target=socket_target, env=env, token=action.key)
                            interaction_triggered = True

                        if action.hotkey:
                            detail = action.hotkey
                            _send_key(socket_target=socket_target, env=env, token=action.hotkey)
                            interaction_triggered = True

                        if interaction_triggered:
                            last_screen_snapshot = _drain_agent_prompts(
                                socket_target=socket_target,
                                env=env,
                                adapter_name=scenario.adapter,
                                scenario=scenario.label,
                                step_index=step_index,
                                events_path=events_path,
                                prompt_policy=prompt_policy,
                            )

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
                                baseline_text=baseline_screen if interaction_triggered else None,
                                scenario=scenario.label,
                                step_index=step_index,
                                events_path=events_path,
                                prompt_policy=prompt_policy,
                                prompt_detection_regex=prompt_detection_regex,
                            )
                            if not ok:
                                raise RuntimeError(message)
                        else:
                            last_screen_snapshot = _drain_agent_prompts(
                                socket_target=socket_target,
                                env=env,
                                adapter_name=scenario.adapter,
                                scenario=scenario.label,
                                step_index=step_index,
                                events_path=events_path,
                                prompt_policy=prompt_policy,
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
                        failure_reason = _redact_sensitive_text(str(exc))
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
                            detail=_redact_sensitive_text(detail),
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
                failure_reason = _redact_sensitive_text(str(exc))
                failed_step_index = failed_step_index if failed_step_index is not None else -1
                failed_action = failed_action or "scenario_bootstrap"
                failed_scenario = failed_scenario or scenario.label
            finally:
                _stop_ffmpeg(ffmpeg_proc)
                _stop_process(kitty_proc)
                _stop_process(xvfb_proc)
                shutil.rmtree(socket_dir, ignore_errors=True)

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
            target_gif = final_gif if produce_gif else None
            compose_split_screen(
                inputs=scene_videos,
                labels=scene_labels,
                output_mp4=target_mp4,
                output_gif=target_gif,
                playback_mode=playback_mode,
                redaction_mode=resolved_redaction_mode,
            )
        except Exception as exc:  # noqa: BLE001
            success = False
            failure_reason = _redact_sensitive_text(str(exc))
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
            "agent_prompts": {
                "override_mode": resolved_agent_prompt_mode,
                "scenarios": scenario_prompt_modes,
                "warnings": scenario_prompt_warnings,
            },
            "media_redaction": resolved_redaction_mode,
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
            "reason": "" if success else _redact_sensitive_text(failure_reason),
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
