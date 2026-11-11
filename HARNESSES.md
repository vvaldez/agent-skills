# Harness Support Matrix

All skills in this repo target **Claude Code and OpenCode first** (the
supported pair). Codex CLI and Cursor Agent are **deployment-supported
with documented degradation**: the skills install and load, but some
capabilities a skill relies on do not exist in those harnesses. This
file records what each harness provides and what each skill does about
it.

Last verified against vendor docs: 2026-11-11
([Codex skills](https://developers.openai.com/codex/skills/),
[Cursor skills](https://cursor.com/docs/skills)).

## Deployment

| Harness | Loads from | Deployed by |
|---------|-----------|-------------|
| Claude Code | plugin marketplace cache (`claude plugins update`) | marketplace |
| OpenCode | `~/.config/opencode/skills/` + `~/.agents/skills/` + `~/.claude/skills/` | `deploy-local-skills.sh` (agent-rules) |
| Codex CLI | `~/.agents/skills/` (USER scope) + `<repo>/.agents/skills/` | `deploy-local-skills.sh` — same run, dual target |
| Cursor Agent | `~/.agents/skills/` + `~/.cursor/skills/` (+ compat dirs `~/.claude/skills/`, `~/.codex/skills/`) | `deploy-local-skills.sh` — same run, dual target |

`~/.agents/skills/` is the **shared, harness-independent location**: one
deploy run covers OpenCode, Codex, and Cursor. The OpenCode-specific
directory is kept because OpenCode reads it first and it predates the
shared location.

## Harness capabilities

| Capability | Claude Code | OpenCode | Codex CLI | Cursor Agent |
|---|---|---|---|---|
| Skill discovery | plugin cache | 3 dirs (see above) | `~/.agents/skills` (USER) | `~/.agents/skills` (USER) |
| Explicit invocation | `/skill-name` | `/skill-name` (`opencode/slash` metadata) | `$skill-name` / `/skills` | `/skill-name` in chat |
| Implicit (description-match) invocation | yes | yes | yes (budget-capped, shortens descriptions) | yes (`disable-model-invocation: true` opts out) |
| Structured question tool | `AskUserQuestion` | `question` | **Plan mode only** — none in Act mode | ask-questions tool |
| Subagents | Task tool (`subagent_type`) | `subagent` tool (`agent` param) | **none** | yes (custom subagents) |
| Read image files | yes | yes | unverified | yes |
| Frontmatter requirements | `name`, `description` | `name`, `description` | `name`, `description` | `name` (must equal folder name), `description` |
| `metadata:` passthrough | unknown keys tolerated | `opencode/slash` honored | tolerated | preserved as arbitrary mapping |

## Per-skill degradation matrix

Legend: **full** = no degradation · **degrades** = works with a named
fallback · **n/a** = the skill has no data source in that harness.

| Skill | Claude Code | OpenCode | Codex CLI | Cursor |
|---|---|---|---|---|
| drain | full | full | full | full |
| tidy | full | full | full | full |
| issue-to-spec | full | full | degrades: question tool is Plan-mode-only — Act-mode grilling falls back to numbered markdown lists (the skill's documented fallback) | full |
| spec-to-mr | full | full | degrades: no subagent tool — dual-blind review falls back to a single-pass inline review; VM verification unaffected (plain ssh) | full |
| mr-followthrough | full | full | degrades: same review fallback as spec-to-mr | full |
| ship | full | full | full (gh/glab are plain CLIs) | full |
| stats | full | full | n/a: no Codex transcript/store reader — the script errors with a clear message | n/a: no Cursor session-store reader — same clear error |
| local-review | full | full | full (invokes the local runner via bash; the runner itself drives opencode) | full |
| ansibleize | full | full | full (references read with file tools) | full |
| red-hat-quick-diagram | full | full | degrades: no subagent tool — the single-long-lived-subagent loop runs inline on the main thread; image read unverified | full |
| handoff-issue | full | full | full (gh CLI) | full |
| code-review-override | full | full | full (composes with the pack's code-review skill in `~/.agents/skills`) | full |
| triage-override | full | full | full | full |
| grill-harness | full | full | degrades: expert panel works (persona files are read from disk), question tool Plan-mode-only → numbered-list fallback in Act mode | full |

## Skill-count and collision safety

`~/.agents/skills/` also holds the mattpocock pack (its install dir
since 2026-10-13) and may hold **shared-skills installer symlinks** —
the team shared-skills install links some of these same skills (today:
`drain`, `tidy`, `ship`, `mr-followthrough`) into `~/.agents/skills/`.
Two protections in `deploy-local-skills.sh` keep both safe:

- **Collision guard**: a target skill dir whose `SKILL.md` matches
  neither the current render nor has a `.bak` sibling (nor carries the
  `opencode/slash` provenance marker every deployed skill has) is
  foreign — the script reports it and aborts before writing anything to
  that target. Pack skills are never clobbered.
- **Symlink skip**: a skill dir that is itself a symlink is managed
  elsewhere (shared-skills install) — the local render is not deployed
  over it; the skill is skipped with a loud warning and the team copy
  stays canonical for that directory. `scripts/refresh-grill-wrappers.sh`
  restores the two custom grill wrappers after pack updates.

### OpenCode double-registration (tested, not assumed)

A skill present in BOTH OpenCode load paths (`~/.config/opencode/skills/`
and `~/.agents/skills/`) registers **exactly once**: OpenCode keys skills
by folder name (`Skill.ID` derived from the skill directory name) and
deduplicates across sources in a single map
(`packages/core/src/config/plugin/skill.ts`, `refresh()`; ID derivation in
`config/plugin/skill-file.ts`). Session evidence agrees: with skills live
in both dirs, each skill appeared once in the harness skill list. Keeping
both directories populated is therefore safe — no canonical-location
workaround needed.

## Smoke checklist (user-performed, after deploy)

Not a merge gate — run after `deploy-local-skills.sh` reports both
targets:

- [ ] **Codex CLI**: restart Codex; run `/skills` and confirm the 14
  skills appear; invoke one explicitly (e.g. `$tidy`) and confirm the
  instructions load.
- [ ] **Cursor**: open Customize → Skills and confirm the 14 appear
  alongside pack skills; `/`-invoke one and confirm it attaches.
- [ ] **OpenCode**: start a session in any directory; confirm no skill
  is listed twice (OpenCode dedupes by skill folder name across load
  paths — verified in source and live; see the double-registration note
  above).
- [ ] **Claude Code**: unaffected (plugin cache path); no action.
