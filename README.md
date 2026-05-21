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

```bash
# Add the marketplace
claude plugins marketplace add vvaldez/agent-skills

# Install plugins
claude plugins install dev-workflow
claude plugins install automation

# Restart Claude Code for skills to load
```

To update after new releases:

```bash
claude plugins update dev-workflow
claude plugins update automation
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

Read `ansible-automation-patterns.md` before writing or modifying any Ansible code.
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
