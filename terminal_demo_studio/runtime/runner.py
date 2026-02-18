from __future__ import annotations

import json
import platform
import re
import time
from dataclasses import dataclass
from pathlib import Path

from terminal_demo_studio.adapters import get_adapter
from terminal_demo_studio.models import Action, Screenplay, load_screenplay
from terminal_demo_studio.runtime.events import RuntimeEvent, append_event
from terminal_demo_studio.runtime.pty_posix import execute_command as execute_posix
from terminal_demo_studio.runtime.pty_windows import execute_command as execute_windows
from terminal_demo_studio.runtime.vt_screen import VirtualTerminalScreen
from terminal_demo_studio.runtime.waits import evaluate_wait_condition, wait_stable


@dataclass(slots=True)
class AutonomousRunResult:
    success: bool
    events_path: Path
    summary_path: Path
    failure_dir: Path | None


def _run_path(screenplay_path: Path, output_dir: Path | None) -> Path:
    base = output_dir.resolve() if output_dir else screenplay_path.resolve().parent
    run_id = f"{screenplay_path.stem}-{int(time.time())}"
    path = base / ".terminal_demo_studio_runs" / run_id
    path.mkdir(parents=True, exist_ok=True)
    return path


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


def _execute(command: str, cwd: Path, shell: str) -> tuple[str, int]:
    if platform.system() == "Windows":
        return execute_windows(command, cwd=cwd, shell=shell)
    return execute_posix(command, cwd=cwd, shell=shell)


def _evaluate_assertions(
    action: Action, screen_text: str, last_exit_code: int | None
) -> tuple[bool, str]:
    wait_screen_regex = action.wait_screen_regex
    wait_line_regex = action.wait_line_regex
    if action.wait_for:
        if action.wait_mode == "line":
            wait_line_regex = action.wait_for
        else:
            wait_screen_regex = action.wait_for

    ok, message = evaluate_wait_condition(
        screen_text,
        wait_screen_regex=wait_screen_regex,
        wait_line_regex=wait_line_regex,
    )
    if not ok:
        return False, message

    if action.assert_screen_regex and not re.search(
        action.assert_screen_regex, screen_text, re.MULTILINE
    ):
        return False, f"assert_screen_regex failed: {action.assert_screen_regex}"

    if action.assert_not_screen_regex and re.search(
        action.assert_not_screen_regex, screen_text, re.MULTILINE
    ):
        return False, f"assert_not_screen_regex failed: {action.assert_not_screen_regex}"

    if action.expect_exit_code is not None and last_exit_code != action.expect_exit_code:
        return False, f"expected exit_code={action.expect_exit_code}, got {last_exit_code}"

    return True, ""


def _unsupported_interactive_reason(action_name: str) -> str:
    return (
        f"interactive input action '{action_name}' is not supported in autonomous_pty yet; "
        "use command actions or scripted_vhs for key-driven playback"
    )


def _write_failure_bundle(run_dir: Path, screen_text: str, reason: str) -> Path:
    failure_dir = run_dir / "failure"
    failure_dir.mkdir(parents=True, exist_ok=True)
    (failure_dir / "screen.txt").write_text(screen_text, encoding="utf-8")
    (failure_dir / "reason.txt").write_text(reason, encoding="utf-8")
    return failure_dir


def run_autonomous_screenplay(
    screenplay_path: Path,
    output_dir: Path | None = None,
    screenplay: Screenplay | None = None,
) -> AutonomousRunResult:
    loaded = screenplay if screenplay is not None else load_screenplay(screenplay_path)
    run_dir = _run_path(screenplay_path, output_dir)
    events_path = run_dir / "events.jsonl"
    summary_path = run_dir / "summary.json"
    screen = VirtualTerminalScreen()

    success = True
    failure_reason = ""
    failure_dir: Path | None = None
    last_exit_code: int | None = None
    working_dir = screenplay_path.resolve().parent

    for scenario in loaded.scenarios:
        adapter = get_adapter(scenario.adapter)

        for setup_cmd in scenario.setup:
            output, exit_code = _execute(setup_cmd, cwd=working_dir, shell=scenario.shell)
            screen.append(adapter.normalize_output(output))
            last_exit_code = exit_code
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
                failure_reason = f"setup command failed: {setup_cmd}"
                break

        if not success:
            break

        for index, action in enumerate(scenario.actions):
            if isinstance(action, str):
                action = Action(command=action)

            action_name = _action_name(action)
            detail = ""

            if action.input or action.key or action.hotkey:
                detail = action.input or action.key or action.hotkey or ""
                success = False
                failure_reason = _unsupported_interactive_reason(action_name)
            elif action.command or action.type:
                command = action.command or action.type or ""
                output, exit_code = _execute(command, cwd=working_dir, shell=scenario.shell)
                screen.append(adapter.normalize_output(output))
                last_exit_code = exit_code
                detail = command
                if exit_code != 0:
                    success = False
                    failure_reason = (
                        f"command failed ({command}) with exit code {exit_code}"
                    )

            if action.sleep:
                wait_stable(action.sleep)

            if action.wait_stable:
                wait_stable(action.wait_stable)

            if success:
                ok, message = _evaluate_assertions(action, screen.snapshot(), last_exit_code)
                if not ok:
                    success = False
                    failure_reason = message

            append_event(
                events_path,
                RuntimeEvent(
                    scenario=scenario.label,
                    step_index=index,
                    action=action_name,
                    status="ok" if success else "failed",
                    detail=detail,
                    exit_code=last_exit_code,
                ),
            )

            if not success:
                break

        if not success:
            break

    if not success:
        failure_dir = _write_failure_bundle(run_dir, screen.snapshot(), failure_reason)

    summary = {
        "success": success,
        "events": str(events_path),
        "failure_dir": str(failure_dir) if failure_dir else None,
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return AutonomousRunResult(
        success=success,
        events_path=events_path,
        summary_path=summary_path,
        failure_dir=failure_dir,
    )
