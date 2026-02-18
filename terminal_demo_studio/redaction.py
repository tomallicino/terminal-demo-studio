from __future__ import annotations

import os
import re
from typing import Literal

from terminal_demo_studio.models import Action, Screenplay

MediaRedactionMode = Literal["auto", "off", "input_line"]
ResolvedMediaRedactionMode = Literal["off", "input_line"]

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

_SENSITIVE_HINT_TERMS = (
    "api_key",
    "apikey",
    "token",
    "secret",
    "password",
    "passwd",
)


def sensitive_values_from_env() -> list[str]:
    values: list[str] = []
    for name in _SENSITIVE_VALUE_ENV_NAMES:
        value = os.environ.get(name)
        if value and len(value) >= 6:
            values.append(value)
    return values


def text_contains_sensitive(value: str) -> bool:
    lowered = value.lower()
    if any(term in lowered for term in _SENSITIVE_HINT_TERMS):
        return True

    for secret in sensitive_values_from_env():
        if secret in value:
            return True

    for pattern in _SENSITIVE_PATTERNS:
        if pattern.search(value):
            return True

    return False


def screenplay_has_sensitive_actions(screenplay: Screenplay) -> bool:
    for scenario in screenplay.scenarios:
        for raw_action in scenario.actions:
            action = raw_action if isinstance(raw_action, Action) else Action(command=raw_action)
            for candidate in [action.command, action.type, action.input]:
                if candidate and text_contains_sensitive(candidate):
                    return True
    return False


def resolve_media_redaction_mode(
    *,
    screenplay: Screenplay,
    override_mode: MediaRedactionMode,
) -> ResolvedMediaRedactionMode:
    requested_mode = override_mode
    if requested_mode == "auto":
        requested_mode = screenplay.settings.media_redaction

    if requested_mode == "auto":
        return "input_line" if screenplay_has_sensitive_actions(screenplay) else "off"

    if requested_mode == "input_line":
        return "input_line"
    return "off"
