# 9. Base images are pinned by digest, and something watches each pin

Status: accepted

Builds on [ADR-0006](0006-dependency-hygiene.md).

## Context

Every Python and npm dependency is pinned exactly, on the reasoning that a pin makes the
version a recorded decision rather than an accident of resolution. Base images are the
easy exception: `node:22-alpine`, `python:3.13-slim` and `caddy:2-alpine` are floating
tags, and a CVE in the base image's OpenSSL is outside what `pip-audit` and `npm audit`
read.

## Decision

Pin every registry reference by digest, keeping the tag alongside for readability, and give
every pin a watcher.

- **The Dockerfile's two** are watched by Dependabot's `docker` ecosystem. A moved tag
  arrives as a PR through the `check` gate.
- **Caddy's, in `compose.yaml`, is watched by the `images` job in `audit.yml`.**
  Dependabot's docker ecosystem reads Dockerfiles and Kubernetes manifests — not Compose
  files. Pinning it without a watcher would trade a floating tag for a permanently stale
  one, which is worse than where we started.
- **The dev overlay's `assets` watcher reuses the Dockerfile's node pin verbatim**, so
  the development host builds assets with the same toolchain CI does.

`tests/test_image_pinning.py` asserts all of this.

## Consequences

- **A base image change is now a diff.** It is reviewed, it runs the gate, it is in history.
- **The weekly audit can go red for a reason that is not a vulnerability.** A moved
  `caddy:2-alpine` fails the `images` job; the fix is a one-line digest bump.
- **When Dependabot bumps the Dockerfile's node digest, `compose.dev.yaml` must follow**,
  or the pinning test fails. That is the test doing its job.
