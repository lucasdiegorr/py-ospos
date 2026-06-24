# Napkin Runbook

## Curation Rules
- Re-prioritize on every read.
- Keep recurring, high-value notes only.
- Max 10 items per category.
- Each item includes date + "Do instead".

## User Directives (Highest Priority)

1. **[2026-06-24] PRs MUST be created automatically via `gh pr create`**
   Do instead: After push, always run `gh pr create --repo lucasdiegorr/py-ospos --base master --head <owner>:<branch-name>` without asking user.

2. **[2026-06-24] Baby steps commits - never bundle features**
   Do instead: Make 1-3 focused commits per feature. Never commit 30+ files at once. Target 5-10 small commits per PR, not 1 mega commit.

3. **[2026-06-24] Never ask user to create PRs manually**
   Do instead: Create PRs automatically as part of workflow. Use `gh pr create` command.

4. **[2026-06-24] Cleanup after PR merge**
   Do instead: Delete feature branch, checkout master, pull upstream. Never leave stale branches.

## Execution & Validation

1. **[2026-06-24] Verify before commit**
   Do instead: Run `git status` before committing to ensure correct files are staged.

2. **[2026-06-24] Use `--repo` flag with gh pr create**
   Do instead: Always use `--repo lucasdiegorr/py-ospos` when creating PRs to avoid authentication issues.

## Domain Behavior Guardrails

1. **[2026-06-24] Commit message format: type(scope): description**
   Do instead: Follow Conventional Commits. Example: `feat(quotation): add quotation model`

2. **[2026-06-24] Always push to origin after creating branch**
   Do instead: Run `git push -u origin <branch-name>` immediately after `git checkout -b`

## Workflow Reminders

1. **[2026-06-24] Create PR immediately after push**
   Do instead: Run `gh pr create` right after successful push, before any other work.

2. **[2026-06-24] Document directives in napkin for future sessions**
   Do instead: Add important user directives to this napkin file so they persist across sessions.