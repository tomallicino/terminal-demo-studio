from __future__ import annotations

from terminal_demo_studio.models import Action, Scenario, Settings
from terminal_demo_studio.tape import compile_tape


def test_compile_tape_emits_wait_and_setup() -> None:
    scenario = Scenario(
        label="With Cask",
        setup=["export CASK_MODE=safe"],
        actions=[
            Action(type="cask run --tool delete_prod_db"),
            Action(wait_for="Analyzing lockfile...", wait_mode="line", wait_timeout="500ms"),
            Action(sleep="1s"),
        ],
    )
    settings = Settings(width=1200, height=600, font_size=24, theme="Catppuccin Mocha")

    tape = compile_tape(scenario, settings, ["scene_1.mp4"])

    assert 'Output "scene_1.mp4"' in tape
    assert "Hide" in tape
    assert "Type \"export CASK_MODE=safe\"" in tape
    assert "Wait+Line@500ms /Analyzing\\ lockfile\\.\\.\\./" in tape
    assert "Sleep 1s" in tape


def test_compile_tape_escapes_slashes_in_wait_regex() -> None:
    scenario = Scenario(
        label="test",
        actions=[Action(wait_for="path /tmp/x", wait_mode="default")],
    )
    settings = Settings()

    tape = compile_tape(scenario, settings, ["scene.mp4"])

    wait_line = next(line for line in tape.splitlines() if line.startswith("Wait "))
    assert wait_line.count("/") == 2
    assert "tmp.*x" in wait_line


def test_compile_tape_quotes_absolute_output_path() -> None:
    scenario = Scenario(
        label="abs",
        actions=[Action(type="echo hi")],
    )
    settings = Settings()

    tape = compile_tape(scenario, settings, ["/tmp/tui/output.mp4"])

    assert 'Output "/tmp/tui/output.mp4"' in tape


def test_compile_tape_emits_visual_shell_settings() -> None:
    scenario = Scenario(
        label="style",
        actions=[Action(type="echo hi")],
    )
    settings = Settings()

    tape = compile_tape(scenario, settings, ["scene.mp4"])

    assert "Set Margin 12" in tape
    assert 'Set MarginFill "#0F172A"' in tape
    assert "Set BorderRadius 10" in tape
    assert "Set CursorBlink false" in tape
    assert "Set FontFamily" not in tape


def test_compile_tape_escapes_dollar_signs_in_type_text() -> None:
    scenario = Scenario(
        label="vars",
        actions=[Action(type='echo "Preparing ${RELEASE_VERSION}"')],
    )
    settings = Settings()

    tape = compile_tape(scenario, settings, ["scene.mp4"])

    assert "Type 'echo \"Preparing ${RELEASE_VERSION}\"'" in tape


def test_compile_tape_supports_macos_prompt_setup() -> None:
    scenario = Scenario(
        label="prompt",
        prompt={"style": "macos", "user": "dev", "host": "workstation", "path": "full"},
        actions=[Action(type="pwd")],
    )
    settings = Settings()

    tape = compile_tape(scenario, settings, ["scene.mp4"])

    assert "Hide" in tape
    assert "Type \"export PS1='dev@workstation ${PWD} % '\"" in tape
    assert "Type \"clear\"" in tape
    assert "Show" in tape


def test_compile_tape_supports_macos_prompt_basename_path() -> None:
    scenario = Scenario(
        label="prompt",
        prompt={"style": "macos", "user": "dev", "host": "mbp", "path": "basename"},
        actions=[Action(type="pwd")],
    )
    settings = Settings()

    tape = compile_tape(scenario, settings, ["scene.mp4"])

    assert "Type \"export PS1='dev@mbp ${PWD##*/} % '\"" in tape


def test_compile_tape_supports_command_key_and_hotkey_actions() -> None:
    scenario = Scenario(
        label="keys",
        actions=[
            Action(command="echo hello"),
            Action(key="Tab"),
            Action(hotkey="Ctrl+C"),
        ],
    )
    settings = Settings()

    tape = compile_tape(scenario, settings, ["scene.mp4"])

    assert "Type \"echo hello\"" in tape
    assert "Enter" in tape
    assert "Tab" in tape
    assert "Ctrl+C" in tape


def test_compile_tape_splits_multiline_commands_into_safe_lines() -> None:
    scenario = Scenario(
        label="multiline",
        setup=["echo setup-one\necho setup-two"],
        actions=[Action(command="echo action-one\necho action-two")],
    )
    settings = Settings()

    tape = compile_tape(scenario, settings, ["scene.mp4"])

    assert "Type \"echo setup-one\"" in tape
    assert "Type \"echo setup-two\"" in tape
    assert "Type \"echo action-one\"" in tape
    assert "Type \"echo action-two\"" in tape
    assert "setup-one\\necho setup-two" not in tape
