from __future__ import annotations

import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from terminal_demo_studio.artifacts import (
    RunLayout,
    create_run_layout,
    write_manifest,
    write_summary,
)
from terminal_demo_studio.editor import compose_split_screen
from terminal_demo_studio.models import Scenario, Screenplay, Settings, load_screenplay
from terminal_demo_studio.redaction import MediaRedactionMode, resolve_media_redaction_mode
from terminal_demo_studio.runtime.shells import build_shell_command
from terminal_demo_studio.tape import compile_tape

PlaybackMode = Literal["sequential", "simultaneous"]


@dataclass(slots=True)
class ScriptedRunResult:
    success: bool
    run_layout: RunLayout
    mp4_path: Path | None
    gif_path: Path | None
    error: str | None = None


def _output_stem(output_value: str) -> str:
    return Path(output_value).stem


def _build_shell_command(command: str, shell: str = "auto") -> list[str]:
    return build_shell_command(command, shell)


def _run_preinstall(screenplay: Screenplay, workdir: Path) -> None:
    for command in screenplay.preinstall:
        subprocess.run(_build_shell_command(command, "auto"), check=True, cwd=workdir)


def _render_terminal_scenario(
    scenario: Scenario,
    settings: Settings,
    tape_path: Path,
    output_video_path: Path,
    working_dir: Path,
) -> None:
    tape_path.write_text(
        compile_tape(scenario, settings, [str(output_video_path)]),
        encoding="utf-8",
    )
    subprocess.run(["vhs", str(tape_path)], check=True, cwd=working_dir)


_SCENARIO_RENDERERS: dict[
    str, Callable[[Scenario, Settings, Path, Path, Path], None]
] = {
    "terminal": _render_terminal_scenario,
}


def run_director(
    screenplay_path: Path,
    output_dir: Path | None = None,
    keep_temp: bool = False,
    produce_mp4: bool = True,
    produce_gif: bool = True,
    playback_mode: PlaybackMode = "sequential",
    media_redaction_mode: MediaRedactionMode = "auto",
) -> ScriptedRunResult:
    screenplay = load_screenplay(screenplay_path)
    resolved_redaction_mode = resolve_media_redaction_mode(
        screenplay=screenplay,
        override_mode=media_redaction_mode,
    )
    run_layout = create_run_layout(
        screenplay_path=screenplay_path,
        output_dir=output_dir,
        lane="scripted_vhs",
    )
    write_manifest(
        run_layout,
        screenplay_path=screenplay_path,
        command="tds render",
        mode="scripted_vhs",
    )

    if not produce_mp4 and not produce_gif:
        raise ValueError("At least one output type must be enabled")

    working_dir = screenplay_path.resolve().parent
    _run_preinstall(screenplay, working_dir)

    if keep_temp:
        temp_dir = run_layout.run_dir / "tmp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_context = None
    else:
        temp_context = tempfile.TemporaryDirectory(prefix="terminal-demo-studio-")
        temp_dir = Path(temp_context.name)

    try:
        try:
            scene_videos: list[Path] = []
            labels: list[str] = []

            for index, scenario in enumerate(screenplay.scenarios):
                scene_tape = run_layout.tapes_dir / f"scene_{index}.tape"
                scene_video = run_layout.scenes_dir / f"scene_{index}.mp4"
                renderer = _SCENARIO_RENDERERS.get(scenario.surface)
                if renderer is None:
                    raise NotImplementedError(
                        f"Scenario surface '{scenario.surface}' is not implemented yet"
                    )
                renderer(
                    scenario,
                    screenplay.settings,
                    scene_tape,
                    scene_video,
                    working_dir,
                )

                scene_videos.append(scene_video)
                labels.append(scenario.label)

            output_stem = _output_stem(screenplay.output)
            final_mp4 = run_layout.media_dir / f"{output_stem}.mp4"
            final_gif = run_layout.media_dir / f"{output_stem}.gif"

            target_mp4 = final_mp4 if produce_mp4 else temp_dir / f"{output_stem}.discard.mp4"
            target_gif = final_gif if produce_gif else None

            compose_split_screen(
                inputs=scene_videos,
                labels=labels,
                output_mp4=target_mp4,
                output_gif=target_gif,
                playback_mode=playback_mode,
                redaction_mode=resolved_redaction_mode,
            )

            summary_payload: dict[str, object] = {
                "run_id": run_layout.run_id,
                "lane": "scripted_vhs",
                "status": "success",
                "screenplay": str(screenplay_path.resolve()),
                "playback_mode": playback_mode,
                "media_redaction": resolved_redaction_mode,
                "media": {
                    "gif": str(final_gif) if produce_gif else None,
                    "mp4": str(final_mp4) if produce_mp4 else None,
                },
                "scenes": [str(path) for path in scene_videos],
            }
            write_summary(run_layout, summary_payload)

            return ScriptedRunResult(
                success=True,
                run_layout=run_layout,
                mp4_path=final_mp4 if produce_mp4 else None,
                gif_path=final_gif if produce_gif else None,
                error=None,
            )
        except Exception as exc:  # noqa: BLE001
            reason = str(exc)
            (run_layout.failure_dir / "reason.txt").write_text(reason, encoding="utf-8")
            write_summary(
                run_layout,
                {
                    "run_id": run_layout.run_id,
                    "lane": "scripted_vhs",
                    "status": "failed",
                    "screenplay": str(screenplay_path.resolve()),
                    "error": reason,
                    "failure_dir": str(run_layout.failure_dir),
                },
            )
            raise
    finally:
        if temp_context is not None:
            temp_context.cleanup()
