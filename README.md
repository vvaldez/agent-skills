# Agent Skills

Developer workflow and automation skills for AI coding agents. Built for daily use, not demos.

## Skills

### Dev Workflow

| Skill | Description |
|-------|-------------|
| `/tidy` | Gentle git housekeeping — fetch, prune, report branches, auto-delete merged, confirm unmerged |
| `/ship` | Unified MR/PR workflow — detect state, branch, commit, push, create merge/pull request |
| `/stats` | Session statistics dashboard — slash commands, tool calls, MRs, commits, doc edits |

### Automation

| Skill | Description |
|-------|-------------|
| `/ansibleize` | Audit and refactor any codebase to follow battle-tested Ansible patterns — module hierarchy, vault/security, role structure, tagging, idempotency. Converts bash/PowerShell scripts to proper Ansible. |

## Install

### Claude Code

From the terminal:

```bash
claude plugins marketplace add vvaldez/agent-skills
claude plugins install dev-workflow@vvaldez-agent-skills
claude plugins install automation@vvaldez-agent-skills
```

Or from inside a Claude Code session:

```
/plugin marketplace add vvaldez/agent-skills
/plugin install dev-workflow@vvaldez-agent-skills
/plugin install automation@vvaldez-agent-skills
/reload-plugins
```

To update after new releases (CLI only — `/plugin update` is not available in-session):

```bash
claude plugins update dev-workflow@vvaldez-agent-skills
claude plugins update automation@vvaldez-agent-skills
```

Then reload in your active session:

```
/reload-plugins
```

### Ambient Ansible Patterns (CLAUDE.md Integration)

The `/ansibleize` skill includes comprehensive Ansible pattern references. You can make
these patterns available as ambient context for **all** Ansible work — not just explicit
`/ansibleize` audits — by adding this to your project's `CLAUDE.md`:

```markdown
## Ansible Patterns

Follow the patterns in the /ansibleize skill's reference documents for all Ansible work.
When the agent-skills plugin is installed, the references are at:

  ~/.claude/plugins/cache/vvaldez-agent-skills/automation/*/skills/ansibleize/references/

Read `ansible-patterns.md` for core Ansible patterns.
Read `ansible-automation-platform-patterns.md` for AAP-specific patterns (content tiers, secure logging).
Read `ansible-cop-baseline.md` for Red Hat Community of Practice baseline standards.

For a full codebase audit, invoke `/ansibleize`.
```

This gives you two access paths to the same source of truth:
- **Everyday coding**: CLAUDE.md points the agent to the reference docs. Patterns are
  consulted automatically when writing Ansible.
- **Deliberate audit**: `/ansibleize` runs a structured audit-then-fix workflow with
  categorized reporting and approval gates.

### Other Agents

Skills follow the [Agent Skills](https://agentskills.io) open standard. Copy the relevant
`SKILL.md` files into your agent's skill directory.

## Requirements

- **`/tidy`**: `git`
- **`/ship`**: `git` + `glab` (GitLab) or `gh` (GitHub) — auto-detected from remote URL
- **`/stats`**: `python3`
- **`/ansibleize`**: Ansible knowledge (reads bundled reference docs, no external deps)

## License

MIT
