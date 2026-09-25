# 5. Push to main deploys the image the gate tested

Status: accepted

Builds on [ADR-0004](0004-deployment.md).

## Context

Deploying by hand means opening an SSH session and typing the same commands, which is fine
until it is done at the wrong moment, in the wrong directory, or on the wrong host. The
predecessor project went through two stages: first the host rebuilt the image on every
push, then — after a rollback path that rebuilt on the same memory-starved box shared the
failure mode of the thing it was recovering from — the runner published the image it had
tested and the host only pulled it. This project starts at the second stage.

## Decision

`.github/workflows/deploy.yml` has three jobs.

**`check`** runs the policy tests, builds the image on the runner, starts the whole stack
there over plain HTTP, runs the HTTP and browser suites against it, and only then publishes
the image to `ghcr.io/<repository>:<sha>`. It touches nothing live and needs no secrets,
so it runs on pull requests as well (without publishing).

**`deploy`** needs `check`, and is skipped for pull requests. It opens one SSH session to
production, resets `/srv/website` to the exact commit, writes `APP_IMAGE` into the
untracked `.env`, **pulls before touching anything**, tags whatever is serving as
`<repository>:<previous sha>`, swaps the app container with `--no-build`, waits for its
healthcheck, reloads Caddy, and asserts two facts: `HEAD` is the deployed commit, and the
running container's image is the deployed tag. Any failure restarts the tagged-aside image:
no build, no registry, no network.

**`verify`** re-runs the HTTP suite against production. The application was already proven
on the runner; what is left to prove is that this host, this Caddy and this certificate are
serving it.

Deliberately **not** chosen: a self-hosted runner (a long-lived agent with a token, to
replace a 60-second SSH session), and blue-green (one app container; Caddy's
`lb_try_duration` absorbs the restart instead).

## Consequences

- **What ships is what passed.** The artefact is identical, not equivalent, and the second
  assertion proves it.
- **The host is a deploy target, not a workspace.** `git reset --hard` discards anything
  edited there. `.env` is untracked and survives.
- **A registry outage is a failed deploy, not an incident.** The pull precedes every change.
- **The app restart does not show.** The image is byte-compiled at build time so it starts
  in about three seconds, and Caddy holds connections across the gap. Measured on the
  predecessor: zero errors through a deploy, one request held 3.7 seconds.
- **Bind-mounted config is invisible to Compose.** It compares mount definitions, not file
  contents, so the deploy reloads Caddy explicitly after every run.
- **Two secrets are the whole trust model**: `DEPLOY_KEY` and `DEPLOY_KNOWN_HOSTS`. The
  key is a root shell on the host; anyone who can push to `main` already controls what
  runs there.
- **Nothing in the workflow names the repository.** The image and the fetch URL come from
  the run context, so a fork or a second white-label instance publishes under, and
  deploys from, its own repository. `tests/test_image_pinning.py` asserts this.
- **The image is private,** like the repository. ADR-0011 covers how the host pulls it
  without holding a credential.
