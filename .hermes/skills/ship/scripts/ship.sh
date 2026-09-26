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
# The commit is pushed, so arming cannot merge anything the tests have not seen. Arming
# fails when the repository lacks the ruleset that requires `check` (DEPLOY.md, one-time
# setup); say so, because a silent failure here looks like a slow merge to the owner.
if gh pr merge --auto --merge "$branch" >/dev/null 2>&1; then
  armed=yes
else
  armed=no
fi
echo "Publishing: $note"
echo "Pull request: $url"
if [ "$armed" = yes ]; then
  echo "It merges itself when the tests pass (about 2 minutes) and is live about 3 minutes after that."
else
  echo "Could not arm auto-merge: the pull request is waiting for someone to merge it."
  echo "Tell the developer; the usual cause is a missing branch ruleset (DEPLOY.md, one-time setup)."
fi
