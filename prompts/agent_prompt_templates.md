# Agent Prompt Templates (Copy/Paste)

## 1) Fast Valid Screenplay Generator
Use this when you need a brand new demo screenplay quickly.

```text
You are generating a screenplay YAML for this repo's `studio validate` command.

Return ONLY raw YAML. No markdown fences. No explanation.

Hard schema rules (must satisfy all):
- Top-level keys: `title`, `output`, `settings`, `scenarios`.
- Optional keys: `variables`, `preinstall`.
- `scenarios` must contain at least 2 items.
- Each scenario must include: `label`, `surface`, `setup`, `actions`.
- `surface` must be exactly `terminal`.
- `actions` must be a non-empty list of action objects.
- Every action object must include at least one of: `type`, `sleep`, `wait_for`.
- If `sleep` or `wait_timeout` is used, duration format must be `<number>ms` or `<number>s` (example: `500ms`, `2s`).
- If `wait_mode` is used, allowed values are `default`, `screen`, `line`.
- Prefer `wait_mode: screen` for robust matching in rendered demos.
- `wait_mode` and `wait_timeout` are only allowed when `wait_for` is present.

Goal:
- Theme: marketing demo triage for an LLM agent asked to move quickly.
- Show contrast between weak instructions and strong instructions.
- Use realistic terminal commands/messages.
- Keep YAML concise and deterministic.

Output constraints:
- `output` slug: `agent_generated_triage`
- Include at least one `wait_for` action in scenario 2.
- Keep settings consistent with this repo defaults.
```

## 2) Narrative-to-Screenplay Converter
Use this when you already have a narrative and need valid YAML.

```text
Convert the narrative below into a valid screenplay YAML for this repo.

Return ONLY YAML.

Narrative:
[PASTE NARRATIVE]

Validation contract:
- Produce top-level keys: `title`, `output`, `settings`, `scenarios`.
- Keep `scenarios` length >= 2.
- Use scenario structure exactly:
  - `label`: string
  - `surface`: `terminal`
  - `setup`: list of shell commands (can be empty)
  - `actions`: list of action objects
- Action object rules:
  - Must include one or more of `type`, `sleep`, `wait_for`
  - `sleep` and `wait_timeout` must match `^\d+(ms|s)$`
  - `wait_mode` allowed values: `default`, `screen`, `line`
  - Prefer `wait_mode: screen` unless you explicitly need current-line semantics
  - Never include `wait_mode` or `wait_timeout` without `wait_for`

Quality requirements:
- Use deterministic command text.
- Include a clear before/after comparison.
- Include one explicit validation success line in scenario 2.
- No extra keys, no comments, no prose.

Set output slug to: [OUTPUT_SLUG]
Set title to: [TITLE]
```

## 3) Self-Repair Prompt for Invalid YAML
Use this when an agent produced invalid screenplay YAML and you want a fixed version.

```text
You are fixing invalid screenplay YAML for this repository.

Input YAML:
[PASTE YAML]

Known validation error(s):
[PASTE ERROR TEXT]

Task:
- Return a corrected YAML screenplay that preserves original intent.
- Return YAML only.

Must-pass rules:
- Keep required top-level keys: `title`, `output`, `settings`, `scenarios`.
- Ensure at least 2 scenarios.
- Ensure every scenario has non-empty `actions`.
- Ensure every action has one of `type`, `sleep`, `wait_for`.
- Enforce duration format `<number>ms|<number>s`.
- Enforce `wait_mode` in {`default`,`screen`,`line`}.
- Remove any fields not supported by this schema.

Before finalizing internally, run this checklist:
1. Scenarios >= 2
2. All actions valid
3. Wait fields consistent
4. YAML is syntactically valid
5. Output is only YAML text
```
