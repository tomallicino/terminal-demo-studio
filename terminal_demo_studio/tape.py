from __future__ import annotations

import re

from terminal_demo_studio.models import Action, PromptSettings, Scenario, Settings


def _escape_type_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _format_type_command(text: str) -> str:
    # VHS parser has edge cases with $ inside escaped double-quoted strings.
    if '"' in text and "$" in text and "'" not in text:
        return f"Type '{text}'"
    return f'Type "{_escape_type_text(text)}"'


def _escape_regex(text: str) -> str:
    parts = text.split("/")
    escaped_parts = [re.escape(part) for part in parts]
    return ".*".join(escaped_parts)


def _wait_command(action: Action) -> str:
    wait_prefix = {
        "default": "Wait",
        "screen": "Wait+Screen",
        "line": "Wait+Line",
    }[action.wait_mode]
    if action.wait_timeout:
        wait_prefix = f"{wait_prefix}@{action.wait_timeout}"
    return f"{wait_prefix} /{_escape_regex(action.wait_for or '')}/"


def _wait_regex_command(pattern: str, mode: str = "screen") -> str:
    wait_prefix = "Wait+Line" if mode == "line" else "Wait+Screen"
    return f"{wait_prefix} /{_escape_regex(pattern)}/"


def _escape_single_quotes(text: str) -> str:
    return text.replace("'", "'\"'\"'")


def _prompt_setup_command(prompt: PromptSettings) -> str:
    path_token = "${PWD##*/}" if prompt.path == "basename" else "${PWD}"
    if prompt.style == "venv":
        env_name = prompt.env or ".venv"
        ps1_value = f"\\n({env_name}) {prompt.user}@{prompt.host} {path_token} {prompt.symbol} "
    else:
        ps1_value = f"\\n{prompt.user}@{prompt.host} {path_token} {prompt.symbol} "
    escaped = _escape_single_quotes(ps1_value)
    return f"export PS1='{escaped}'"


def _append_typed_lines(lines: list[str], command: str, *, press_enter: bool) -> None:
    chunks = command.splitlines() or [command]
    for chunk in chunks:
        lines.append(_format_type_command(chunk))
        if press_enter:
            lines.append("Enter")


def compile_tape(scenario: Scenario, settings: Settings, outputs: list[str]) -> str:
    lines: list[str] = []
    for output in outputs:
        lines.append(f'Output "{_escape_type_text(output)}"')
    lines.append(f"Set FontSize {settings.font_size}")
    lines.append(f"Set Framerate {settings.framerate}")
    lines.append(f"Set LineHeight {settings.line_height}")
    lines.append(f"Set LetterSpacing {settings.letter_spacing}")
    lines.append(f"Set Width {settings.width}")
    lines.append(f"Set Height {settings.height}")
    lines.append(f'Set Theme "{_escape_type_text(settings.theme)}"')
    lines.append(f"Set Padding {settings.padding}")
    lines.append(f"Set Margin {settings.margin}")
    lines.append(f'Set MarginFill "{_escape_type_text(settings.margin_fill)}"')
    lines.append(f"Set BorderRadius {settings.border_radius}")
    lines.append(f"Set CursorBlink {str(settings.cursor_blink).lower()}")
    lines.append(f"Set WindowBar {settings.window_bar}")
    if settings.font_family:
        lines.append(f'Set FontFamily "{_escape_type_text(settings.font_family)}"')

    setup_commands: list[str] = []
    if scenario.prompt is not None:
        setup_commands.append(_prompt_setup_command(scenario.prompt))
    setup_commands.extend(scenario.setup)

    if setup_commands:
        lines.append("Hide")
        for command in setup_commands:
            _append_typed_lines(lines, command, press_enter=True)
        _append_typed_lines(lines, "clear", press_enter=True)
        lines.append("Show")

    for action in scenario.actions:
        if isinstance(action, str):
            _append_typed_lines(lines, action, press_enter=True)
            continue

        command_text = action.command or action.type
        if command_text:
            _append_typed_lines(lines, command_text, press_enter=True)
        if action.input:
            _append_typed_lines(lines, action.input, press_enter=False)
        if action.key:
            lines.append(action.key)
        if action.hotkey:
            lines.append(action.hotkey)
        if action.wait_for:
            lines.append(_wait_command(action))
        if action.wait_screen_regex:
            lines.append(_wait_regex_command(action.wait_screen_regex, mode="screen"))
        if action.wait_line_regex:
            lines.append(_wait_regex_command(action.wait_line_regex, mode="line"))
        if action.wait_stable:
            lines.append(f"Sleep {action.wait_stable}")
        if action.assert_screen_regex:
            lines.append(_wait_regex_command(action.assert_screen_regex, mode="screen"))
        if action.assert_not_screen_regex:
            lines.append(
                _format_type_command(
                    f"echo \"assert_not_screen_regex:{action.assert_not_screen_regex}\" >/dev/null"
                )
            )
            lines.append("Enter")
        if action.sleep:
            lines.append(f"Sleep {action.sleep}")

    return "\n".join(lines) + "\n"
