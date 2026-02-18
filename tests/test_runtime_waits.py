from __future__ import annotations

from terminal_demo_studio.runtime.waits import evaluate_wait_condition


def test_wait_condition_line_regex_matches_line() -> None:
    text = "alpha\nbeta\n"
    ok, _ = evaluate_wait_condition(text, wait_line_regex="beta")
    assert ok is True


def test_wait_condition_screen_regex_fails_with_message() -> None:
    text = "alpha\nbeta\n"
    ok, message = evaluate_wait_condition(text, wait_screen_regex="gamma")
    assert ok is False
    assert "gamma" in message
