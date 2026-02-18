from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import terminal_demo_studio.doctor as doctor
from terminal_demo_studio.doctor import run_doctor_checks


@dataclass
class _ProcResult:
    returncode: int
    stdout: str
    stderr: str


def test_doctor_sanitizes_docker_error_noise(monkeypatch: object) -> None:
    def fake_run(cmd: list[str], check: bool, capture_output: bool, text: bool) -> _ProcResult:
        assert check is False
        assert capture_output is True
        assert text is True
        if cmd == ["docker", "info"]:
            return _ProcResult(
                returncode=1,
                stdout="",
                stderr=(
                    "Cannot connect to the Docker daemon at unix:///tmp/docker.sock. "
                    "Is the docker daemon running?\nerrors pretty printing info"
                ),
            )
        raise AssertionError(f"Unexpected subprocess call: {cmd}")

    monkeypatch.setattr("terminal_demo_studio.doctor.subprocess.run", fake_run)
    monkeypatch.setattr(doctor, "_binary_exists", lambda name: False)
    monkeypatch.setattr(doctor, "_ffmpeg_has_drawtext", lambda: False)
    monkeypatch.setattr(
        doctor,
        "_packaged_template_checks",
        lambda: [
            ("screenplay-template", True, "ok"),
            ("screenplay-sample", True, "ok"),
        ],
    )
    monkeypatch.setattr(
        doctor,
        "_container_binary_check",
        lambda docker_ok: ("container-binaries", False, "skipped"),
    )

    checks = run_doctor_checks(mode="scripted_vhs")

    docker_check = next(item for item in checks if item[0] == "docker-daemon")
    assert docker_check[1] is False
    assert "Cannot connect" in docker_check[2]
    assert "pretty printing info" not in docker_check[2]


def test_doctor_loads_packaged_screenplay_checks_without_repo_layout(
    monkeypatch: object, tmp_path: Path
) -> None:
    fake_file = tmp_path / "site-packages" / "terminal_demo_studio" / "doctor.py"
    fake_file.parent.mkdir(parents=True, exist_ok=True)
    fake_file.write_text("# fake", encoding="utf-8")
    monkeypatch.setattr(doctor, "__file__", str(fake_file))

    def fake_run(cmd: list[str], check: bool, capture_output: bool, text: bool) -> _ProcResult:
        assert check is False
        assert capture_output is True
        assert text is True
        if cmd == ["docker", "info"]:
            return _ProcResult(
                returncode=1,
                stdout="",
                stderr="Cannot connect to the Docker daemon",
            )
        raise AssertionError(f"Unexpected subprocess call: {cmd}")

    monkeypatch.setattr("terminal_demo_studio.doctor.subprocess.run", fake_run)
    monkeypatch.setattr(doctor, "_binary_exists", lambda name: False)
    monkeypatch.setattr(doctor, "_ffmpeg_has_drawtext", lambda: False)
    monkeypatch.setattr(
        doctor,
        "_container_binary_check",
        lambda docker_ok: ("container-binaries", False, "skipped"),
    )

    checks = run_doctor_checks(mode="scripted_vhs")

    template_check = next(item for item in checks if item[0] == "screenplay-template")
    sample_check = next(item for item in checks if item[0] == "screenplay-sample")
    assert template_check[1] is True
    assert sample_check[1] is True


def test_doctor_handles_missing_docker_binary(monkeypatch: object) -> None:
    def fake_run(cmd: list[str], check: bool, capture_output: bool, text: bool) -> _ProcResult:
        assert cmd == ["docker", "info"]
        raise FileNotFoundError("docker")

    monkeypatch.setattr("terminal_demo_studio.doctor.subprocess.run", fake_run)

    name, ok, message = doctor._docker_check()
    assert name == "docker-daemon"
    assert ok is False
    assert "Docker CLI not found" in message
