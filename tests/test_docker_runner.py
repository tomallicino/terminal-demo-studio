from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from terminal_demo_studio import docker_runner
from terminal_demo_studio.docker_runner import compute_image_tag


def test_compute_image_tag_is_stable_for_same_inputs(tmp_path: Path) -> None:
    (tmp_path / "Dockerfile").write_text("FROM alpine:3.20\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("PyYAML==6.0.3\n", encoding="utf-8")
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "starship.toml").write_text("add_newline = false\n", encoding="utf-8")

    a = compute_image_tag(tmp_path)
    b = compute_image_tag(tmp_path)

    assert a == b
    assert a.startswith("terminal-demo-studio:v1-")


def test_compute_image_tag_changes_when_package_code_changes(tmp_path: Path) -> None:
    (tmp_path / "Dockerfile").write_text("FROM alpine:3.20\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("PyYAML==6.0.3\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    package_dir = tmp_path / "terminal_demo_studio"
    package_dir.mkdir()
    module = package_dir / "cli.py"
    module.write_text("def main() -> None:\n    pass\n", encoding="utf-8")

    before = compute_image_tag(tmp_path)
    module.write_text("def main() -> None:\n    print('updated')\n", encoding="utf-8")
    after = compute_image_tag(tmp_path)

    assert before != after


def test_run_in_docker_forwards_playback_mode(monkeypatch: object) -> None:
    captured: dict[str, object] = {}

    def fake_ensure_image(project_root: Path, rebuild: bool = False) -> str:
        return "terminal-demo-studio:test"

    def fake_run(cmd: list[str], check: bool) -> subprocess.CompletedProcess[str]:
        assert check is True
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(args=cmd, returncode=0)

    monkeypatch.setattr(docker_runner, "ensure_image", fake_ensure_image)
    monkeypatch.setattr(docker_runner.subprocess, "run", fake_run)

    project_root = Path(docker_runner.__file__).resolve().parents[1]
    screenplay = project_root / "screenplays" / "drift_protection.yaml"

    docker_runner.run_in_docker(screenplay_path=screenplay, playback_mode="simultaneous")

    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert "--playback" in cmd
    assert cmd[cmd.index("--playback") + 1] == "simultaneous"


def test_ensure_docker_reachable_raises_clear_error_when_docker_missing(
    monkeypatch: object,
) -> None:
    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("docker")

    monkeypatch.setattr(docker_runner.subprocess, "run", fake_run)

    with pytest.raises(docker_runner.DockerError, match="Docker CLI not found"):
        docker_runner.ensure_docker_reachable()
