"""MCP server for terminal-demo-studio.

Exposes tds operations as callable tools for Claude Code, Cursor, and other
MCP-compatible agents.  Requires the ``mcp`` optional dependency::

    pip install terminal-demo-studio[mcp]
"""
from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

try:
    from mcp.server.fastmcp import FastMCP

    _HAS_MCP = True
except ImportError:
    _HAS_MCP = False
    FastMCP = None


class _StubMCP:
    """No-op stand-in so tool functions are still importable without ``mcp``."""

    @staticmethod
    def tool() -> Callable[..., Any]:
        def _passthrough(fn: Any) -> Any:
            return fn

        return _passthrough

    def run(self, **_kw: object) -> None:  # pragma: no cover
        print(
            "The 'mcp' package is required for the MCP server. "
            "Install it with: pip install terminal-demo-studio[mcp]",
            file=sys.stderr,
        )
        raise SystemExit(1)


mcp: Any = FastMCP("terminal-demo-studio") if _HAS_MCP else _StubMCP()


# ---------------------------------------------------------------------------
# Tool: tds_validate
# ---------------------------------------------------------------------------


@mcp.tool()
def tds_validate(screenplay_path: str, explain: bool = False) -> str:
    """Validate a screenplay YAML file and return structured results.

    Args:
        screenplay_path: Absolute path to the screenplay YAML file.
        explain: Include per-scenario action/wait/setup counts.
    """
    from pydantic import ValidationError

    from terminal_demo_studio.models import Action, format_validation_error, load_screenplay

    path = Path(screenplay_path)
    if not path.is_file():
        return json.dumps({"valid": False, "error": f"File not found: {screenplay_path}"})

    try:
        screenplay = load_screenplay(path)
    except ValidationError as exc:
        return json.dumps({"valid": False, "error": format_validation_error(exc)})
    except Exception as exc:
        return json.dumps({"valid": False, "error": str(exc)})

    result: dict[str, object] = {
        "valid": True,
        "title": screenplay.title,
        "output": screenplay.output,
        "scenario_count": len(screenplay.scenarios),
    }

    if explain:
        scenarios = []
        for scenario in screenplay.scenarios:
            actions = [
                a if isinstance(a, Action) else Action(command=a)
                for a in scenario.actions
            ]
            scenarios.append({
                "label": scenario.label,
                "execution_mode": scenario.execution_mode,
                "actions": len(actions),
                "waits": sum(
                    1 for a in actions if a.wait_for or a.wait_screen_regex or a.wait_line_regex
                ),
                "setup": len(scenario.setup),
            })
        result["scenarios"] = scenarios

    return json.dumps(result)


# ---------------------------------------------------------------------------
# Tool: tds_lint
# ---------------------------------------------------------------------------


@mcp.tool()
def tds_lint(screenplay_path: str, strict: bool = False) -> str:
    """Lint a screenplay for policy and safety violations.

    Args:
        screenplay_path: Absolute path to the screenplay YAML file.
        strict: Treat warnings as errors.
    """
    from terminal_demo_studio.linting import lint_screenplay
    from terminal_demo_studio.models import load_screenplay

    path = Path(screenplay_path)
    if not path.is_file():
        return json.dumps({"status": "error", "error": f"File not found: {screenplay_path}"})

    try:
        screenplay = load_screenplay(path)
        lint_result = lint_screenplay(screenplay)
        output = lint_result.to_json()
        output["screenplay"] = str(path.resolve())
        output["strict"] = strict
        if strict and lint_result.warnings:
            output["status"] = "fail"
        return json.dumps(output)
    except Exception as exc:
        return json.dumps({"status": "error", "error": str(exc)})


# ---------------------------------------------------------------------------
# Tool: tds_render
# ---------------------------------------------------------------------------


@mcp.tool()
def tds_render(
    screenplay_path: str,
    mode: str = "auto",
    output_dir: str = "",
    output_formats: str = "gif",
    playback: str = "sequential",
    agent_prompts: str = "auto",
    redact: str = "auto",
) -> str:
    """Render a screenplay to GIF/MP4 terminal demo media.

    Args:
        screenplay_path: Absolute path to the screenplay YAML file.
        mode: Execution lane (auto, scripted_vhs, autonomous_pty, autonomous_video).
        output_dir: Output directory for rendered media. Empty string uses screenplay dir.
        output_formats: Comma-separated output formats (gif, mp4, or gif,mp4).
        playback: Playback mode (sequential or simultaneous).
        agent_prompts: Prompt handling for visual lane (auto, manual, approve, deny).
        redact: Media redaction mode (auto, off, input_line).
    """
    from terminal_demo_studio.cli import _execute_render

    path = Path(screenplay_path)
    if not path.is_file():
        return json.dumps({"status": "failed", "error": f"File not found: {screenplay_path}"})

    out_dir = Path(output_dir) if output_dir else None
    formats = tuple(f.strip() for f in output_formats.split(",") if f.strip())

    try:
        _execute_render(
            screenplay=path,
            use_docker=None,
            output_dir=out_dir,
            keep_temp=False,
            rebuild=False,
            playback_mode=playback,
            output_formats=formats,
            run_mode=mode,
            agent_prompt_mode=agent_prompts,
            media_redact_mode=redact,
        )
    except Exception as exc:
        return json.dumps({"status": "failed", "error": str(exc)})

    # Read the most recent summary to return structured output
    search_dir = out_dir or path.resolve().parent
    runs_dir = search_dir / ".terminal_demo_studio_runs"
    if runs_dir.is_dir():
        run_dirs = sorted(runs_dir.iterdir(), key=lambda p: p.name, reverse=True)
        for run_dir in run_dirs:
            summary_path = run_dir / "summary.json"
            if summary_path.is_file():
                payload = json.loads(summary_path.read_text(encoding="utf-8"))
                result: dict[str, object] = {
                    "status": payload.get("status", "success"),
                    "run_dir": str(run_dir.resolve()),
                    "summary": str(summary_path.resolve()),
                }
                media = payload.get("media")
                if isinstance(media, dict):
                    if media.get("gif"):
                        result["media_gif"] = media["gif"]
                    if media.get("mp4"):
                        result["media_mp4"] = media["mp4"]
                events_path = run_dir / "runtime" / "events.jsonl"
                if events_path.is_file():
                    result["events"] = str(events_path.resolve())
                return json.dumps(result)

    return json.dumps({"status": "success", "note": "Render completed but summary not found"})


# ---------------------------------------------------------------------------
# Tool: tds_debug
# ---------------------------------------------------------------------------


@mcp.tool()
def tds_debug(run_dir: str) -> str:
    """Inspect a completed run's artifacts and failure diagnostics.

    Args:
        run_dir: Absolute path to the run directory (.terminal_demo_studio_runs/run-xxx).
    """
    run_path = Path(run_dir)
    summary_path = run_path / "summary.json"
    if not summary_path.is_file():
        return json.dumps({"error": f"Missing summary.json in {run_dir}"})

    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    payload["run_dir"] = str(run_path.resolve())
    return json.dumps(payload, indent=2, sort_keys=True)


# ---------------------------------------------------------------------------
# Tool: tds_list_templates
# ---------------------------------------------------------------------------


@mcp.tool()
def tds_list_templates() -> str:
    """List available screenplay templates."""
    from terminal_demo_studio.resources import list_template_names

    return json.dumps({"templates": list_template_names()})


# ---------------------------------------------------------------------------
# Tool: tds_doctor
# ---------------------------------------------------------------------------


@mcp.tool()
def tds_doctor(
    mode: str = "auto",
) -> str:
    """Check environment readiness for rendering.

    Args:
        mode: Lane to check (auto, scripted_vhs, autonomous_pty, autonomous_video).
    """
    from terminal_demo_studio.doctor import DoctorMode, run_doctor_checks

    resolved_mode: DoctorMode = "auto"
    if mode in ("scripted_vhs", "autonomous_pty", "autonomous_video"):
        resolved_mode = mode  # type: ignore[assignment]

    checks = run_doctor_checks(resolved_mode)
    results = []
    for name, ok, message in checks:
        results.append({"name": name, "status": "pass" if ok else "fail", "message": message})

    overall = all(c[1] for c in checks)
    return json.dumps({
        "overall_status": "ready" if overall else "not_ready",
        "checks": results,
    })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the MCP server over stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
