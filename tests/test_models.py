from __future__ import annotations

import pytest
from pydantic import ValidationError

from terminal_demo_studio.models import Screenplay, parse_screenplay_data


def test_parse_legacy_two_scenario_format() -> None:
    data = {
        "title": "Legacy",
        "output": "demo",
        "settings": {},
        "scenario_unsafe": {"label": "Without", "actions": [{"type": "echo bad"}]},
        "scenario_safe": {"label": "With", "actions": [{"type": "echo good"}]},
    }

    parsed = parse_screenplay_data(data)

    assert isinstance(parsed, Screenplay)
    assert len(parsed.scenarios) == 2
    assert parsed.scenarios[0].label == "Without"
    assert parsed.scenarios[1].label == "With"


def test_action_requires_at_least_one_field() -> None:
    data = {
        "title": "Invalid",
        "output": "demo",
        "settings": {},
        "scenarios": [
            {"label": "Only", "actions": [{}]},
            {"label": "Two", "actions": [{"type": "ok"}]},
        ],
    }

    with pytest.raises(ValidationError):
        parse_screenplay_data(data)


def test_requires_at_least_one_scenario() -> None:
    data = {
        "title": "Invalid",
        "output": "demo",
        "settings": {},
        "scenarios": [],
    }

    with pytest.raises(ValidationError):
        parse_screenplay_data(data)


def test_allows_single_scenario() -> None:
    data = {
        "title": "Single",
        "output": "demo",
        "settings": {},
        "scenarios": [{"label": "Only", "actions": [{"type": "echo hi"}]}],
    }

    parsed = parse_screenplay_data(data)

    assert isinstance(parsed, Screenplay)
    assert len(parsed.scenarios) == 1


def test_invalid_wait_mode_rejected() -> None:
    data = {
        "title": "Invalid",
        "output": "demo",
        "settings": {},
        "scenarios": [
            {"label": "One", "actions": [{"wait_for": "Ready", "wait_mode": "oops"}]},
            {"label": "Two", "actions": [{"type": "ok"}]},
        ],
    }

    with pytest.raises(ValidationError):
        parse_screenplay_data(data)


def test_parses_macos_prompt_configuration() -> None:
    data = {
        "title": "Prompt",
        "output": "demo",
        "settings": {},
        "scenarios": [
            {
                "label": "Only",
                "prompt": {
                    "style": "macos",
                    "user": "dev",
                    "host": "mbp",
                    "path": "basename",
                },
                "actions": [{"type": "pwd"}],
            }
        ],
    }

    parsed = parse_screenplay_data(data)
    prompt = parsed.scenarios[0].prompt

    assert prompt is not None
    assert prompt.user == "dev"
    assert prompt.host == "mbp"


def test_accepts_autonomous_action_fields() -> None:
    data = {
        "title": "Advanced",
        "output": "demo",
        "settings": {},
        "scenarios": [
            {
                "label": "Only",
                "execution_mode": "autonomous_pty",
                "shell": "pwsh",
                "adapter": "generic",
                "actions": [
                    {"command": "echo hi"},
                    {"input": "next"},
                    {"key": "Tab"},
                    {"hotkey": "Ctrl+C"},
                    {"wait_screen_regex": "hi"},
                    {"wait_line_regex": "hi"},
                    {"wait_stable": "250ms"},
                    {"assert_screen_regex": "hi"},
                    {"assert_not_screen_regex": "error"},
                    {"expect_exit_code": 0},
                ],
            }
        ],
    }

    parsed = parse_screenplay_data(data)
    scenario = parsed.scenarios[0]
    assert scenario.execution_mode == "autonomous_pty"
    assert scenario.shell == "pwsh"
    assert scenario.adapter == "generic"


def test_accepts_autonomous_video_execution_mode() -> None:
    data = {
        "title": "Video",
        "output": "demo",
        "settings": {},
        "scenarios": [
            {
                "label": "Only",
                "execution_mode": "autonomous_video",
                "actions": [
                    {"command": "python3 mock.py"},
                    {"wait_screen_regex": "Connected"},
                    {"key": "Enter"},
                ],
            }
        ],
    }

    parsed = parse_screenplay_data(data)
    assert parsed.scenarios[0].execution_mode == "autonomous_video"


def test_rejects_multiple_action_primitives() -> None:
    data = {
        "title": "Invalid",
        "output": "demo",
        "settings": {},
        "scenarios": [
            {
                "label": "Only",
                "actions": [
                    {"command": "echo one", "input": "two"},
                ],
            }
        ],
    }

    with pytest.raises(ValidationError):
        parse_screenplay_data(data)


def test_variable_references_are_resolved_recursively() -> None:
    data = {
        "title": "Vars",
        "output": "demo",
        "variables": {
            "base_dir": "{{tmp_dir}}/terminal_demo_studio_vars",
            "demo_dir": "{{base_dir}}/nested",
        },
        "settings": {},
        "scenarios": [
            {
                "label": "Only",
                "setup": ["cd {{demo_dir}}"],
                "actions": [{"type": "pwd"}],
            }
        ],
    }

    parsed = parse_screenplay_data(data)
    setup_cmd = parsed.scenarios[0].setup[0]

    assert "{{" not in setup_cmd
    assert "terminal_demo_studio_vars/nested" in setup_cmd
