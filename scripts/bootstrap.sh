#!/usr/bin/env bash
# Bring this site up on a fresh host. Installs Docker if it is missing, clones the
# repository, and starts the stack.
#
# This provisions a host; it does not update one. Once a checkout exists, the deploy
# workflow owns it, and re-running here refuses rather than pulling. See ALLOW_EXISTING_
# CHECKOUT below and DEPLOY.md, "Automatic deploys".
#
# The repository is private, and the host is given no GitHub credential — not even for
# this. The repository arrives as a git bundle, which `git clone` accepts as a source,
# and the first deploy repoints origin at GitHub with the workflow's own token. From a
# laptop with a clone:
#
#   git bundle create site.bundle HEAD main
#   scp site.bundle root@<host>:/root/site.bundle
#   ssh root@<host> "REPO=/root/site.bundle SITE_ADDRESS=<domain> bash -s" < scripts/bootstrap.sh
#   ssh root@<host> rm /root/site.bundle
#
# Environment:
#   REPO           what to clone: the bundle path above, or a URL the host can reach.
#                  The default is the GitHub URL, which a private repository refuses
#                  anonymously — so for a private repository, pass the bundle.
#   SITE_ADDRESS   hostname Caddy serves, or ":80" for plain HTTP on the IP.
#                  Default ":80", which works before DNS points here. Once the A
#                  record is right: `rm /srv/website/.env && docker compose up -d`,
#                  since example.com is the built-in default.
#   ALLOW_EXISTING_CHECKOUT
#                  "yes" lets this script update a checkout that already exists, which
#                  it otherwise refuses to touch. For rebuilding a host whose checkout
#                  survived, not for shipping changes: pushes to main deploy themselves.
#                  Default "no".
set -euo pipefail

REPO=${REPO:-https://github.com/OWNER/REPO.git}
DIR=${DIR:-/srv/website}
if [ -z "${SITE_ADDRESS+x}" ] && [ -f "$DIR/.env" ]; then
  SITE_ADDRESS=$(grep '^SITE_ADDRESS=' "$DIR/.env" | cut -d= -f2- || true)
fi
SITE_ADDRESS=${SITE_ADDRESS:-:80}
# Caddy obtains a certificate for every *named* site it is given. When SITE_ADDRESS is a
# bare address, DNS has not moved here yet and neither name can answer a challenge, so the
# www redirect gets an address too rather than its real hostname.
case "$SITE_ADDRESS" in
  :*) WWW_ADDRESS=${WWW_ADDRESS:-:8080} ;;
  *)  WWW_ADDRESS=${WWW_ADDRESS:-www.$SITE_ADDRESS} ;;
esac
ALLOW_EXISTING_CHECKOUT=${ALLOW_EXISTING_CHECKOUT:-no}
# The Compose project the live site runs under. compose.yaml deliberately defaults to a
# different name, so only this checkout addresses the live containers.
COMPOSE_PROJECT=${COMPOSE_PROJECT:-whitelabel}

log() { echo "[bootstrap] $*"; }

# $DIR is a deploy target, not a workspace. .github/workflows/deploy.yml resets it to the
# commit it is shipping and rolls back if that commit is unhealthy. Pulling into it from
# here would leave the host serving a commit no deploy run ever tested, outside that
# rollback path and invisible from the repository — the next push would silently discard
# it. Refuse before touching anything: provisioning a fresh host is this script's job.
if [ -d "$DIR/.git" ] && [ "$ALLOW_EXISTING_CHECKOUT" != yes ]; then
  log "$DIR already holds a checkout; the deploy workflow owns it from here."
  log "To ship a change, push to main. To rebuild this host anyway, re-run with"
  log "ALLOW_EXISTING_CHECKOUT=yes."
  exit 1
fi

# A small droplet has no swap, and pulling and extracting an image while the old
# container still runs can push a 1 GB host into thrashing: TCP still connects, nothing
# answers, for minutes. Two gigabytes of swap turns that into a slow pull instead.
if [ "$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo)" -lt 2048 ] && [ -z "$(swapon --noheadings 2>/dev/null)" ]; then
  log "adding a 2 GB swapfile (host has under 2 GB of RAM and no swap)"
  fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile >/dev/null && swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

if ! command -v docker >/dev/null; then
  log "installing Docker"
  apt-get update
  apt-get install -y ca-certificates curl git
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  . /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

# Some images ship Docker without Compose v2, which compose.yaml requires.
docker compose version >/dev/null 2>&1 || apt-get install -y docker-compose-plugin
command -v git >/dev/null || apt-get install -y git

mkdir -p "$(dirname "$DIR")"
if [ -d "$DIR/.git" ]; then
  # Only reachable with ALLOW_EXISTING_CHECKOUT=yes, checked above. The checkout's origin
  # is GitHub, which this host cannot fetch (private repository, no credential), so the
  # rebuild path insists on a bundle, the same way the first clone does.
  [ -f "$REPO" ] || { log "REPO must be a git bundle on this host to rebuild an existing checkout"; exit 1; }
  log "updating $DIR from $REPO (ALLOW_EXISTING_CHECKOUT=yes)"
  git -C "$DIR" pull --ff-only "$REPO" main
else
  log "cloning into $DIR"
  git clone "$REPO" "$DIR"
fi

# compose.yaml reads the addresses; .env keeps them across restarts and reboots.
if ! grep -q '^SITE_ADDRESS=' "$DIR/.env" 2>/dev/null; then
  printf 'SITE_ADDRESS=%s\nWWW_ADDRESS=%s\n' "$SITE_ADDRESS" "$WWW_ADDRESS" > "$DIR/.env"
fi

# compose.yaml defaults to a project name that is not production's, so a stray clone
# cannot act on the live stack. This is the host that is entitled to the real one.
grep -q '^COMPOSE_PROJECT_NAME=' "$DIR/.env" ||
  printf 'COMPOSE_PROJECT_NAME=%s\n' "$COMPOSE_PROJECT" >> "$DIR/.env"

cd "$DIR"
if grep -q '^APP_IMAGE=' .env; then
  # A host that has deployed runs the runner-tested image named in .env. Building here
  # would replace that tag with a host build; start what is already on the host instead.
  log "starting the deployed image"
  docker compose up -d --no-build
else
  log "building and starting"
  docker compose up -d --build
fi

log "finished at $(date -Is)"
docker compose ps
