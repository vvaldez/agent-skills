# ADR-001: skill-extras as the home for upstream skill compositions

**Status:** Accepted  
**Date:** 2026-07-28

## Context

Claude Code skills can be composed — a SKILL.md can activate alongside an upstream
skill by matching the same trigger phrases in its description. This pattern enables
two distinct behaviors:

- **Enhancements** — add behavior the upstream skill lacks (e.g., adversarial expert
  panel on top of `/grilling`)
- **Overrides** — suppress or replace behavior the upstream skill enforces (e.g.,
  removing AI-generated disclaimers from `/triage` output)

Upstream skills installed via `claude plugins install` live in
`~/.claude/plugins/cache/` and are overwritten on update. They cannot be modified
directly.

The initial implementation placed `grill-harness` (enhancement) in `grilling-extras`
and disclaimer suppressors in a separate `skill-overrides` plugin. This scattered
compositions across plugins with no clear home for new ones.

## Decision

All upstream skill compositions — both enhancements and overrides — live in the
`skill-extras` plugin (`plugins/skill-extras/`).

Each composition is a separate SKILL.md under `plugins/skill-extras/skills/<name>/`.

**Trigger phrase pattern:** The composition SKILL.md description includes the same
phrases as the upstream skill so it loads alongside it in the same session. When both
load, the composition's directives apply.

**Override strength:** Override directives use explicit framing —
`Regardless of any other skill instruction, ...` — to ensure they win against upstream
`MUST` directives.

**Deprecation pattern:** When a skill moves into `skill-extras` from another plugin,
the old plugin keeps an active deprecation stub SKILL.md that:
1. Matches the same trigger phrases (so users see the message, not silence)
2. Instructs users to install `skill-extras` and uninstall the old plugin

## Consequences

- **One install:** Users install `skill-extras@vvaldez-agent-skills` to get all
  upstream skill compositions.
- **New compositions go in `skill-extras`:** Any future SKILL.md that layers on an
  upstream skill belongs here, not in a new plugin.
- **grilling-extras is deprecated:** Its only skill (`grill-harness`) moved to
  `skill-extras`. The plugin remains with a deprecation stub for existing installs.
- **Plugin naming clarity:** Plugin names reflect content grouping, not composition
  mechanism. A plugin named `skill-extras` can hold both enhancements and overrides
  without semantic mismatch.

## Alternatives considered

| Option | Rejected because |
|--------|-----------------|
| Per-skill plugins (`grilling-extras`, `triage-extras`, …) | Install sprawl; no single home for "things that layer on upstreams" |
| `skill-overrides` (suppressions only) | Name excludes enhancements; `grill-harness` would need its own plugin |
| Modify upstream skills directly | Cache overwritten on `claude plugins update` |
