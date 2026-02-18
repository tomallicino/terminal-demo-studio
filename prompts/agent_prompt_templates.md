# Agent Prompt Templates

Copy/paste prompts for generating valid screenplay YAML for `tds`.

## 1) Fast valid screenplay generator

```text
Generate a valid screenplay YAML for terminal-demo-studio.

Return only raw YAML. No markdown fences.

Validation requirements:
- Top-level required keys: title, output, scenarios
- Optional top-level keys: settings, variables, preinstall, agent_prompts
- scenarios must contain at least 1 scenario
- each scenario must include: label, actions
- scenario surface must be terminal when provided
- execution_mode values: scripted_vhs | autonomous_pty | autonomous_video
- every action entry must be either:
  - a string command, or
  - an object containing at least one of:
    type, command, input, key, hotkey, sleep, wait_for,
    wait_screen_regex, wait_line_regex, wait_stable,
    assert_screen_regex, assert_not_screen_regex, expect_exit_code
- durations must match <number>ms or <number>s
- wait_mode/wait_timeout are only valid when wait_for is present

Quality requirements:
- deterministic text output
- explicit waits/assertions for state transitions
- no ambiguous "just wait" behavior

Use output slug: [OUTPUT_SLUG]
Use title: [TITLE]
```

## 2) Narrative-to-screenplay converter

```text
Convert this narrative into valid terminal-demo-studio screenplay YAML.
Return YAML only.

Narrative:
[PASTE NARRATIVE]

Constraints:
- Include settings with width, height, theme, and font_family.
- Use execution_mode: scripted_vhs unless narrative explicitly requires autonomous interaction.
- Add at least one wait/assert anchor for each scenario.
- Keep command text realistic and deterministic.
- Avoid unsupported fields.

Set output slug to: [OUTPUT_SLUG]
Set title to: [TITLE]
```

## 3) Autonomous-video policy-safe generator

```text
Generate a valid autonomous_video screenplay YAML for terminal-demo-studio.
Return only YAML.

Requirements:
- execution_mode must be autonomous_video
- include a policy section using agent_prompts
- if mode=approve, include allow_regex
- include bounded max_rounds (<= 6)
- include at least one wait_for per control step
- do not use expect_exit_code
- include explicit final wait_for success text

Goal narrative:
[PASTE NARRATIVE]

Output slug: [OUTPUT_SLUG]
Title: [TITLE]
```

## 4) Self-repair prompt for invalid YAML

```text
You are repairing invalid terminal-demo-studio screenplay YAML.

Input YAML:
[PASTE YAML]

Validation error(s):
[PASTE ERRORS]

Task:
- Return corrected YAML only.
- Preserve original intent.
- Keep schema-valid fields only.
- Ensure every scenario has at least one action.
- Ensure duration formatting and wait constraints are valid.
```
