from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from terminal_demo_studio.models import Action, Screenplay
from terminal_demo_studio.prompt_policy import (
    lint_agent_prompt_policy,
    resolve_merged_agent_prompt_policy,
)


@dataclass(slots=True)
class LintFinding:
    severity: Literal["error", "warning"]
    code: str
    message: str
    scenario: str | None = None
    step_index: int | None = None


@dataclass(slots=True)
class ScreenplayLintResult:
    findings: list[LintFinding]

    @property
    def errors(self) -> list[LintFinding]:
        return [finding for finding in self.findings if finding.severity == "error"]

    @property
    def warnings(self) -> list[LintFinding]:
        return [finding for finding in self.findings if finding.severity == "warning"]

    @property
    def status(self) -> Literal["pass", "fail"]:
        return "fail" if self.errors else "pass"

    def to_json(self) -> dict[str, object]:
        return {
            "status": self.status,
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "findings": [asdict(finding) for finding in self.findings],
        }


def lint_screenplay(screenplay: Screenplay) -> ScreenplayLintResult:
    findings: list[LintFinding] = []
    has_video_scenarios = False

    for scenario in screenplay.scenarios:
        if scenario.execution_mode != "autonomous_video":
            if scenario.agent_prompts is not None:
                findings.append(
                    LintFinding(
                        severity="warning",
                        code="agent-prompts-ignored",
                        scenario=scenario.label,
                        message=(
                            "agent_prompts is set but this scenario is not autonomous_video; "
                            "the policy is ignored"
                        ),
                    )
                )
            continue

        has_video_scenarios = True
        merged_policy = resolve_merged_agent_prompt_policy(
            screenplay_policy=screenplay.agent_prompts,
            scenario_policy=scenario.agent_prompts,
            override_mode="auto",
            env_mode=None,
        )
        lint_result = lint_agent_prompt_policy(merged_policy, allow_unbounded_approve=False)
        for error in lint_result.errors:
            findings.append(
                LintFinding(
                    severity="error",
                    code="agent-policy",
                    scenario=scenario.label,
                    message=error,
                )
            )
        for warning in lint_result.warnings:
            findings.append(
                LintFinding(
                    severity="warning",
                    code="agent-policy",
                    scenario=scenario.label,
                    message=warning,
                )
            )

        for step_index, raw_action in enumerate(scenario.actions):
            action = raw_action if isinstance(raw_action, Action) else Action(command=raw_action)
            if action.expect_exit_code is not None:
                findings.append(
                    LintFinding(
                        severity="error",
                        code="autonomous-video-expect-exit-code",
                        scenario=scenario.label,
                        step_index=step_index,
                        message=(
                            "expect_exit_code is not supported in autonomous_video; "
                            "use screen assertions instead"
                        ),
                    )
                )

    if screenplay.agent_prompts is not None and not has_video_scenarios:
        findings.append(
            LintFinding(
                severity="warning",
                code="screenplay-agent-prompts-ignored",
                message=(
                    "screenplay-level agent_prompts is ignored without "
                    "autonomous_video scenarios"
                ),
            )
        )

    return ScreenplayLintResult(findings=findings)
