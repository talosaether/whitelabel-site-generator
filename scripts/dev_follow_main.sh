#!/usr/bin/env bash
# Keep the development host's checkout on main, and restart or rebuild only when the
# change needs it. Meant for a systemd timer (DEPLOY.md §1); safe to run by hand.
#
#   scripts/dev_follow_main.sh [checkout]        default /srv/whitelabel
#
# The tree is a shared workspace (ADR-0010): the owner's unshipped edits are stashed
# around the pull and put back. Merges are merge commits (ADR-0014), so local main, which
# the ship script fast-forwards onto shipped commits, is always an ancestor of origin/main
# and the pull is a fast-forward. If it is not, or the stash does not apply cleanly, this
# exits non-zero and touches nothing else; `journalctl -u dev-follow-main` shows it.
set -euo pipefail
cd "${1:-/srv/whitelabel}"

[ "$(git branch --show-current)" = main ] || { echo "not on main; leaving it alone" >&2; exit 1; }

before=$(git rev-parse HEAD)
git pull -q --ff-only --autostash origin main
after=$(git rev-parse HEAD)
[ "$before" != "$after" ] || exit 0

changed() { ! git diff --quiet "$before" "$after" -- "$@"; }

if changed Dockerfile requirements.txt frontend/package.json frontend/package-lock.json; then
  # Build inputs changed: rebuild the app image, and restart the asset watcher so its
  # `npm ci` sees the new lockfile. This is the one case that costs the small host a build.
  docker compose up -d --build
  docker compose restart assets
elif changed compose.yaml compose.dev.yaml; then
  docker compose up -d
fi
if changed Caddyfile Caddyfile.dev; then
  docker compose exec -T caddy caddy reload --config /etc/caddy/Caddyfile </dev/null
fi
echo "dev checkout: ${before:0:7} -> ${after:0:7}"
