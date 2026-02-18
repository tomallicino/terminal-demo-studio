from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RuntimeAdapter:
    name: str = "generic"

    def normalize_output(self, text: str) -> str:
        return text


class ShellMarkedAdapter(RuntimeAdapter):
    name = "shell_marked"


def get_adapter(name: str) -> RuntimeAdapter:
    if name == "shell_marked":
        return ShellMarkedAdapter(name="shell_marked")
    return RuntimeAdapter(name="generic")
