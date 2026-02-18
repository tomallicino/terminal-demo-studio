from __future__ import annotations

from pathlib import Path

from terminal_demo_studio import director


def _write_screenplay(path: Path) -> None:
    path.write_text(
        """
        title: Demo
        output: demo
        settings: {}
        scenarios:
          - label: Left
            actions:
              - type: echo left
          - label: Right
            actions:
              - type: echo right
        """,
        encoding="utf-8",
    )


def _write_single_screenplay(path: Path) -> None:
    path.write_text(
        """
        title: Demo
        output: demo
        settings: {}
        scenarios:
          - label: Only
            actions:
              - type: echo only
        """,
        encoding="utf-8",
    )


def test_run_director_uses_sequential_playback_by_default(
    monkeypatch: object, tmp_path: Path
) -> None:
    screenplay = tmp_path / "demo.yaml"
    _write_screenplay(screenplay)

    captured: dict[str, object] = {}

    def fake_renderer(*_: object) -> None:
        return None

    def fake_compose(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setitem(director._SCENARIO_RENDERERS, "terminal", fake_renderer)
    monkeypatch.setattr(director, "compose_split_screen", fake_compose)

    director.run_director(screenplay_path=screenplay, output_dir=tmp_path)

    assert captured["playback_mode"] == "sequential"


def test_run_director_forwards_requested_playback_mode(
    monkeypatch: object, tmp_path: Path
) -> None:
    screenplay = tmp_path / "demo.yaml"
    _write_screenplay(screenplay)

    captured: dict[str, object] = {}

    def fake_renderer(*_: object) -> None:
        return None

    def fake_compose(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setitem(director._SCENARIO_RENDERERS, "terminal", fake_renderer)
    monkeypatch.setattr(director, "compose_split_screen", fake_compose)

    director.run_director(
        screenplay_path=screenplay,
        output_dir=tmp_path,
        playback_mode="simultaneous",
    )

    assert captured["playback_mode"] == "simultaneous"


def test_run_director_allows_single_scenario(
    monkeypatch: object, tmp_path: Path
) -> None:
    screenplay = tmp_path / "demo.yaml"
    _write_single_screenplay(screenplay)
    captured: dict[str, object] = {}

    def fake_renderer(*_: object) -> None:
        return None

    def fake_compose(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setitem(director._SCENARIO_RENDERERS, "terminal", fake_renderer)
    monkeypatch.setattr(director, "compose_split_screen", fake_compose)

    director.run_director(screenplay_path=screenplay, output_dir=tmp_path)

    assert len(captured["inputs"]) == 1


def test_run_director_returns_none_for_disabled_outputs(
    monkeypatch: object, tmp_path: Path
) -> None:
    screenplay = tmp_path / "demo.yaml"
    _write_screenplay(screenplay)

    def fake_renderer(*_: object) -> None:
        return None

    def fake_compose(**_: object) -> None:
        return None

    monkeypatch.setitem(director._SCENARIO_RENDERERS, "terminal", fake_renderer)
    monkeypatch.setattr(director, "compose_split_screen", fake_compose)

    result = director.run_director(
        screenplay_path=screenplay,
        output_dir=tmp_path,
        produce_mp4=False,
        produce_gif=True,
    )

    assert result.mp4_path is None
    assert result.gif_path == result.run_layout.media_dir / "demo.gif"


def test_run_director_writes_canonical_artifact_layout(
    monkeypatch: object, tmp_path: Path
) -> None:
    screenplay = tmp_path / "demo.yaml"
    _write_screenplay(screenplay)

    def fake_renderer(*_: object) -> None:
        return None

    def fake_compose(**_: object) -> None:
        return None

    monkeypatch.setitem(director._SCENARIO_RENDERERS, "terminal", fake_renderer)
    monkeypatch.setattr(director, "compose_split_screen", fake_compose)

    result = director.run_director(screenplay_path=screenplay, output_dir=tmp_path)

    run_dir = result.run_layout.run_dir
    assert (run_dir / "manifest.json").exists()
    assert (run_dir / "summary.json").exists()
    assert (run_dir / "media").is_dir()
    assert (run_dir / "scenes").is_dir()
    assert (run_dir / "tapes").is_dir()


def test_shell_command_prefers_configured_powershell_on_windows(monkeypatch: object) -> None:
    import terminal_demo_studio.runtime.shells as shells

    monkeypatch.setattr(shells.platform, "system", lambda: "Windows")
    monkeypatch.setattr(shells.shutil, "which", lambda name: "powershell")

    cmd = director._build_shell_command("echo hi", "pwsh")

    assert cmd[:3] == ["powershell", "-NoProfile", "-Command"]
    assert cmd[-1] == "echo hi"


def test_shell_command_defaults_to_bash_then_sh_on_posix(monkeypatch: object) -> None:
    import terminal_demo_studio.runtime.shells as shells

    monkeypatch.setattr(shells.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(
        shells.shutil, "which", lambda name: "/bin/bash" if name == "bash" else None
    )

    cmd = director._build_shell_command("echo hi", "auto")

    assert cmd == ["bash", "-lc", "echo hi"]
