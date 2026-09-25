# 4. Docker Compose and Caddy on a single droplet

Status: accepted

## Context

One low-traffic site, one owner, no ops team. It needs HTTPS, it needs to survive a reboot,
and it needs to be reconstructible after the host is destroyed.

## Decision

Two containers via Compose: the app, and Caddy as the reverse proxy. Caddy obtains and
renews Let's Encrypt certificates automatically using the `tls-alpn-01` challenge. The
repository is the only artefact: `scripts/bootstrap.sh` installs Docker if missing, clones,
and starts the stack. It is run over SSH from a laptop; see ADR-0011 for why there is no
cloud-init file.

## Consequences

- **The DNS record must be DNS-only, not proxied.** A Cloudflare proxied record terminates
  TLS itself and the `tls-alpn-01` challenge can never complete.
- **DNS must resolve to the host before it starts with a hostname set.** The bootstrap
  therefore starts on plain HTTP (`SITE_ADDRESS=:80`), so a record that has not moved yet
  cannot wedge the first boot on a failing certificate request.
- Certificates live in the `caddy_data` volume and are re-issued on a new host. Never run
  `docker compose down -v`; it deletes them and burns a rate-limited re-issue.
- Running as root on the droplet is acceptable. The `docker` group is root-equivalent, so a
  deploy account is not a security boundary. The application is unprivileged regardless:
  uid 10001, read-only filesystem, capabilities dropped.
- The places that name the domain must agree — `SITE_ADDRESS`, `SITE['domain']` in
  `app/main.py`, and the test defaults. [DEPLOY.md](../../DEPLOY.md) has the table.
