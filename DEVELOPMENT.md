# Development

How to develop, test, and publish skills in this repo.

## Repo Structure

```
agent-skills/
├── .claude-plugin/
│   └── marketplace.json          # Plugin manifest for Claude Code
├── decisions/                    # Architecture Decision Records
│   └── ADR-001-skill-extras-plugin.md
├── plugins/
│   ├── dev-workflow/             # Git workflow tools (tidy, ship, stats)
│   ├── automation/               # Ansible patterns (ansibleize)
│   ├── skill-extras/             # Upstream skill compositions (grill-harness, overrides)
│   ├── diagrams/                 # Red Hat branded diagram generation
│   └── handoff-extras/           # Session handoffs as GitHub issues
├── README.md
├── DEVELOPMENT.md
└── LICENSE
```

### Architecture decisions

Significant design choices are recorded in `decisions/ADR-NNN-*.md`. Read these before
adding a new plugin or skill that layers on upstream skills — the conventions are
non-obvious without context.

## Development Workflow

### Creating or Editing a Skill

1. **Edit in this repo** — all skill source lives here, not in `~/.claude/skills/`.

2. **Copy to local skills for testing** — while iterating on a skill, copy it to the
   local skills directory so Claude Code picks it up immediately:

   ```bash
   cp -r plugins/dev-workflow/skills/stats ~/.claude/skills/stats
   ```

3. **Test the skill** — invoke it in a Claude Code session (`/stats`, `/tidy`, `/ship`).
   Verify the behavior matches expectations.

4. **Delete the local copy** — once the skill works:

   ```bash
   rm -rf ~/.claude/skills/stats
   ```

5. **Commit and push** — standard git workflow. Use conventional commits:

   ```
   feat(stats): add --global flag for cross-project aggregation
   fix(ship): handle gh CLI auth failure gracefully
   ```

6. **Update your installed plugin** — after pushing, refresh the cached plugin:

   ```bash
   claude plugins update dev-workflow@vvaldez-agent-skills
   claude plugins update automation@vvaldez-agent-skills
   ```

   Then reload in your active session (no restart needed):

   ```
   /reload-plugins
   ```

   This pulls the latest commit from GitHub into `~/.claude/plugins/cache/`.

### Adding a New Skill

1. Create the skill directory under the appropriate plugin:
   - `plugins/dev-workflow/skills/<skill-name>/` — git workflows, session tools
   - `plugins/automation/skills/<skill-name>/` — infrastructure, Ansible, scripting
2. Write `SKILL.md` with YAML frontmatter (`name`, `description`).
3. Add bundled resources if needed (`scripts/`, `references/`, `assets/`).
4. Copy to `~/.claude/skills/` for local testing.
5. Once stable, delete local copy, commit, push, and update:
   ```bash
   claude plugins update <plugin-name>@vvaldez-agent-skills
   /reload-plugins
   ```

### Adding a New Plugin

If a skill doesn't fit `dev-workflow` (e.g., an Ansible-specific tool), add a new
plugin entry to `.claude-plugin/marketplace.json`:

```json
{
  "name": "automation",
  "description": "Ansible automation skills.",
  "source": "./plugins/automation",
  "category": "development"
}
```

Then create `plugins/automation/skills/<skill-name>/SKILL.md`.

## For Contributors

1. Fork the repo.
2. Create a branch: `feat/skill-name` or `fix/skill-name`.
3. Follow the development workflow above.
4. Submit a pull request with a description of what the skill does and how to test it.
5. Once merged, users get the update via `claude plugins update <plugin>@vvaldez-agent-skills`.

## How Users Get Updates

Users install once:

```bash
claude plugins marketplace add vvaldez/agent-skills
claude plugins install dev-workflow@vvaldez-agent-skills
claude plugins install automation@vvaldez-agent-skills
/reload-plugins
```

Claude Code caches the plugin locally at `~/.claude/plugins/cache/vvaldez-agent-skills/`
and tracks the git commit SHA. When the user runs
`claude plugins update <plugin>@vvaldez-agent-skills` followed by `/reload-plugins`,
it pulls the latest commit and hot-reloads without restarting.
