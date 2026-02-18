from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(slots=True)
class RuntimeEvent:
    scenario: str
    step_index: int
    action: str
    status: str
    detail: str = ""
    exit_code: int | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)


def append_event(path: Path, event: RuntimeEvent) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(event.to_json())
        handle.write("\n")
