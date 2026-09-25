# 8. The Compose project name is an isolation boundary

Status: accepted

Builds on [ADR-0004](0004-deployment.md) and [ADR-0005](0005-continuous-deployment.md).

## Context

Compose names a project after its working directory unless told otherwise. On the
predecessor project, production ran from `/srv/website`, so its project was `website` —
and a development clone into any directory called `website` inherited that name and
addressed the same containers. `docker compose down -v` from the clone would have deleted
the live TLS certificate. Nothing in those commands named the production path.

## Decision

Invert the default: the file names a project that is **nobody's**, and each host opts in.

- `compose.yaml` declares `name: whitelabel-local`. Any clone gets that, whatever its
  directory.
- Production sets `COMPOSE_PROJECT_NAME=whitelabel` in its untracked `.env`, written by
  `scripts/bootstrap.sh` and ensured by `deploy.yml` before any Compose command.
- The development host sets `COMPOSE_PROJECT_NAME=whitelabel-dev` beside `COMPOSE_FILE`.

Precedence makes this work: `COMPOSE_PROJECT_NAME` beats the file's `name:`, which beats
the directory.

## Consequences

- **A clone is safe by default.** Being unsafe takes a deliberate edit to an untracked file.
- **`.env` is load-bearing on both hosts.** It decides which checkout is which site. The
  deploy rewrites production's every run, so a lost or hand-edited `.env` self-heals.
- `tests/test_production_runtime.py` asserts the default is not production's, that a
  directory named `whitelabel` does not inherit it, and that `.env` opts back in.
