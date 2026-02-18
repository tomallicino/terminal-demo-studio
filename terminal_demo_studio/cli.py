from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Literal, cast

import click
from pydantic import ValidationError

from terminal_demo_studio.director import run_director
from terminal_demo_studio.docker_runner import DockerError, run_in_docker
from terminal_demo_studio.doctor import run_doctor_checks
from terminal_demo_studio.models import Screenplay, format_validation_error, load_screenplay
from terminal_demo_studio.resources import list_template_names, read_template
from terminal_demo_studio.runtime.runner import run_autonomous_screenplay

PlaybackMode = Literal["sequential", "simultaneous"]
RunMode = Literal["auto", "scripted_vhs", "autonomous_pty"]


def _list_templates() -> list[str]:
    return list_template_names()


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


@click.group(help="Terminal Demo Studio: deterministic, agent-native CLI demo pipeline")
def app() -> None:
    pass


@app.command("run")
@click.argument("screenplay", type=click.Path(exists=True, path_type=Path))
@click.option("use_docker", "--docker/--local", default=None, help="Execution mode")
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
@click.option("produce_mp4", "--mp4/--no-mp4", default=True)
@click.option("produce_gif", "--gif/--no-gif", default=True)
@click.option(
    "run_mode",
    "--mode",
    type=click.Choice(["auto", "scripted_vhs", "autonomous_pty"], case_sensitive=False),
    default="auto",
    show_default=True,
)
def run(
    screenplay: Path,
    use_docker: bool | None,
    output_dir: Path | None,
    keep_temp: bool,
    rebuild: bool,
    playback_mode: str,
    produce_mp4: bool,
    produce_gif: bool,
    run_mode: str,
) -> None:
    if not produce_mp4 and not produce_gif:
        raise click.ClickException("At least one output type must be enabled")

    resolved_mode = run_mode
    if run_mode == "auto":
        loaded = load_screenplay(screenplay)
        if any(s.execution_mode == "autonomous_pty" for s in loaded.scenarios):
            resolved_mode = "autonomous_pty"
        else:
            resolved_mode = "scripted_vhs"

    if resolved_mode == "autonomous_pty":
        result = run_autonomous_screenplay(screenplay_path=screenplay, output_dir=output_dir)
        if not result.success:
            failure_hint = (
                f" Failure bundle: {result.failure_dir}" if result.failure_dir is not None else ""
            )
            raise click.ClickException(f"Autonomous run failed.{failure_hint}")
        click.echo(f"Autonomous run complete: events={result.events_path}")
        click.echo(f"Autonomous summary: {result.summary_path}")
        return

    in_container = os.environ.get("TERMINAL_DEMO_STUDIO_IN_CONTAINER") == "1"
    auto_mode = use_docker is None
    docker_mode = use_docker is True or (
        auto_mode and not in_container and resolved_mode in {"auto", "scripted_vhs"}
    )

    if docker_mode:
        playback = cast(PlaybackMode, playback_mode)
        try:
            run_in_docker(
                screenplay_path=screenplay,
                output_dir=output_dir,
                keep_temp=keep_temp,
                rebuild=rebuild,
                playback_mode=playback,
                produce_mp4=produce_mp4,
                produce_gif=produce_gif,
            )
        except DockerError as exc:
            if not auto_mode:
                raise click.ClickException(str(exc)) from exc
            click.echo(f"Docker unavailable ({exc}). Falling back to local mode.")
        else:
            click.echo("Rendering complete (docker mode).")
            return

    playback = cast(PlaybackMode, playback_mode)
    mp4_path, gif_path = run_director(
        screenplay_path=screenplay,
        output_dir=output_dir,
        keep_temp=keep_temp,
        playback_mode=playback,
        produce_mp4=produce_mp4,
        produce_gif=produce_gif,
    )
    if mp4_path is not None:
        click.echo(f"MP4: {mp4_path}")
    if gif_path is not None:
        click.echo(f"GIF: {gif_path}")


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
@click.option(
    "template",
    "--template",
    type=str,
    default="dev_bugfix",
)
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
    click.echo(f"Next: studio validate {output_path}")


@app.command("init")
@click.option(
    "destination",
    "--destination",
    type=click.Path(path_type=Path),
    default=Path("."),
    show_default=True,
)
@click.option("template", "--template", type=str, default="mock_wizard", show_default=True)
@click.option("name", "--name", type=str, default="getting_started", show_default=True)
@click.option("force", "--force", is_flag=True, default=False)
def init(destination: Path, template: str, name: str, force: bool) -> None:
    templates = _list_templates()
    if template not in templates:
        message = (
            f"Unknown template '{template}'. "
            "Use 'studio new --list-templates' to see valid options."
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
    click.echo(f"Next: studio validate {output_path}")
    click.echo(
        "Then: "
        f"studio run {output_path} --mode scripted_vhs --local --output-dir {outputs_dir}"
    )


@app.command("doctor")
@click.option(
    "mode",
    "--mode",
    type=click.Choice(["auto", "scripted_vhs", "autonomous_pty"], case_sensitive=False),
    default="auto",
    show_default=True,
)
def doctor(mode: str) -> None:
    checks = run_doctor_checks(cast(RunMode, mode))
    has_failures = False
    warning_checks = {"docker-daemon", "container-binaries", "local-ffmpeg-drawtext"}
    if mode == "autonomous_pty":
        warning_checks.update({"local-vhs", "local-ffmpeg", "local-ffprobe"})
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


def main() -> None:
    app()


if __name__ == "__main__":
    main()
