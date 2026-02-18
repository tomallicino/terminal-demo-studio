from __future__ import annotations

from pathlib import Path

from PIL import Image

import terminal_demo_studio.editor as editor
from terminal_demo_studio.editor import compose_split_screen


def _extract_filter_complex(cmd: list[str]) -> str:
    filter_arg_index = cmd.index("-filter_complex") + 1
    return cmd[filter_arg_index]


def test_compose_runs_mp4_and_gif_ffmpeg_commands(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], check: bool) -> None:
        assert check is True
        calls.append(cmd)

    left = tmp_path / "left.mp4"
    right = tmp_path / "right.mp4"
    out_mp4 = tmp_path / "out.mp4"
    out_gif = tmp_path / "out.gif"

    compose_split_screen(
        [left, right],
        ["Without Cask", "With Cask"],
        out_mp4,
        out_gif,
        run_cmd=fake_run,
        probe_duration=lambda _: 2.5,
    )

    assert len(calls) == 2
    assert calls[0][0] == "ffmpeg"
    assert "xstack=inputs=2:layout=" in " ".join(calls[0])
    assert "start_duration=2.500" in " ".join(calls[0])
    assert str(out_mp4) in calls[0]
    assert calls[1][0] == "ffmpeg"
    assert "palettegen" in " ".join(calls[1])
    assert str(out_gif) in calls[1]


def test_compose_simultaneous_mode_does_not_delay_inputs(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], check: bool) -> None:
        assert check is True
        calls.append(cmd)

    left = tmp_path / "left.mp4"
    right = tmp_path / "right.mp4"
    out_mp4 = tmp_path / "out.mp4"
    out_gif = tmp_path / "out.gif"

    compose_split_screen(
        [left, right],
        ["Left", "Right"],
        out_mp4,
        out_gif,
        run_cmd=fake_run,
        playback_mode="simultaneous",
        probe_duration=lambda _: 3.0,
    )

    filter_value = _extract_filter_complex(calls[0])
    assert "start_duration=0.000" in filter_value
    assert "start_duration=3.000" not in filter_value


def test_compose_falls_back_when_drawtext_unavailable(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], check: bool) -> None:
        assert check is True
        calls.append(cmd)

    left = tmp_path / "left.mp4"
    right = tmp_path / "right.mp4"
    out_mp4 = tmp_path / "out.mp4"
    out_gif = tmp_path / "out.gif"

    compose_split_screen(
        [left, right],
        ["Left", "Right"],
        out_mp4,
        out_gif,
        run_cmd=fake_run,
        supports_drawtext=False,
        supports_image_labels=True,
        probe_duration=lambda _: 2.0,
    )

    mp4_cmd = calls[0]
    assert mp4_cmd.count("-i") == 4
    filter_value = _extract_filter_complex(calls[0])
    assert "xstack=inputs=2:layout=" in filter_value
    assert "drawtext" not in filter_value
    assert "overlay=" in filter_value
    assert "main_w-" in filter_value


def test_compose_supports_single_input_layout(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], check: bool) -> None:
        assert check is True
        calls.append(cmd)

    single = tmp_path / "single.mp4"
    out_mp4 = tmp_path / "out.mp4"
    out_gif = tmp_path / "out.gif"

    compose_split_screen(
        [single],
        ["Single"],
        out_mp4,
        out_gif,
        run_cmd=fake_run,
        supports_drawtext=False,
        probe_duration=lambda _: 2.0,
    )

    filter_value = _extract_filter_complex(calls[0])
    assert "xstack=" not in filter_value
    assert "pad=w=iw+" in filter_value


def test_compose_skips_header_when_no_label_renderer_available(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], check: bool) -> None:
        assert check is True
        calls.append(cmd)

    left = tmp_path / "left.mp4"
    right = tmp_path / "right.mp4"

    compose_split_screen(
        [left, right],
        ["Left", "Right"],
        tmp_path / "out.mp4",
        tmp_path / "out.gif",
        run_cmd=fake_run,
        supports_drawtext=False,
        supports_image_labels=False,
        probe_duration=lambda _: 1.0,
    )

    filter_value = _extract_filter_complex(calls[0])
    pane_top = editor.CANVAS_MARGIN
    assert f"layout=36_{pane_top}|36+w0+56_{pane_top}" in filter_value
    assert "drawbox=x=0:y=0:w=iw:h=" not in filter_value


def test_compose_skips_header_when_labels_are_empty(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], check: bool) -> None:
        assert check is True
        calls.append(cmd)

    left = tmp_path / "left.mp4"
    right = tmp_path / "right.mp4"

    compose_split_screen(
        [left, right],
        [],
        tmp_path / "out.mp4",
        tmp_path / "out.gif",
        run_cmd=fake_run,
        supports_drawtext=True,
        probe_duration=lambda _: 1.0,
    )

    filter_value = _extract_filter_complex(calls[0])
    pane_top = editor.CANVAS_MARGIN
    assert f"layout=36_{pane_top}|36+w0+56_{pane_top}" in filter_value
    assert "drawtext=" not in filter_value
    assert "drawbox=x=0:y=0:w=iw:h=" not in filter_value


def test_drawtext_detection_checks_both_stdout_and_stderr(monkeypatch: object) -> None:
    class _Proc:
        returncode = 0
        stdout = ""
        stderr = " ... drawtext ..."

    monkeypatch.setattr(editor.subprocess, "run", lambda *args, **kwargs: _Proc())

    assert editor._detect_drawtext_support() is True


def test_drawtext_detection_returns_false_when_ffmpeg_missing(monkeypatch: object) -> None:
    def _raise(*args: object, **kwargs: object) -> object:
        raise FileNotFoundError("ffmpeg")

    monkeypatch.setattr(editor.subprocess, "run", _raise)

    assert editor._detect_drawtext_support() is False


def test_render_label_badge_respects_max_width(tmp_path: Path) -> None:
    badge = tmp_path / "label.png"
    editor._render_label_badge(
        "Non-Compliant Candidate with an extremely long label title that should truncate",
        badge,
        max_width=260,
    )

    with Image.open(badge) as img:
        width, _height = img.size

    assert width <= 260
