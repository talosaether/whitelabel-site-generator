# 14. Merge commits only, and a ruleset that makes auto-merge wait

Status: accepted

Builds on [ADR-0010](0010-two-hosts.md) and [ADR-0013](0013-owner-assistant-account.md).

## Context

The owner's assistant publishes by committing the dev tree, pushing a `hermes/<timestamp>`
branch, opening a pull request and arming auto-merge, so that the merge waits for `check`.
Two things have to be true for that sentence to hold, and neither is in the code.

GitHub's auto-merge waits only for *required* checks. A repository with "Allow auto-merge"
on but no rule requiring `check` on `main` gives it nothing to wait for: arming a pull
request whose checks are still running fails, and arming one whose checks have finished
merges immediately. The first site built from this scaffold ran that way for a day; the
assistant's pull request sat green and unmerged until a person noticed.

And the dev tree's `main` is ahead of GitHub by the commits it just made. A merge commit
keeps them as ancestors, so the next `git pull --rebase --autostash` brings the tree back
in line. A squash rewrites them, the tree diverges, and every later pull conflicts. That
rule lived in a comment and a handoff note, which is not enough to stop a merge button.

## Decision

- **A ruleset on `main`**, `require_pr_workflow`: restrict deletions, block force pushes,
  require the status check `check` from GitHub Actions, strict mode off, no bypass
  actors. It is what auto-merge waits for. DEPLOY.md records how to create and verify it.
- **Merge commits only.** Squash and rebase merging are disabled at the repository level,
  so no button and no `gh pr merge --squash` can rewrite the assistant's commits.
- **The ship script reports when arming fails** instead of silencing it. The owner hears
  "waiting for someone to merge it" and tells the developer, whose first check is the
  ruleset.
- **The gate job keeps the id `check` with no `name:` override.** The ruleset is bound to
  that string; a test asserts it, and that the ship script arms with `--merge`.

## Consequences

- Direct pushes to `main` are refused for everyone. Every change is a pull request, which
  is how the developer's assistant works too; its pull requests are the developer's to
  arm or merge, since it cannot arm them unattended.
- History on `main` carries a merge commit per pull request. The pull request number is
  in the merge commit's subject rather than appended to a squashed one.
- Renaming the gate job breaks shipping in a way that looks like a slow merge. The test
  fails first.
- The dev tree still needs something to pull `main` into it between ships; the ship
  script pulls only when it runs. That is a separate decision (see the open questions).
