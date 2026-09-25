# 10. A development host serves the working tree; production serves `main`

Status: accepted

Builds on [ADR-0005](0005-continuous-deployment.md) and [ADR-0008](0008-compose-project-isolation.md).

## Context

The predecessor project had one host, and grew a preview mechanism to show work in
progress on it: a mutable `preview` branch, a separately dispatched workflow, a
forced-command SSH user on the production box, a runner-built image streamed over SSH and
loaded beside the live containers. It worked, and it was a lot of machinery whose entire
purpose was to keep an untested candidate from touching production while sharing its host.

This project has two hosts from the start. The question the preview machinery answered —
how do you look at a change before it ships? — has a much shorter answer when production
is not the only machine.

## Decision

**The development host serves the working tree, live.** `compose.dev.yaml`, layered over
`compose.yaml` by `COMPOSE_FILE` in that host's `.env`, changes three things:

- the app container bind-mounts `./app` read-only over `/srv/app` and runs uvicorn with
  `--reload`;
- an `assets` service runs Vite in watch mode, writing into `./app/static` through the
  same mount;
- Caddy serves `Caddyfile.dev`, identical to production's site block plus
  `X-Robots-Tag: noindex, nofollow, noarchive`.

Everything else — the image, the hardening, the limits, Caddy's headers — is the
production configuration, so what is seen on the dev host is what production will serve.

**Production serves `main` and nothing else**, through the pipeline in ADR-0005. The dev
host has no role in that pipeline: the runner builds and tests, production pulls. A push
to `main` is a release.

No preview branch, no preview workflow, no second SSH credential, no host-owned deployer.

## Consequences

- **Iteration is a file save.** Templates and Python are live on the next request;
  stylesheets on the next reload. Dependency and Compose changes still need
  `docker compose up -d --build`.
- **The dev host is a workspace and production is not.** Work lives in the dev checkout
  until it is pushed. The production checkout is reset on every deploy.
- **The dev tree is a shared workspace.** It lives at `/srv/whitelabel` and is
  edited by two assistants; `app/HANDOFF.md` records the split. The one writing on behalf of
  the site owner may touch only `app/` and `frontend/`, and ships through pull requests
  that auto-merge on a green `check`.
- **The dev site is not private, only unindexed.** `noindex` discourages search engines; it
  is not access control. Nothing confidential belongs in the working tree.
- **The dev site's canonical URLs name production.** It is the same site, and the dev copy
  must never be the one indexed.
- **The deploy strips `COMPOSE_FILE` from production's `.env` every run**, so the overlay
  cannot reach production by accident. `tests/test_production_runtime.py` asserts the
  strip and that `compose.yaml` alone has no bind mount, no `--reload` and no `assets`
  service; `tests/test_dev_overlay.py` asserts the overlay does what this record says.
- **The dev host needs to build.** It is a 1 GB droplet; it has a 2 GB swapfile so the
  image build and the watcher fit beside whatever else runs there.
- What was lost: a way to show a *branch* on a public URL without it being the working
  tree. If two people ever need to preview different things at once, that is the moment
  to revisit this — with a second dev host, not with the old machinery.
