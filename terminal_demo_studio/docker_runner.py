from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Literal


class DockerError(RuntimeError):
    """Raised when docker operations fail."""


def _hash_files(base: Path, paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.relative_to(base).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def compute_image_tag(project_root: Path) -> str:
    studio_root = project_root
    files_to_hash: list[Path] = []

    for filename in ["Dockerfile", "requirements.txt", "pyproject.toml"]:
        target = studio_root / filename
        if target.exists():
            files_to_hash.append(target)

    assets_dir = studio_root / "assets"
    if assets_dir.exists():
        files_to_hash.extend(path for path in assets_dir.rglob("*") if path.is_file())

    package_dir = studio_root / "terminal_demo_studio"
    if package_dir.exists():
        files_to_hash.extend(
            path
            for path in package_dir.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        )

    if not files_to_hash:
        raise DockerError(f"No Docker inputs found under {studio_root}")

    short_hash = _hash_files(studio_root, files_to_hash)[:12]
    return f"terminal-demo-studio:v1-{short_hash}"


def ensure_docker_reachable() -> None:
    try:
        result = subprocess.run(["docker", "info"], check=False, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise DockerError(
            "Docker CLI not found. Install Docker or run with --local."
        ) from exc
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "docker daemon unreachable"
        raise DockerError(message)


def _image_exists(tag: str) -> bool:
    result = subprocess.run(["docker", "image", "inspect", tag], check=False, capture_output=True)
    return result.returncode == 0


def ensure_image(project_root: Path, rebuild: bool = False) -> str:
    ensure_docker_reachable()

    studio_root = project_root
    dockerfile = studio_root / "Dockerfile"
    if not dockerfile.exists():
        raise DockerError(f"Missing Dockerfile at {dockerfile}")

    image_tag = compute_image_tag(project_root)
    if not rebuild and _image_exists(image_tag):
        return image_tag

    subprocess.run(
        [
            "docker",
            "build",
            "-f",
            str(dockerfile),
            "-t",
            image_tag,
            str(project_root),
        ],
        check=True,
    )
    return image_tag


def run_in_docker(
    screenplay_path: Path,
    output_dir: Path | None = None,
    keep_temp: bool = False,
    rebuild: bool = False,
    playback_mode: Literal["sequential", "simultaneous"] = "sequential",
    produce_mp4: bool = True,
    produce_gif: bool = True,
) -> None:
    project_root = Path(__file__).resolve().parents[1]
    image_tag = ensure_image(project_root, rebuild=rebuild)

    screenplay_abs = screenplay_path.resolve()
    try:
        screenplay_rel = screenplay_abs.relative_to(project_root)
    except ValueError as exc:
        raise DockerError(
            f"Screenplay must be inside repository root: {project_root}"
        ) from exc
    container_screenplay = Path("/workspace") / screenplay_rel

    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{project_root}:/workspace",
        "-w",
        "/workspace",
        "-e",
        "TERMINAL_DEMO_STUDIO_IN_CONTAINER=1",
        image_tag,
        "python3",
        "-m",
        "terminal_demo_studio.cli",
        "run",
        str(container_screenplay),
        "--local",
        "--playback",
        playback_mode,
    ]

    if output_dir is not None:
        output_abs = output_dir.resolve()
        try:
            output_rel = output_abs.relative_to(project_root)
        except ValueError as exc:
            raise DockerError(
                f"Output directory must be inside repository root: {project_root}"
            ) from exc
        cmd.extend(["--output-dir", str(Path("/workspace") / output_rel)])
    if keep_temp:
        cmd.append("--keep-temp")
    if produce_mp4 and not produce_gif:
        cmd.extend(["--output", "mp4"])
    elif produce_gif and not produce_mp4:
        cmd.extend(["--output", "gif"])

    subprocess.run(cmd, check=True)
