# Adopting the process in an existing site

For a site of this architecture that already exists and wants the way of working, not the
scaffold: an owner-facing assistant that changes the site live on a development host, a
developer assistant that does everything else, and GitHub issues as the only channel
between them. The scaffold's own copy of each piece is named so it can be lifted.

## The roles

| | Developer assistant (`root`) | Owner's assistant (`hermes`) |
| --- | --- | --- |
| Talks to | the developer | the site owner, over Telegram |
| Edits | anything | `app/` and `frontend/` only: copy, the `SITE` block, services, palette, photos |
| Cannot write | — | `compose*.yaml`, `Dockerfile`, `.github/`, `tests/`, `scripts/`, `.hermes/`, the docs |
| Ships by | pushing to `main`, or a PR | a PR that auto-merges when `check` is green |
| GitHub token | fine-grained, this repo, no admin | fine-grained, this repo: contents, pull requests, issues |

The developer assistant here is Claude Code; the owner's is a Hermes agent. Nothing below
depends on which agents they are, only on what each may touch.

## The loop

1. The owner asks for a change in plain words. The assistant edits the file in the shared
   tree, and the development host serves it within seconds (`site` skill).
2. The owner looks at the dev site. When it is right, `/ship`: the assistant's script
   commits `app/` and `frontend/`, pushes a `hermes/<timestamp>` branch, opens a PR and
   arms auto-merge. `check` runs the full suite; a green run merges and deploys (`ship`).
3. Anything outside copy, colours and photos — a new page, a form, artwork that needs
   cutting, a broken build — is `/todo add (dev) …`: a GitHub issue labelled `dev`, which
   is the developer's queue (`gh issue list --label dev`). Files the owner sends land in
   `app/inbox/`, referenced from the issue (`todo`).
4. `/recent` tells the owner what is on dev, what is waiting on tests, what is live, and
   how many items the developer holds (`recent`).
5. `app/HANDOFF.md` carries the *why* between the two assistants, newest first. `git
   status` says what changed; the handoff says what to do about it.

## What to copy

| Piece | Files | Adapt |
| --- | --- | --- |
| The rules both assistants read | `AGENTS.md` (the "two hosts" and "shared tree" bullets) | host names, the tree path |
| The handoff | `app/HANDOFF.md` | start the entries fresh |
| The owner's assistant's skills | `.hermes/skills/{site,todo,ship,recent}` | the `cd /srv/…` line in each script and the dev/live URLs in `recent.sh` and the `site` and `ship` skills; the "where things live" table in `site` to the site's own data blocks |
| The development host | `compose.dev.yaml`, `Caddyfile.dev`, `.env.example`, `tests/test_dev_overlay.py`, `docs/adr/0010-two-hosts.md` | the Dockerfile pins the overlay must match (the test checks) |
| Keeping the notes out of the image | the `app/HANDOFF.md`, `app/inbox` and `.hermes` lines of `.dockerignore` | — |
| Photos without the developer (optional) | `scripts/build_photos.py`, the `photos` stage of `Dockerfile`, the `photos` service of `compose.dev.yaml`, `app/photos/README.md`, the `hero_photo`/`about_photo` slots and `photo()` helper in `app/main.py`, `docs/adr/0012-photos.md` | the templates that show them |

The tests that come with these assert structure, not copy, so they survive branding.

## Repository settings

- **Labels** `dev` and `owner`. `todo.sh` applies them and does not create them.
- **Auto-merge allowed**, and a ruleset on `main` that requires the `check` job, so
  `gh pr merge --auto --merge` waits for the tests. Merge commits, not squash: the shared
  tree's local `main` is ahead of GitHub by the commits it just made, and a merge commit
  keeps them as ancestors so `git pull --rebase --autostash` stays conflict-free.
- **Two fine-grained tokens**, one per assistant, each limited to this repository. The
  owner's assistant needs contents and pull requests (to ship) and issues (for the to-do
  list); neither needs administration. A token that can fork or create repositories is
  wider than either job, and its absence is a feature.
- **`DEPLOY_HOST`** as a repository variable and the two deploy secrets, per `DEPLOY.md`.

`scripts/preflight.sh OWNER/REPO` checks these and says which are missing; `docs/PLAYBOOK.md`
is the same setup as an ordered procedure, with the exceptions.

## The development host

A second host, not a preview mechanism on production: ADR-0010 explains why the machinery
gets shorter when production is not the only machine. On it:

- The checkout lives at `/srv/<name>` and is the live site. Its `.env` is the first block
  of `.env.example`: `SITE_ADDRESS=dev.<domain>`, the `<name>-dev` project name, and
  `COMPOSE_FILE=compose.yaml:compose.dev.yaml`, which is what layers the overlay in.
  `dev.<domain>` needs a DNS record before Caddy's first start.
- The tree is owned by root. ACLs give the owner's assistant write access to exactly the
  directories its skills may edit, plus `.git` so `/ship` can commit and push, and read
  access everywhere else:

  ```sh
  setfacl -m u:hermes:rx /srv/<name>
  setfacl -R -m u:hermes:rwx -m d:u:hermes:rwx /srv/<name>/app /srv/<name>/frontend /srv/<name>/.git
  ```

  `.hermes/` stays root-owned and read-only to the assistant, so it cannot rewrite its own
  instructions. The assistant's rules say the same thing the ACLs enforce; keep both in
  step when the boundary moves.
- The `hermes` account is an ordinary unprivileged user with no sudo (ADR-0013 has the
  commands). It has its own git
  identity, `safe.directory` for the tree, and `gh auth login` with its own token. Its
  agent configuration points `skills.external_dirs` at `/srv/<name>/.hermes/skills` and
  enables the Telegram platform; the skills in the tree are the whole of what it knows
  about the site.
- The `assets` and `photos` watchers in the overlay rebuild the stylesheet and the photo
  derivatives within seconds of a save. Nothing on this host is ever pushed from the host
  by the developer: it is a workspace, and production is a deploy target.

## What not to carry over

The scaffold's placeholders. The process is worth copying whole; the copy, palette and
artwork are the site's own, and `README.md` "Branding it" is the map of where they live.
