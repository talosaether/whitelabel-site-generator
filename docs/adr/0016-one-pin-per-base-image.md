# 16. Each base image is pinned once; the dev watchers build that stage

Status: accepted

Amends [ADR-0009](0009-base-images-pinned-by-digest.md).

## Context

ADR-0009 had the development overlay repeat the Dockerfile's node and python pins
verbatim, with a test requiring the copies to match. Dependabot's docker ecosystem reads
Dockerfiles and not Compose files, so every base image bump it opened changed one copy
and failed the test on the other. On the second site built from this scaffold it happened on node 22 to 25, again on
node 25 to 26 and on a python digest, where two pull requests sat red for five days, and
each time the fix was a person copying a digest by hand. ADR-0009 called that "the test doing its
job"; it was the layout making work.

## Decision

- **The Dockerfile names each base image once**, as a stage: `node-base` and
  `python-base`. The assets, photos and runtime stages build `FROM` those names.
- **The dev watchers build those stages** (`build: {context: ., target: node-base}`)
  instead of pulling an image by a pin of their own. `compose.dev.yaml` carries no
  registry reference for node or python.
- **The tests assert the shape**: one registry `FROM` per base image, the build stages on
  the named bases, the watchers on those targets, and no node or python `image:` in
  either Compose file.

## Consequences

- A Dependabot base image pull request is a one-line diff that passes or fails on the
  image itself.
- On the development host, a base image bump needs `docker compose up -d --build` after
  the pull, like a change to `requirements.txt`. A plain `up -d` keeps the old watcher
  images. DEPLOY.md says so.
- The watcher images are local tags (`<project>-assets`, `<project>-photos`) a few
  kilobytes larger than the base: one empty layer each.
- Caddy's pin in `compose.yaml` is unchanged and still watched by the weekly audit.
