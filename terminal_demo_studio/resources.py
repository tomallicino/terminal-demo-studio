from __future__ import annotations

from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path


def _templates_root() -> Traversable:
    return files("terminal_demo_studio").joinpath("templates")


def list_template_names() -> list[str]:
    templates = _templates_root()
    names: list[str] = []
    for entry in templates.iterdir():
        if entry.is_file() and entry.name.endswith(".yaml"):
            names.append(Path(entry.name).stem)
    return sorted(names)


def read_template(template_name: str) -> str:
    template_path = _templates_root().joinpath(f"{template_name}.yaml")
    if not template_path.is_file():
        raise FileNotFoundError(f"Template not found: {template_name}")
    return template_path.read_text(encoding="utf-8")
