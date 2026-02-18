from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Literal, cast

import click
from pydantic import ValidationError

from terminal_demo_studio.director import ScriptedRunResult, run_director
from terminal_demo_studio.docker_runner import DockerError, run_in_docker
from terminal_demo_studio.doctor import run_doctor_checks
from terminal_demo_studio.linting import lint_screenplay
from terminal_demo_studio.models import Screenplay, format_validation_error, load_screenplay
from terminal_demo_studio.redaction import MediaRedactionMode
from terminal_demo_studio.resources import list_template_names, read_template
from terminal_demo_studio.runtime.runner import AutonomousRunResult, run_autonomous_screenplay
from terminal_demo_studio.runtime.video_runner import (
    AutonomousVideoRunResult,
    format_local_video_dependency_help,
    missing_local_video_dependencies,
    run_autonomous_video_screenplay,
)

PlaybackMode = Literal["sequential", "simultaneous"]
RunMode = Literal["auto", "scripted_vhs", "autonomous_pty", "autonomous_video"]
AgentPromptMode = Literal["auto", "manual", "approve", "deny"]
DoctorMode = RunMode

_RUN_MODE_ALIASES: dict[str, RunMode] = {
    "auto": "auto",
    "scripted": "scripted_vhs",
    "scripted_vhs": "scripted_vhs",
    "interactive": "autonomous_pty",
    "autonomous_pty": "autonomous_pty",
    "visual": "autonomous_video",
    "video": "autonomous_video",
    "autonomous_video": "autonomous_video",
}


def _list_templates() -> list[str]:
    return list_template_names()


def _normalize_run_mode(value: str) -> RunMode:
    normalized = value.strip().lower()
    resolved = _RUN_MODE_ALIASES.get(normalized)
    if resolved is None:
        supported = ", ".join(sorted(_RUN_MODE_ALIASES))
        raise click.ClickException(f"Unsupported mode '{value}'. Try one of: {supported}")
    return resolved


def _normalize_agent_prompt_mode(value: str) -> AgentPromptMode:
    normalized = value.strip().lower()
    if normalized not in {"auto", "manual", "approve", "deny"}:
        raise click.ClickException(
            f"Unsupported --agent-prompts value '{value}'. "
            "Try one of: auto, manual, approve, deny"
        )
    return cast(AgentPromptMode, normalized)


def _normalize_redact_mode(value: str) -> MediaRedactionMode:
    normalized = value.strip().lower()
    if normalized not in {"auto", "off", "input_line"}:
        raise click.ClickException(
            f"Unsupported --redact value '{value}'. Try one of: auto, off, input_line"
        )
    return cast(MediaRedactionMode, normalized)


def _write_screenplay_from_template(
    *,
    name: str,
    destination: Path,
    template: str,
    force: bool,
) -> tuple[Path, bool]:
    destination.mkdir(parents=True, exist_ok=True)
    output_path = destination / f"{name}.yaml"
    overwritten = output_path.exists()
    if overwritten and not force:
        raise click.ClickException(f"File already exists: {output_path}")

    content = read_template(template)
    content = re.sub(
        r'(?m)^output:\s*".*"$',
        f'output: "{name}"',
        content,
        count=1,
    )
    output_path.write_text(content, encoding="utf-8")
    return output_path, overwritten


def _resolve_run_mode(screenplay: Path, requested_mode: str) -> RunMode:
    normalized_mode = _normalize_run_mode(requested_mode)
    if normalized_mode != "auto":
        return normalized_mode
    loaded = load_screenplay(screenplay)
    if any(s.execution_mode == "autonomous_video" for s in loaded.scenarios):
        return "autonomous_video"
    if any(s.execution_mode == "autonomous_pty" for s in loaded.scenarios):
        return "autonomous_pty"
    return "scripted_vhs"


def _resolve_outputs(output_formats: tuple[str, ...]) -> tuple[bool, bool]:
    selected_outputs = {value.lower() for value in output_formats}
    produce_mp4 = not selected_outputs or "mp4" in selected_outputs
    produce_gif = not selected_outputs or "gif" in selected_outputs
    if not produce_mp4 and not produce_gif:
        raise click.ClickException("At least one output type must be enabled")
    return produce_mp4, produce_gif


def _emit_result(
    *,
    status: str,
    run_dir: Path | None,
    media_mp4: Path | None = None,
    media_gif: Path | None = None,
    events: Path | None = None,
    summary: Path | None = None,
) -> None:
    click.echo(f"STATUS={status}")
    if run_dir is not None:
        click.echo(f"RUN_DIR={run_dir}")
    if media_mp4 is not None:
        click.echo(f"MEDIA_MP4={media_mp4}")
    if media_gif is not None:
        click.echo(f"MEDIA_GIF={media_gif}")
    if events is not None:
        click.echo(f"EVENTS={events}")
    if summary is not None:
        click.echo(f"SUMMARY={summary}")


def _run_local_or_autonomous(
    *,
    screenplay: Path,
    output_dir: Path | None,
    keep_temp: bool,
    playback_mode: PlaybackMode,
    produce_mp4: bool,
    produce_gif: bool,
    resolved_mode: RunMode,
    agent_prompt_mode: AgentPromptMode,
    media_redact_mode: MediaRedactionMode,
) -> None:
    if resolved_mode == "autonomous_pty":
        auto_result: AutonomousRunResult = run_autonomous_screenplay(
            screenplay_path=screenplay,
            output_dir=output_dir,
        )
        _emit_result(
            status="success" if auto_result.success else "failed",
            run_dir=auto_result.run_dir,
            events=auto_result.events_path,
            summary=auto_result.summary_path,
        )
        if not auto_result.success:
            failure_hint = (
                f" Failure bundle: {auto_result.failure_dir}"
                if auto_result.failure_dir is not None
                else ""
            )
            raise click.ClickException(f"Autonomous run failed.{failure_hint}")
        return

    if resolved_mode == "autonomous_video":
        video_result: AutonomousVideoRunResult = run_autonomous_video_screenplay(
            screenplay_path=screenplay,
            output_dir=output_dir,
            keep_temp=keep_temp,
            playback_mode=playback_mode,
            produce_mp4=produce_mp4,
            produce_gif=produce_gif,
            agent_prompt_mode=agent_prompt_mode,
            media_redaction_mode=media_redact_mode,
        )
        _emit_result(
            status="success" if video_result.success else "failed",
            run_dir=video_result.run_dir,
            media_mp4=video_result.mp4_path,
            media_gif=video_result.gif_path,
            events=video_result.events_path,
            summary=video_result.summary_path,
        )
        if not video_result.success:
            failure_hint = (
                f" Failure bundle: {video_result.failure_dir}"
                if video_result.failure_dir is not None
                else ""
            )
            raise click.ClickException(f"Autonomous video run failed.{failure_hint}")
        return

    scripted_result: ScriptedRunResult = run_director(
        screenplay_path=screenplay,
        output_dir=output_dir,
        keep_temp=keep_temp,
        playback_mode=playback_mode,
        produce_mp4=produce_mp4,
        produce_gif=produce_gif,
        media_redaction_mode=media_redact_mode,
    )
    _emit_result(
        status="success" if scripted_result.success else "failed",
        run_dir=scripted_result.run_layout.run_dir,
        media_mp4=scripted_result.mp4_path,
        media_gif=scripted_result.gif_path,
        summary=scripted_result.run_layout.summary_path,
    )


def _execute_render(
    *,
    screenplay: Path,
    use_docker: bool | None,
    output_dir: Path | None,
    keep_temp: bool,
    rebuild: bool,
    playback_mode: str,
    output_formats: tuple[str, ...],
    run_mode: str,
    agent_prompt_mode: str,
    media_redact_mode: str,
) -> None:
    produce_mp4, produce_gif = _resolve_outputs(output_formats)
    resolved_mode = _resolve_run_mode(screenplay, run_mode)
    resolved_prompt_mode = _normalize_agent_prompt_mode(agent_prompt_mode)
    resolved_redact_mode = _normalize_redact_mode(media_redact_mode)
    in_container = os.environ.get("TERMINAL_DEMO_STUDIO_IN_CONTAINER") == "1"
    auto_mode = use_docker is None

    if resolved_mode == "autonomous_pty":
        _run_local_or_autonomous(
            screenplay=screenplay,
            output_dir=output_dir,
            keep_temp=keep_temp,
            playback_mode=cast(PlaybackMode, playback_mode),
            produce_mp4=produce_mp4,
            produce_gif=produce_gif,
            resolved_mode=resolved_mode,
            agent_prompt_mode=resolved_prompt_mode,
            media_redact_mode=resolved_redact_mode,
        )
        return

    if resolved_mode == "autonomous_video":
        missing_video_deps = missing_local_video_dependencies()
        local_ready = len(missing_video_deps) == 0
        if use_docker is False:
            if not local_ready:
                raise click.ClickException(format_local_video_dependency_help(missing_video_deps))
            _run_local_or_autonomous(
                screenplay=screenplay,
                output_dir=output_dir,
                keep_temp=keep_temp,
                playback_mode=cast(PlaybackMode, playback_mode),
                produce_mp4=produce_mp4,
                produce_gif=produce_gif,
                resolved_mode=resolved_mode,
                agent_prompt_mode=resolved_prompt_mode,
                media_redact_mode=resolved_redact_mode,
            )
            return
        if use_docker is True:
            try:
                docker_result = run_in_docker(
                    screenplay_path=screenplay,
                    output_dir=output_dir,
                    keep_temp=keep_temp,
                    rebuild=rebuild,
                    playback_mode=cast(PlaybackMode, playback_mode),
                    run_mode="autonomous_video",
                    produce_mp4=produce_mp4,
                    produce_gif=produce_gif,
                    agent_prompt_mode=resolved_prompt_mode,
                    media_redaction_mode=resolved_redact_mode,
                )
            except DockerError as exc:
                raise click.ClickException(str(exc)) from exc
            _emit_result(
                status=cast(str, docker_result.get("status", "success")),
                run_dir=cast(Path | None, docker_result.get("run_dir")),
                media_mp4=cast(Path | None, docker_result.get("media_mp4")),
                media_gif=cast(Path | None, docker_result.get("media_gif")),
                events=cast(Path | None, docker_result.get("events")),
                summary=cast(Path | None, docker_result.get("summary")),
            )
            return

        if local_ready:
            _run_local_or_autonomous(
                screenplay=screenplay,
                output_dir=output_dir,
                keep_temp=keep_temp,
                playback_mode=cast(PlaybackMode, playback_mode),
                produce_mp4=produce_mp4,
                produce_gif=produce_gif,
                resolved_mode=resolved_mode,
                agent_prompt_mode=resolved_prompt_mode,
                media_redact_mode=resolved_redact_mode,
            )
            return

        if in_container:
            raise click.ClickException(
                "autonomous_video local dependencies are missing inside the container. "
                f"{format_local_video_dependency_help(missing_video_deps)}"
            )

        try:
            docker_result = run_in_docker(
                screenplay_path=screenplay,
                output_dir=output_dir,
                keep_temp=keep_temp,
                rebuild=rebuild,
                playback_mode=cast(PlaybackMode, playback_mode),
                run_mode="autonomous_video",
                produce_mp4=produce_mp4,
                produce_gif=produce_gif,
                agent_prompt_mode=resolved_prompt_mode,
                media_redaction_mode=resolved_redact_mode,
            )
        except DockerError as exc:
            message = format_local_video_dependency_help(missing_video_deps)
            raise click.ClickException(f"{message} Docker fallback also failed: {exc}") from exc
        _emit_result(
            status=cast(str, docker_result.get("status", "success")),
            run_dir=cast(Path | None, docker_result.get("run_dir")),
            media_mp4=cast(Path | None, docker_result.get("media_mp4")),
            media_gif=cast(Path | None, docker_result.get("media_gif")),
            events=cast(Path | None, docker_result.get("events")),
            summary=cast(Path | None, docker_result.get("summary")),
        )
        return

    docker_mode = use_docker is True or (auto_mode and not in_container)

    if docker_mode:
        try:
            docker_result = run_in_docker(
                screenplay_path=screenplay,
                output_dir=output_dir,
                keep_temp=keep_temp,
                rebuild=rebuild,
                playback_mode=cast(PlaybackMode, playback_mode),
                run_mode="scripted_vhs",
                produce_mp4=produce_mp4,
                produce_gif=produce_gif,
                agent_prompt_mode=resolved_prompt_mode,
                media_redaction_mode=resolved_redact_mode,
            )
        except DockerError as exc:
            if not auto_mode:
                raise click.ClickException(str(exc)) from exc
            click.echo(f"Docker unavailable ({exc}). Falling back to local mode.")
        else:
            _emit_result(
                status=cast(str, docker_result.get("status", "success")),
                run_dir=cast(Path | None, docker_result.get("run_dir")),
                media_mp4=cast(Path | None, docker_result.get("media_mp4")),
                media_gif=cast(Path | None, docker_result.get("media_gif")),
                events=cast(Path | None, docker_result.get("events")),
                summary=cast(Path | None, docker_result.get("summary")),
            )
            return

    _run_local_or_autonomous(
        screenplay=screenplay,
        output_dir=output_dir,
        keep_temp=keep_temp,
        playback_mode=cast(PlaybackMode, playback_mode),
        produce_mp4=produce_mp4,
        produce_gif=produce_gif,
        resolved_mode=resolved_mode,
        agent_prompt_mode=resolved_prompt_mode,
        media_redact_mode=resolved_redact_mode,
    )


@click.group(
    help=(
        "Terminal Demo Studio CLI (alpha): deterministic terminal demos in three lanes "
        "(scripted, interactive, visual)."
    )
)
def app() -> None:
    pass


@app.command("render")
@click.argument("screenplay", type=click.Path(exists=True, path_type=Path), required=False)
@click.option("template", "--template", type=str, default=None)
@click.option("name", "--name", type=str, default=None)
@click.option("destination", "--destination", type=click.Path(path_type=Path), default=None)
@click.option(
    "use_docker",
    "--docker/--local",
    default=None,
    help="Runtime location (local machine or Docker container).",
)
@click.option("output_dir", "--output-dir", type=click.Path(path_type=Path), default=None)
@click.option("keep_temp", "--keep-temp", is_flag=True, default=False)
@click.option("rebuild", "--rebuild", is_flag=True, default=False)
@click.option(
    "playback_mode",
    "--playback",
    type=click.Choice(["sequential", "simultaneous"], case_sensitive=False),
    default="sequential",
    show_default=True,
)
@click.option(
    "output_formats",
    "--output",
    type=click.Choice(["mp4", "gif"], case_sensitive=False),
    multiple=True,
    help="Output format(s). Repeat to request multiple. Defaults to both.",
)
@click.option(
    "run_mode",
    "--mode",
    type=click.Choice(
        [
            "auto",
            "scripted",
            "interactive",
            "visual",
            "video",
            "scripted_vhs",
            "autonomous_pty",
            "autonomous_video",
        ],
        case_sensitive=False,
    ),
    default="auto",
    show_default=True,
    help=(
        "Execution lane: scripted (tape replay), interactive (PTY command/assert), "
        "visual (full-screen TUI capture)."
    ),
)
@click.option(
    "agent_prompt_mode",
    "--agent-prompts",
    type=click.Choice(["auto", "manual", "approve", "deny"], case_sensitive=False),
    default="auto",
    show_default=True,
    help=(
        "How visual lane handles approval prompts: auto (use screenplay policy), "
        "manual (no auto confirm), approve, or deny."
    ),
)
@click.option(
    "media_redact_mode",
    "--redact",
    type=click.Choice(["auto", "off", "input_line"], case_sensitive=False),
    default="auto",
    show_default=True,
    help="Media redaction mode: auto, off, or input_line.",
)
def render(
    screenplay: Path | None,
    template: str | None,
    name: str | None,
    destination: Path | None,
    use_docker: bool | None,
    output_dir: Path | None,
    keep_temp: bool,
    rebuild: bool,
    playback_mode: str,
    output_formats: tuple[str, ...],
    run_mode: str,
    agent_prompt_mode: str,
    media_redact_mode: str,
) -> None:
    if screenplay is not None and template is not None:
        raise click.ClickException("Use either a screenplay path or --template, not both")
    if screenplay is None and template is None:
        raise click.ClickException("Provide <screenplay> or --template")

    temp_dir_ctx: tempfile.TemporaryDirectory[str] | None = None
    try:
        resolved_screenplay = screenplay
        if template is not None:
            templates = _list_templates()
            if template not in templates:
                raise click.ClickException(
                    f"Unknown template '{template}'. Use 'tds new --list-templates' to see options."
                )
            temp_dir_ctx = tempfile.TemporaryDirectory(prefix="terminal-demo-studio-template-")
            destination_dir = destination if destination is not None else Path(temp_dir_ctx.name)
            output_name = name or template
            resolved_screenplay, _ = _write_screenplay_from_template(
                name=output_name,
                destination=destination_dir,
                template=template,
                force=True,
            )

        assert resolved_screenplay is not None
        _execute_render(
            screenplay=resolved_screenplay,
            use_docker=use_docker,
            output_dir=output_dir,
            keep_temp=keep_temp,
            rebuild=rebuild,
            playback_mode=playback_mode,
            output_formats=output_formats,
            run_mode=run_mode,
            agent_prompt_mode=agent_prompt_mode,
            media_redact_mode=media_redact_mode,
        )
    finally:
        if temp_dir_ctx is not None:
            temp_dir_ctx.cleanup()


@app.command("run")
@click.argument("screenplay", type=click.Path(exists=True, path_type=Path))
@click.option(
    "use_docker",
    "--docker/--local",
    default=None,
    help="Runtime location (local machine or Docker container).",
)
@click.option("output_dir", "--output-dir", type=click.Path(path_type=Path), default=None)
@click.option("keep_temp", "--keep-temp", is_flag=True, default=False)
@click.option("rebuild", "--rebuild", is_flag=True, default=False)
@click.option(
    "playback_mode",
    "--playback",
    type=click.Choice(["sequential", "simultaneous"], case_sensitive=False),
    default="sequential",
    show_default=True,
)
@click.option(
    "output_formats",
    "--output",
    type=click.Choice(["mp4", "gif"], case_sensitive=False),
    multiple=True,
    help="Output format(s). Repeat to request multiple. Defaults to both.",
)
@click.option(
    "run_mode",
    "--mode",
    type=click.Choice(
        [
            "auto",
            "scripted",
            "interactive",
            "visual",
            "video",
            "scripted_vhs",
            "autonomous_pty",
            "autonomous_video",
        ],
        case_sensitive=False,
    ),
    default="auto",
    show_default=True,
    help=(
        "Execution lane: scripted (tape replay), interactive (PTY command/assert), "
        "visual (full-screen TUI capture)."
    ),
)
@click.option(
    "agent_prompt_mode",
    "--agent-prompts",
    type=click.Choice(["auto", "manual", "approve", "deny"], case_sensitive=False),
    default="auto",
    show_default=True,
    help=(
        "How visual lane handles approval prompts: auto (use screenplay policy), "
        "manual (no auto confirm), approve, or deny."
    ),
)
@click.option(
    "media_redact_mode",
    "--redact",
    type=click.Choice(["auto", "off", "input_line"], case_sensitive=False),
    default="auto",
    show_default=True,
    help="Media redaction mode: auto, off, or input_line.",
)
def run(
    screenplay: Path,
    use_docker: bool | None,
    output_dir: Path | None,
    keep_temp: bool,
    rebuild: bool,
    playback_mode: str,
    output_formats: tuple[str, ...],
    run_mode: str,
    agent_prompt_mode: str,
    media_redact_mode: str,
) -> None:
    _execute_render(
        screenplay=screenplay,
        use_docker=use_docker,
        output_dir=output_dir,
        keep_temp=keep_temp,
        rebuild=rebuild,
        playback_mode=playback_mode,
        output_formats=output_formats,
        run_mode=run_mode,
        agent_prompt_mode=agent_prompt_mode,
        media_redact_mode=media_redact_mode,
    )


@app.command("validate")
@click.argument("screenplay", type=click.Path(exists=True, path_type=Path))
@click.option("show_json_schema", "--json-schema", is_flag=True, default=False)
@click.option("explain", "--explain", is_flag=True, default=False)
def validate(screenplay: Path, show_json_schema: bool, explain: bool) -> None:
    if show_json_schema:
        click.echo(json.dumps(Screenplay.model_json_schema(), indent=2, sort_keys=True))
        return

    try:
        loaded = load_screenplay(screenplay)
    except ValidationError as exc:
        raise click.ClickException(format_validation_error(exc)) from exc
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Valid screenplay: {screenplay}")
    if explain:
        click.echo(f"Title: {loaded.title}")
        click.echo(f"Output: {loaded.output}")
        click.echo(f"Scenarios: {len(loaded.scenarios)}")
        for scenario in loaded.scenarios:
            action_count = len(scenario.actions)
            wait_count = sum(
                1 for action in scenario.actions if not isinstance(action, str) and action.wait_for
            )
            click.echo(
                f"- {scenario.label}: actions={action_count}, waits={wait_count}, "
                f"setup={len(scenario.setup)}"
            )


@app.command("new")
@click.argument("name", type=str, required=False)
@click.option(
    "destination",
    "--destination",
    type=click.Path(path_type=Path),
    default=Path("screenplays"),
)
@click.option("template", "--template", type=str, default="before_after_bugfix")
@click.option("list_templates", "--list-templates", is_flag=True, default=False)
@click.option("force", "--force", is_flag=True, default=False)
def new(
    name: str | None,
    destination: Path,
    template: str,
    list_templates: bool,
    force: bool,
) -> None:
    templates = _list_templates()
    if list_templates:
        click.echo("Available templates:")
        for template_name in templates:
            click.echo(f"- {template_name}")
        return

    if not name:
        raise click.ClickException("Name is required unless --list-templates is provided")
    if template not in templates:
        raise click.ClickException(
            f"Unknown template '{template}'. Use --list-templates to see valid options."
        )
    output_path, overwritten = _write_screenplay_from_template(
        name=name,
        destination=destination,
        template=template,
        force=force,
    )
    click.echo(f"Created screenplay: {output_path}")
    click.echo(f"Template: {template}")
    click.echo(f"Overwritten: {'yes' if overwritten else 'no'}")
    click.echo(f"Next: tds validate {output_path}")


@app.command("lint")
@click.argument("screenplay", type=click.Path(exists=True, path_type=Path))
@click.option("as_json", "--json", is_flag=True, default=False)
@click.option(
    "strict",
    "--strict",
    is_flag=True,
    default=False,
    help="Treat warnings as failures.",
)
def lint(screenplay: Path, as_json: bool, strict: bool) -> None:
    try:
        loaded = load_screenplay(screenplay)
    except ValidationError as exc:
        raise click.ClickException(format_validation_error(exc)) from exc
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    result = lint_screenplay(loaded)
    fail = bool(result.errors) or (strict and bool(result.warnings))
    status = "fail" if fail else "pass"

    if as_json:
        payload = result.to_json()
        payload["screenplay"] = str(screenplay.resolve())
        payload["strict"] = strict
        payload["status"] = status
        click.echo(json.dumps(payload, indent=2, sort_keys=True))
        if fail:
            raise SystemExit(1)
        return

    for finding in result.findings:
        location = ""
        if finding.scenario is not None:
            location = f" scenario={finding.scenario}"
            if finding.step_index is not None:
                location += f" step={finding.step_index}"
        level = "ERROR" if finding.severity == "error" else "WARN"
        click.echo(f"{level}{location} [{finding.code}] {finding.message}")

    click.echo(f"STATUS={status}")
    click.echo(f"ERRORS={len(result.errors)}")
    click.echo(f"WARNINGS={len(result.warnings)}")
    if fail:
        raise SystemExit(1)


@app.command("init")
@click.option(
    "destination",
    "--destination",
    type=click.Path(path_type=Path),
    default=Path("."),
    show_default=True,
)
@click.option(
    "template", "--template", type=str, default="install_first_command", show_default=True
)
@click.option("name", "--name", type=str, default="getting_started", show_default=True)
@click.option("force", "--force", is_flag=True, default=False)
def init(destination: Path, template: str, name: str, force: bool) -> None:
    templates = _list_templates()
    if template not in templates:
        message = (
            f"Unknown template '{template}'. "
            "Use 'tds new --list-templates' to see valid options."
        )
        raise click.ClickException(message)

    workspace = destination
    screenplays_dir = workspace / "screenplays"
    outputs_dir = workspace / "outputs"
    screenplays_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    output_path, overwritten = _write_screenplay_from_template(
        name=name,
        destination=screenplays_dir,
        template=template,
        force=force,
    )

    click.echo(f"Initialized workspace: {workspace.resolve()}")
    click.echo(f"Starter screenplay: {output_path}")
    click.echo(f"Template: {template}")
    click.echo(f"Overwritten: {'yes' if overwritten else 'no'}")
    click.echo(f"Next: tds validate {output_path}")
    click.echo(
        "Then: "
        f"tds render {output_path} --mode scripted_vhs --local --output-dir {outputs_dir}"
    )
    click.echo("Add to .gitignore:")
    click.echo("outputs/")
    click.echo(".terminal_demo_studio_runs/")


@app.command("doctor")
@click.option(
    "mode",
    "--mode",
    type=click.Choice(
        [
            "auto",
            "scripted",
            "interactive",
            "visual",
            "video",
            "scripted_vhs",
            "autonomous_pty",
            "autonomous_video",
        ],
        case_sensitive=False,
    ),
    default="auto",
    show_default=True,
    help="Lane health check. Friendly aliases: scripted, interactive, visual.",
)
def doctor(mode: str) -> None:
    resolved_mode = _normalize_run_mode(mode)
    checks = run_doctor_checks(resolved_mode)
    has_failures = False
    warning_checks = {"docker-daemon", "container-binaries", "local-ffmpeg-drawtext"}
    if resolved_mode == "autonomous_pty":
        warning_checks.update({"local-vhs", "local-ffmpeg", "local-ffprobe"})
    if resolved_mode == "autonomous_video":
        warning_checks.update(
            {
                "docker-daemon",
                "container-binaries",
                "local-kitty",
                "local-kitten",
                "local-xvfb",
                "local-ffmpeg",
                "local-ffprobe",
            }
        )
    for name, ok, message in checks:
        if ok:
            status = "PASS"
        elif name in warning_checks:
            status = "WARN"
        else:
            status = "FAIL"
        click.echo(f"{status} {name}: {message}")
        has_failures = has_failures or (status == "FAIL")

    if has_failures:
        raise SystemExit(1)


@app.command("debug")
@click.argument("run_dir", type=click.Path(exists=True, path_type=Path))
@click.option("as_json", "--json", is_flag=True, default=False)
def debug(run_dir: Path, as_json: bool) -> None:
    summary_path = run_dir / "summary.json"
    if not summary_path.exists():
        raise click.ClickException(f"Missing summary file: {summary_path}")
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    payload["run_dir"] = str(run_dir.resolve())

    if as_json:
        click.echo(json.dumps(payload, indent=2, sort_keys=True))
        return

    status = payload.get("status", "unknown")
    lane = payload.get("lane", "unknown")
    reason = payload.get("reason") or payload.get("error") or ""
    failed_step = payload.get("failed_step_index")
    failed_action = payload.get("failed_action")
    failure_dir = payload.get("failure_dir")
    media = payload.get("media") if isinstance(payload.get("media"), dict) else {}
    media_gif = media.get("gif") if isinstance(media, dict) else None
    media_mp4 = media.get("mp4") if isinstance(media, dict) else None

    lines = [
        f"RUN_DIR={run_dir.resolve()}",
        f"STATUS={status}",
        f"LANE={lane}",
    ]
    if payload.get("screenplay"):
        lines.append(f"SCREENPLAY={payload['screenplay']}")
    if media_gif:
        lines.append(f"MEDIA_GIF={media_gif}")
    if media_mp4:
        lines.append(f"MEDIA_MP4={media_mp4}")
    if failed_step is not None:
        lines.append(f"FAILED_STEP={failed_step}")
    if failed_action:
        lines.append(f"FAILED_ACTION={failed_action}")
    if reason:
        lines.append(f"REASON={reason}")

    next_action = ""
    if status == "failed" and failure_dir:
        next_action = f"tds debug {run_dir} --json"
    elif status == "success":
        next_action = (
            "tds render --template install_first_command "
            "--output gif --output-dir outputs"
        )
    if next_action:
        lines.append(f"NEXT={next_action}")

    for line in lines[:10]:
        click.echo(line)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
