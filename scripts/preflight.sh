#!/usr/bin/env bash
# Preflight: is this repository, and the host this runs on, set up the way the process
# assumes? Prints one line per check. Read-only; nothing is changed.
#
#   ok       the check passed
#   MISSING  the check failed; the line says who fixes it and where
#   ?        this token cannot see the setting (HTTP 403); ask the repository owner to
#            confirm it in the web UI. A fine-grained token without administration cannot
#            read variables, secrets, branch protection or check rollups, by design.
#
# Usage: scripts/preflight.sh [OWNER/REPO]     (default: the repository this checkout tracks)
# Exit status is 1 if anything is MISSING. `?` lines do not fail it.
#
# docs/PLAYBOOK.md walks through the setup this verifies.
set -uo pipefail

repo=${1:-$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || true)}
[ -n "$repo" ] || { echo "Which repository? scripts/preflight.sh OWNER/REPO"; exit 2; }
missing=0
ok()      { printf 'ok       %s\n' "$1"; }
bad()     { printf 'MISSING  %s\n' "$1"; missing=1; }
cannot()  { printf '?        %s\n' "$1"; }
check()   { if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 (is: ${2:-unset}; $4)"; fi; }
api()     { gh api "$@" 2>/dev/null; }
# api_or_403 <path> <jq>: prints the value, or the literal 403 when the token cannot see it.
api_or_403() { local out; if out=$(gh api "$1" -q "$2" 2>&1); then printf '%s' "$out"; elif grep -q 'HTTP 403' <<<"$out"; then printf 403; else printf 'error'; fi; }

echo "Repository $repo"
login=$(api user -q .login)
if [ -n "$login" ]; then ok "gh is logged in as $login"; else bad "gh is not logged in (gh auth login --with-token < a root-only file)"; fi

settings=$(api "repos/$repo" -q '{private: .private, auto: .allow_auto_merge, merge: .allow_merge_commit, squash: .allow_squash_merge, rebase: .allow_rebase_merge, delete: .delete_branch_on_merge}')
if [ -z "$settings" ]; then
  bad "cannot read repos/$repo at all: wrong name, or the token does not cover this repository"
else
  field() { jq -r ".$1" <<<"$settings"; }
  ok "visibility: $([ "$(field private)" = true ] && echo private || echo public)"
  check "auto-merge allowed"        "$(field auto)"   true  "Settings → General → Pull Requests → Allow auto-merge"
  check "merge commits allowed"     "$(field merge)"  true  "Settings → General → Pull Requests → Allow merge commits"
  check "squash merging off"        "$(field squash)" false "Settings → General → Pull Requests, untick Allow squash merging (ADR-0014)"
  check "rebase merging off"        "$(field rebase)" false "Settings → General → Pull Requests, untick Allow rebase merging (ADR-0014)"
  [ "$(field delete)" = true ] && ok "merged branches are deleted automatically" || cannot "merged branches are kept; optional: Settings → General → Automatically delete head branches"
fi

rules=$(api "repos/$repo/rules/branches/main" -q '.[].type' | sort -u | tr '\n' ' ')
case "$rules" in
  *deletion*non_fast_forward*required_status_checks*)
    ctx=$(api "repos/$repo/rules/branches/main" -q '.[] | select(.type=="required_status_checks") | .parameters.required_status_checks[].context' | tr '\n' ' ')
    if grep -qw check <<<"$ctx"; then ok "ruleset on main requires the status check \`check\` (rules: $rules)"; else bad "the ruleset on main requires [$ctx], not \`check\`: edit the ruleset, Require status checks → check"; fi ;;
  "") bad "no ruleset applies to main; auto-merge has nothing to wait for (DEPLOY.md, one-time setup: ruleset require_pr_workflow)" ;;
  *)  bad "ruleset on main has [$rules]; needs deletion, non_fast_forward and required_status_checks" ;;
esac

labels=$(api "repos/$repo/labels?per_page=100" -q '.[].name' | tr '\n' ' ')
for l in dev owner; do grep -qw "$l" <<<"$labels" && ok "label \`$l\` exists" || bad "label \`$l\` missing: gh label create $l -R $repo (todo.sh applies labels, it does not create them)"; done

workflows=$(api "repos/$repo/actions/workflows" -q '.workflows[].name' | tr '\n' ' ')
grep -qw Deploy <<<"$workflows" && ok "the Deploy workflow is registered" || bad "no Deploy workflow: push .github/workflows/deploy.yml to main once"

case "$(api_or_403 "repos/$repo/actions/variables/DEPLOY_HOST" .value)" in
  403) cannot "DEPLOY_HOST variable: this token cannot read Actions variables; the owner confirms it under Settings → Secrets and variables → Actions → Variables" ;;
  error|"") cannot "DEPLOY_HOST variable is not set: pushes to main run check and stop (fine until production exists)" ;;
  *) ok "DEPLOY_HOST is set" ;;
esac
secrets=$(api_or_403 "repos/$repo/actions/secrets" '.secrets[].name')
case "$secrets" in
  403) cannot "DEPLOY_KEY / DEPLOY_KNOWN_HOSTS secrets: this token cannot list secrets; the owner confirms them, or the first deploy run says which is missing" ;;
  *) for s in DEPLOY_KEY DEPLOY_KNOWN_HOSTS; do grep -qw "$s" <<<"$secrets" && ok "secret $s is set" || bad "secret $s is missing (DEPLOY.md, one-time setup)"; done ;;
esac

last=$(gh run list -R "$repo" --workflow Deploy --branch main --limit 1 --json conclusion,createdAt -q '.[0] | "\(.conclusion // "running") \(.createdAt | sub("T.*";""))"' 2>/dev/null)
[ -n "$last" ] && ok "last Deploy run on main: $last" || cannot "no Deploy run on main yet"

# The development host, if this is it.
tree=$(sed -n 's/^cd \(\/srv\/.*\)$/\1/p' .hermes/skills/ship/scripts/ship.sh 2>/dev/null | head -1)
if [ -n "$tree" ] && [ -d "$tree" ]; then
  echo; echo "Development host, tree $tree"
  [ "$(realpath "$tree")" = "$(git rev-parse --show-toplevel 2>/dev/null)" ] && ok "this checkout is the tree the skills cd into" || bad "this checkout is not $tree; the skills will act on the other one"
  if [ -f "$tree/.env" ]; then
    grep -q '^COMPOSE_FILE=compose.yaml:compose.dev.yaml' "$tree/.env" && ok ".env layers the development overlay" || bad ".env has no COMPOSE_FILE=compose.yaml:compose.dev.yaml (first block of .env.example)"
    grep -q -- '-dev$' <(sed -n 's/^COMPOSE_PROJECT_NAME=//p' "$tree/.env") && ok ".env opts into the -dev Compose project" || bad ".env does not set COMPOSE_PROJECT_NAME=<project>-dev"
  else bad "no .env in $tree"; fi
  if id hermes >/dev/null 2>&1; then
    ok "account hermes exists"
    if [ "$(id -u)" = 0 ]; then
      sudo -l -U hermes 2>/dev/null | grep -q 'not allowed to run sudo' && ok "hermes cannot sudo" || bad "hermes can sudo (ADR-0013: remove /etc/sudoers.d/hermes and the sudo group)"
      [ "$(id -Gn hermes | wc -w)" = 1 ] && ok "hermes is in no extra groups" || bad "hermes is in extra groups: $(id -Gn hermes)"
    fi
    for d in app frontend .git; do
      getfacl -p "$tree/$d" 2>/dev/null | grep -q '^default:user:hermes:rwx' && ok "hermes has a default rwx ACL on $d" || bad "no default ACL for hermes on $d (setfacl -R -m u:hermes:rwx -m d:u:hermes:rwx $tree/$d)"
    done
    getfacl -p "$tree/.hermes" 2>/dev/null | grep -q 'user:hermes:rwx' && bad "hermes can write .hermes/ and so its own skills" || ok "hermes cannot write .hermes/"
    sudo -u hermes gh auth status >/dev/null 2>&1 && ok "hermes is logged in to gh" || bad "hermes has no gh login (sudo -u hermes gh auth login --with-token < a hermes-only file)"
    home=$(sudo -u hermes sh -c 'echo ${HERMES_HOME:-$HOME/.hermes}' 2>/dev/null)
    grep -qs "^  *- $tree/.hermes/skills" "$home/config.yaml" && ok "the gateway's skills.external_dirs points at $tree/.hermes/skills" || cannot "cannot confirm skills.external_dirs in $home/config.yaml (HERMES_HOME may differ; see the playbook)"
  else bad "no hermes account (ADR-0013, reconstruction)"; fi
  [ -n "$(swapon --show --noheadings 2>/dev/null)" ] && ok "swap is on" || bad "no swap: a 1 GB host stalls under the image build (DEPLOY.md §2b)"
fi

exit $missing
