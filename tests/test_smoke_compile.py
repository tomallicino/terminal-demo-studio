from __future__ import annotations

from pathlib import Path

from terminal_demo_studio.models import load_screenplay
from terminal_demo_studio.tape import compile_tape


def test_drift_protection_compiles_to_tape() -> None:
    screenplay_path = Path(__file__).resolve().parents[1] / "screenplays" / "drift_protection.yaml"
    screenplay = load_screenplay(screenplay_path)

    tape = compile_tape(screenplay.scenarios[0], screenplay.settings, ["scene_0.mp4"])

    assert 'Output "scene_0.mp4"' in tape
    assert "Set Theme \"TokyoNightStorm\"" in tape


def test_dev_bugfix_workflow_compiles_to_tape() -> None:
    screenplay_path = (
        Path(__file__).resolve().parents[1] / "screenplays" / "dev_bugfix_workflow.yaml"
    )
    screenplay = load_screenplay(screenplay_path)

    tape = compile_tape(screenplay.scenarios[0], screenplay.settings, ["scene_0.mp4"])

    assert "python3 -m unittest -q" in tape
    assert "Wait+Screen@8s /FAIL:/" in tape


def test_single_prompt_macos_demo_compiles_to_tape() -> None:
    screenplay_path = (
        Path(__file__).resolve().parents[1] / "screenplays" / "single_prompt_macos_demo.yaml"
    )
    screenplay = load_screenplay(screenplay_path)

    tape = compile_tape(screenplay.scenarios[0], screenplay.settings, ["scene_0.mp4"])

    assert "Type \"export PS1='dev@workstation ${PWD} % '\"" in tape
    assert "Wait+Screen@8s /OK/" in tape
