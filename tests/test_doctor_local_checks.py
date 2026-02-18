from __future__ import annotations

import terminal_demo_studio.doctor as doctor


def test_doctor_reports_missing_local_tools(monkeypatch: object) -> None:
    monkeypatch.setattr(doctor, "_binary_exists", lambda name: False)
    monkeypatch.setattr(doctor, "_ffmpeg_has_drawtext", lambda: False)
    monkeypatch.setattr(doctor, "_docker_check", lambda: ("docker-daemon", False, "no docker"))
    monkeypatch.setattr(
        doctor,
        "_packaged_template_checks",
        lambda: [
            ("screenplay-template", True, "ok"),
            ("screenplay-sample", True, "ok"),
        ],
    )
    monkeypatch.setattr(
        doctor,
        "_container_binary_check",
        lambda docker_ok, mode: ("container-binaries", False, "skipped"),
    )

    checks = doctor.run_doctor_checks(mode="autonomous_pty")
    names = {name for name, _, _ in checks}

    assert "local-vhs" in names
    assert "local-ffmpeg" in names
    assert "local-ffprobe" in names


def test_doctor_autonomous_video_reports_runtime_unavailable(monkeypatch: object) -> None:
    monkeypatch.setattr(doctor, "_binary_exists", lambda name: False)
    monkeypatch.setattr(doctor, "_docker_check", lambda: ("docker-daemon", False, "no docker"))
    monkeypatch.setattr(
        doctor,
        "_container_binary_check",
        lambda docker_ok, mode: ("container-binaries", False, "skipped"),
    )
    monkeypatch.setattr(
        doctor,
        "_packaged_template_checks",
        lambda: [
            ("screenplay-template", True, "ok"),
            ("screenplay-sample", True, "ok"),
        ],
    )

    checks = doctor.run_doctor_checks(mode="autonomous_video")
    runtime_check = next(item for item in checks if item[0] == "autonomous-video-runtime")

    assert runtime_check[1] is False
