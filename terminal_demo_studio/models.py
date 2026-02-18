from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from terminal_demo_studio.interpolate import interpolate_variables

_DURATION_PATTERN = re.compile(r"^\d+(ms|s)$")
_VARIABLE_TOKEN_PATTERN = re.compile(r"{{\s*([A-Za-z_][A-Za-z0-9_]*)\s*}}")
_VARIABLE_FULL_TOKEN_PATTERN = re.compile(r"^{{\s*([A-Za-z_][A-Za-z0-9_]*)\s*}}$")


class Settings(BaseModel):
    width: int = 1440
    height: int = 900
    font_size: int = 22
    theme: str = "Catppuccin Mocha"
    padding: int = 24
    margin: int = 12
    margin_fill: str = "#0F172A"
    border_radius: int = 10
    window_bar: str = "Colorful"
    font_family: str | None = None
    framerate: int = 60
    line_height: float = 1.15
    letter_spacing: int = 0
    cursor_blink: bool = False


class Action(BaseModel):
    type: str | None = None
    command: str | None = None
    input: str | None = None
    key: str | None = None
    hotkey: str | None = None
    sleep: str | None = None
    wait_for: str | None = None
    wait_screen_regex: str | None = None
    wait_line_regex: str | None = None
    wait_stable: str | None = None
    assert_screen_regex: str | None = None
    assert_not_screen_regex: str | None = None
    expect_exit_code: int | None = None
    wait_mode: Literal["default", "screen", "line"] = "default"
    wait_timeout: str | None = None

    @field_validator("sleep", "wait_timeout", "wait_stable")
    @classmethod
    def validate_duration(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not _DURATION_PATTERN.match(value):
            raise ValueError("Duration must match '<number>ms' or '<number>s'")
        return value

    @model_validator(mode="after")
    def validate_action(self) -> Action:
        command_primitives = [self.type, self.command, self.input, self.key, self.hotkey]
        populated_primitives = [item for item in command_primitives if item]
        if len(populated_primitives) > 1:
            raise ValueError("Action must not define multiple input primitives")

        if not any(
            [
                self.type,
                self.command,
                self.input,
                self.key,
                self.hotkey,
                self.sleep,
                self.wait_for,
                self.wait_screen_regex,
                self.wait_line_regex,
                self.wait_stable,
                self.assert_screen_regex,
                self.assert_not_screen_regex,
                self.expect_exit_code is not None,
            ]
        ):
            raise ValueError(
                "Action must contain at least one command, key, wait, assert, or sleep field"
            )
        if (self.wait_mode != "default" or self.wait_timeout) and not self.wait_for:
            raise ValueError("wait_mode/wait_timeout require wait_for")
        return self


class PromptSettings(BaseModel):
    style: Literal["macos", "venv"] = "macos"
    env: str | None = None
    user: str = "dev"
    host: str = "workstation"
    path: Literal["basename", "full"] = "basename"
    symbol: str = "%"


class Scenario(BaseModel):
    label: str
    surface: Literal["terminal"] = "terminal"
    execution_mode: Literal["scripted_vhs", "autonomous_pty", "autonomous_video"] = (
        "scripted_vhs"
    )
    shell: Literal["auto", "bash", "zsh", "fish", "pwsh", "cmd"] = "auto"
    adapter: str = "generic"
    prompt: PromptSettings | None = None
    setup: list[str] = Field(default_factory=list)
    actions: list[Action | str] = Field(min_length=1)


class Screenplay(BaseModel):
    title: str
    output: str
    settings: Settings = Field(default_factory=Settings)
    scenarios: list[Scenario] = Field(min_length=1)
    variables: dict[str, Any] = Field(default_factory=dict)
    preinstall: list[str] = Field(default_factory=list)


def _resolve_variables(variables: dict[str, Any]) -> dict[str, Any]:
    resolved: dict[str, Any] = {}
    resolving: set[str] = set()

    def resolve(name: str) -> Any:
        if name in resolved:
            return resolved[name]
        if name in resolving:
            raise ValueError(f"Cyclic variable reference detected for '{name}'")
        if name not in variables:
            raise ValueError(f"Unresolved variable '{name}' in variables map")

        resolving.add(name)
        value = variables[name]

        if isinstance(value, str):
            full_match = _VARIABLE_FULL_TOKEN_PATTERN.match(value)
            if full_match:
                token = full_match.group(1)
                value = resolve(token)
            else:
                value = _VARIABLE_TOKEN_PATTERN.sub(
                    lambda match: str(resolve(match.group(1))),
                    value,
                )

        resolving.remove(name)
        resolved[name] = value
        return value

    return {name: resolve(name) for name in variables}


def normalize_screenplay_data(data: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(data)
    has_legacy = "scenario_unsafe" in normalized and "scenario_safe" in normalized
    if has_legacy and "scenarios" not in normalized:
        normalized["scenarios"] = [
            normalized.pop("scenario_unsafe"),
            normalized.pop("scenario_safe"),
        ]
    return normalized


def parse_screenplay_data(data: dict[str, Any]) -> Screenplay:
    normalized = normalize_screenplay_data(data)
    variables = normalized.get("variables", {})
    if not isinstance(variables, dict):
        raise ValidationError.from_exception_data(
            title="Screenplay",
            line_errors=[
                {
                    "type": "dict_type",
                    "loc": ("variables",),
                    "input": variables,
                }
            ],
        )
    variables = {**variables}
    variables.setdefault("tmp_dir", tempfile.gettempdir())
    variables = _resolve_variables(variables)
    normalized["variables"] = variables
    interpolated = interpolate_variables(normalized, variables)
    return Screenplay.model_validate(interpolated)


def load_screenplay(path: Path) -> Screenplay:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Screenplay at {path} must be a YAML object")
    return parse_screenplay_data(raw)


def format_validation_error(exc: ValidationError) -> str:
    messages: list[str] = []
    for issue in exc.errors():
        loc = ".".join(str(part) for part in issue.get("loc", []))
        message = issue.get("msg", "validation error")
        messages.append(f"{loc}: {message}")
    return "\n".join(messages)
