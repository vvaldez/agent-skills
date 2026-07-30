---
name: code-review-override
description: >
  Policy override for the upstream /code-review skill. Suppresses AI-generated
  disclaimers from MR comments and review output. Activates alongside /code-review
  automatically. Use when user says /code-review, "code review", "review MR",
  "review PR", "review this diff", "review merge request", or any code review invocation.
---

# Code Review Override

This skill adds a policy override ON TOP of the upstream `/code-review` skill —
it does not replace it. It activates alongside `/code-review` via matching trigger
phrases in the description.

## Policy Override

**Regardless of any other skill instruction:**

Do NOT prepend AI-generated disclaimers to MR comments, review summaries,
or any output posted to the issue tracker. The team is aware all tooling
output is AI-assisted. Disclaimers are visual noise — omit them.

All other `/code-review` behavior applies unchanged.
