from __future__ import annotations

import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Literal

CommandRunner = Callable[[list[str], bool], None]
DurationProbe = Callable[[Path], float]
PlaybackMode = Literal["sequential", "simultaneous"]
HeaderMode = Literal["auto", "always", "never"]

TARGET_HEIGHT = 840
FRAME_RATE = 30
CANVAS_MARGIN = 36
HEADER_HEIGHT = 92
PANE_GAP = 56
BACKGROUND_COLOR = "0x11111B"
HEADER_COLOR = "0x181825@0.96"
HEADER_RULE_COLOR = "0x313244@0.9"
LABEL_TEXT_COLOR = "0xCDD6F4"
LABEL_BOX_COLOR = "0x0F172A@0.88"
LABEL_BORDER_COLOR = "0x6C7086@0.95"


def _default_run(cmd: list[str], check: bool) -> None:
    subprocess.run(cmd, check=check)


def _detect_drawtext_support() -> bool:
    probe = subprocess.run(
        ["ffmpeg", "-hide_banner", "-filters"],
        check=False,
        capture_output=True,
        text=True,
    )
    combined = f"{probe.stdout}\n{probe.stderr}"
    return probe.returncode == 0 and "drawtext" in combined


def _probe_duration(video: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "unknown ffprobe error"
        raise RuntimeError(f"Unable to probe duration for {video}: {message}")

    duration_text = result.stdout.strip()
    try:
        duration = float(duration_text)
    except ValueError as exc:
        raise RuntimeError(
            f"Unable to parse duration for {video}: {duration_text or '<empty>'}"
        ) from exc
    return max(duration, 0.0)


def _pane_x_expr(index: int, margin: int, gap: int) -> str:
    if index == 0:
        return str(margin)
    terms: list[str] = [str(margin)]
    for prior_index in range(index):
        terms.append(f"w{prior_index}")
        terms.append(str(gap))
    return "+".join(terms)


def _timeline_offsets(durations: list[float], playback_mode: PlaybackMode) -> list[float]:
    if playback_mode == "simultaneous":
        return [0.0 for _ in durations]

    offsets: list[float] = []
    elapsed = 0.0
    for duration in durations:
        offsets.append(elapsed)
        elapsed += duration
    return offsets


def _escape_filter_path(path: Path) -> str:
    return str(path).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


def _normalize_labels(labels: list[str], input_count: int) -> list[str]:
    if not labels:
        return []

    normalized = labels[:]
    if len(normalized) < input_count:
        normalized.extend(
            [
                f"Scenario {index + 1}"
                for index in range(len(normalized), input_count)
            ]
        )
    return normalized[:input_count]


def _resolve_header_mode(
    *,
    requested: HeaderMode,
    supports_drawtext: bool,
    labels: list[str],
) -> HeaderMode:
    if requested == "never":
        return "never"
    if requested == "always":
        if supports_drawtext and any(label.strip() for label in labels):
            return "always"
        return "never"
    if supports_drawtext and any(label.strip() for label in labels):
        return "always"
    return "never"


def _build_input_filters(
    *,
    input_count: int,
    durations: list[float],
    offsets: list[float],
    total_duration: float,
) -> list[str]:
    filters: list[str] = []
    for index in range(input_count):
        start_duration = offsets[index]
        stop_duration = max(
            total_duration - (offsets[index] + durations[index]),
            0.0,
        )
        filters.append(
            f"[{index}:v]"
            f"fps={FRAME_RATE},"
            f"scale=-2:{TARGET_HEIGHT}:flags=lanczos,"
            "format=yuv420p,"
            f"tpad=start_mode=clone:start_duration={start_duration:.3f}:"
            f"stop_mode=clone:stop_duration={stop_duration:.3f}"
            f"[v{index}]"
        )
    return filters


def _build_stacked_filter(*, input_count: int, pane_top: int, header_inset: int) -> str:
    if input_count == 1:
        return (
            "[v0]"
            f"pad=w=iw+{2 * CANVAS_MARGIN}:"
            f"h=ih+{2 * CANVAS_MARGIN + header_inset}:"
            f"x={CANVAS_MARGIN}:"
            f"y={pane_top}:"
            f"color={BACKGROUND_COLOR}"
            "[stacked]"
        )

    stack_inputs = "".join(f"[v{index}]" for index in range(input_count))
    layout = "|".join(
        f"{_pane_x_expr(index, CANVAS_MARGIN, PANE_GAP)}_{pane_top}"
        for index in range(input_count)
    )
    return (
        f"{stack_inputs}"
        f"xstack=inputs={input_count}:layout={layout}:fill={BACKGROUND_COLOR}"
        "[stacked]"
    )


def _build_filter_complex(
    *,
    input_count: int,
    labels: list[str],
    label_paths: list[Path],
    durations: list[float],
    offsets: list[float],
    total_duration: float,
    header_mode: HeaderMode,
) -> str:
    draw_header = header_mode == "always"
    pane_top = CANVAS_MARGIN + (HEADER_HEIGHT if draw_header else 0)
    input_filters = _build_input_filters(
        input_count=input_count,
        durations=durations,
        offsets=offsets,
        total_duration=total_duration,
    )
    stacked = _build_stacked_filter(
        input_count=input_count,
        pane_top=pane_top,
        header_inset=HEADER_HEIGHT if draw_header else 0,
    )
    filter_parts = [*input_filters, stacked]

    draw_labels = draw_header and bool(labels)
    if draw_header:
        style_chain = (
            "[stacked]"
            f"drawbox=x=0:y=0:w=iw:h={pane_top}:color={HEADER_COLOR}:t=fill,"
            f"drawbox=x=0:y={pane_top-2}:w=iw:h=2:color={HEADER_RULE_COLOR}:t=fill"
            "[styled]"
        )
        filter_parts.append(style_chain)
        if draw_labels:
            draw_parts: list[str] = []
            pane_width_expr = (
                f"(w-{2 * CANVAS_MARGIN}-{(input_count - 1) * PANE_GAP})/{input_count}"
            )
            for index, label_path in enumerate(label_paths):
                x_expr = (
                    f"{CANVAS_MARGIN}"
                    f"+{index}*({pane_width_expr}+{PANE_GAP})"
                    f"+({pane_width_expr})/2-text_w/2"
                )
                draw_parts.append(
                    "drawtext="
                    f"textfile='{_escape_filter_path(label_path)}':"
                    f"fontcolor={LABEL_TEXT_COLOR}:fontsize=34:"
                    f"x={x_expr}:y={CANVAS_MARGIN + 20}:"
                    f"box=1:boxcolor={LABEL_BOX_COLOR}:boxborderw=14:"
                    f"borderw=1:bordercolor={LABEL_BORDER_COLOR}:"
                    "shadowcolor=0x000000@0.6:shadowx=0:shadowy=2"
                )
            filter_parts.append(f"[styled]{','.join(draw_parts)}[outv]")
        else:
            filter_parts.append("[styled]copy[outv]")
    else:
        filter_parts.append("[stacked]copy[outv]")

    return ";".join(filter_parts)


def compose_split_screen(
    inputs: list[Path],
    labels: list[str],
    output_mp4: Path,
    output_gif: Path,
    run_cmd: CommandRunner = _default_run,
    supports_drawtext: bool | None = None,
    playback_mode: PlaybackMode = "sequential",
    probe_duration: DurationProbe = _probe_duration,
    header_mode: HeaderMode = "auto",
) -> None:
    if len(inputs) < 1:
        raise ValueError("At least one input video is required for output")
    if playback_mode not in {"sequential", "simultaneous"}:
        raise ValueError(f"Unsupported playback mode: {playback_mode}")
    if header_mode not in {"auto", "always", "never"}:
        raise ValueError(f"Unsupported header mode: {header_mode}")

    if supports_drawtext is None:
        supports_drawtext = _detect_drawtext_support()
    normalized_labels = _normalize_labels(labels, len(inputs))
    resolved_header_mode = _resolve_header_mode(
        requested=header_mode,
        supports_drawtext=supports_drawtext,
        labels=normalized_labels,
    )

    durations = [probe_duration(video) for video in inputs]
    offsets = _timeline_offsets(durations, playback_mode)
    total_duration = max(
        offsets[index] + durations[index] for index in range(len(inputs))
    )

    with tempfile.TemporaryDirectory(prefix="terminal-demo-studio-labels-") as tmpdir:
        label_paths: list[Path] = []
        for index, label in enumerate(normalized_labels):
            label_file = Path(tmpdir) / f"label_{index}.txt"
            label_file.write_text(label, encoding="utf-8")
            label_paths.append(label_file)
        filter_complex = _build_filter_complex(
            input_count=len(inputs),
            labels=normalized_labels,
            label_paths=label_paths,
            durations=durations,
            offsets=offsets,
            total_duration=total_duration,
            header_mode=resolved_header_mode,
        )

        mp4_cmd: list[str] = ["ffmpeg", "-y"]
        for video in inputs:
            mp4_cmd.extend(["-i", str(video)])
        mp4_cmd.extend(
            [
                "-filter_complex",
                filter_complex,
                "-map",
                "[outv]",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                "-an",
                str(output_mp4),
            ]
        )

        gif_cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(output_mp4),
            "-filter_complex",
            "fps=18,split[s0][s1];[s0]palettegen=stats_mode=diff[p];"
            "[s1][p]paletteuse=dither=sierra2_4a",
            "-loop",
            "0",
            str(output_gif),
        ]

        run_cmd(mp4_cmd, True)
        run_cmd(gif_cmd, True)
