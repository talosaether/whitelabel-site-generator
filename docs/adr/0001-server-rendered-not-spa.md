# 1. Server-rendered FastAPI and HTMX, not a static SPA

Status: accepted

## Context

The brief for this kind of site tends to arrive as "a static, self-contained SPA". Those
three things pull against each other: a static site has no server, an SPA implies a
client-side router and a JavaScript framework, and self-contained means no CDN. The site's
actual job is a handful of mostly-textual pages, read by people on phones.

## Decision

Server-render with FastAPI and Jinja2. Use HTMX `hx-boost` for navigation, which swaps the
body and pushes history without a full reload — SPA-like movement without an SPA. Bundle
all browser assets locally with Vite; nothing is fetched from a CDN at runtime.

Vue 3 and `@vitejs/plugin-vue` stay installed and configured, but no component is mounted.
The tooling is there for the first interaction that genuinely needs it.

## Consequences

- A server is required. This is not a site that can be dropped on static hosting as-is.
- Every page works without JavaScript: navigation is real links.
- Because boosted navigation replaces only the body, `frontend/main.js` copies the page
  description and canonical URL out of `main[data-*]` into `<head>` after each swap, and
  browser tests assert the two stay in sync.
- Nothing in the app is async-heavy or stateful, so one uvicorn process on a 1 GB host
  is ample.
