# py-ospos — Workflow Guide

POS/ERP for a small beverage warehouse. Stack: **FastAPI + React/TS + PostgreSQL**, offline-first (outbox + reconciliation), 11 capabilities defined in `openspec/`.

**All documentation, code, comments, and agent-facing instructions in this repository are written in English.**

## Rule #1 — never work on master/main

**Never edit, commit, or push to `master`/`main`.** All work happens on a **feature branch created from `master`** and is integrated **only via a Pull Request that a human reviews and merges**.

The hook in `.claude/settings.local.json` **blocks** (deny) `Write`/`Edit` and `git commit`/`git push` while the current branch is `master`/`main`.

## Standard flow (agent → branch → PR → review)

1. **Create a branch** from `master` (always, before editing code):
   ```bash
   git checkout -b feat/<work-slug> master
   ```
   For isolated parallel work, use a **worktree**:
   ```bash
   git worktree add ../feat-<slug> -b feat/<slug> master
   ```
2. **Implement** and **commit** on the branch. Commit messages follow **Conventional Commits**:
   ```
   feat(scope): description    # new capability
   fix(scope): description     # bug fix
   chore(scope): description   # infra/setup
   docs(scope): description    # documentation
   test(scope): description    # tests
   ```
3. **Publish the branch** and **open a PR** to `master`, **no auto-merge**:
   ```bash
   git push -u origin <branch>
   gh pr create --base master --head <branch> --title "..." --body "..."
   gh pr view --web
   ```
4. **Stop and wait for the user to review** the PR. Do not merge on your own; report the PR URL and await approval.

## Secrets — never commit them

- **NEVER** include secrets, tokens, keys, passwords, credentials, real environment values, or PII in commits.
- **Never** add agent co-authors (Claude, OpenCode, etc.) to commits — **no agent co-author is allowed** in this project.
- `gitleaks` runs in `pre-commit` and as a session hook; any secret detection **blocks the commit**.
- Secrets go in `.env` (untracked) and environment variables; use env vars for API/JWT/DB keys.
- Files with secrets are **never** staged; when in doubt, don't commit.

## Required setup

- `pre-commit` hooks installed (`pre-commit install` + `pre-commit install --hook-type pre-push`).
- Git hooks and secret scans are triggered automatically by `.claude/settings.local.json`.
