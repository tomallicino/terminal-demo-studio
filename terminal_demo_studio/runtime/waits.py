from __future__ import annotations

import re
import time


def duration_to_seconds(value: str) -> float:
    if value.endswith("ms"):
        return float(value[:-2]) / 1000.0
    if value.endswith("s"):
        return float(value[:-1])
    raise ValueError(f"Unsupported duration format: {value}")


def evaluate_wait_condition(
    screen_text: str,
    *,
    wait_screen_regex: str | None = None,
    wait_line_regex: str | None = None,
) -> tuple[bool, str]:
    if wait_screen_regex:
        if re.search(wait_screen_regex, screen_text, re.MULTILINE):
            return True, ""
        return False, f"screen regex not found: {wait_screen_regex}"

    if wait_line_regex:
        for line in screen_text.splitlines():
            if re.search(wait_line_regex, line):
                return True, ""
        return False, f"line regex not found: {wait_line_regex}"

    return True, ""


def wait_stable(duration: str) -> None:
    time.sleep(duration_to_seconds(duration))
