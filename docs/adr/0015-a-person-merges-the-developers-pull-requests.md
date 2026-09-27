# 15. A person merges the developer's assistant's pull requests, and the repository says so

Status: accepted

Builds on [ADR-0013](0013-owner-assistant-account.md) and
[ADR-0014](0014-merge-commits-and-a-required-check.md).

## Context

Two assistants change this repository. The owner's assistant ships through one script,
`/ship`, which opens a pull request and arms auto-merge; it runs as an unprivileged account
with a token that can do exactly that, and the ruleset makes the merge wait for `check`.

The developer's assistant is a Claude Code session with a broader remit and a token that
can push branches, open pull requests and edit the workflow. On both first installations
it was refused `gh pr merge --auto` by the session's own review of the command, as a
merge without review, and spent a turn rediscovering that before handing the merge to the
developer at the bottom of a long message. Nothing in the repository said whose the merge
was. Nothing declared the other commands that are never right in a shared tree either:
`git add -A`, a force push, `docker compose down -v`, a push straight to `main`.

The first site's own repository already carried a `.claude/settings.json` that denied
`gh pr merge` and force pushes and allowed `git push` and `gh pr create`. The scaffold did
not, so the second site ran with no declared rules at all.

## Decision

- **The developer's assistant opens pull requests; the developer merges them.** The
  assistant's message that reports a pull request puts the merge command first
  (`gh pr merge <n> --merge`), then what the change is. It never arms auto-merge; `/ship`
  is the only thing that does, and only for the owner's changes.
- **The boundary is data in the repository:** `.claude/settings.json` allows the branch,
  push, pull-request and issue commands the assistant needs and denies `gh pr merge`,
  force pushes, pushes to `main`, `git add -A` and `git add .`, `gh repo edit` and
  `gh repo delete`, and `docker compose down -v`. A new instance inherits it with the
  clone. It is prefix matching on the command, a declared rule rather than a guard; the
  ruleset and the ACLs are the guards.
- **After a merge, the assistant follows up itself:** `git pull --rebase --autostash` in
  the shared tree, then the deploy watched with `gh run list`, `gh run watch` and
  `gh run view`, never `gh pr checks`, which the narrow token cannot use.
- **AGENTS.md carries the rule in one bullet**, and `docs/PLAYBOOK.md` the reasoning and
  the exceptions around it.

## Consequences

- Every developer change waits for a person. On the first two sites that person was in the
  conversation already, so the wait was a message; that is the intended cost.
- A session that needs `gh pr merge` for a legitimate reason (closing a Dependabot pull
  request after migrating it) asks, and the developer runs it.
- The settings file applies to whoever opens the repository with Claude Code, including a
  future maintainer; widening it is a pull request like any other, and the reason goes in
  the description.
- The developer's token stays without administration, because nothing the assistant is
  now expected to do needs it. When a command returns 403, the playbook's answer applies:
  name the setting, name who can change it, move on.
