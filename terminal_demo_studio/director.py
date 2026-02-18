from __future__ import annotations

import subprocess
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from terminal_demo_studio.editor import compose_split_screen
from terminal_demo_studio.models import Scenario, Screenplay, Settings, load_screenplay
from terminal_demo_studio.runtime.shells import build_shell_command
from terminal_demo_studio.tape import compile_tape

PlaybackMode = Literal["sequential", "simultaneous"]


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
) -> tuple[Path | None, Path | None]:
    screenplay = load_screenplay(screenplay_path)

    if not produce_mp4 and not produce_gif:
        raise ValueError("At least one output type must be enabled")

    working_dir = screenplay_path.resolve().parent
    destination = output_dir.resolve() if output_dir else working_dir
    destination.mkdir(parents=True, exist_ok=True)

    _run_preinstall(screenplay, working_dir)

    if keep_temp:
        temp_dir = destination / f".terminal_demo_studio_tmp_{int(time.time())}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_context = None
    else:
        temp_context = tempfile.TemporaryDirectory(prefix="terminal-demo-studio-")
        temp_dir = Path(temp_context.name)

    try:
        scene_videos: list[Path] = []
        labels: list[str] = []

        for index, scenario in enumerate(screenplay.scenarios):
            scene_tape = temp_dir / f"scene_{index}.tape"
            scene_video = temp_dir / f"scene_{index}.mp4"
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
        final_mp4 = destination / f"{output_stem}.mp4"
        final_gif = destination / f"{output_stem}.gif"

        target_mp4 = final_mp4 if produce_mp4 else temp_dir / f"{output_stem}.discard.mp4"
        target_gif = final_gif if produce_gif else temp_dir / f"{output_stem}.discard.gif"

        compose_split_screen(
            inputs=scene_videos,
            labels=labels,
            output_mp4=target_mp4,
            output_gif=target_gif,
            playback_mode=playback_mode,
        )

        return (
            final_mp4 if produce_mp4 else None,
            final_gif if produce_gif else None,
        )
    finally:
        if temp_context is not None:
            temp_context.cleanup()
