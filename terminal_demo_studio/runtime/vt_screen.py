from __future__ import annotations


class VirtualTerminalScreen:
    """Minimal running text snapshot used by autonomous assertions."""

    def __init__(self) -> None:
        self._chunks: list[str] = []

    def append(self, text: str) -> None:
        if text:
            self._chunks.append(text)

    def snapshot(self) -> str:
        return "".join(self._chunks)
