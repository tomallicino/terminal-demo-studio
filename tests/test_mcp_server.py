from __future__ import annotations

import json
from pathlib import Path

from terminal_demo_studio.mcp_server import (
    tds_debug,
    tds_doctor,
    tds_lint,
    tds_list_templates,
    tds_validate,
)

MOCK_SCREENPLAY = Path(__file__).resolve().parents[1] / "examples" / "mock" / "agent_loop.yaml"
SHOWCASE_SCREENPLAY = (
    Path(__file__).resolve().parents[1] / "examples" / "mock" / "install_first_command.yaml"
)


def test_tds_validate_valid_screenplay() -> None:
    result = json.loads(tds_validate(str(MOCK_SCREENPLAY)))
    assert result["valid"] is True
    assert "title" in result
    assert result["scenario_count"] >= 1


def test_tds_validate_with_explain() -> None:
    result = json.loads(tds_validate(str(SHOWCASE_SCREENPLAY), explain=True))
    assert result["valid"] is True
    assert "scenarios" in result
    for scenario in result["scenarios"]:
        assert "label" in scenario
        assert "actions" in scenario


def test_tds_validate_missing_file() -> None:
    result = json.loads(tds_validate("/nonexistent/path.yaml"))
    assert result["valid"] is False
    assert "error" in result


def test_tds_lint_clean_screenplay() -> None:
    result = json.loads(tds_lint(str(SHOWCASE_SCREENPLAY)))
    assert result["status"] == "pass"
    assert result["errors"] == 0


def test_tds_lint_missing_file() -> None:
    result = json.loads(tds_lint("/nonexistent/path.yaml"))
    assert result["status"] == "error"


def test_tds_list_templates() -> None:
    result = json.loads(tds_list_templates())
    assert "templates" in result
    assert len(result["templates"]) >= 3
    assert "install_first_command" in result["templates"]
    assert "before_after_bugfix" in result["templates"]


def test_tds_doctor_auto_mode() -> None:
    result = json.loads(tds_doctor("auto"))
    assert "overall_status" in result
    assert "checks" in result
    assert len(result["checks"]) >= 1
    for check in result["checks"]:
        assert "name" in check
        assert "status" in check
        assert check["status"] in ("pass", "fail")


def test_tds_debug_missing_summary(tmp_path: Path) -> None:
    result = json.loads(tds_debug(str(tmp_path)))
    assert "error" in result


def test_tds_debug_valid_summary(tmp_path: Path) -> None:
    summary = {
        "status": "success",
        "lane": "scripted_vhs",
        "screenplay": "test.yaml",
    }
    (tmp_path / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    result = json.loads(tds_debug(str(tmp_path)))
    assert result["status"] == "success"
    assert result["lane"] == "scripted_vhs"
    assert "run_dir" in result
