# Operating agreement (human ↔ assistant)

This project uses the following defaults so instructions do not need to be repeated in chat.

## 1. Prefer execution over delegation

When something can be done **in this environment** (run commands, edit files, run tests, apply migrations on a local DB, verify with tooling), the assistant should **do it** rather than only telling the human what to run.

## 2. Low-risk: do it, then say what you did

For **low-risk** work, the assistant should **perform the action** and then **briefly report** the outcome (what ran, what changed, where).

Examples: run tests, run linters/formatters, `alembic upgrade` on a local database, small targeted edits the user already asked for, read-only inspection, creating/updating docs the user requested.

## 3. Higher-risk: ask first (yes / no)

For **higher-risk** or **irreversible** actions, the assistant should **describe the plan** and **ask for confirmation** (yes/no) before proceeding.

Examples: changing production or shared infrastructure, destructive deletes, anything involving secrets or credentials, installs that affect the whole machine, operations that cost money or are hard to undo.

If unsure whether something is low- vs higher-risk, **ask once** instead of guessing.

## 4. Communication

- It is **fine** to explain context, tradeoffs, or what a doc means — explanations do not replace doing the work when (1) and (2) apply.
- Avoid ending with long “homework lists” for the human when the assistant can safely execute the steps under (1)–(2).

---

*Additions or exceptions can be noted here or in Cursor project rules.*
