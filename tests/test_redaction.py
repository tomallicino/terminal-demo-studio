from __future__ import annotations

from terminal_demo_studio.models import parse_screenplay_data
from terminal_demo_studio.redaction import resolve_media_redaction_mode, text_contains_sensitive


def _base_screenplay(action_command: str) -> dict[str, object]:
    return {
        "title": "Demo",
        "output": "demo",
        "settings": {},
        "scenarios": [
            {
                "label": "One",
                "execution_mode": "autonomous_video",
                "actions": [{"command": action_command}],
            }
        ],
    }


def test_resolve_media_redaction_auto_defaults_to_off() -> None:
    screenplay = parse_screenplay_data(_base_screenplay("echo hello"))

    resolved = resolve_media_redaction_mode(
        screenplay=screenplay,
        override_mode="auto",
    )

    assert resolved == "off"


def test_resolve_media_redaction_auto_enables_input_line_for_sensitive_actions() -> None:
    screenplay = parse_screenplay_data(
        _base_screenplay("export OPENAI_API_KEY=sk-testsecretvalue123456")
    )

    resolved = resolve_media_redaction_mode(
        screenplay=screenplay,
        override_mode="auto",
    )

    assert resolved == "input_line"


def test_resolve_media_redaction_respects_screenplay_setting_when_override_auto() -> None:
    screenplay = parse_screenplay_data(
        {
            "title": "Demo",
            "output": "demo",
            "settings": {"media_redaction": "input_line"},
            "scenarios": [
                {
                    "label": "One",
                    "execution_mode": "autonomous_video",
                    "actions": [{"command": "echo hello"}],
                }
            ],
        }
    )

    resolved = resolve_media_redaction_mode(
        screenplay=screenplay,
        override_mode="auto",
    )

    assert resolved == "input_line"


def test_resolve_media_redaction_override_takes_precedence_over_auto_detection() -> None:
    screenplay = parse_screenplay_data(
        _base_screenplay("export OPENAI_API_KEY=sk-testsecretvalue123456")
    )

    resolved = resolve_media_redaction_mode(
        screenplay=screenplay,
        override_mode="off",
    )

    assert resolved == "off"


def test_text_contains_sensitive_detects_env_secret(monkeypatch: object) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-live-testsecret99999")

    assert text_contains_sensitive("prefix sk-live-testsecret99999 suffix") is True
