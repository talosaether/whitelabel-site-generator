#!/usr/bin/env bash
# Recent site activity for the owner: unpublished edits, recent commits, pull requests, last deploy.
set -uo pipefail
cd /srv/whitelabel
git fetch -q origin main 2>/dev/null || true
echo "Unpublished edits on dev:"
changed=$(git status --short -- app frontend | grep -vE 'app/(HANDOFF\.md|inbox/)' || true)
if [ -n "$changed" ]; then echo "$changed" | sed 's/^/  /'; else echo "  (none — dev matches what is published or waiting)"; fi
ahead=$(git rev-list --count origin/main..HEAD 2>/dev/null || echo 0)
[ "$ahead" -gt 0 ] && echo "  plus $ahead commit(s) on dev not yet on main"
echo; echo "Recent changes:"
git log -8 --format='  %ad  %an: %s' --date=short
echo; echo "Pull requests:"
gh pr list --state all --limit 5 --json number,title,state,author,mergedAt \
  -q '.[] | "  #\(.number) \(.title) — \(if .state=="MERGED" then "published" elif .state=="OPEN" then "waiting" else "closed" end)"' 2>/dev/null || echo "  (could not reach GitHub)"
echo; echo "Last publish to production:"
gh run list --workflow Deploy --branch main --limit 1 --json conclusion,status,createdAt,displayTitle \
  -q '.[0] | "  \(.createdAt | sub("T.*";"")) \(.displayTitle) — \(.conclusion // .status | sub("success";"ok") | sub("failure";"FAILED"))"' 2>/dev/null || echo "  (could not reach GitHub)"
echo; echo "Waiting on the developer: $(gh issue list --state open --label dev --json number -q length 2>/dev/null || echo '?') item(s) — /todo for the list"
echo; echo "Look:  dev https://dev.example.com   live https://example.com"
