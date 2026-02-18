from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Literal

import yaml

from terminal_demo_studio.docker_runner import DockerError, ensure_image
from terminal_demo_studio.models import parse_screenplay_data
from terminal_demo_studio.resources import read_template

DoctorMode = Literal["auto", "scripted_vhs", "autonomous_pty"]


def _clean_docker_message(raw: str) -> str:
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    filtered = [line for line in lines if "pretty printing info" not in line.lower()]
    if filtered:
        return "\n".join(filtered)
    return raw.strip()


def _binary_exists(name: str) -> bool:
    return shutil.which(name) is not None


def _ffmpeg_has_drawtext() -> bool:
    if not _binary_exists("ffmpeg"):
        return False
    probe = subprocess.run(
        ["ffmpeg", "-hide_banner", "-filters"],
        check=False,
        capture_output=True,
        text=True,
    )
    combined = f"{probe.stdout}\n{probe.stderr}"
    return probe.returncode == 0 and "drawtext" in combined


def _load_packaged_screenplay(template_name: str) -> None:
    raw = yaml.safe_load(read_template(template_name))
    if not isinstance(raw, dict):
        raise ValueError(f"Packaged template '{template_name}' must be a YAML object")
    parsed = parse_screenplay_data(raw)
    _ = parsed.title


def _docker_check() -> tuple[str, bool, str]:
    try:
        docker_info = subprocess.run(
            ["docker", "info"],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return (
            "docker-daemon",
            False,
            "Docker CLI not found. Install Docker for container mode, or use local mode.",
        )
    if docker_info.returncode == 0:
        return ("docker-daemon", True, "Docker daemon is reachable")

    raw_message = (
        docker_info.stderr.strip() or docker_info.stdout.strip() or "Docker daemon unreachable"
    )
    return ("docker-daemon", False, _clean_docker_message(raw_message))


def _packaged_template_checks() -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []
    try:
        _load_packaged_screenplay("dev_bugfix")
        checks.append(("screenplay-template", True, "Template screenplay validates"))
    except Exception as exc:  # noqa: BLE001
        checks.append(("screenplay-template", False, str(exc)))

    try:
        _load_packaged_screenplay("drift_protection")
        checks.append(("screenplay-sample", True, "Drift sample validates"))
    except Exception as exc:  # noqa: BLE001
        checks.append(("screenplay-sample", False, str(exc)))

    return checks


def _container_binary_check(docker_ok: bool) -> tuple[str, bool, str]:
    project_root = Path(__file__).resolve().parents[1]
    if not docker_ok:
        return ("container-binaries", False, "Skipped because docker daemon is unavailable")

    try:
        image_tag = ensure_image(project_root, rebuild=False)
        cmd = [
            "docker",
            "run",
            "--rm",
            image_tag,
            "sh",
            "-lc",
            (
                "command -v vhs >/dev/null "
                "&& command -v ffmpeg >/dev/null "
                "&& command -v python3 >/dev/null "
                "&& ffmpeg -hide_banner -filters | grep -q drawtext"
            ),
        ]
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if result.returncode == 0:
            return (
                "container-binaries",
                True,
                "vhs/ffmpeg/python3 present in image with drawtext support",
            )

        message = (
            result.stderr.strip()
            or result.stdout.strip()
            or "required binaries/drawtext support missing"
        )
        return ("container-binaries", False, message)
    except DockerError as exc:
        return ("container-binaries", False, str(exc))
    except subprocess.CalledProcessError as exc:
        return ("container-binaries", False, str(exc))


def run_doctor_checks(mode: DoctorMode = "auto") -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []
    vhs_ok = _binary_exists("vhs")
    ffmpeg_ok = _binary_exists("ffmpeg")
    ffprobe_ok = _binary_exists("ffprobe")

    checks.append(
        ("local-vhs", vhs_ok, "vhs found in PATH" if vhs_ok else "vhs not found in PATH")
    )
    checks.append(
        (
            "local-ffmpeg",
            ffmpeg_ok,
            "ffmpeg found in PATH" if ffmpeg_ok else "ffmpeg not found in PATH",
        )
    )
    checks.append(
        (
            "local-ffprobe",
            ffprobe_ok,
            "ffprobe found in PATH" if ffprobe_ok else "ffprobe not found in PATH",
        )
    )

    drawtext_ok = _ffmpeg_has_drawtext()
    checks.append(
        (
            "local-ffmpeg-drawtext",
            drawtext_ok,
            "ffmpeg drawtext filter is available"
            if drawtext_ok
            else "ffmpeg drawtext filter not detected",
        )
    )

    checks.extend(_packaged_template_checks())

    if mode in {"auto", "scripted_vhs"}:
        docker_check = _docker_check()
        checks.append(docker_check)
        checks.append(_container_binary_check(docker_check[1]))

    return checks
