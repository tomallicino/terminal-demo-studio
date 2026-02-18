from __future__ import annotations

from pathlib import Path

from terminal_demo_studio.editor import compose_split_screen


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

    filter_arg_index = calls[0].index("-filter_complex") + 1
    filter_value = calls[0][filter_arg_index]
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
        probe_duration=lambda _: 2.0,
    )

    filter_arg_index = calls[0].index("-filter_complex") + 1
    filter_value = calls[0][filter_arg_index]
    assert "xstack=inputs=2:layout=" in filter_value
    assert "drawtext" not in filter_value


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

    filter_arg_index = calls[0].index("-filter_complex") + 1
    filter_value = calls[0][filter_arg_index]
    assert "xstack=" not in filter_value
    assert "pad=w=iw+" in filter_value
