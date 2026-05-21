# Development

How to develop, test, and publish skills in this repo.

## Repo Structure

```
agent-skills/
├── .claude-plugin/
│   └── marketplace.json          # Plugin manifest for Claude Code
├── plugins/
│   └── dev-workflow/
│       └── skills/
│           ├── tidy/
│           │   └── SKILL.md
│           ├── ship/
│           │   └── SKILL.md
│           └── stats/
│               ├── SKILL.md
│               └── scripts/
│                   └── stats.py
├── README.md
├── DEVELOPMENT.md
└── LICENSE
```

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

   ```
   claude plugins update
   ```

   This pulls the latest commit from GitHub into `~/.claude/plugins/cache/`.

### Adding a New Skill

1. Create the skill directory under `plugins/dev-workflow/skills/<skill-name>/`.
2. Write `SKILL.md` with YAML frontmatter (`name`, `description`).
3. Add bundled resources if needed (`scripts/`, `references/`, `assets/`).
4. Copy to `~/.claude/skills/` for local testing.
5. Once stable, delete local copy, commit, push, and run `claude plugins update`.

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
5. Once merged, users get the update on their next `claude plugins update`.

## How Users Get Updates

Users install once:

```
/install-plugin github:vvaldez/agent-skills
```

Claude Code caches the plugin locally and tracks the git commit SHA. When the user
runs `claude plugins update`, it pulls the latest commit. No manual file copying,
no symlinks — the plugin cache handles versioning.
