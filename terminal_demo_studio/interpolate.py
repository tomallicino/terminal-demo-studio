from __future__ import annotations

import re
from typing import Any

_TOKEN_PATTERN = re.compile(r"{{\s*([A-Za-z_][A-Za-z0-9_]*)\s*}}")
_FULL_TOKEN_PATTERN = re.compile(r"^{{\s*([A-Za-z_][A-Za-z0-9_]*)\s*}}$")


def _interpolate_string(value: str, variables: dict[str, Any], path: str) -> Any:
    full_match = _FULL_TOKEN_PATTERN.match(value)
    if full_match:
        token = full_match.group(1)
        if token not in variables:
            raise ValueError(f"Unresolved variable '{token}' at {path}")
        return variables[token]

    def replace(match: re.Match[str]) -> str:
        token = match.group(1)
        if token not in variables:
            raise ValueError(f"Unresolved variable '{token}' at {path}")
        return str(variables[token])

    return _TOKEN_PATTERN.sub(replace, value)


def interpolate_variables(data: Any, variables: dict[str, Any], path: str = "$") -> Any:
    if isinstance(data, dict):
        return {
            key: interpolate_variables(value, variables, f"{path}.{key}")
            for key, value in data.items()
        }
    if isinstance(data, list):
        return [
            interpolate_variables(item, variables, f"{path}[{index}]")
            for index, item in enumerate(data)
        ]
    if isinstance(data, str):
        return _interpolate_string(data, variables, path)
    return data
