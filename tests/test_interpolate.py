from __future__ import annotations

import pytest

from terminal_demo_studio.interpolate import interpolate_variables


def test_interpolates_nested_values() -> None:
    data = {
        "title": "{{title}}",
        "output": "{{name}}",
        "settings": {"width": "{{w}}"},
        "scenarios": [{"label": "{{left}}", "actions": [{"type": "echo {{name}}"}]}],
    }
    variables = {"title": "Demo", "name": "drift", "w": 1200, "left": "Without"}

    result = interpolate_variables(data, variables)

    assert result["title"] == "Demo"
    assert result["output"] == "drift"
    assert result["settings"]["width"] == 1200
    assert result["scenarios"][0]["actions"][0]["type"] == "echo drift"


def test_unresolved_variable_fails() -> None:
    with pytest.raises(ValueError):
        interpolate_variables({"title": "{{missing}}"}, {})
