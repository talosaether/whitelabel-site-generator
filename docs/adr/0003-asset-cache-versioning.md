# 3. Content-versioned asset URLs and explicit cache headers

Status: accepted

## Context

Generated assets keep stable filenames across builds. Without explicit `Cache-Control`,
browsers apply heuristic caching, and a stale stylesheet can outlive a deploy and render
new HTML with old rules.

## Decision

Templates call `asset('/static/site.css')`, which appends a version derived from the file's
size and mtime. A middleware sends `public, max-age=31536000, immutable` for URLs carrying
that version, and `no-cache` for bare asset URLs and for HTML.

The helper stats the file on every call rather than caching per process. On the
development host the watcher rewrites `site.css` under a running server; a cached version
would pin browsers to the old file for the life of the process. Four stats per page is
nothing.

## Consequences

- Every asset the templates reference must go through `asset()`, including the brand
  artwork under `/brand/`.
- `tests/smoke.py` asserts both headers and the `?v=` markers; `tests/test_dev_overlay.py`
  asserts the helper has no per-process cache.
- A global `img { max-width: 100% }` rule is the belt-and-braces guard for the day a
  stylesheet does go stale anyway.
