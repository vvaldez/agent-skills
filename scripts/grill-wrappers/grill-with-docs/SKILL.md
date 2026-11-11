---
name: grill-with-docs
description: Grilling session that challenges your plan against the existing domain model, sharpens terminology, and updates documentation (CONTEXT.md, ADRs) inline as decisions crystallise. Use when user wants to stress-test a plan against their project's language and documented decisions.
---

Run a `/grilling` session, using the `/domain-modeling` skill for the documentation side
(CONTEXT.md, ADRs, glossary), and applying the `/grill-harness` enhancements throughout:
assemble the adversarial expert panel from `~/.claude/agents/` before asking questions,
frame questions from the panelists' perspectives, use the enhanced CONTEXT.md format
(relationships, example dialogue, flagged ambiguities), and produce the structured
decision table and `docs/grill-decisions/` record at session end.
