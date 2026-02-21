# Showcase Gallery

Curated demos used in the README gallery. Every GIF and MP4 is generated from a YAML screenplay and is fully reproducible.

Regenerate all assets:

```bash
./scripts/render_showcase_media.sh
```

## Scripted style set

Pixel-perfect renders across six terminal themes, each with a unique font, color scheme, and workflow pattern.

| Demo | Lane | Theme / Font | MP4 | GIF | Source |
| --- | --- | --- | --- | --- | --- |
| Onboarding Neon | scripted_vhs | TokyoNightStorm / Menlo | `docs/media/onboarding_tokyo_neon.mp4` | `docs/media/onboarding_tokyo_neon.gif` | `examples/showcase/onboarding_tokyo_neon.yaml` |
| Bugfix Glow | scripted_vhs | Catppuccin Mocha / Monaco | `docs/media/bugfix_catppuccin_glow.mp4` | `docs/media/bugfix_catppuccin_glow.gif` | `examples/showcase/bugfix_catppuccin_glow.yaml` |
| Recovery Retro | scripted_vhs | GruvboxDark / Courier New | `docs/media/recovery_gruvbox_retro.mp4` | `docs/media/recovery_gruvbox_retro.gif` | `examples/showcase/recovery_gruvbox_retro.yaml` |
| Policy Guard | scripted_vhs | Nord / SF Mono | `docs/media/policy_nord_guard.mp4` | `docs/media/policy_nord_guard.gif` | `examples/showcase/policy_nord_guard.yaml` |
| Menu Contrast | scripted_vhs | Dracula / Courier | `docs/media/menu_dracula_contrast.mp4` | `docs/media/menu_dracula_contrast.gif` | `examples/showcase/menu_dracula_contrast.yaml` |
| Nightshift Speedrun | scripted_vhs | TokyoNightStorm / Monaco | `docs/media/speedrun_nightshift.mp4` | `docs/media/speedrun_nightshift.gif` | `examples/showcase/speedrun_nightshift.yaml` |

## Autonomous visual set

Real TUI captures using the visual execution lane with Kitty terminal, Xvfb, and FFmpeg.

| Demo | Lane | MP4 | GIF | Source |
| --- | --- | --- | --- | --- |
| Autonomous Codex Real TUI | autonomous_video | `docs/media/autonomous_codex_real_short.mp4` | `docs/media/autonomous_codex_real_short.gif` | `examples/showcase/autonomous_codex_real_short.yaml` |
| Autonomous Claude Code Real TUI | autonomous_video | `docs/media/autonomous_claude_real_short.mp4` | `docs/media/autonomous_claude_real_short.gif` | `examples/showcase/autonomous_claude_real_short.yaml` |

## Starter patterns

Ready-to-use mock examples that demonstrate common demo patterns. Great for learning and as templates.

| Demo | Pattern | GIF | Source |
| --- | --- | --- | --- |
| Install First Command | Quickstart onboarding | `docs/media/install_first_command.gif` | `examples/mock/install_first_command.yaml` |
| Before & After Bugfix | Two-scene comparison | `docs/media/before_after_bugfix.gif` | `examples/mock/before_after_bugfix.yaml` |
| Error Then Fix | Error diagnosis flow | `docs/media/error_then_fix.gif` | `examples/mock/error_then_fix.yaml` |
| Interactive Menu | TUI menu navigation | `docs/media/interactive_menu_showcase.gif` | `examples/mock/interactive_menu_showcase.yaml` |
| Policy Warning Gate | Safety policy enforcement | `docs/media/policy_warning_gate.gif` | `examples/mock/policy_warning_gate.yaml` |
| Speedrun Cuts | Rapid CI pipeline | `docs/media/speedrun_cuts.gif` | `examples/mock/speedrun_cuts.yaml` |

## Production screenplays

Complete workflow demos in `screenplays/` covering developer workflows, safety enforcement, and agent integration patterns.

| Demo | Theme | Description |
| --- | --- | --- |
| Developer Bugfix Workflow | TokyoNightStorm | Regression in `add()`, tests fail, fix applied, tests pass |
| Drift Protection | TokyoNightStorm | Unsafe tool execution vs. lockfile-guarded safe mode |
| Single Prompt macOS | TokyoNightStorm | Log triage with macOS-style prompt and error pattern display |
| Rust CLI Safety Guard | Catppuccin Mocha | Unguarded deletion vs. policy-checked execution |
| Feature Flag Bugfix | Nord | Checkout flag misconfigured, tests fail, reconfigure, pass |
| Agent Safety Policy Guard | Catppuccin Mocha | Raw PII export blocked, routed to secure vault |
| Release Compliance | GruvboxDark | Lockfile, security scan, changelog, approver signoff |
| Agent Triage | Catppuccin Mocha | Unguided output fails validation vs. guided output passes |

## Media inventory

**14 GIFs** and **8 MP4s** in `docs/media/`:

```
docs/media/
  autonomous_claude_real_short.gif    (364 KB)
  autonomous_claude_real_short.mp4    (126 KB)
  autonomous_codex_real_short.gif     (186 KB)
  autonomous_codex_real_short.mp4     (64 KB)
  before_after_bugfix.gif             (368 KB)
  bugfix_catppuccin_glow.gif          (368 KB)
  bugfix_catppuccin_glow.mp4          (82 KB)
  error_then_fix.gif                  (401 KB)
  install_first_command.gif           (798 KB)
  interactive_menu_showcase.gif       (636 KB)
  menu_dracula_contrast.gif           (835 KB)
  menu_dracula_contrast.mp4           (131 KB)
  onboarding_tokyo_neon.gif           (838 KB)
  onboarding_tokyo_neon.mp4           (217 KB)
  policy_nord_guard.gif               (261 KB)
  policy_nord_guard.mp4               (54 KB)
  policy_warning_gate.gif             (602 KB)
  recovery_gruvbox_retro.gif          (135 KB)
  recovery_gruvbox_retro.mp4          (31 KB)
  speedrun_cuts.gif                   (126 KB)
  speedrun_nightshift.gif             (102 KB)
  speedrun_nightshift.mp4             (21 KB)
```
