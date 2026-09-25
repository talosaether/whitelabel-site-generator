# 7. Production containers are bounded

Status: accepted

Builds on [ADR-0004](0004-deployment.md).

## Context

The hardening the containers have — `read_only`, `cap_drop: [ALL]`, `no-new-privileges`,
an unprivileged uid — limits what a compromised container may *do*, not how much of the
host it may *consume*. Unbounded, the kernel's OOM killer chooses a victim by its own
heuristic, and the smallest, best-behaved process on the box is not the one it picks.
Losing `dockerd` or Caddy takes the site off the internet; losing the app does not.

## Decision

- **`app`**: 512 MiB, 128 PIDs, `/tmp` capped at 64 MiB, logs rotated at 3 × 10 MiB.
- **`caddy`**: 128 MiB, 64 PIDs, the same log rotation.
- **No CPU cap.** Nothing else on the production host should be able to out-schedule the site.
- The dev overlay's `assets` watcher gets the same 512 MiB / 128 PIDs ceiling.

`tests/test_production_runtime.py` asserts these against the *rendered* Compose config, so
a change that keeps the same words but a different effective value still fails.

## Consequences

- **A runaway app is killed as the app.** `restart: unless-stopped` and the healthcheck
  bring it back.
- **The ceilings are not sized to the app** (tens of MiB resident). They are sized to leave
  the host room for its neighbours; if the app ever legitimately needs more, that is a
  signal worth reading, not a number to raise reflexively.
- **Applying a change here recreates both containers.** A `compose.yaml` edit is not a
  graceful reload.
