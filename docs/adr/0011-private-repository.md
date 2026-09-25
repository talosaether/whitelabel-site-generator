# 11. The repository is private, and production borrows the deploy job's token

Status: accepted

Builds on [ADR-0005](0005-continuous-deployment.md).

## Context

The predecessor project was public, and its pipeline leaned on that: the production host
fetched the repository over anonymous HTTPS, pulled the image from GHCR anonymously, and
the first boot fetched `bootstrap.sh` from `raw.githubusercontent.com` via cloud-init.
This repository is private, which closes all three paths.

The obvious fix is a credential on the production host — a read-only deploy key for git
and a registry token for GHCR. That is two long-lived secrets on a box whose only job is
to run what it is told, plus rotation to remember, plus the question of what a token
that can read packages can read beyond this one.

## Decision

**The production host holds no GitHub credential.** The `deploy` job's own
`GITHUB_TOKEN` — minted for that run, scoped to this repository, dead when the run ends —
is passed to the host as an argument of the SSH session and used for two things:

- `docker login ghcr.io` before the pull, with a `trap` that logs out on every exit path,
  including rollback;
- a per-command `http.extraheader` on the `git fetch`, so the remote URL in `.git/config`
  stays plain and nothing is persisted.

The job declares `packages: read` alongside `contents: read`, which is all the token has.

**Bootstrap carries the repository as a git bundle**, copied over SSH from a laptop and
cloned from the local file. The first thought was to lend the operator's `gh auth token`
to the clone the same way; it was rejected because that token is the operator's whole
GitHub account, not this repository, and the host has no business seeing it even for one
command. The bundle needs no credential at all; the first deploy repoints `origin` at
GitHub. There is no `cloud-init.yaml`: cloud-init would need a credential embedded in
user data, which stays readable in the droplet's metadata service.

**The dev host uses `gh`** with a fine-grained personal access token scoped to this one
repository: contents, pull requests, issues and workflows, no administration. Its
existence on that box is the dev host's identity as a workspace; the token's scope is
the boundary, not the process holding it.

## Consequences

- **Nothing to rotate on production.** Rebuilding the host means re-running bootstrap and
  refreshing `DEPLOY_KNOWN_HOSTS`, as before; there is no registry or repository secret
  to re-place.
- **A hand-run `docker pull` on production fails.** Between deploys the host has no
  registry login. The serving image and the rollback image are local tags, and
  `restart: unless-stopped` needs no pull, so this costs nothing in normal operation.
- **The token is briefly visible in the host's process list** as an argument to
  `bash -s`. The host is single-tenant and root-only, and the token expires with the run.
- **Actions minutes are metered.** Private repositories draw on the account's monthly
  allowance; a run is about five minutes.
- **`ALLOW_EXISTING_CHECKOUT=yes` also takes a bundle.** A host whose checkout survived
  has GitHub as `origin` and no way to fetch it; the rebuild path pulls from `REPO`.
- `tests/test_image_pinning.py` asserts the login-before-pull order, the logout trap, the
  header-not-URL rule, that bootstrap takes no token, and the absence of any anonymous
  fetch path.
