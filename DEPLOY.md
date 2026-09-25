# Deploying

Two hosts, one repository.

| | Development | Production |
| --- | --- | --- |
| Host | `dev.example.com` | `example.com` |
| Serves | This working tree, live | The image built and tested from `main` |
| Changes by | Saving a file | Pushing to `main` |
| Checkout | `/srv/whitelabel`, shared by both assistants | `/srv/website`, owned by the deploy workflow |
| Compose files | `compose.yaml` + `compose.dev.yaml`, via `COMPOSE_FILE` in `.env` | `compose.yaml` alone |
| Compose project | `whitelabel-dev` | `whitelabel` |
| Indexed | No — `X-Robots-Tag: noindex` | Yes |

Everything either host needs is in this repository: source, templates, styles, artwork,
the Dockerfile, the Compose files, and the tests. Nothing has to be copied off an old host.

**The repository is private**, and so is the image it publishes. Production holds no
GitHub credential, ever: it is bootstrapped from a git bundle and is lent the deploy job's
own short-lived token for the length of each deploy. The dev host uses `gh` with a
fine-grained token scoped to this one repository. See
[ADR-0011](docs/adr/0011-private-repository.md).

## 1. The development host

The dev host serves the checkout through the same containers production uses, plus an
overlay ([`compose.dev.yaml`](compose.dev.yaml)) that changes three things:

- the app container bind-mounts `./app` read-only over `/srv/app` and runs uvicorn with
  `--reload`, so a template or Python edit is live on the next request;
- an `assets` container runs Vite in watch mode, writing `site.css` and `site.js` into
  `./app/static`, which the app container sees through the same mount, so a stylesheet
  edit is live on the next reload;
- Caddy serves [`Caddyfile.dev`](Caddyfile.dev), which adds a `noindex` header.

Setting it up on a fresh box is the same Docker install as production (§2a), then:

```sh
gh repo clone OWNER/REPO
cd REPO
printf 'SITE_ADDRESS=dev.example.com\nWWW_ADDRESS=:8080\nCOMPOSE_PROJECT_NAME=whitelabel-dev\nCOMPOSE_FILE=compose.yaml:compose.dev.yaml\n' > .env
docker compose up -d --build
docker compose logs -f assets     # until "built in ..." appears; the first npm ci takes a minute
```

After that, edit and refresh. `docker compose ps` should show `app`, `assets` and `caddy`
all up. The watcher rebuilds in about 100ms; uvicorn restarts in about a second.

Two things do still need a restart: a change to `requirements.txt` or `frontend/package.json`
(`docker compose up -d --build`), and a change to `compose.yaml` or `compose.dev.yaml`
(`docker compose up -d`). A `Caddyfile.dev` edit needs
`docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile`.

The dev host is small (1 GB). Docker was installed there with a 2 GB swapfile
(`/swapfile`, in `/etc/fstab`) so the image build and the watcher fit beside everything else.

## 2. Production

### 2a. Bootstrap

[`scripts/bootstrap.sh`](scripts/bootstrap.sh) installs Docker if the host lacks it, clones
this repository to `/srv/website`, writes `.env`, and starts the site. The repository is
private and the host is given no GitHub credential, so the repository is carried over as a
**git bundle** — the commits as a single file, which `git clone` accepts as a source. From
your laptop, with a clone of this repository and root SSH access to the new host:

```sh
git bundle create site.bundle HEAD main
scp site.bundle root@example.com:/root/site.bundle
ssh root@example.com "REPO=/root/site.bundle SITE_ADDRESS=example.com WWW_ADDRESS=:8080 bash -s" < scripts/bootstrap.sh
ssh root@example.com rm /root/site.bundle
```

The checkout's `origin` points at the bundle path until the first deploy, which repoints it
at GitHub and fetches with the workflow's own token, as every deploy does. The first start
builds the image on the host, which takes a few minutes; every later deploy pulls the image
the runner tested instead. `SITE_ADDRESS` can be the real hostname because DNS already
resolves to this host; use `:80` on a host DNS has not reached yet.

There is no cloud-init file: cloud-init cannot clone a private repository without a
credential embedded in user data, which stays readable in the droplet's metadata forever.

**It refuses to run against a checkout that already exists.** Once `/srv/website` is there,
the deploy workflow owns it — it resets that checkout to the commit it is shipping and rolls
back if the commit turns out unhealthy. Pulling into it from the host would leave the site
serving a commit no run ever tested, outside that rollback path, until the next push
silently discarded it. So: to ship a change, push to `main`. To rebuild a host whose
checkout survived — disaster recovery, not deployment — re-run with
`ALLOW_EXISTING_CHECKOUT=yes`, with `REPO` pointing at a bundle as for a first bootstrap; on
a host that has deployed, it restarts the deployed image rather than building.

If it was started with `SITE_ADDRESS=:80`, set the hostname once the A record points at
the droplet and restart:

```sh
cd /srv/website
printf 'SITE_ADDRESS=example.com\nWWW_ADDRESS=www.example.com\nCOMPOSE_PROJECT_NAME=whitelabel\n' > .env
docker compose up -d
```

If `www.example.com` has no A record yet, keep `WWW_ADDRESS=:8080` until it does:
Caddy requests a certificate for every named site, and a name that does not resolve here
fails the challenge and retries forever.

### 2b. What the host needs

- **Docker Engine and the Compose plugin.** Nothing else: Node and Python run inside the
  build, not on the host. The bootstrap installs Docker from Docker's own apt repository,
  not `docker.io` (older engine) and not the snap.
- **Ports 80 and 443 free and reachable from the internet.** Caddy needs both to obtain a
  certificate (it uses the `tls-alpn-01` challenge on 443, and redirects 80 to 443).
- **DNS already pointing at the host** before the first start with a hostname set.
- **A DNS-only record, not a proxied one.** A Cloudflare-proxied record terminates TLS
  itself and the challenge can never complete.
- **RAM, plus swap.** The bootstrap adds a 2 GB swapfile on any host with under 2 GB of
  RAM, and that is what makes a deploy's image pull survivable on a 512 MB droplet. Without
  it, the pull starves the running containers: connections are accepted and nothing is
  served for minutes (seen on such a host, two deploys back to back). 1 GB is the
  comfortable size. On a host bootstrapped before this was added:
  `fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile && echo '/swapfile none swap sw 0 0' >> /etc/fstab`.

Running as root is fine and is the shorter path. The application is unprivileged either
way — uid 10001, read-only filesystem, all capabilities dropped. A deploy account is
optional hardening: the `docker` group is root-equivalent, so it is not a security boundary;
what it buys is switching off root SSH login, which needs keys.

### 2c. Automatic deploys

Once the host is up, every push to `main` redeploys it. `.github/workflows/deploy.yml` has
three jobs, in order:

| Job | Where | What |
| --- | --- | --- |
| `check` | runner | Runs the policy tests, builds the image, starts the stack on plain HTTP, runs the HTTP and browser suites against it, then publishes the image to `ghcr.io/<repository>:<sha>`. Runs on pull requests too (without publishing); touches nothing live. |
| `deploy` | production | Resets `/srv/website` to the commit, pulls the image `check` published, swaps the app container, waits for its healthcheck, reloads Caddy, asserts `HEAD` **and** the running image. Rolls back on any failure. Skipped for pull requests. |
| `verify` | runner | Re-runs the HTTP suite against production, proving this host and its certificate serve what was tested. |

**What a deploy does to the live site.** The image was built and tested on the runner, so
the host only pulls it — and the pull happens before anything is touched, so a registry
failure or a bad tag leaves the site exactly where it was. The swap is a restart, but the
image is byte-compiled at build time so it starts in about three seconds, and Caddy holds
connections and retries across the gap rather than returning 502. Replacing Caddy itself
costs a few seconds of refused connections; that happens only when `compose.yaml` changes.

**If the new image will not serve**, the deploy puts the previous commit back, restarts the
image that was running minutes earlier — tagged aside before the swap, so nothing is built or
fetched — waits for it to become healthy, then fails the job. A rollback is an incident:
read the log, fix forward, push again.

**The production host is a deploy target, not a workspace.** The deploy runs
`git reset --hard`, so anything edited on the host is discarded. `.env` is untracked and
survives; the deploy rewrites `COMPOSE_PROJECT_NAME` and `APP_IMAGE` in it every run and
strips any `COMPOSE_FILE` line, so production can never accidentally pick up the dev overlay.

`DEPLOY_HOST` is a repository variable (Settings → Secrets and variables → Actions →
Variables). Until it is set, a push to `main` runs `check` and stops there, green: nothing
is published to the registry and nothing is deployed. `DEPLOY_USER` (default `root`) is a
second variable, if it ever needs overriding.

### One-time setup

Two repository secrets, from your own machine:

```sh
# A key only Actions uses. No passphrase — nothing can type one for it.
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_site_ci -N '' -C 'github-actions@example.com'

# Let the production host accept it.
ssh-copy-id -i ~/.ssh/id_ed25519_site_ci.pub root@example.com

# Hand GitHub the private half, and pin the host key so the runner cannot be
# redirected to some other machine.
gh secret set DEPLOY_KEY -R OWNER/REPO < ~/.ssh/id_ed25519_site_ci
ssh-keyscan -t ed25519 example.com |
  gh secret set DEPLOY_KNOWN_HOSTS -R OWNER/REPO
```

Without `gh`, the same two values go in by hand at **Settings → Secrets and variables →
Actions → New repository secret**. `DEPLOY_KEY` is the whole private key file including its
`-----BEGIN`/`-----END` lines; `DEPLOY_KNOWN_HOSTS` is the one-line output of `ssh-keyscan`.

The `check` job pushes to GitHub Container Registry with the workflow's own token, and the
`deploy` job lends that same token to the host to pull; nothing to set up. The package is
private, like the repository, and stays that way.

Then push to `main`. The run fails on its first deploy step, before touching the host, if
either secret is missing.

### When it goes wrong

- **`Permission denied (publickey)`** — the public half is not in the host's
  `authorized_keys`, or `DEPLOY_KEY` was pasted without its trailing newline.
- **`Host key verification failed`** — the host was rebuilt and its key changed. Re-run the
  `ssh-keyscan` line. This is the check working, not misfiring.
- **`/srv/website: No such file or directory`** — the checkout is elsewhere. Move it; the
  path is fixed on purpose.
- **`could not pull <image>; the site is untouched`** — the registry, a bad tag, or a
  half-published image. Nothing changed. Re-run the job once the image is there.
- **`rolling back to <sha>`** — the new image never became healthy. The job prints
  `docker compose logs` first; that is where the reason is.
- **`the rollback is unhealthy too - the site is down`** — the image that was serving
  minutes ago no longer starts, which points at the host: check `df -h /` in the same log,
  then `docker compose logs` on the host.
- **A red `verify` with a handshake or read timeout, deploy green** — the host was too
  busy to answer, usually a second deploy starting on a swapless 1 GB box. Check the
  site by hand; if it answers, nothing is wrong with the commit. Add swap (above).
- **A red `verify` with an assertion** — the deploy happened and the live site broke.
  Fix forward, or `git revert` and push, which deploys the revert.

## 3. Serving a different domain

These name the domain, and they have to agree:

| What | Where | Default |
| --- | --- | --- |
| Certificate + virtual host | `SITE_ADDRESS` in each host's `.env`, read by `compose.yaml` → `Caddyfile` | `example.com` / `dev.example.com` |
| The www redirect's own host | `WWW_ADDRESS`, same route | `www.example.com` |
| `<link rel="canonical">` | `SITE['domain']` in `app/main.py` | `https://example.com/...` |
| Deploy target and post-deploy check | the `DEPLOY_HOST` repository variable, read by `.github/workflows/deploy.yml` | unset, so nothing deploys |
| Default target of the test suites | `tests/smoke.py`, `tests/browser/playwright.config.js` | same |
| Bootstrap | the repository URL in `scripts/bootstrap.sh` | `OWNER/REPO` |

Canonical URLs pointing at a domain you no longer serve quietly tell search engines the
wrong thing, so do not skip `SITE['domain']`. The dev host deliberately keeps production's
canonical: it is the same site, and the dev copy should never be the one indexed.

## 4. Verify, in order

```sh
curl -fsS https://<host>/healthz              # {"status":"ok"}
python3 tests/smoke.py https://<host>         # pages, head metadata, headers, caching
cd tests/browser && npm ci && PLAYWRIGHT_BROWSERS_PATH=../../recovery/browsers npx playwright install chromium
BASE_URL=https://<host> npm test              # desktop + mobile, axe WCAG A/AA
```

Always test through Caddy: the `X-Content-Type-Options: nosniff` assertion is set by the
proxy, so hitting port 8000 directly fails it.

## 5. What does not come from this repository

- **The TLS certificates.** They live in the `caddy_data` volume and are re-issued
  automatically on a new host. Do not run `docker compose down -v`, which deletes them and
  burns a rate-limited re-issue.
- **`app/static`.** Generated by the build, or by the dev watcher; git-ignored.
- **`.env`.** Untracked and load-bearing on both hosts: it is what makes a checkout the
  dev site or the production site. [`.env.example`](.env.example) has both.
- **The deployed image.** Production runs `ghcr.io/<repository>:<sha>`, published by the
  `check` job. The host builds nothing after bootstrap; it holds the tag it is serving and
  the one a rollback would need. It has no registry login between deploys, so a hand-run
  `docker pull` there fails — by design.
- **The dev host's swapfile.** `/swapfile`, 2 GB, in `/etc/fstab`.
