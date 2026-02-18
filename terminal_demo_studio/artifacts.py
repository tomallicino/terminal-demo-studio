from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

Lane = Literal["scripted_vhs", "autonomous_pty", "autonomous_video"]


@dataclass(slots=True)
class RunLayout:
    run_id: str
    lane: Lane
    run_dir: Path
    manifest_path: Path
    summary_path: Path
    media_dir: Path
    scenes_dir: Path
    tapes_dir: Path
    runtime_dir: Path
    failure_dir: Path


def _run_timestamp(now: datetime | None = None) -> str:
    resolved_now = now.astimezone(UTC) if now is not None else datetime.now(UTC)
    return resolved_now.strftime("%Y%m%dT%H%M%SZ")


def build_run_id(screenplay_stem: str, lane: Lane, now: datetime | None = None) -> str:
    return f"{_run_timestamp(now)}-{screenplay_stem}-{lane}"


def create_run_layout(
    *,
    screenplay_path: Path,
    output_dir: Path | None,
    lane: Lane,
) -> RunLayout:
    base = output_dir.resolve() if output_dir is not None else screenplay_path.resolve().parent
    run_id = build_run_id(screenplay_path.stem, lane)
    run_dir = base / ".terminal_demo_studio_runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    media_dir = run_dir / "media"
    scenes_dir = run_dir / "scenes"
    tapes_dir = run_dir / "tapes"
    runtime_dir = run_dir / "runtime"
    failure_dir = run_dir / "failure"
    for target in [media_dir, scenes_dir, tapes_dir, runtime_dir, failure_dir]:
        target.mkdir(parents=True, exist_ok=True)

    return RunLayout(
        run_id=run_id,
        lane=lane,
        run_dir=run_dir,
        manifest_path=run_dir / "manifest.json",
        summary_path=run_dir / "summary.json",
        media_dir=media_dir,
        scenes_dir=scenes_dir,
        tapes_dir=tapes_dir,
        runtime_dir=runtime_dir,
        failure_dir=failure_dir,
    )


def write_manifest(
    layout: RunLayout,
    *,
    screenplay_path: Path,
    command: str,
    mode: str,
) -> None:
    payload = {
        "run_id": layout.run_id,
        "lane": layout.lane,
        "screenplay": str(screenplay_path.resolve()),
        "command": command,
        "mode": mode,
        "created_at": _run_timestamp(),
    }
    layout.manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_summary(layout: RunLayout, payload: dict[str, object]) -> None:
    layout.summary_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
