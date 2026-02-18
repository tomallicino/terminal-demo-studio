from __future__ import annotations

import json
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


def test_select_prunable_image_tags_keeps_latest_and_protected() -> None:
    ordered = [
        "terminal-demo-studio:v1-new",
        "terminal-demo-studio:v1-mid",
        "terminal-demo-studio:v1-old",
        "terminal-demo-studio:v1-ancient",
    ]
    prunable = docker_runner._select_prunable_image_tags(
        ordered_tags=ordered,
        keep_tags={"terminal-demo-studio:v1-old"},
        retention_count=2,
    )

    assert prunable == ["terminal-demo-studio:v1-ancient"]


def test_select_prunable_image_tags_allows_disable_retention() -> None:
    ordered = [
        "terminal-demo-studio:v1-new",
        "terminal-demo-studio:v1-old",
    ]
    prunable = docker_runner._select_prunable_image_tags(
        ordered_tags=ordered,
        keep_tags={"terminal-demo-studio:v1-new"},
        retention_count=0,
    )

    assert prunable == ["terminal-demo-studio:v1-old"]


def test_docker_image_retention_count_parses_env(monkeypatch: object) -> None:
    monkeypatch.setenv("TDS_DOCKER_IMAGE_RETENTION", "7")
    assert docker_runner._docker_image_retention_count() == 7

    monkeypatch.setenv("TDS_DOCKER_IMAGE_RETENTION", "invalid")
    assert docker_runner._docker_image_retention_count() == 3

    monkeypatch.setenv("TDS_DOCKER_IMAGE_RETENTION", "-5")
    assert docker_runner._docker_image_retention_count() == 0


def test_ensure_image_prunes_stale_tags_when_image_exists(
    monkeypatch: object, tmp_path: Path
) -> None:
    image_tag = "terminal-demo-studio:v1-hash123"
    captured: dict[str, object] = {}

    monkeypatch.setattr(docker_runner, "ensure_docker_reachable", lambda: None)
    monkeypatch.setattr(docker_runner, "compute_image_tag", lambda project_root: image_tag)
    monkeypatch.setattr(docker_runner, "_image_exists", lambda tag: True)

    def fake_prune(*, keep_tags: set[str]) -> None:
        captured["keep_tags"] = keep_tags

    monkeypatch.setattr(docker_runner, "_prune_stale_hashed_images", fake_prune)

    (tmp_path / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    result = docker_runner.ensure_image(tmp_path, rebuild=False)

    assert result == image_tag
    assert captured["keep_tags"] == {image_tag}


def test_ensure_image_prunes_stale_tags_after_build(monkeypatch: object, tmp_path: Path) -> None:
    image_tag = "terminal-demo-studio:v1-hash123"
    captured: dict[str, object] = {"build_called": False}

    monkeypatch.setattr(docker_runner, "ensure_docker_reachable", lambda: None)
    monkeypatch.setattr(docker_runner, "compute_image_tag", lambda project_root: image_tag)
    monkeypatch.setattr(docker_runner, "_image_exists", lambda tag: False)

    def fake_run(
        cmd: list[str], *, check: bool, capture_output: bool, text: bool
    ) -> subprocess.CompletedProcess[str]:
        _ = capture_output
        _ = text
        assert check is True
        assert cmd[:2] == ["docker", "build"]
        captured["build_called"] = True
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    def fake_prune(*, keep_tags: set[str]) -> None:
        captured["keep_tags"] = keep_tags

    monkeypatch.setattr(docker_runner.subprocess, "run", fake_run)
    monkeypatch.setattr(docker_runner, "_prune_stale_hashed_images", fake_prune)

    (tmp_path / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    result = docker_runner.ensure_image(tmp_path, rebuild=False)

    assert result == image_tag
    assert captured["build_called"] is True
    assert captured["keep_tags"] == {image_tag}


def test_run_in_docker_forwards_playback_mode(monkeypatch: object) -> None:
    captured: dict[str, object] = {}

    def fake_ensure_image(project_root: Path, rebuild: bool = False) -> str:
        return "terminal-demo-studio:test"

    def fake_run(
        cmd: list[str], *, check: bool, capture_output: bool, text: bool
    ) -> subprocess.CompletedProcess[str]:
        assert check is False
        assert capture_output is True
        assert text is True
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=(
                "STATUS=success\n"
                "RUN_DIR=/tmp/tds/run\n"
                "SUMMARY=/tmp/tds/run/summary.json\n"
                "MEDIA_MP4=/tmp/tds/run/media/demo.mp4\n"
            ),
            stderr="",
        )

    monkeypatch.setattr(docker_runner, "ensure_image", fake_ensure_image)
    monkeypatch.setattr(docker_runner.subprocess, "run", fake_run)

    project_root = Path(docker_runner.__file__).resolve().parents[1]
    screenplay = project_root / "screenplays" / "drift_protection.yaml"

    result = docker_runner.run_in_docker(screenplay_path=screenplay, playback_mode="simultaneous")

    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert "--playback" in cmd
    assert cmd[cmd.index("--playback") + 1] == "simultaneous"
    assert "--mode" in cmd
    assert cmd[cmd.index("--mode") + 1] == "scripted_vhs"
    assert result["status"] == "success"


def test_run_in_docker_forwards_explicit_run_mode(monkeypatch: object) -> None:
    captured: dict[str, object] = {}

    def fake_ensure_image(project_root: Path, rebuild: bool = False) -> str:
        return "terminal-demo-studio:test"

    def fake_run(
        cmd: list[str], *, check: bool, capture_output: bool, text: bool
    ) -> subprocess.CompletedProcess[str]:
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="STATUS=success\nRUN_DIR=/tmp/tds/run\n",
            stderr="",
        )

    monkeypatch.setattr(docker_runner, "ensure_image", fake_ensure_image)
    monkeypatch.setattr(docker_runner.subprocess, "run", fake_run)

    project_root = Path(docker_runner.__file__).resolve().parents[1]
    screenplay = project_root / "examples" / "mock" / "autonomous_video_codex_like.yaml"

    docker_runner.run_in_docker(screenplay_path=screenplay, run_mode="autonomous_video")

    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert "--mode" in cmd
    assert cmd[cmd.index("--mode") + 1] == "autonomous_video"


def test_run_in_docker_forwards_agent_prompt_mode(monkeypatch: object) -> None:
    captured: dict[str, object] = {}

    def fake_ensure_image(project_root: Path, rebuild: bool = False) -> str:
        return "terminal-demo-studio:test"

    def fake_run(
        cmd: list[str], *, check: bool, capture_output: bool, text: bool
    ) -> subprocess.CompletedProcess[str]:
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="STATUS=success\nRUN_DIR=/tmp/tds/run\n",
            stderr="",
        )

    monkeypatch.setattr(docker_runner, "ensure_image", fake_ensure_image)
    monkeypatch.setattr(docker_runner.subprocess, "run", fake_run)

    project_root = Path(docker_runner.__file__).resolve().parents[1]
    screenplay = project_root / "examples" / "mock" / "autonomous_video_codex_like.yaml"

    docker_runner.run_in_docker(
        screenplay_path=screenplay,
        run_mode="autonomous_video",
        agent_prompt_mode="approve",
    )

    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert "--agent-prompts" in cmd
    assert cmd[cmd.index("--agent-prompts") + 1] == "approve"


def test_run_in_docker_forwards_media_redaction_mode(monkeypatch: object) -> None:
    captured: dict[str, object] = {}

    def fake_ensure_image(project_root: Path, rebuild: bool = False) -> str:
        return "terminal-demo-studio:test"

    def fake_run(
        cmd: list[str], *, check: bool, capture_output: bool, text: bool
    ) -> subprocess.CompletedProcess[str]:
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="STATUS=success\nRUN_DIR=/tmp/tds/run\n",
            stderr="",
        )

    monkeypatch.setattr(docker_runner, "ensure_image", fake_ensure_image)
    monkeypatch.setattr(docker_runner.subprocess, "run", fake_run)

    project_root = Path(docker_runner.__file__).resolve().parents[1]
    screenplay = project_root / "examples" / "mock" / "autonomous_video_codex_like.yaml"

    docker_runner.run_in_docker(
        screenplay_path=screenplay,
        run_mode="autonomous_video",
        media_redaction_mode="input_line",
    )

    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert "--redact" in cmd
    assert cmd[cmd.index("--redact") + 1] == "input_line"


def test_run_in_docker_is_quiet_by_default(monkeypatch: object) -> None:
    printed: list[str] = []

    def fake_ensure_image(project_root: Path, rebuild: bool = False) -> str:
        return "terminal-demo-studio:test"

    def fake_run(
        cmd: list[str], *, check: bool, capture_output: bool, text: bool
    ) -> subprocess.CompletedProcess[str]:
        _ = check
        _ = capture_output
        _ = text
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="STATUS=success\nRUN_DIR=/tmp/tds/run\n",
            stderr="ffmpeg noise",
        )

    def fake_print(*args: object, **kwargs: object) -> None:
        _ = kwargs
        printed.append(" ".join(str(part) for part in args))

    monkeypatch.setattr(docker_runner, "ensure_image", fake_ensure_image)
    monkeypatch.setattr(docker_runner.subprocess, "run", fake_run)
    monkeypatch.setattr("builtins.print", fake_print)

    project_root = Path(docker_runner.__file__).resolve().parents[1]
    screenplay = project_root / "examples" / "mock" / "autonomous_video_codex_like.yaml"
    docker_runner.run_in_docker(screenplay_path=screenplay)

    assert printed == []


def test_run_in_docker_can_stream_logs_when_verbose_enabled(monkeypatch: object) -> None:
    printed: list[str] = []

    def fake_ensure_image(project_root: Path, rebuild: bool = False) -> str:
        return "terminal-demo-studio:test"

    def fake_run(
        cmd: list[str], *, check: bool, capture_output: bool, text: bool
    ) -> subprocess.CompletedProcess[str]:
        _ = check
        _ = capture_output
        _ = text
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="STATUS=success\nRUN_DIR=/tmp/tds/run\n",
            stderr="ffmpeg noise",
        )

    def fake_print(*args: object, **kwargs: object) -> None:
        _ = kwargs
        printed.append(" ".join(str(part) for part in args))

    monkeypatch.setattr(docker_runner, "ensure_image", fake_ensure_image)
    monkeypatch.setattr(docker_runner.subprocess, "run", fake_run)
    monkeypatch.setattr("builtins.print", fake_print)
    monkeypatch.setenv("TDS_DOCKER_VERBOSE", "1")

    project_root = Path(docker_runner.__file__).resolve().parents[1]
    screenplay = project_root / "examples" / "mock" / "autonomous_video_codex_like.yaml"
    docker_runner.run_in_docker(screenplay_path=screenplay)

    assert any("STATUS=success" in line for line in printed)


def test_ensure_docker_reachable_raises_clear_error_when_docker_missing(
    monkeypatch: object,
) -> None:
    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("docker")

    monkeypatch.setattr(docker_runner.subprocess, "run", fake_run)

    with pytest.raises(docker_runner.DockerError, match="Docker CLI not found"):
        docker_runner.ensure_docker_reachable()


def test_run_in_docker_maps_workspace_paths_to_host(monkeypatch: object) -> None:
    def fake_ensure_image(project_root: Path, rebuild: bool = False) -> str:
        return "terminal-demo-studio:test"

    def fake_run(
        cmd: list[str], *, check: bool, capture_output: bool, text: bool
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=(
                "STATUS=success\n"
                "RUN_DIR=/workspace/examples/mock/.terminal_demo_studio_runs/run-123\n"
                "SUMMARY=/workspace/examples/mock/.terminal_demo_studio_runs/run-123/summary.json\n"
                "MEDIA_MP4=/workspace/examples/mock/.terminal_demo_studio_runs/run-123/media/demo.mp4\n"
                "EVENTS=/workspace/examples/mock/.terminal_demo_studio_runs/run-123/runtime/events.jsonl\n"
            ),
            stderr="",
        )

    monkeypatch.setattr(docker_runner, "ensure_image", fake_ensure_image)
    monkeypatch.setattr(docker_runner.subprocess, "run", fake_run)

    project_root = Path(docker_runner.__file__).resolve().parents[1]
    screenplay = project_root / "examples" / "mock" / "autonomous_video_codex_like.yaml"

    result = docker_runner.run_in_docker(screenplay_path=screenplay)

    assert result["run_dir"] == (
        project_root / "examples/mock/.terminal_demo_studio_runs/run-123"
    ).resolve()
    assert result["summary"] == (
        project_root / "examples/mock/.terminal_demo_studio_runs/run-123/summary.json"
    ).resolve()
    assert result["media_mp4"] == (
        project_root / "examples/mock/.terminal_demo_studio_runs/run-123/media/demo.mp4"
    ).resolve()
    assert result["events"] == (
        project_root / "examples/mock/.terminal_demo_studio_runs/run-123/runtime/events.jsonl"
    ).resolve()


def test_ensure_image_tolerates_already_exists_build_error(
    monkeypatch: object, tmp_path: Path
) -> None:
    image_tag = "terminal-demo-studio:v1-testhash"
    calls = {"inspect": 0}

    def fake_ensure_docker_reachable() -> None:
        return None

    def fake_compute_image_tag(project_root: Path) -> str:
        return image_tag

    def fake_image_exists(tag: str) -> bool:
        assert tag == image_tag
        calls["inspect"] += 1
        # First call (pre-build): image missing. Second call (post-build error): present.
        return calls["inspect"] >= 2

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=["docker", "build"],
            stderr=(
                'failed to solve: image '
                '"docker.io/library/terminal-demo-studio:v1-testhash": already exists'
            ),
        )

    monkeypatch.setattr(docker_runner, "ensure_docker_reachable", fake_ensure_docker_reachable)
    monkeypatch.setattr(docker_runner, "compute_image_tag", fake_compute_image_tag)
    monkeypatch.setattr(docker_runner, "_image_exists", fake_image_exists)
    monkeypatch.setattr(docker_runner.subprocess, "run", fake_run)

    (tmp_path / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")

    result = docker_runner.ensure_image(tmp_path, rebuild=False)
    assert result == image_tag


def test_rewrite_summary_paths_maps_workspace_prefix(tmp_path: Path) -> None:
    summary = tmp_path / "summary.json"
    summary.write_text(
        '{"events": "/workspace/out/events.jsonl", "media": {"mp4": "/workspace/out/demo.mp4"}}',
        encoding="utf-8",
    )

    docker_runner._rewrite_summary_paths(summary, tmp_path)
    rewritten = json.loads(summary.read_text(encoding="utf-8"))

    assert rewritten["events"] == str((tmp_path / "out/events.jsonl").resolve())
    assert rewritten["media"]["mp4"] == str((tmp_path / "out/demo.mp4").resolve())


def test_rewrite_summary_paths_maps_windows_style_workspace_prefix(tmp_path: Path) -> None:
    summary = tmp_path / "summary_windows.json"
    summary.write_text(
        '{"events": "\\\\workspace\\\\out\\\\events.jsonl", '
        '"media": {"mp4": "\\\\workspace\\\\out\\\\demo.mp4"}}',
        encoding="utf-8",
    )

    docker_runner._rewrite_summary_paths(summary, tmp_path)
    rewritten = json.loads(summary.read_text(encoding="utf-8"))

    assert rewritten["events"] == str((tmp_path / "out/events.jsonl").resolve())
    assert rewritten["media"]["mp4"] == str((tmp_path / "out/demo.mp4").resolve())


def test_run_in_docker_forwards_openai_env_vars(monkeypatch: object) -> None:
    captured: dict[str, object] = {}

    def fake_ensure_image(project_root: Path, rebuild: bool = False) -> str:
        return "terminal-demo-studio:test"

    def fake_run(
        cmd: list[str], *, check: bool, capture_output: bool, text: bool
    ) -> subprocess.CompletedProcess[str]:
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="STATUS=success\nRUN_DIR=/tmp/tds/run\n",
            stderr="",
        )

    monkeypatch.setattr(docker_runner, "ensure_image", fake_ensure_image)
    monkeypatch.setattr(docker_runner.subprocess, "run", fake_run)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid")
    monkeypatch.setenv("OPENAI_ORGANIZATION", "org-test")

    project_root = Path(docker_runner.__file__).resolve().parents[1]
    screenplay = project_root / "examples" / "mock" / "autonomous_video_codex_like.yaml"
    docker_runner.run_in_docker(screenplay_path=screenplay)

    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert "-e" in cmd
    assert "OPENAI_API_KEY" in cmd
    assert "OPENAI_BASE_URL" in cmd
    assert "OPENAI_ORGANIZATION" in cmd


def test_run_in_docker_applies_hardening_flags_by_default(monkeypatch: object) -> None:
    captured: dict[str, object] = {}

    def fake_ensure_image(project_root: Path, rebuild: bool = False) -> str:
        return "terminal-demo-studio:test"

    def fake_run(
        cmd: list[str], *, check: bool, capture_output: bool, text: bool
    ) -> subprocess.CompletedProcess[str]:
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="STATUS=success\nRUN_DIR=/tmp/tds/run\n",
            stderr="",
        )

    monkeypatch.setattr(docker_runner, "ensure_image", fake_ensure_image)
    monkeypatch.setattr(docker_runner.subprocess, "run", fake_run)
    monkeypatch.delenv("TDS_DOCKER_HARDENING", raising=False)
    monkeypatch.delenv("TDS_DOCKER_PIDS_LIMIT", raising=False)

    project_root = Path(docker_runner.__file__).resolve().parents[1]
    screenplay = project_root / "examples" / "mock" / "autonomous_video_codex_like.yaml"
    docker_runner.run_in_docker(screenplay_path=screenplay)

    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert "--security-opt" in cmd
    assert cmd[cmd.index("--security-opt") + 1] == "no-new-privileges=true"
    assert "--cap-drop" in cmd
    assert cmd[cmd.index("--cap-drop") + 1] == "ALL"
    assert "--pids-limit" in cmd
    assert cmd[cmd.index("--pids-limit") + 1] == "512"


def test_run_in_docker_respects_hardening_env_overrides(monkeypatch: object) -> None:
    captured: dict[str, object] = {}

    def fake_ensure_image(project_root: Path, rebuild: bool = False) -> str:
        return "terminal-demo-studio:test"

    def fake_run(
        cmd: list[str], *, check: bool, capture_output: bool, text: bool
    ) -> subprocess.CompletedProcess[str]:
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="STATUS=success\nRUN_DIR=/tmp/tds/run\n",
            stderr="",
        )

    monkeypatch.setattr(docker_runner, "ensure_image", fake_ensure_image)
    monkeypatch.setattr(docker_runner.subprocess, "run", fake_run)
    monkeypatch.setenv("TDS_DOCKER_HARDENING", "0")
    monkeypatch.setenv("TDS_DOCKER_NETWORK", "none")
    monkeypatch.setenv("TDS_DOCKER_READ_ONLY", "1")

    project_root = Path(docker_runner.__file__).resolve().parents[1]
    screenplay = project_root / "examples" / "mock" / "autonomous_video_codex_like.yaml"
    docker_runner.run_in_docker(screenplay_path=screenplay)

    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert "--security-opt" not in cmd
    assert "--cap-drop" not in cmd
    assert "--network" in cmd
    assert cmd[cmd.index("--network") + 1] == "none"
    assert "--read-only" in cmd
    assert "--tmpfs" in cmd


def test_run_in_docker_failure_includes_host_paths(monkeypatch: object) -> None:
    def fake_ensure_image(project_root: Path, rebuild: bool = False) -> str:
        return "terminal-demo-studio:test"

    def fake_run(
        cmd: list[str], *, check: bool, capture_output: bool, text: bool
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=1,
            stdout=(
                "STATUS=failed\n"
                "RUN_DIR=/workspace/examples/mock/.terminal_demo_studio_runs/run-err\n"
                "SUMMARY=/workspace/examples/mock/.terminal_demo_studio_runs/run-err/summary.json\n"
                "EVENTS=/workspace/examples/mock/.terminal_demo_studio_runs/run-err/runtime/events.jsonl\n"
            ),
            stderr="autonomous run failed",
        )

    monkeypatch.setattr(docker_runner, "ensure_image", fake_ensure_image)
    monkeypatch.setattr(docker_runner.subprocess, "run", fake_run)

    project_root = Path(docker_runner.__file__).resolve().parents[1]
    screenplay = project_root / "examples" / "mock" / "autonomous_video_codex_like.yaml"

    with pytest.raises(docker_runner.DockerError) as exc_info:
        docker_runner.run_in_docker(screenplay_path=screenplay, run_mode="autonomous_video")

    message = str(exc_info.value)
    run_dir = (project_root / "examples/mock/.terminal_demo_studio_runs/run-err").resolve()
    assert str(run_dir) in message
    assert (
        str(
            (
                project_root
                / "examples/mock/.terminal_demo_studio_runs/run-err/summary.json"
            ).resolve()
        )
        in message
    )
