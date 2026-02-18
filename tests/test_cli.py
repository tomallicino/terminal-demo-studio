from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from terminal_demo_studio import cli


def test_validate_json_schema_outputs_schema(tmp_path: Path) -> None:
    screenplay = tmp_path / "demo.yaml"
    screenplay.write_text(
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
    runner = CliRunner()

    result = runner.invoke(cli.app, ["validate", str(screenplay), "--json-schema"])

    assert result.exit_code == 0
    assert "properties" in result.output


def test_new_creates_screenplay_file(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        ["new", "sample", "--destination", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert (tmp_path / "sample.yaml").exists()
    assert "Template: dev_bugfix" in result.output
    assert "Next: studio validate" in result.output
    created = (tmp_path / "sample.yaml").read_text(encoding="utf-8")
    assert 'output: "sample"' in created


def test_new_uses_root_screenplays_as_default_destination(tmp_path: Path) -> None:
    runner = CliRunner()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Invoke from project directory to validate the relative default destination.
    with runner.isolated_filesystem(temp_dir=str(project_dir)):
        result = runner.invoke(cli.app, ["new", "sample"])
        assert result.exit_code == 0
        assert (Path("screenplays") / "sample.yaml").exists()


def test_new_list_templates() -> None:
    runner = CliRunner()

    result = runner.invoke(cli.app, ["new", "--list-templates"])

    assert result.exit_code == 0
    assert "dev_bugfix" in result.output
    assert "drift_protection" in result.output
    assert "release_compliance" in result.output
    assert "policy_guard" in result.output


def test_new_list_templates_ignores_module_file_location(
    monkeypatch: object, tmp_path: Path
) -> None:
    # Simulate an installed layout where templates are not adjacent to cli.py.
    fake_cli = tmp_path / "site-packages" / "terminal_demo_studio" / "cli.py"
    fake_cli.parent.mkdir(parents=True, exist_ok=True)
    fake_cli.write_text("# fake", encoding="utf-8")
    monkeypatch.setattr(cli, "__file__", str(fake_cli))

    runner = CliRunner()
    result = runner.invoke(cli.app, ["new", "--list-templates"])

    assert result.exit_code == 0
    assert "dev_bugfix" in result.output
    assert "triage" in result.output


def test_validate_explain_outputs_scenario_summary(tmp_path: Path) -> None:
    screenplay = tmp_path / "demo.yaml"
    screenplay.write_text(
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
    runner = CliRunner()

    result = runner.invoke(cli.app, ["validate", str(screenplay), "--explain"])

    assert result.exit_code == 0
    assert "Scenarios: 2" in result.output
    assert "Left" in result.output
    assert "Right" in result.output


def test_run_local_dispatches_to_director(monkeypatch: object, tmp_path: Path) -> None:
    screenplay = tmp_path / "demo.yaml"
    screenplay.write_text(
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

    called: dict[str, object] = {}

    def fake_run_director(**kwargs: object) -> tuple[Path, Path]:
        called.update(kwargs)
        return (Path("a.mp4"), Path("a.gif"))

    monkeypatch.setattr(cli, "run_director", fake_run_director)

    runner = CliRunner()
    result = runner.invoke(cli.app, ["run", str(screenplay), "--local"])

    assert result.exit_code == 0
    assert called["screenplay_path"] == screenplay
    assert called["playback_mode"] == "sequential"


def test_run_local_allows_simultaneous_playback(monkeypatch: object, tmp_path: Path) -> None:
    screenplay = tmp_path / "demo.yaml"
    screenplay.write_text(
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

    called: dict[str, object] = {}

    def fake_run_director(**kwargs: object) -> tuple[Path, Path]:
        called.update(kwargs)
        return (Path("a.mp4"), Path("a.gif"))

    monkeypatch.setattr(cli, "run_director", fake_run_director)

    runner = CliRunner()
    result = runner.invoke(
        cli.app,
        ["run", str(screenplay), "--local", "--playback", "simultaneous"],
    )

    assert result.exit_code == 0
    assert called["playback_mode"] == "simultaneous"


def test_run_docker_forwards_playback_mode(monkeypatch: object, tmp_path: Path) -> None:
    screenplay = tmp_path / "demo.yaml"
    screenplay.write_text(
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

    called: dict[str, object] = {}

    def fake_run_in_docker(**kwargs: object) -> None:
        called.update(kwargs)

    monkeypatch.setattr(cli, "run_in_docker", fake_run_in_docker)

    runner = CliRunner()
    result = runner.invoke(
        cli.app,
        ["run", str(screenplay), "--docker", "--playback", "simultaneous"],
    )

    assert result.exit_code == 0
    assert called["playback_mode"] == "simultaneous"


def test_run_auto_falls_back_to_local_when_docker_unavailable(
    monkeypatch: object, tmp_path: Path
) -> None:
    screenplay = tmp_path / "demo.yaml"
    screenplay.write_text(
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

    local_called: dict[str, object] = {}

    def fake_run_in_docker(**kwargs: object) -> None:
        raise cli.DockerError("docker daemon unreachable")

    def fake_run_director(**kwargs: object) -> tuple[Path, Path]:
        local_called.update(kwargs)
        return (Path("a.mp4"), Path("a.gif"))

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
    screenplay.write_text(
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

    local_called = False

    def fake_run_in_docker(**kwargs: object) -> None:
        raise cli.DockerError("docker daemon unreachable")

    def fake_run_director(**kwargs: object) -> tuple[Path, Path]:
        nonlocal local_called
        local_called = True
        return (Path("a.mp4"), Path("a.gif"))

    monkeypatch.setattr(cli, "run_in_docker", fake_run_in_docker)
    monkeypatch.setattr(cli, "run_director", fake_run_director)

    runner = CliRunner()
    result = runner.invoke(cli.app, ["run", str(screenplay), "--docker"])

    assert result.exit_code != 0
    assert "docker daemon unreachable" in result.output
    assert local_called is False


def test_doctor_command_reports_pass(monkeypatch: object) -> None:
    def fake_doctor(mode: str = "auto") -> list[tuple[str, bool, str]]:
        assert mode == "auto"
        return [("docker", True, "ok")]

    monkeypatch.setattr(cli, "run_doctor_checks", fake_doctor)

    runner = CliRunner()
    result = runner.invoke(cli.app, ["doctor"])

    assert result.exit_code == 0
    assert "PASS" in result.output


def test_doctor_treats_docker_failures_as_warning(monkeypatch: object) -> None:
    def fake_doctor(mode: str = "auto") -> list[tuple[str, bool, str]]:
        assert mode == "auto"
        return [
            ("docker-daemon", False, "docker is unavailable"),
            ("screenplay-template", True, "ok"),
            ("screenplay-sample", True, "ok"),
            ("container-binaries", False, "skipped"),
        ]

    monkeypatch.setattr(cli, "run_doctor_checks", fake_doctor)

    runner = CliRunner()
    result = runner.invoke(cli.app, ["doctor"])

    assert result.exit_code == 0
    assert "WARN docker-daemon: docker is unavailable" in result.output
    assert "PASS screenplay-template: ok" in result.output


def test_doctor_autonomous_mode_treats_render_binaries_as_warnings(monkeypatch: object) -> None:
    def fake_doctor(mode: str = "auto") -> list[tuple[str, bool, str]]:
        assert mode == "autonomous_pty"
        return [
            ("local-vhs", False, "vhs not found in PATH"),
            ("local-ffmpeg", False, "ffmpeg not found in PATH"),
            ("local-ffprobe", False, "ffprobe not found in PATH"),
            ("screenplay-template", True, "ok"),
            ("screenplay-sample", True, "ok"),
        ]

    monkeypatch.setattr(cli, "run_doctor_checks", fake_doctor)

    runner = CliRunner()
    result = runner.invoke(cli.app, ["doctor", "--mode", "autonomous_pty"])

    assert result.exit_code == 0
    assert "WARN local-vhs: vhs not found in PATH" in result.output
    assert "WARN local-ffmpeg: ffmpeg not found in PATH" in result.output
    assert "WARN local-ffprobe: ffprobe not found in PATH" in result.output
    assert "PASS screenplay-template: ok" in result.output


def test_run_autonomous_mode_invokes_autonomous_runner(
    monkeypatch: object, tmp_path: Path
) -> None:
    screenplay = tmp_path / "demo.yaml"
    screenplay.write_text(
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

    called: dict[str, object] = {}

    class _Result:
        success = True
        events_path = Path("events.jsonl")
        summary_path = Path("summary.json")
        failure_dir = None

    def fake_run_autonomous(**kwargs: object) -> _Result:
        called.update(kwargs)
        return _Result()

    monkeypatch.setattr(cli, "run_autonomous_screenplay", fake_run_autonomous)

    runner = CliRunner()
    result = runner.invoke(cli.app, ["run", str(screenplay), "--mode", "autonomous_pty"])

    assert result.exit_code == 0
    assert "Autonomous run complete" in result.output
    assert called["screenplay_path"] == screenplay


def test_run_auto_mode_uses_autonomous_when_scenario_declares_it(
    monkeypatch: object, tmp_path: Path
) -> None:
    screenplay = tmp_path / "demo.yaml"
    screenplay.write_text(
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

    called = {"autonomous": False}

    class _Result:
        success = True
        events_path = Path("events.jsonl")
        summary_path = Path("summary.json")
        failure_dir = None

    def fake_run_autonomous(**kwargs: object) -> _Result:
        called["autonomous"] = True
        return _Result()

    monkeypatch.setattr(cli, "run_autonomous_screenplay", fake_run_autonomous)

    runner = CliRunner()
    result = runner.invoke(cli.app, ["run", str(screenplay), "--mode", "auto"])

    assert result.exit_code == 0
    assert called["autonomous"] is True


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
    assert "studio run" in result.output


def test_init_respects_existing_file_without_force(tmp_path: Path) -> None:
    runner = CliRunner()
    workspace = tmp_path / "workspace"
    screenplays = workspace / "screenplays"
    screenplays.mkdir(parents=True)
    starter = screenplays / "getting_started.yaml"
    starter.write_text("title: Existing\n", encoding="utf-8")

    result = runner.invoke(cli.app, ["init", "--destination", str(workspace)])

    assert result.exit_code != 0
    assert "already exists" in result.output
