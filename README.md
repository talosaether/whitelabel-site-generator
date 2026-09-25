# White-label brochure site

A small, server-rendered marketing site for a local business: four pages, no database, no
contact form. The layout, build, tests and deployment are done, and the copy, colours and
artwork are placeholders waiting for a brand. It comes with a way of working: an
owner-facing assistant edits the site live on a development host and hands everything else
to a developer through GitHub issues, and every change reaches production through a tested
pull request.

Two ways to use it:

- **Start a new site.** Copy the repository (a template, a fork, or a clone with a new
  remote), then work through "Branding it" below and [DEPLOY.md §3](DEPLOY.md#3-serving-a-different-domain)
  for the domain. Nothing deploys until the `DEPLOY_HOST` repository variable is set, so
  the first pushes only run the tests. This template is public; an instance may be private,
  and [ADR-0011](docs/adr/0011-private-repository.md) covers what that changes.
- **Adopt the process in a site that already exists.** [docs/ADOPTING.md](docs/ADOPTING.md)
  lists what to copy, what to adapt and how the hosts and accounts are set up.

| Host | What it is | How it changes |
| --- | --- | --- |
| <https://dev.example.com> | Development. Serves this working tree, live. | Edit a file; it is on the site. No commit, no build, no deploy. |
| <https://example.com> | Production. | Push to `main`. A runner builds, tests and ships the image. |

The two hosts run the same image from the same Compose file; the development host layers
[`compose.dev.yaml`](compose.dev.yaml) on top to bind-mount the checkout and reload. See
[ADR-0010](docs/adr/0010-two-hosts.md).

## Run it

Requires Docker Engine with Compose v2. Nothing else — Node and Python run inside the build.

```sh
gh repo clone OWNER/REPO     # or any clone; a private instance needs an authenticated one
cd REPO
printf 'SITE_ADDRESS=:80\nWWW_ADDRESS=:8080\n' > .env   # plain HTTP, no certificate
docker compose up -d --build
curl -s -o /dev/null -w '%{http_code}\n' http://localhost/     # 200
```

To serve the working tree live instead, as the development host does, use the first block
of [`.env.example`](.env.example) as your `.env` — `COMPOSE_FILE` is what adds the overlay.

Deploying to a fresh production host is [DEPLOY.md](DEPLOY.md): two commands from a
laptop. After that it is automatic: **every push to `main` is built and tested on a
runner, then deployed**, and production is re-checked afterwards. Pull requests run the
tests and stop there. The production host is a deploy target, not a workspace — the deploy
resets `/srv/website` to the pushed commit, so anything edited there is discarded.

## Branding it

Everything a new instance has to say about itself is in one place each.

| To change | Edit |
| --- | --- |
| Name, tagline, domain, phone, email, area, hours | The `SITE` block at the top of `app/main.py`. Empty `phone` and `email` hide every call, text and mail link at once. |
| Page titles, headings, descriptions, the header links | `PAGES` and `NAV` in `app/main.py`. The description doubles as the page's intro paragraph. |
| The service list | `SERVICES` in `app/main.py`; the home page previews the first three. |
| Page copy | `app/templates/*.html` — one partial per page, `page.html` is the layout. |
| Colours | The custom properties at the top of `frontend/style.css`. `--brand` for buttons and focus, `--accent` for the current-page underline. |
| Photos on the home and about pages | Drop a JPEG or PNG in `app/photos/`, name it in `hero_photo` / `about_photo` in the `SITE` block with an `_alt` sentence. `scripts/build_photos.py` makes metadata-free WebPs into `app/media/` at build time, or within seconds on the dev host. |
| Logo and browser icon | `app/brand/logo.svg` and `app/brand/icon.svg`. Square. Served as-is from `/brand/`. |
| The domain | `SITE['domain']`, plus `SITE_ADDRESS`/`WWW_ADDRESS` in each host's `.env`, plus the defaults in `compose.yaml`, `Caddyfile`, `Caddyfile.dev`, `deploy.yml` and the three tests. [DEPLOY.md §3](DEPLOY.md#3-serving-a-different-domain) has the table. |

The tests assert structure, not copy, so branding does not mean rewriting them.

## How it fits together

| Layer | What |
| --- | --- |
| Server | FastAPI + Jinja2. One route renders every page from `PAGES` in `app/main.py`. |
| Navigation | HTMX `hx-boost` swaps the body; `frontend/main.js` keeps `<title>`, description and canonical in sync. |
| Assets | Vite bundles `frontend/` to `app/static/site.{js,css}`. Vue is installed but no component is mounted. |
| Photos | `scripts/build_photos.py` (Pillow, in its own build stage) turns `app/photos/` into resized, metadata-free WebPs in `app/media/`. Only the derivatives ship. |
| Serving | Caddy terminates TLS, adds security headers, proxies to the app. Certificates are automatic. |

The Dockerfile has three stages — Node assets, Pillow photos, Python runtime — so the
runtime image carries no toolchain. The app runs as uid 10001 on a read-only filesystem with all
capabilities dropped.

## Where things live

```text
app/main.py              Routes, and every word of site configuration: SITE, PAGES, NAV, SERVICES
app/templates/           page.html is the layout; one partial per page
app/brand/               Logo and icon, tracked, served from /brand
frontend/                style.css, main.js (HTMX glue), Vite config
compose.yaml             The stack: app + Caddy. Both hosts run this.
compose.dev.yaml         The development overlay: bind mount, reload, asset watcher, noindex
Caddyfile, Caddyfile.dev Production and development proxy config
scripts/bootstrap.sh     Stand production up on a fresh host
tests/                   Dependency-free HTTP and policy suites, plus Playwright
docs/adr/                Why things are the way they are
.github/workflows/       Deploy on push to main, then test the live site; weekly audit
DEPLOY.md                Rebuilding production on a new host
```

`app/static/` and `app/media/` are generated during the build (or by the dev watchers)
and are **not** tracked. `recovery/` is local scratch — logs, screenshots, Playwright browsers — and is
ignored.

## Tests

Three suites. The HTTP and browser suites point at production by default; pass a base URL
to test somewhere else.

```sh
python3 tests/smoke.py                      # pages, head metadata, headers, caching
python3 tests/smoke.py https://dev.example.com
python3 tests/test_production_runtime.py    # container limits and project isolation
python3 tests/test_image_pinning.py         # every registry image pinned by digest
python3 tests/test_dev_overlay.py           # the overlay bind-mounts, reloads, watches, noindexes
python3 tests/test_bootstrap_guard.py       # bootstrap refuses a checkout the pipeline owns
cd tests/browser && npm ci
PLAYWRIGHT_BROWSERS_PATH=../../recovery/browsers npx playwright install chromium
BASE_URL=https://dev.example.com npm test   # desktop + mobile, axe WCAG 2 A/AA
```

The Python suites need no dependencies beyond `docker compose` for the policy checks. The
browser suite covers boosted navigation and history, head-metadata sync, keyboard focus
and the skip link, the one-row navigation down to 320px, and axe accessibility checks on
every page. It is not a substitute for real-device or Safari testing.

## Decisions

Short records of why the non-obvious choices were made, in [docs/adr](docs/adr):

| # | Decision |
| --- | --- |
| [0001](docs/adr/0001-server-rendered-not-spa.md) | Server-rendered FastAPI + HTMX, not a static SPA |
| [0002](docs/adr/0002-visible-navigation.md) | At most four visible links, nothing hidden behind a menu |
| [0003](docs/adr/0003-asset-cache-versioning.md) | Content-versioned asset URLs and explicit cache headers |
| [0004](docs/adr/0004-deployment.md) | Docker Compose + Caddy on a single droplet |
| [0005](docs/adr/0005-continuous-deployment.md) | Push to main deploys the image the gate tested |
| [0006](docs/adr/0006-dependency-hygiene.md) | Dependencies audited weekly and pinned exactly |
| [0007](docs/adr/0007-production-runtime-limits.md) | Production containers are bounded |
| [0008](docs/adr/0008-compose-project-isolation.md) | The Compose project name is an isolation boundary |
| [0009](docs/adr/0009-base-images-pinned-by-digest.md) | Base images pinned by digest, each with a watcher |
| [0010](docs/adr/0010-two-hosts.md) | A development host serves the working tree; production serves `main` |
| [0011](docs/adr/0011-private-repository.md) | The repository is private; the deploy job's token is the only credential production ever sees |
| [0012](docs/adr/0012-photos.md) | Photo originals are tracked beside the app; only generated derivatives are served |
| [0013](docs/adr/0013-owner-assistant-account.md) | The owner's assistant runs as an unprivileged account; the ACLs are the boundary |

## Conventions

- Keep source, config, tests and decisions in the repository. Never commit secrets,
  dependencies, generated assets or raw session logs.
- `recovery/` is for local diagnostics and is ignored by both Git and Docker.
- Don't run `docker compose down -v` — it deletes Caddy's certificate volume and burns a
  rate-limited re-issue.
- Open questions that need a human answer live in [docs/open-questions.md](docs/open-questions.md).
- Two assistants share the dev tree; [app/HANDOFF.md](app/HANDOFF.md) is how they hand work across.
