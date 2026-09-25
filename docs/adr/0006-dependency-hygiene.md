# 6. Dependencies are audited weekly and pinned exactly

Status: accepted

## Context

Every dependency is pinned to an exact version — good for reproducible builds. The cost is
that a pin never moves on its own, so a vulnerability disclosed after the pin was chosen
sits in the tree indefinitely. That is not hypothetical: `starlette` 0.48.0 carried an
unauthenticated Range-header DoS that every `/static` response is exposed to, and on the
predecessor project it was found only when someone finally ran `pip-audit` by hand.

## Decision

Two mechanisms, deliberately separate from the deploy pipeline.

- **Dependabot** (`.github/dependabot.yml`) opens weekly update PRs for five ecosystems:
  the runtime Python deps, the shipped frontend bundle, the browser-test toolchain, the
  Dockerfile's base images, and the GitHub Actions themselves. Each PR runs the `check`
  gate like any other, so a bump that breaks a test cannot merge.
- **A scheduled audit** (`.github/workflows/audit.yml`) runs `pip-audit` and `npm audit`
  every Monday, and on demand. Its failure means "a dependency needs attention",
  decoupled from any code change.

`starlette` is pinned explicitly rather than floated via FastAPI's floor, so its version is
a decision recorded in `requirements.txt`.

## Consequences

- **A new CVE never turns a code merge red.** The audit is on its own clock.
- **Dependabot PRs are real deploys once merged**, through the same gate and rollback.
- **Exact pins still mean manual intent.** Dependabot proposes; a human merges.
