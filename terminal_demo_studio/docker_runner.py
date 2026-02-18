from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Literal

IMAGE_REPOSITORY = "terminal-demo-studio"
IMAGE_TAG_PREFIX = f"{IMAGE_REPOSITORY}:v1-"


class DockerError(RuntimeError):
    """Raised when docker operations fail."""


def _env_enabled(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _docker_hardening_flags() -> list[str]:
    if not _env_enabled("TDS_DOCKER_HARDENING", True):
        return []
    flags = [
        "--security-opt",
        "no-new-privileges=true",
        "--cap-drop",
        "ALL",
    ]
    pids_limit = os.environ.get("TDS_DOCKER_PIDS_LIMIT", "512").strip()
    if pids_limit:
        flags.extend(["--pids-limit", pids_limit])
    return flags


def _docker_network_flags() -> list[str]:
    network_mode = os.environ.get("TDS_DOCKER_NETWORK", "").strip()
    if not network_mode:
        return []
    return ["--network", network_mode]


def _docker_read_only_flags() -> list[str]:
    if not _env_enabled("TDS_DOCKER_READ_ONLY", False):
        return []
    return [
        "--read-only",
        "--tmpfs",
        "/tmp:rw,nosuid,nodev,size=256m",
        "-e",
        "HOME=/tmp",
    ]


def _docker_image_retention_count() -> int:
    raw = os.environ.get("TDS_DOCKER_IMAGE_RETENTION", "3").strip()
    try:
        parsed = int(raw)
    except ValueError:
        return 3
    return max(parsed, 0)


def _select_prunable_image_tags(
    *,
    ordered_tags: list[str],
    keep_tags: set[str],
    retention_count: int,
) -> list[str]:
    if retention_count <= 0:
        protected = set(keep_tags)
    else:
        protected = set(ordered_tags[:retention_count]) | keep_tags
    return [tag for tag in ordered_tags if tag not in protected]


def _list_hashed_image_tags() -> list[str]:
    try:
        result = subprocess.run(
            [
                "docker",
                "image",
                "ls",
                "--format",
                "{{.Repository}}:{{.Tag}}",
                "--filter",
                f"reference={IMAGE_TAG_PREFIX}*",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception:  # noqa: BLE001
        return []
    if result.returncode != 0:
        return []
    return [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip() and "<none>" not in line
    ]


def _created_timestamps_by_tag(tags: list[str]) -> dict[str, str]:
    if not tags:
        return {}
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", *tags],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception:  # noqa: BLE001
        return {}
    if result.returncode != 0:
        return {}
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}
    created_by_tag: dict[str, str] = {}
    tag_set = set(tags)
    for image in payload:
        created = str(image.get("Created", ""))
        for repo_tag in image.get("RepoTags") or []:
            if repo_tag in tag_set:
                created_by_tag[repo_tag] = created
    return created_by_tag


def _prune_stale_hashed_images(*, keep_tags: set[str]) -> None:
    retention_count = _docker_image_retention_count()
    tags = _list_hashed_image_tags()
    if not tags:
        return
    created_by_tag = _created_timestamps_by_tag(tags)
    ordered_tags = sorted(tags, key=lambda tag: created_by_tag.get(tag, ""), reverse=True)
    prunable = _select_prunable_image_tags(
        ordered_tags=ordered_tags,
        keep_tags=keep_tags,
        retention_count=retention_count,
    )
    for tag in prunable:
        try:
            subprocess.run(
                ["docker", "image", "rm", tag],
                check=False,
                capture_output=True,
                text=True,
            )
        except Exception:  # noqa: BLE001
            # Pruning is best-effort and must never block demo generation.
            continue


def _container_path_to_host(path_value: str, project_root: Path) -> Path:
    normalized = path_value.replace("\\", "/")
    if normalized == "/workspace":
        return project_root.resolve()
    if normalized.startswith("/workspace/"):
        rel = normalized.removeprefix("/workspace/")
        rel_parts = [part for part in rel.split("/") if part]
        return (project_root.joinpath(*rel_parts)).resolve()
    return Path(path_value)


def _map_workspace_strings(value: object, project_root: Path) -> object:
    if isinstance(value, str):
        normalized = value.replace("\\", "/")
        if normalized == "/workspace" or normalized.startswith("/workspace/"):
            return str(_container_path_to_host(value, project_root))
        return value
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


def _parse_result_output(stdout: str, project_root: Path) -> dict[str, Path | str | None]:
    parsed: dict[str, Path | str | None] = {
        "status": None,
        "run_dir": None,
        "events": None,
        "summary": None,
        "media_mp4": None,
        "media_gif": None,
    }
    for line in stdout.splitlines():
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
    return parsed


def _hash_files(base: Path, paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.relative_to(base).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def compute_image_tag(project_root: Path) -> str:
    studio_root = project_root
    files_to_hash: list[Path] = []

    for filename in ["Dockerfile", "pyproject.toml"]:
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
    return f"{IMAGE_REPOSITORY}:v1-{short_hash}"


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
        _prune_stale_hashed_images(keep_tags={image_tag})
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
            _prune_stale_hashed_images(keep_tags={image_tag})
            return image_tag
        raise DockerError(message) from exc
    _prune_stale_hashed_images(keep_tags={image_tag})
    return image_tag


def run_in_docker(
    screenplay_path: Path,
    output_dir: Path | None = None,
    keep_temp: bool = False,
    rebuild: bool = False,
    playback_mode: Literal["sequential", "simultaneous"] = "sequential",
    run_mode: Literal["scripted_vhs", "autonomous_video"] = "scripted_vhs",
    agent_prompt_mode: Literal["auto", "manual", "approve", "deny"] = "auto",
    media_redaction_mode: Literal["auto", "off", "input_line"] = "auto",
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
        *_docker_hardening_flags(),
        *_docker_network_flags(),
        *_docker_read_only_flags(),
        "-e",
        "TERMINAL_DEMO_STUDIO_IN_CONTAINER=1",
    ]
    if os.environ.get("OPENAI_API_KEY"):
        cmd.extend(["-e", "OPENAI_API_KEY"])
    if os.environ.get("OPENAI_BASE_URL"):
        cmd.extend(["-e", "OPENAI_BASE_URL"])
    if os.environ.get("OPENAI_ORGANIZATION"):
        cmd.extend(["-e", "OPENAI_ORGANIZATION"])
    if os.environ.get("ANTHROPIC_API_KEY"):
        cmd.extend(["-e", "ANTHROPIC_API_KEY"])
    if os.environ.get("ANTHROPIC_BASE_URL"):
        cmd.extend(["-e", "ANTHROPIC_BASE_URL"])
    cmd.extend(
        [
            image_tag,
            "-m",
            "terminal_demo_studio.cli",
            "render",
            str(container_screenplay),
            "--local",
            "--mode",
            run_mode,
            "--agent-prompts",
            agent_prompt_mode,
            "--redact",
            media_redaction_mode,
            "--playback",
            playback_mode,
        ]
    )

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
    if _env_enabled("TDS_DOCKER_VERBOSE", False):
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="")
    parsed_output = _parse_result_output(result.stdout, project_root)
    summary_path = parsed_output.get("summary")
    if isinstance(summary_path, Path):
        _rewrite_summary_paths(summary_path, project_root)

    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "docker run failed"
        if isinstance(parsed_output.get("run_dir"), Path):
            message = f"{message}\nRUN_DIR={parsed_output['run_dir']}"
        if isinstance(parsed_output.get("summary"), Path):
            message = f"{message}\nSUMMARY={parsed_output['summary']}"
        if isinstance(parsed_output.get("events"), Path):
            message = f"{message}\nEVENTS={parsed_output['events']}"
        raise DockerError(message)

    parsed: dict[str, Path | str | None] = {
        "status": "success",
        "run_dir": parsed_output.get("run_dir"),
        "events": parsed_output.get("events"),
        "summary": parsed_output.get("summary"),
        "media_mp4": parsed_output.get("media_mp4"),
        "media_gif": parsed_output.get("media_gif"),
    }
    if isinstance(parsed_output.get("status"), str):
        parsed["status"] = parsed_output["status"]
    return parsed
