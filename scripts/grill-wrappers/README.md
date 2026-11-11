# grill-wrappers — custom grill skills that survive pack updates

## The problem

The `mattpocock/skills` pack (`npx skills@latest add mattpocock/skills`) installs
into `~/.agents/skills/` and clobbers any same-named skill. Two of our grill
skills are same-named customizations of pack skills:

| Skill | Upstream | What we add |
|-------|----------|-------------|
| `grill-me` | pack `grilling` | composes `/grill-harness` (adversarial expert panel from `~/.claude/agents/`, decision tables, `docs/grill-decisions/` record) |
| `grill-with-docs` | pack `grill-with-docs` | same, plus `/domain-modeling` for CONTEXT.md/ADR/glossary |

Every pack update reverts them to upstream versions, and the `/grill-harness`
enhancements silently stop firing — the upstream skills never mention the
harness, and description-matching is probabilistic when a skill is explicitly
invoked. Drift incident: 2026-11-11 (panel stopped assembling after the Oct 13
pack update; the old restore script also kept targeting the pack's OLD install
dir, `~/.claude/skills`).

## The fix

1. **Wrapper sources are versioned here** (`scripts/grill-wrappers/<name>/SKILL.md`).
   Git is the integrity mechanism — no separate checksum file.
2. **After every pack update, run:**

   ```bash
   ~/repos/agent-skills/scripts/refresh-grill-wrappers.sh
   ```

   It replaces the pack's `grill-me`/`grill-with-docs` in `~/.agents/skills/`
   with the wrapper copies (handling the pack's symlink layout) and verifies
   `/grill-harness` itself is deployed somewhere harnesses read.

3. **`/grill-harness` (the public enhancement skill)** lives in this repo as a
   proper plugin skill (`plugins/skill-extras/skills/grill-harness/`):
   - Claude Code gets it via the installed `skill-extras` plugin
     (`claude plugins update skill-extras@vvaldez-agent-skills` after repo changes).
   - OpenCode gets it via `deploy-local-skills.sh` (agent-rules repo), which
     copies it to `~/.config/opencode/skills/`.

## Wrapper SKILL.md convention

Keep them thin — name + trigger description + one instruction paragraph that
explicitly names the composed skills (`/grilling`, `/domain-modeling`,
`/grill-harness`). Explicit naming is the point: it makes composition
deterministic instead of relying on description matching.

Never reference plugin-qualified names (`/grilling-extras:...`) — plugin
layouts have changed before (ADR-001 moved `grilling-extras` into
`skill-extras`); bare skill names survive those moves.
