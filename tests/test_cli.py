from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from terminal_demo_studio import cli
from terminal_demo_studio.artifacts import create_run_layout
from terminal_demo_studio.director import ScriptedRunResult


def _write_scripted_screenplay(path: Path) -> None:
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


def _write_autonomous_screenplay(path: Path) -> None:
    path.write_text(
        """
        title: Demo
        output: demo
        settings: {}
        scenarios:
          - label: Left
            execution_mode: autonomous_pty
            actions:
              - command: echo left
        """,
        encoding="utf-8",
    )


def _write_autonomous_video_screenplay(path: Path) -> None:
    path.write_text(
        """
        title: Demo
        output: demo
        settings: {}
        scenarios:
          - label: Left
            execution_mode: autonomous_video
            actions:
              - command: echo left
        """,
        encoding="utf-8",
    )


def _fake_scripted_result(tmp_path: Path) -> ScriptedRunResult:
    screenplay = tmp_path / "demo.yaml"
    screenplay.write_text(
        """
        title: Demo
        output: demo
        settings: {}
        scenarios:
          - label: One
            actions:
              - type: echo ok
        """,
        encoding="utf-8",
    )
    layout = create_run_layout(
        screenplay_path=screenplay,
        output_dir=tmp_path / "outputs",
        lane="scripted_vhs",
    )
    return ScriptedRunResult(
        success=True,
        run_layout=layout,
        mp4_path=layout.media_dir / "demo.mp4",
        gif_path=layout.media_dir / "demo.gif",
    )


def _fake_autonomous_result(tmp_path: Path, success: bool = True) -> object:
    layout = create_run_layout(
        screenplay_path=tmp_path / "demo.yaml",
        output_dir=tmp_path / "outputs",
        lane="autonomous_pty",
    )
    events = layout.runtime_dir / "events.jsonl"
    summary = layout.summary_path
    events.write_text("", encoding="utf-8")
    summary.write_text(
        json.dumps({"status": "success" if success else "failed", "lane": "autonomous_pty"}),
        encoding="utf-8",
    )

    class _Result:
        pass

    result = _Result()
    result.run_dir = layout.run_dir
    result.events_path = events
    result.summary_path = summary
    result.failure_dir = layout.failure_dir if not success else None
    result.success = success
    return result


def test_validate_json_schema_outputs_schema(tmp_path: Path) -> None:
    screenplay = tmp_path / "demo.yaml"
    _write_scripted_screenplay(screenplay)
    runner = CliRunner()

    result = runner.invoke(cli.app, ["validate", str(screenplay), "--json-schema"])

    assert result.exit_code == 0
    assert "properties" in result.output


def test_console_entrypoint_is_tds_only() -> None:
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")

    assert 'tds = "terminal_demo_studio.cli:main"' in text
    assert 'studio = "terminal_demo_studio.cli:main"' not in text


def test_new_creates_screenplay_file(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(cli.app, ["new", "sample", "--destination", str(tmp_path)])

    assert result.exit_code == 0
    created_path = tmp_path / "sample.yaml"
    assert created_path.exists()
    assert "Template: before_after_bugfix" in result.output
    assert "Next: tds validate" in result.output
    assert 'output: "sample"' in created_path.read_text(encoding="utf-8")


def test_new_uses_root_screenplays_as_default_destination(tmp_path: Path) -> None:
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    with runner.isolated_filesystem(temp_dir=str(project_dir)):
        result = runner.invoke(cli.app, ["new", "sample"])
        assert result.exit_code == 0
        assert (Path("screenplays") / "sample.yaml").exists()


def test_new_list_templates_returns_launch_pack_set() -> None:
    runner = CliRunner()

    result = runner.invoke(cli.app, ["new", "--list-templates"])

    assert result.exit_code == 0
    lines = [line.strip() for line in result.output.splitlines() if line.startswith("- ")]
    assert lines == [
        "- before_after_bugfix",
        "- error_then_fix",
        "- install_first_command",
        "- interactive_menu_showcase",
        "- policy_warning_gate",
        "- speedrun_cuts",
    ]


def test_new_list_templates_ignores_module_file_location(
    monkeypatch: object, tmp_path: Path
) -> None:
    fake_cli = tmp_path / "site-packages" / "terminal_demo_studio" / "cli.py"
    fake_cli.parent.mkdir(parents=True, exist_ok=True)
    fake_cli.write_text("# fake", encoding="utf-8")
    monkeypatch.setattr(cli, "__file__", str(fake_cli))

    runner = CliRunner()
    result = runner.invoke(cli.app, ["new", "--list-templates"])

    assert result.exit_code == 0
    assert "install_first_command" in result.output
    assert "speedrun_cuts" in result.output


def test_render_local_dispatches_to_director(monkeypatch: object, tmp_path: Path) -> None:
    screenplay = tmp_path / "demo.yaml"
    _write_scripted_screenplay(screenplay)

    called: dict[str, object] = {}

    def fake_run_director(**kwargs: object) -> ScriptedRunResult:
        called.update(kwargs)
        return _fake_scripted_result(tmp_path)

    monkeypatch.setattr(cli, "run_director", fake_run_director)

    runner = CliRunner()
    result = runner.invoke(cli.app, ["render", str(screenplay), "--local"])

    assert result.exit_code == 0
    assert called["screenplay_path"] == screenplay
    assert called["playback_mode"] == "sequential"
    assert called["produce_mp4"] is True
    assert called["produce_gif"] is True
    assert "STATUS=success" in result.output
    assert "RUN_DIR=" in result.output


def test_render_output_option_limits_artifacts(monkeypatch: object, tmp_path: Path) -> None:
    screenplay = tmp_path / "demo.yaml"
    _write_scripted_screenplay(screenplay)

    called: dict[str, object] = {}

    def fake_run_director(**kwargs: object) -> ScriptedRunResult:
        called.update(kwargs)
        scripted = _fake_scripted_result(tmp_path)
        return ScriptedRunResult(
            success=True,
            run_layout=scripted.run_layout,
            mp4_path=scripted.mp4_path,
            gif_path=None,
        )

    monkeypatch.setattr(cli, "run_director", fake_run_director)

    runner = CliRunner()
    result = runner.invoke(cli.app, ["render", str(screenplay), "--local", "--output", "mp4"])

    assert result.exit_code == 0
    assert called["produce_mp4"] is True
    assert called["produce_gif"] is False
    assert "MEDIA_MP4=" in result.output
    assert "MEDIA_GIF=" not in result.output


def test_render_docker_forwards_playback_mode(monkeypatch: object, tmp_path: Path) -> None:
    screenplay = tmp_path / "demo.yaml"
    _write_scripted_screenplay(screenplay)

    called: dict[str, object] = {}

    def fake_run_in_docker(**kwargs: object) -> dict[str, Path | str | None]:
        called.update(kwargs)
        return {
            "status": "success",
            "run_dir": Path("/tmp/run"),
            "summary": Path("/tmp/run/summary.json"),
            "media_mp4": Path("/tmp/run/media/demo.mp4"),
            "media_gif": Path("/tmp/run/media/demo.gif"),
        }

    monkeypatch.setattr(cli, "run_in_docker", fake_run_in_docker)

    runner = CliRunner()
    result = runner.invoke(
        cli.app,
        ["render", str(screenplay), "--docker", "--playback", "simultaneous"],
    )

    assert result.exit_code == 0
    assert called["playback_mode"] == "simultaneous"
    assert "MEDIA_GIF=" in result.output


def test_run_auto_falls_back_to_local_when_docker_unavailable(
    monkeypatch: object, tmp_path: Path
) -> None:
    screenplay = tmp_path / "demo.yaml"
    _write_scripted_screenplay(screenplay)

    local_called: dict[str, object] = {}

    def fake_run_in_docker(**kwargs: object) -> dict[str, Path | str | None]:
        raise cli.DockerError("docker daemon unreachable")

    def fake_run_director(**kwargs: object) -> ScriptedRunResult:
        local_called.update(kwargs)
        return _fake_scripted_result(tmp_path)

    monkeypatch.setattr(cli, "run_in_docker", fake_run_in_docker)
    monkeypatch.setattr(cli, "run_director", fake_run_director)

    runner = CliRunner()
    result = runner.invoke(cli.app, ["run", str(screenplay)])

    assert result.exit_code == 0
    assert local_called["screenplay_path"] == screenplay
    assert "Falling back to local mode" in result.output


def test_run_explicit_docker_stays_strict_when_docker_unavailable(
    monkeypatch: object, tmp_path: Path
) -> None:
    screenplay = tmp_path / "demo.yaml"
    _write_scripted_screenplay(screenplay)

    local_called = False

    def fake_run_in_docker(**kwargs: object) -> dict[str, Path | str | None]:
        raise cli.DockerError("docker daemon unreachable")

    def fake_run_director(**kwargs: object) -> ScriptedRunResult:
        nonlocal local_called
        local_called = True
        return _fake_scripted_result(tmp_path)

    monkeypatch.setattr(cli, "run_in_docker", fake_run_in_docker)
    monkeypatch.setattr(cli, "run_director", fake_run_director)

    runner = CliRunner()
    result = runner.invoke(cli.app, ["run", str(screenplay), "--docker"])

    assert result.exit_code != 0
    assert "docker daemon unreachable" in result.output
    assert local_called is False


def test_run_autonomous_mode_invokes_autonomous_runner(monkeypatch: object, tmp_path: Path) -> None:
    screenplay = tmp_path / "demo.yaml"
    _write_autonomous_screenplay(screenplay)

    called: dict[str, object] = {}

    def fake_run_autonomous(**kwargs: object) -> object:
        called.update(kwargs)
        return _fake_autonomous_result(tmp_path)

    monkeypatch.setattr(cli, "run_autonomous_screenplay", fake_run_autonomous)

    runner = CliRunner()
    result = runner.invoke(cli.app, ["run", str(screenplay), "--mode", "autonomous_pty"])

    assert result.exit_code == 0
    assert called["screenplay_path"] == screenplay
    assert "STATUS=success" in result.output
    assert "EVENTS=" in result.output


def test_run_autonomous_video_mode_invokes_video_runner(
    monkeypatch: object, tmp_path: Path
) -> None:
    screenplay = tmp_path / "demo.yaml"
    _write_autonomous_video_screenplay(screenplay)

    called: dict[str, object] = {}

    def fake_run_video(**kwargs: object) -> object:
        called.update(kwargs)
        layout = create_run_layout(
            screenplay_path=screenplay,
            output_dir=tmp_path / "outputs",
            lane="autonomous_video",
        )

        class _Result:
            success = True
            run_dir = layout.run_dir
            events_path = layout.runtime_dir / "events.jsonl"
            summary_path = layout.summary_path
            failure_dir = None
            mp4_path = layout.media_dir / "demo.mp4"
            gif_path = layout.media_dir / "demo.gif"

        return _Result()

    monkeypatch.setattr(cli, "missing_local_video_dependencies", lambda: [])
    monkeypatch.setattr(cli, "run_autonomous_video_screenplay", fake_run_video)

    runner = CliRunner()
    result = runner.invoke(cli.app, ["run", str(screenplay), "--mode", "autonomous_video"])

    assert result.exit_code == 0
    assert called["screenplay_path"] == screenplay
    assert "MEDIA_MP4=" in result.output
    assert "EVENTS=" in result.output


def test_run_autonomous_video_auto_falls_back_to_docker_when_local_missing(
    monkeypatch: object, tmp_path: Path
) -> None:
    screenplay = tmp_path / "demo.yaml"
    _write_autonomous_video_screenplay(screenplay)

    called: dict[str, object] = {}

    def fake_run_in_docker(**kwargs: object) -> dict[str, Path | str | None]:
        called.update(kwargs)
        return {
            "status": "success",
            "run_dir": Path("/tmp/tds/run"),
            "events": Path("/tmp/tds/run/runtime/events.jsonl"),
            "summary": Path("/tmp/tds/run/summary.json"),
            "media_mp4": Path("/tmp/tds/run/media/demo.mp4"),
            "media_gif": None,
        }

    monkeypatch.setattr(cli, "missing_local_video_dependencies", lambda: ["kitty", "xvfb"])
    monkeypatch.setattr(cli, "run_in_docker", fake_run_in_docker)

    runner = CliRunner()
    result = runner.invoke(cli.app, ["run", str(screenplay), "--mode", "autonomous_video"])

    assert result.exit_code == 0
    assert called["run_mode"] == "autonomous_video"
    assert "MEDIA_MP4=" in result.output


def test_run_auto_mode_uses_autonomous_video_when_scenario_declares_it(
    monkeypatch: object, tmp_path: Path
) -> None:
    screenplay = tmp_path / "demo.yaml"
    _write_autonomous_video_screenplay(screenplay)

    called = {"video": False}

    def fake_run_video(**kwargs: object) -> object:
        _ = kwargs
        called["video"] = True
        layout = create_run_layout(
            screenplay_path=screenplay,
            output_dir=tmp_path / "outputs",
            lane="autonomous_video",
        )

        class _Result:
            success = True
            run_dir = layout.run_dir
            events_path = layout.runtime_dir / "events.jsonl"
            summary_path = layout.summary_path
            failure_dir = None
            mp4_path = layout.media_dir / "demo.mp4"
            gif_path = layout.media_dir / "demo.gif"

        return _Result()

    monkeypatch.setattr(cli, "missing_local_video_dependencies", lambda: [])
    monkeypatch.setattr(cli, "run_autonomous_video_screenplay", fake_run_video)

    runner = CliRunner()
    result = runner.invoke(cli.app, ["run", str(screenplay), "--mode", "auto"])

    assert result.exit_code == 0
    assert called["video"] is True


def test_run_autonomous_video_auto_fails_when_local_and_docker_unavailable(
    monkeypatch: object, tmp_path: Path
) -> None:
    screenplay = tmp_path / "demo.yaml"
    _write_autonomous_video_screenplay(screenplay)

    monkeypatch.setattr(cli, "missing_local_video_dependencies", lambda: ["kitty"])
    monkeypatch.setattr(
        cli, "run_in_docker", lambda **_: (_ for _ in ()).throw(cli.DockerError("no docker"))
    )

    runner = CliRunner()
    result = runner.invoke(cli.app, ["run", str(screenplay), "--mode", "autonomous_video"])

    assert result.exit_code != 0
    assert "Missing local autonomous_video dependencies" in result.output
    assert "Docker fallback also failed" in result.output


def test_init_creates_starter_workspace(tmp_path: Path) -> None:
    runner = CliRunner()
    workspace = tmp_path / "workspace"

    result = runner.invoke(cli.app, ["init", "--destination", str(workspace)])

    assert result.exit_code == 0
    assert (workspace / "screenplays").is_dir()
    assert (workspace / "outputs").is_dir()
    starter = workspace / "screenplays" / "getting_started.yaml"
    assert starter.exists()
    assert 'output: "getting_started"' in starter.read_text(encoding="utf-8")
    assert "tds render" in result.output
    assert ".terminal_demo_studio_runs/" in result.output


def test_doctor_command_reports_pass(monkeypatch: object) -> None:
    def fake_doctor(mode: str = "auto") -> list[tuple[str, bool, str]]:
        assert mode == "auto"
        return [("docker", True, "ok")]

    monkeypatch.setattr(cli, "run_doctor_checks", fake_doctor)

    runner = CliRunner()
    result = runner.invoke(cli.app, ["doctor"])

    assert result.exit_code == 0
    assert "PASS docker: ok" in result.output


def test_doctor_treats_docker_failures_as_warning(monkeypatch: object) -> None:
    def fake_doctor(mode: str = "auto") -> list[tuple[str, bool, str]]:
        assert mode == "auto"
        return [
            ("docker-daemon", False, "docker is unavailable NEXT: open -a Docker"),
            ("screenplay-template", True, "ok"),
            ("screenplay-sample", True, "ok"),
            ("container-binaries", False, "skipped"),
        ]

    monkeypatch.setattr(cli, "run_doctor_checks", fake_doctor)

    runner = CliRunner()
    result = runner.invoke(cli.app, ["doctor"])

    assert result.exit_code == 0
    assert "WARN docker-daemon: docker is unavailable" in result.output


def test_debug_outputs_compact_summary(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True)
    summary = {
        "status": "failed",
        "lane": "scripted_vhs",
        "screenplay": "/tmp/demo.yaml",
        "failed_step_index": 1,
        "failed_action": "command",
        "reason": "command failed",
        "failure_dir": str(run_dir / "failure"),
        "media": {"gif": None, "mp4": None},
    }
    (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli.app, ["debug", str(run_dir)])

    assert result.exit_code == 0
    lines = [line for line in result.output.splitlines() if line.strip()]
    assert len(lines) <= 10
    assert any(line.startswith("STATUS=failed") for line in lines)
    assert any(line.startswith("NEXT=tds debug") for line in lines)


def test_debug_json_outputs_machine_readable_payload(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True)
    (run_dir / "summary.json").write_text(
        json.dumps({"status": "success", "lane": "scripted_vhs", "media": {}}),
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(cli.app, ["debug", str(run_dir), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["status"] == "success"
    assert payload["lane"] == "scripted_vhs"
    assert payload["run_dir"] == str(run_dir.resolve())


def test_render_template_quickstart_path(monkeypatch: object, tmp_path: Path) -> None:
    called: dict[str, object] = {}

    def fake_execute_render(**kwargs: object) -> None:
        called.update(kwargs)

    monkeypatch.setattr(cli, "_execute_render", fake_execute_render)

    runner = CliRunner()
    result = runner.invoke(
        cli.app,
        [
            "render",
            "--template",
            "install_first_command",
            "--name",
            "quickstart",
            "--destination",
            str(tmp_path),
            "--output",
            "gif",
            "--mode",
            "scripted_vhs",
            "--local",
        ],
    )

    assert result.exit_code == 0
    screenplay_path = called["screenplay"]
    assert isinstance(screenplay_path, Path)
    assert screenplay_path.exists()
    assert screenplay_path.name == "quickstart.yaml"
    assert called["output_formats"] == ("gif",)
