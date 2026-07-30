---
name: grill-harness
description: >
  Adversarial grilling harness that extends upstream /grilling with an expert panel,
  structured decision output, and enhanced CONTEXT.md format. Scans ~/.claude/agents/
  for available expert personas and assembles a challenge panel. Composes with /grilling,
  /grill-with-docs, /grill-me, and /wayfinder sessions that invoke grilling.
  Use when user says /grill-harness, /grilling, /grill-with-docs, /grill-me,
  "grill with experts", "adversarial review", "challenge this with a panel",
  or wants structured decision tables from grilling.
---

# Grill Harness

Extends upstream `/grilling` with an adversarial expert panel, structured decision output,
and enhanced documentation format. Works standalone or composed with `/grill-with-docs`
and `/domain-modeling`.

This skill adds behavior ON TOP of `/grilling` — it does not replace it. It activates
alongside any grilling skill (`/grilling`, `/grill-with-docs`, `/grill-me`) via matching
trigger phrases in the description. When both this skill and an upstream grilling skill
load, apply the harness enhancements (panel, decisions, enhanced format) to the upstream
session.

## Step 1: Assemble the Adversarial Panel

Before asking any questions, scan `~/.claude/agents/` to discover available expert personas.

```bash
ls ~/.claude/agents/*.md 2>/dev/null
```

If agents are found, read the filenames and select 3-5 agents whose expertise is most
relevant to the topic being grilled. These become the **adversarial panel** — each question
should be framed from the perspective of one of these experts.

**Recommended panel composition** (if matching agents are found):
- **An appropriate security persona** (e.g., Security Architect, AppSec Engineer, SecOps Engineer) — threat model, attack surface, credential exposure, trust boundaries
- **A code review persona** (e.g., Code Reviewer, Minimal Change Engineer) — correctness, conventions, shell safety, test coverage gaps
- Plus 1-3 topic-relevant experts (SRE, DevOps, Architect, etc.)

Select the most relevant agent file by reading its description, not just its filename.

**If no agents are found in `~/.claude/agents/`:**
Skip the adversarial panel and inform the user:

> No agent personas found in `~/.claude/agents/`. The adversarial panel adds significant
> value to grilling sessions by challenging decisions from multiple expert perspectives.
> Consider installing agent personas from [agency-agents](https://github.com/msitarzewski/agency-agents)
> or creating your own.

Proceed with the grilling session without the panel — all other harness features still apply.

**Announce the panel** at the start of the session, using the actual agent names selected:

> **Panel assembled for this grilling:**
> - **Security Architect** — threat model, attack surface, secrets handling
> - **Minimal Change Engineer** — scope creep, unnecessary abstractions
> - **SRE** — reliability, failure modes, operational burden

When asking questions, prefix each with the actual agent name driving it:
`**[Security Architect]** How are you protecting...`

Different experts may challenge the same decision from different angles — that's the point.

## Step 2: Interview Style

In addition to the base `/grilling` behavior:

- **One question at a time.** Never dump multiple questions.
- **Prefer AskUserQuestion with selectable options.** Put recommended choice first with
  "(Recommended)" suffix. Use the `description` field for tradeoffs. If AskUserQuestion
  is not available, fall back to a numbered markdown list.
- **Challenge vague answers.** "It depends" → "On what? Enumerate the cases."
- **Acknowledge good decisions fast.** Don't grill for the sake of grilling.
- **Expose hidden dependencies.** "You said A, but earlier we decided B. Those conflict."
- **Be direct about risks.** "This will break when Y. Are you OK with that?"
- **Explore the codebase before asking.** If a question can be answered by reading code,
  read the code instead.
- Don't present false choices — if one answer is clearly right, say so.
- Don't rehash decided items — check memory and plan files first.
- Don't let minor decisions drag — recommend and move on unless objected.

## Decision Output Format

When the grilling session is complete and all decisions are locked:

### 1. Display the decision table in the conversation

```markdown
| # | Decision | Options Considered | Chosen | Rationale | Reversible? |
|---|----------|--------------------|--------|-----------|-------------|
| 1 | ... | A, B, C | A | ... | Yes |
```

### 2. Write a decision record

Filename: `grill-decisions-YYYYMMDD.md` (using today's date).
If the file exists (multiple sessions same day), append with a section divider.

```markdown
# Grill Decisions — YYYYMMDD

## Topic

[One-sentence summary of the plan being grilled]

## Panel

- [Expert 1] — [angle]
- [Expert 2] — [angle]

## Decisions

| # | Decision | Options Considered | Chosen | Rationale | Reversible? |
|---|----------|--------------------|--------|-----------|-------------|
| 1 | ... | A, B, C | A | ... | Yes |

## Context

- Grilled on: YYYY-MM-DD
- Triggered by: [the original request]
```

This file is a local working artifact, not committed to git.

## Enhanced CONTEXT.md Format

When used alongside `/domain-modeling` or `/grill-with-docs`, extend the base CONTEXT.md
format with these additional sections:

**Relationships** — Express relationships between domain terms with cardinality:
```markdown
## Relationships

- An **Order** produces one or more **Invoices**
- An **Invoice** belongs to exactly one **Customer**
```

**Example dialogue** — A conversation demonstrating how terms interact:
```markdown
## Example dialogue

> **Dev:** "When a **Customer** places an **Order**, do we create the **Invoice** immediately?"
> **Domain expert:** "No — an **Invoice** is only generated once a **Fulfillment** is confirmed."
```

**Flagged ambiguities** — Terms used ambiguously, with resolutions:
```markdown
## Flagged ambiguities

- "account" was used to mean both **Customer** and **User** — resolved: distinct concepts.
```

## Composing with Other Skills

This harness composes with upstream skills — it extends, never replaces:

| Composition | What happens |
|-------------|-------------|
| `/grill-harness` alone | Runs `/grilling` with adversarial panel + decision output |
| `/grill-with-docs` | Auto-chains — harness activates alongside, adds panel + decisions |
| `/grill-me` | Auto-chains — harness activates alongside, adds panel + decisions |
| `/grilling` | Auto-chains — harness activates alongside, adds panel + decisions |
| `/wayfinder` → `/grilling` | Panel + decisions apply when wayfinder invokes grilling |
| Any grilling + `/domain-modeling` | Panel challenges domain terms; enhanced CONTEXT.md format used |
