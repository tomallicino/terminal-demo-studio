from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from terminal_demo_studio.models import AgentPromptPolicy

AgentPromptMode = Literal["auto", "manual", "approve", "deny"]

DEFAULT_AGENT_PROMPT_MODE: Literal["manual", "approve", "deny"] = "manual"
DEFAULT_AGENT_PROMPT_REGEX = "Press enter to confirm or esc to cancel"


@dataclass(slots=True)
class PromptPolicyLintResult:
    errors: list[str]
    warnings: list[str]


def merge_agent_prompt_policy(
    base: AgentPromptPolicy,
    override: AgentPromptPolicy | None,
) -> AgentPromptPolicy:
    if override is None:
        return base
    merged = base.model_copy(deep=True)
    for field_name in override.model_fields_set:
        setattr(merged, field_name, getattr(override, field_name))
    return merged


def resolve_merged_agent_prompt_policy(
    *,
    screenplay_policy: AgentPromptPolicy | None,
    scenario_policy: AgentPromptPolicy | None,
    override_mode: AgentPromptMode = "auto",
    env_mode: Literal["manual", "approve", "deny"] | None = None,
) -> AgentPromptPolicy:
    merged = AgentPromptPolicy(
        mode=DEFAULT_AGENT_PROMPT_MODE,
        prompt_regex=DEFAULT_AGENT_PROMPT_REGEX,
    )
    merged = merge_agent_prompt_policy(merged, screenplay_policy)
    merged = merge_agent_prompt_policy(merged, scenario_policy)

    if env_mode is not None:
        merged.mode = env_mode
    if override_mode != "auto":
        merged.mode = override_mode
    return merged


def looks_unbounded_allow_regex(pattern: str) -> bool:
    normalized = pattern.strip()
    lowered = normalized.lower()
    return lowered in {".*", "^.*$", "(?s).*", ".+", "^.+$", "[\\s\\S]*", "[\\s\\S]+"}


def lint_agent_prompt_policy(
    policy: AgentPromptPolicy,
    *,
    allow_unbounded_approve: bool,
) -> PromptPolicyLintResult:
    errors: list[str] = []
    warnings: list[str] = []

    if policy.mode == "approve":
        if not (policy.allow_regex and policy.allow_regex.strip()):
            errors.append("approve mode requires a non-empty allow_regex")
        elif looks_unbounded_allow_regex(policy.allow_regex) and not allow_unbounded_approve:
            errors.append(
                "approve mode allow_regex is too broad; use a scoped pattern or set "
                "TDS_ALLOW_UNSAFE_APPROVE=1 to bypass"
            )

        if not policy.allowed_command_prefixes:
            warnings.append(
                "approve mode has no allowed_command_prefixes; approvals rely only on "
                "regex matching"
            )
    elif policy.allow_regex:
        warnings.append("allow_regex is ignored unless mode=approve")

    if policy.allowed_command_prefixes and policy.mode != "approve":
        warnings.append("allowed_command_prefixes is ignored unless mode=approve")

    if policy.max_rounds > 12:
        warnings.append("max_rounds above 12 can cause long unattended prompt loops")

    return PromptPolicyLintResult(errors=errors, warnings=warnings)
