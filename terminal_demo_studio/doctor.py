from __future__ import annotations

import platform
import shutil
import subprocess
from pathlib import Path
from typing import Literal

import yaml

from terminal_demo_studio.docker_runner import DockerError, ensure_image
from terminal_demo_studio.models import parse_screenplay_data
from terminal_demo_studio.resources import read_template

DoctorMode = Literal["auto", "scripted_vhs", "autonomous_pty", "autonomous_video"]


def _platform_family() -> str:
    system = platform.system().lower()
    if "windows" in system:
        return "windows"
    if "darwin" in system:
        return "macos"
    return "linux"


def _next_action(tool: str) -> str:
    family = _platform_family()
    tool_map: dict[str, dict[str, str]] = {
        "vhs": {
            "macos": "brew install vhs",
            "linux": "go install github.com/charmbracelet/vhs@v0.10.0",
            "windows": "go install github.com/charmbracelet/vhs@v0.10.0",
        },
        "ffmpeg": {
            "macos": "brew install ffmpeg",
            "linux": "sudo apt-get update && sudo apt-get install -y ffmpeg",
            "windows": "choco install ffmpeg --yes --no-progress",
        },
        "ffprobe": {
            "macos": "brew install ffmpeg",
            "linux": "sudo apt-get update && sudo apt-get install -y ffmpeg",
            "windows": "choco install ffmpeg --yes --no-progress",
        },
        "kitty": {
            "macos": "brew install --cask kitty",
            "linux": "sudo apt-get update && sudo apt-get install -y kitty",
            "windows": "Use Docker mode for autonomous_video on Windows",
        },
        "xvfb": {
            "macos": "brew install --cask xquartz",
            "linux": "sudo apt-get update && sudo apt-get install -y xvfb",
            "windows": "Use Docker mode for autonomous_video on Windows",
        },
        "docker": {
            "macos": "open -a Docker",
            "linux": "sudo systemctl start docker",
            "windows": 'start "" "C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe"',
        },
        "drawtext": {
            "macos": "brew reinstall ffmpeg",
            "linux": "sudo apt-get install --reinstall -y ffmpeg",
            "windows": "choco upgrade ffmpeg --yes --no-progress",
        },
    }
    resolved = tool_map.get(tool, {})
    return resolved.get(family, "echo 'No platform-specific remediation available'")


def _with_next(message: str, tool: str) -> str:
    return f"{message} NEXT: {_next_action(tool)}"


def _clean_docker_message(raw: str) -> str:
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    filtered = [line for line in lines if "pretty printing info" not in line.lower()]
    if filtered:
        return "\n".join(filtered)
    return raw.strip()


def _binary_exists(name: str) -> bool:
    return shutil.which(name) is not None


def _missing_tool_hint(tool: str, mode: DoctorMode) -> str:
    if mode == "autonomous_pty":
        message = (
            f"{tool} not found in PATH. Optional for autonomous_pty; "
            "required for local scripted_vhs rendering."
        )
        return _with_next(
            message,
            tool,
        )
    if mode == "autonomous_video":
        return _with_next(
            f"{tool} not found in PATH. autonomous_video will use Docker fallback when available.",
            tool,
        )
    message = (
        f"{tool} not found in PATH. Install it for local scripted_vhs mode, "
        "or run with --docker when Docker is available."
    )
    return _with_next(
        message,
        tool,
    )


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
            _with_next(
                "Docker CLI not found. Install Docker for container mode, or use local mode.",
                "docker",
            ),
        )
    if docker_info.returncode == 0:
        return ("docker-daemon", True, "Docker daemon is reachable")

    raw_message = (
        docker_info.stderr.strip() or docker_info.stdout.strip() or "Docker daemon unreachable"
    )
    cleaned = _clean_docker_message(raw_message)
    return ("docker-daemon", False, _with_next(cleaned, "docker"))


def _packaged_template_checks() -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []
    try:
        _load_packaged_screenplay("install_first_command")
        checks.append(("screenplay-template", True, "Launch template validates"))
    except Exception as exc:  # noqa: BLE001
        checks.append(("screenplay-template", False, str(exc)))

    try:
        _load_packaged_screenplay("before_after_bugfix")
        checks.append(("screenplay-sample", True, "Comparison template validates"))
    except Exception as exc:  # noqa: BLE001
        checks.append(("screenplay-sample", False, str(exc)))

    return checks


def _container_binary_check(docker_ok: bool, *, mode: DoctorMode) -> tuple[str, bool, str]:
    project_root = Path(__file__).resolve().parents[1]
    if not docker_ok:
        return (
            "container-binaries",
            False,
            _with_next("Skipped because docker daemon is unavailable", "docker"),
        )

    try:
        image_tag = ensure_image(project_root, rebuild=False)
        if mode == "autonomous_video":
            probe_cmd = (
                "command -v kitty >/dev/null "
                "&& command -v kitten >/dev/null "
                "&& command -v Xvfb >/dev/null "
                "&& command -v ffmpeg >/dev/null "
                "&& command -v python3 >/dev/null"
            )
            ok_message = "kitty/kitten/Xvfb/ffmpeg/python3 present in image"
        else:
            probe_cmd = (
                "command -v vhs >/dev/null "
                "&& command -v ffmpeg >/dev/null "
                "&& command -v python3 >/dev/null "
                "&& ffmpeg -hide_banner -filters | grep -q drawtext"
            )
            ok_message = "vhs/ffmpeg/python3 present in image with drawtext support"

        cmd = [
            "docker",
            "run",
            "--rm",
            "--entrypoint",
            "sh",
            image_tag,
            "-lc",
            probe_cmd,
        ]
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if result.returncode == 0:
            return ("container-binaries", True, ok_message)

        message = (
            result.stderr.strip()
            or result.stdout.strip()
            or "required binaries missing in container image"
        )
        return ("container-binaries", False, message)
    except DockerError as exc:
        return ("container-binaries", False, str(exc))
    except subprocess.CalledProcessError as exc:
        return ("container-binaries", False, str(exc))


def _scripted_local_checks(mode: DoctorMode) -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []
    vhs_ok = _binary_exists("vhs")
    ffmpeg_ok = _binary_exists("ffmpeg")
    ffprobe_ok = _binary_exists("ffprobe")

    checks.append(
        (
            "local-vhs",
            vhs_ok,
            "vhs found in PATH" if vhs_ok else _missing_tool_hint("vhs", mode),
        )
    )
    checks.append(
        (
            "local-ffmpeg",
            ffmpeg_ok,
            "ffmpeg found in PATH" if ffmpeg_ok else _missing_tool_hint("ffmpeg", mode),
        )
    )
    checks.append(
        (
            "local-ffprobe",
            ffprobe_ok,
            "ffprobe found in PATH" if ffprobe_ok else _missing_tool_hint("ffprobe", mode),
        )
    )
    drawtext_ok = _ffmpeg_has_drawtext()
    checks.append(
        (
            "local-ffmpeg-drawtext",
            drawtext_ok,
            "ffmpeg drawtext filter is available"
            if drawtext_ok
            else _with_next(
                "ffmpeg drawtext filter not detected. "
                "Labels in composed videos will use Pillow image-overlay fallback.",
                "drawtext",
            ),
        )
    )
    return checks


def _autonomous_video_local_checks(mode: DoctorMode) -> tuple[list[tuple[str, bool, str]], bool]:
    checks: list[tuple[str, bool, str]] = []
    kitty_ok = _binary_exists("kitty")
    kitten_ok = _binary_exists("kitten")
    xvfb_ok = _binary_exists("Xvfb")
    ffmpeg_ok = _binary_exists("ffmpeg")
    ffprobe_ok = _binary_exists("ffprobe")

    checks.append(
        (
            "local-kitty",
            kitty_ok,
            "kitty found in PATH" if kitty_ok else _missing_tool_hint("kitty", mode),
        )
    )
    checks.append(
        (
            "local-kitten",
            kitten_ok,
            "kitten found in PATH" if kitten_ok else _missing_tool_hint("kitty", mode),
        )
    )
    checks.append(
        (
            "local-xvfb",
            xvfb_ok,
            "Xvfb found in PATH" if xvfb_ok else _missing_tool_hint("xvfb", mode),
        )
    )
    checks.append(
        (
            "local-ffmpeg",
            ffmpeg_ok,
            "ffmpeg found in PATH" if ffmpeg_ok else _missing_tool_hint("ffmpeg", mode),
        )
    )
    checks.append(
        (
            "local-ffprobe",
            ffprobe_ok,
            "ffprobe found in PATH" if ffprobe_ok else _missing_tool_hint("ffprobe", mode),
        )
    )

    return checks, all([kitty_ok, kitten_ok, xvfb_ok, ffmpeg_ok, ffprobe_ok])


def run_doctor_checks(mode: DoctorMode = "auto") -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []

    if mode == "autonomous_video":
        video_checks, local_video_ready = _autonomous_video_local_checks(mode)
        checks.extend(video_checks)
    else:
        checks.extend(_scripted_local_checks(mode))
        local_video_ready = False

    checks.extend(_packaged_template_checks())

    if mode in {"auto", "scripted_vhs", "autonomous_video"}:
        docker_check = _docker_check()
        checks.append(docker_check)
        container_check = _container_binary_check(docker_check[1], mode=mode)
        checks.append(container_check)

        if mode == "autonomous_video":
            docker_video_ready = docker_check[1] and container_check[1]
            overall_ready = local_video_ready or docker_video_ready
            if overall_ready:
                if local_video_ready:
                    message = "autonomous_video runtime ready locally"
                else:
                    message = "autonomous_video runtime ready via Docker fallback"
            else:
                message = (
                    "autonomous_video runtime unavailable: local dependencies "
                    "missing and Docker is not ready"
                )
            checks.append(("autonomous-video-runtime", overall_ready, message))

    return checks
