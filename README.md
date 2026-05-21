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

```
/install-plugin github:vvaldez/agent-skills
```

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
