#!/usr/bin/env bash
# Publish the owner's edits: commit app/ and frontend/, open a PR, arm auto-merge.
# Merge commits keep this tree fast-forwardable afterwards (see app/HANDOFF.md).
set -euo pipefail
cd /srv/whitelabel
note=${*:-owner changes from the dev site}
git pull -q --rebase --autostash origin main
if git diff --quiet -- app frontend && git diff --cached --quiet -- app frontend && [ "$(git rev-list --count origin/main..HEAD)" = 0 ]; then
  echo "Nothing to publish: the live site already has everything on dev."; exit 0
fi
git add app frontend
if ! git diff --cached --quiet; then
  git commit -q -m "site: $note"
fi
branch="hermes/$(date +%Y%m%d-%H%M%S)"
git push -q origin "HEAD:refs/heads/$branch"
url=$(gh pr create --base main --head "$branch" --title "site: $note" \
  --body "Published from the dev site by the site assistant. Auto-merges when check passes.")
gh pr merge --auto --merge "$branch" >/dev/null
echo "Publishing: $note"
echo "Pull request: $url"
echo "It merges itself when the tests pass (about 2 minutes) and is live about 3 minutes after that."
