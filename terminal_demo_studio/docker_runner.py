from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Literal


class DockerError(RuntimeError):
    """Raised when docker operations fail."""


def _container_path_to_host(path_value: str, project_root: Path) -> Path:
    container_root = Path("/workspace")
    candidate = Path(path_value)
    if candidate.is_absolute():
        try:
            rel = candidate.relative_to(container_root)
        except ValueError:
            return candidate
        return (project_root / rel).resolve()
    return candidate


def _map_workspace_strings(value: object, project_root: Path) -> object:
    if isinstance(value, str) and value.startswith("/workspace/"):
        return str(_container_path_to_host(value, project_root))
    if isinstance(value, list):
        return [_map_workspace_strings(item, project_root) for item in value]
    if isinstance(value, dict):
        return {key: _map_workspace_strings(item, project_root) for key, item in value.items()}
    return value


def _rewrite_summary_paths(summary_path: Path, project_root: Path) -> None:
    if not summary_path.exists():
        return
    try:
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return
    mapped = _map_workspace_strings(payload, project_root)
    if mapped != payload:
        summary_path.write_text(json.dumps(mapped, indent=2, sort_keys=True), encoding="utf-8")


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

    try:
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
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        message = (exc.stderr or exc.stdout or str(exc)).strip()
        if not rebuild and "already exists" in message.lower() and _image_exists(image_tag):
            return image_tag
        raise DockerError(message) from exc
    return image_tag


def run_in_docker(
    screenplay_path: Path,
    output_dir: Path | None = None,
    keep_temp: bool = False,
    rebuild: bool = False,
    playback_mode: Literal["sequential", "simultaneous"] = "sequential",
    run_mode: Literal["scripted_vhs", "autonomous_video"] = "scripted_vhs",
    produce_mp4: bool = True,
    produce_gif: bool = True,
) -> dict[str, Path | str | None]:
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
        "--entrypoint",
        "python3",
        "-v",
        f"{project_root}:/workspace",
        "-w",
        "/workspace",
        "-e",
        "TERMINAL_DEMO_STUDIO_IN_CONTAINER=1",
        image_tag,
        "-m",
        "terminal_demo_studio.cli",
        "render",
        str(container_screenplay),
        "--local",
        "--mode",
        run_mode,
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

    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="")
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "docker run failed"
        raise DockerError(message)

    parsed: dict[str, Path | str | None] = {
        "status": "success",
        "run_dir": None,
        "events": None,
        "summary": None,
        "media_mp4": None,
        "media_gif": None,
    }
    for line in result.stdout.splitlines():
        if line.startswith("RUN_DIR="):
            parsed["run_dir"] = _container_path_to_host(
                line.removeprefix("RUN_DIR="), project_root
            )
        elif line.startswith("EVENTS="):
            parsed["events"] = _container_path_to_host(
                line.removeprefix("EVENTS="), project_root
            )
        elif line.startswith("SUMMARY="):
            parsed["summary"] = _container_path_to_host(
                line.removeprefix("SUMMARY="), project_root
            )
        elif line.startswith("MEDIA_MP4="):
            parsed["media_mp4"] = _container_path_to_host(
                line.removeprefix("MEDIA_MP4="), project_root
            )
        elif line.startswith("MEDIA_GIF="):
            parsed["media_gif"] = _container_path_to_host(
                line.removeprefix("MEDIA_GIF="), project_root
            )
        elif line.startswith("STATUS="):
            parsed["status"] = line.removeprefix("STATUS=")

    summary_path = parsed.get("summary")
    if isinstance(summary_path, Path):
        _rewrite_summary_paths(summary_path, project_root)
    return parsed
