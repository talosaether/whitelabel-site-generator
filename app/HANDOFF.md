# Handoff

Two assistants share this working tree, and the tree is the live development site at
<https://dev.example.com>. `git status` and `git diff` show *what* has changed;
this file is for *why*, and for questions passed between us. Newest entry first. Keep
entries to a few lines. Delete entries once they are no longer useful.

## Who does what

| | Claude Code (root) | Hermes (`hermes`) |
| --- | --- | --- |
| Talks to | the developer | the site owner, over Telegram |
| Edits | anything | `app/` and `frontend/` — copy, the `SITE` block, services, palette, logo |
| Cannot write | — | `compose*.yaml`, `Dockerfile`, `.github/`, `tests/`, `scripts/`, the docs |
| Ships by | pushing to `main`, or a PR | a PR that auto-merges when `check` is green |
| GitHub token | fine-grained, this repo, no admin | fine-grained, this repo, contents + pull requests only |

## How Hermes ships a change

Everything in the tree is already live on the dev site, so the owner sees an edit the
moment it is saved. Publishing is the owner's `/ship`, which runs
`.hermes/skills/ship/scripts/ship.sh`: it stages **everything under `app/` and
`frontend/`**, commits, pushes a `hermes/<timestamp>` branch, opens a PR and arms
auto-merge. The PR runs the full `check` job and merges itself only if that passes; a
merge to `main` deploys to production within about three minutes.

Consequences for the other assistant: anything of yours left uncommitted under `app/` or
`frontend/` goes out with the owner's next `/ship`. Keep infrastructure work out of those
directories or commit it promptly.

**Merge commits, not squash.** The local `main` in this tree is ahead of GitHub by the
commits just made; a merge commit keeps those commits as ancestors, so `git pull --rebase
--autostash` brings the tree back in line without conflicts. A squash would rewrite them.

The assistant's skills live in `.hermes/skills/` (`site`, `todo`, `recent`, `ship`). They
are in the repo on purpose: the developer can read and change how the assistant works,
and the assistant cannot change the skills (`.hermes/` is outside its writable directories).

**The to-do list is GitHub issues.** `/todo add (dev) …` opens an issue labelled `dev`;
that label is how the assistant dispatches work to the developer, and the developer
checks `gh issue list --label dev` when starting. The assistant writes the title and the
body and can `edit` or `note` an issue later, so read the body, not just the title.
Files the owner sends land in `app/inbox/` (not part of the image), referenced from the
issue.

## Entries

- (date) · Claude · White-label scaffold. Placeholder copy throughout; the branding pass
  is Hermes's to start. `docs/open-questions.md` lists every placeholder. Photos go through
  `app/photos/` and the `SITE` slots; the `site` skill has the procedure.
