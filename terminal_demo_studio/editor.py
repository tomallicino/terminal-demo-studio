from __future__ import annotations

import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

Image: Any
ImageDraw: Any
ImageFont: Any
try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:  # pragma: no cover - runtime fallback when pillow is missing
    Image = None
    ImageDraw = None
    ImageFont = None

CommandRunner = Callable[[list[str], bool], None]
DurationProbe = Callable[[Path], float]
PlaybackMode = Literal["sequential", "simultaneous"]
HeaderMode = Literal["auto", "always", "never"]
LabelRenderer = Literal["drawtext", "image_overlay", "none"]

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
LABEL_IMAGE_TEXT_COLOR = (205, 214, 244, 255)
LABEL_IMAGE_BOX_COLOR = (15, 23, 42, 225)
LABEL_IMAGE_BORDER_COLOR = (108, 112, 134, 242)


def _default_run(cmd: list[str], check: bool) -> None:
    subprocess.run(cmd, check=check)


def _detect_drawtext_support() -> bool:
    try:
        probe = subprocess.run(
            ["ffmpeg", "-hide_banner", "-filters"],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return False
    combined = f"{probe.stdout}\n{probe.stderr}"
    return probe.returncode == 0 and "drawtext" in combined


def _detect_image_label_support() -> bool:
    return Image is not None and ImageDraw is not None and ImageFont is not None


def _load_label_font(size: int) -> Any:
    assert ImageFont is not None
    for name in ("DejaVuSans.ttf", "Arial.ttf", "LiberationSans-Regular.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _truncate_label_text(label: str, draw: Any, font: Any, max_text_width: int) -> str:
    left, _top, right, _bottom = draw.textbbox((0, 0), label, font=font)
    if right - left <= max_text_width:
        return label

    suffix = "..."
    suffix_left, _st, suffix_right, _sb = draw.textbbox((0, 0), suffix, font=font)
    suffix_width = suffix_right - suffix_left
    if suffix_width >= max_text_width:
        return suffix

    for end in range(len(label), 0, -1):
        candidate = f"{label[:end].rstrip()}{suffix}"
        c_left, _ct, c_right, _cb = draw.textbbox((0, 0), candidate, font=font)
        if c_right - c_left <= max_text_width:
            return candidate

    return suffix


def _max_badge_width_for_layout(input_count: int) -> int:
    if input_count <= 1:
        return 760
    if input_count == 2:
        return 500
    return 320


def _render_label_badge(label: str, output_path: Path, max_width: int | None = None) -> None:
    if not _detect_image_label_support():
        raise RuntimeError("Pillow is required for image-overlay labels")

    assert Image is not None
    assert ImageDraw is not None
    font = _load_label_font(34)

    probe = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    probe_draw = ImageDraw.Draw(probe)
    if max_width is not None:
        max_width = max(max_width, 200)
        max_text_width = max(max_width - 56, 120)
        label = _truncate_label_text(label, probe_draw, font, max_text_width)

    left, top, right, bottom = probe_draw.textbbox((0, 0), label, font=font)
    text_width = int(right - left)
    text_height = int(bottom - top)
    pad_x = 28
    pad_y = 14
    badge_width = int(max(text_width + pad_x * 2, 200))
    if max_width is not None:
        badge_width = int(min(badge_width, max_width))
    badge_height = int(text_height + pad_y * 2)

    badge = Image.new("RGBA", (badge_width, badge_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(badge)
    draw.rounded_rectangle(
        (0, 0, badge_width - 1, badge_height - 1),
        radius=16,
        fill=LABEL_IMAGE_BOX_COLOR,
        outline=LABEL_IMAGE_BORDER_COLOR,
        width=2,
    )

    text_x = int((badge_width - text_width) / 2 - left)
    text_y = int((badge_height - text_height) / 2 - top)
    draw.text((text_x, text_y), label, font=font, fill=LABEL_IMAGE_TEXT_COLOR)
    badge.save(output_path, format="PNG")


def _resolve_label_renderer(
    *,
    has_labels: bool,
    supports_drawtext: bool,
    supports_image_labels: bool,
) -> LabelRenderer:
    if not has_labels:
        return "none"
    if supports_drawtext:
        return "drawtext"
    if supports_image_labels:
        return "image_overlay"
    return "none"


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
    labels_renderable: bool,
) -> HeaderMode:
    if requested == "never":
        return "never"
    if labels_renderable:
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
    label_renderer: LabelRenderer,
    label_input_start: int,
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

    draw_labels = draw_header and bool(labels) and label_renderer != "none"
    if draw_header:
        style_chain = (
            "[stacked]"
            f"drawbox=x=0:y=0:w=iw:h={pane_top}:color={HEADER_COLOR}:t=fill,"
            f"drawbox=x=0:y={pane_top-2}:w=iw:h=2:color={HEADER_RULE_COLOR}:t=fill"
            "[styled]"
        )
        filter_parts.append(style_chain)
        if draw_labels and label_renderer == "drawtext":
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
        elif draw_labels and label_renderer == "image_overlay":
            pane_width_expr = (
                f"(main_w-{2 * CANVAS_MARGIN}-{(input_count - 1) * PANE_GAP})/{input_count}"
            )
            current = "[styled]"
            for index in range(input_count):
                x_expr = (
                    f"{CANVAS_MARGIN}"
                    f"+{index}*({pane_width_expr}+{PANE_GAP})"
                    f"+({pane_width_expr})/2-overlay_w/2"
                )
                output_tag = "[outv]" if index == input_count - 1 else f"[ol{index}]"
                filter_parts.append(
                    f"{current}[{label_input_start + index}:v]"
                    "overlay="
                    f"x={x_expr}:y={CANVAS_MARGIN + 18}:"
                    "eof_action=repeat:format=auto"
                    f"{output_tag}"
                )
                current = output_tag
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
    supports_image_labels: bool | None = None,
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
    if supports_image_labels is None:
        supports_image_labels = _detect_image_label_support()
    normalized_labels = _normalize_labels(labels, len(inputs))
    has_labels = any(label.strip() for label in normalized_labels)
    label_renderer = _resolve_label_renderer(
        has_labels=has_labels,
        supports_drawtext=supports_drawtext,
        supports_image_labels=supports_image_labels,
    )
    resolved_header_mode = _resolve_header_mode(
        requested=header_mode,
        labels_renderable=label_renderer != "none",
    )

    durations = [probe_duration(video) for video in inputs]
    offsets = _timeline_offsets(durations, playback_mode)
    total_duration = max(
        offsets[index] + durations[index] for index in range(len(inputs))
    )

    with tempfile.TemporaryDirectory(prefix="terminal-demo-studio-labels-") as tmpdir:
        label_paths: list[Path] = []
        if resolved_header_mode == "always" and label_renderer == "drawtext":
            for index, label in enumerate(normalized_labels):
                label_file = Path(tmpdir) / f"label_{index}.txt"
                label_file.write_text(label, encoding="utf-8")
                label_paths.append(label_file)
        elif resolved_header_mode == "always" and label_renderer == "image_overlay":
            max_badge_width = _max_badge_width_for_layout(len(inputs))
            for index, label in enumerate(normalized_labels):
                label_file = Path(tmpdir) / f"label_{index}.png"
                _render_label_badge(label, label_file, max_width=max_badge_width)
                label_paths.append(label_file)
        filter_complex = _build_filter_complex(
            input_count=len(inputs),
            labels=normalized_labels,
            label_paths=label_paths,
            durations=durations,
            offsets=offsets,
            total_duration=total_duration,
            header_mode=resolved_header_mode,
            label_renderer=label_renderer,
            label_input_start=len(inputs),
        )

        mp4_cmd: list[str] = ["ffmpeg", "-y"]
        for video in inputs:
            mp4_cmd.extend(["-i", str(video)])
        if resolved_header_mode == "always" and label_renderer == "image_overlay":
            for label_path in label_paths:
                mp4_cmd.extend(["-i", str(label_path)])
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
