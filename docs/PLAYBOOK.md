# Standing up a site: the playbook

The order of operations for a new instance of this scaffold, who runs each step and where,
and what went wrong on the first two installations (ivangetsitdone/website and
cottonwoodlearning, September 2026) so that it does not go wrong on the hundredth. README.md
says what the site is and DEPLOY.md how production works; this is the sequence that gets a
site from an empty repository to an owner publishing over Telegram, with the exceptions
beside the steps that produce them.

`scripts/preflight.sh` checks most of what this document sets up and prints one line per
check; run it after §2 and again after §5. `tests/test_installation_names.py` checks the
rename in §1.

## 0. Before the first command

**Every command runs somewhere, as someone.** The first two installations each lost time to
"where do I run this?": the same person is `root` on the development host, a user on a
laptop, and the one clicking in GitHub's web UI, and a `sudo -u hermes` line only makes
sense on the development host, as root. Every block below starts with a comment saying
where it runs; keep that habit in anything added.

| Where | Who | What happens there |
| --- | --- | --- |
| GitHub web UI | the repository owner | settings a token without administration cannot touch: merge policy, rulesets, secrets, variables |
| laptop | the developer | creating the token, bootstrapping production over SSH, anything needing the developer's own credentials |
| development host | `root` | the shared tree, Docker, the owner's assistant's account |
| development host | `hermes` (via `sudo -u hermes` from root) | the assistant's `gh` login, git identity and gateway |
| production host | `root`, over SSH from the laptop | the bootstrap, once; after that the deploy job |

**Three names identify the instance.** Pick them before the rename pass in §1:

| Name | Example | Where it is read |
| --- | --- | --- |
| The tree | `/srv/whitelabel` | every skill `cd`s into it; the ACLs are on it |
| The Compose project | `whitelabel` (`-local` in the file, `-dev` on the dev host, bare on production) | `compose.yaml`, both `.env` files, the runtime policy test |
| The domain | `example.com` (`dev.` and `www.` in front) | `SITE['domain']`, the Caddyfiles, the Compose defaults, the suites' defaults |

**What each credential can do.** Nothing here needs a token with administration, and its
absence is a feature; when a command returns HTTP 403, the answer is to hand that step to
the owner, not to widen the token ([ADR-0011](adr/0011-private-repository.md),
[ADR-0013](adr/0013-owner-assistant-account.md)).

| Credential | Has | Cannot | So |
| --- | --- | --- | --- |
| The developer's assistant's token (fine-grained, this repository) | contents, pull requests, issues, workflows, actions read | administration, secrets, variables, check rollups, fork, create repositories | `gh pr checks` fails (`statusCheckRollup` 403): use `gh run list --branch`, `gh run watch`, `gh run view`. Settings and rulesets are the owner's clicks. |
| The owner's assistant's token (fine-grained, this repository) | contents, pull requests, issues, actions read | workflows, administration | it can ship and keep the to-do list; it cannot change the pipeline |
| The deploy job's `GITHUB_TOKEN` | contents read, packages write, lent to production for one deploy | anything after the job ends | production holds no credential between deploys |

## 1. The repository

```sh
# GitHub web UI, the owner
#   New repository from this template, private. Then Settings → Labels: create `dev` and `owner`
#   (the to-do script applies them and does not create them), or from the laptop:
gh label create dev   -R OWNER/REPO --description "Work for the developer, dispatched by the owner's assistant"
gh label create owner -R OWNER/REPO --description "The owner's own items"
```

**The rename pass**, in a clone on the laptop or on the development host as root. Replace
the three names everywhere they occur, then run the test that says whether one was missed:

```sh
# laptop, or development host as root, in the clone
git grep -l 'whitelabel'     # the tree path /srv/whitelabel and the project whitelabel(-local|-dev)
git grep -l 'example\.com'   # the domain, in code and in the skills
python3 tests/test_installation_names.py
```

The test takes the ship script's `cd` line, `name:` in `compose.yaml` and `SITE['domain']`
as the truth and checks that the skills, the working rules, DEPLOY.md, the Caddyfiles, the
Compose files, `.env.example` and the suites' defaults agree. It runs in `check` as well,
so a miss fails the first pull request rather than the first `/ship`. `scripts/bootstrap.sh`
also carries the repository URL; the bundle path overrides it, but set it.

**The developer's assistant's token.** A fine-grained personal access token, on the
developer's account, limited to this one repository: Contents, Pull requests, Issues and
Workflows read/write, Actions read. Not Administration. The token editor may not offer a
permission that makes `gh pr checks` work; do not go looking for one, the `gh run` commands
in §4 do the job. Log in on the development host from a file, never by pasting into a
prompt: `gh auth login --with-token` reads standard input and looks like a hang when it is
waiting for a paste.

```sh
# development host, as root
gh auth login --with-token < /root/developer-token.txt && shred -u /root/developer-token.txt
gh auth status
```

**Push the tree to `main` once** before §2: the ruleset editor offers only status checks
that have already run, and `check` has to exist as a name before a rule can require it.

## 2. The merge policy

Three settings in the web UI, all the owner's, recorded in DEPLOY.md "One-time setup" and
[ADR-0014](adr/0014-merge-commits-and-a-required-check.md): auto-merge on, squash and
rebase merging off, and the ruleset `require_pr_workflow` on `main` (restrict deletions,
block force pushes, require the status check `check`, strict mode off, no bypass actors).
Then, from any clone:

```sh
# laptop, or development host as root
scripts/preflight.sh OWNER/REPO
```

Every line should read `ok` or `?`; a `MISSING` line names the setting and where it is.
What it looks like when this step is skipped: a pull request the owner's assistant opened
turns green and sits there, or merges the instant it is armed. The first installation ran
that way for a day. The developer's own pull requests are unaffected, because a person
merges those (§8).

## 3. The development host

A small droplet is enough (1 GB RAM) if it has swap; the image build and the Vite watcher
do not fit beside Docker without it. DEPLOY.md §1 has the Docker install and the `.env`.

```sh
# development host, as root
fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile && echo '/swapfile none swap sw 0 0' >> /etc/fstab
gh repo clone OWNER/REPO /srv/<tree> && cd /srv/<tree>
printf 'SITE_ADDRESS=dev.<domain>\nWWW_ADDRESS=:8080\nCOMPOSE_PROJECT_NAME=<project>-dev\nCOMPOSE_FILE=compose.yaml:compose.dev.yaml\n' > .env
docker compose up -d --build
curl -fsS https://dev.<domain>/healthz
```

`dev.<domain>` needs a DNS-only A record before Caddy's first start; until it has one,
`SITE_ADDRESS=:80`. The tree is the live development site from this moment: an edit is on
the site when it is saved. Keep `.env` out of git (it is) and never add `COMPOSE_FILE` to
production's.

## 4. Production and the pipeline

DEPLOY.md §2 is the procedure; this is the order and the things around it.

1. **`DEPLOY_HOST`** as a repository variable and the two secrets (`DEPLOY_KEY`,
   `DEPLOY_KNOWN_HOSTS`), from the laptop with `gh` or in the web UI. Until the variable
   exists a push to `main` runs `check` and stops, green, which is the right state while
   §3 and §5 are in progress.
2. **Bootstrap production from a bundle**, from the laptop. The host never sees a GitHub
   credential; the deploy job lends it one. Keep the developer's own SSH key in the host's
   `authorized_keys` beside the CI key: it is the disaster-recovery path, and the
   development host has no SSH access to production by design.
3. **The `www` record**, or `WWW_ADDRESS=:8080` until it exists: Caddy retries a
   certificate for a name that does not resolve, forever.
4. **The first push to `main`** deploys. Watch it with the token you have:

```sh
# development host, as root, or the laptop
gh run list --workflow Deploy --branch main --limit 1          # id, status
gh run watch <id> --exit-status                                # blocks until done
gh run view <id> --json conclusion,jobs -q '.jobs[] | "\(.name): \(.conclusion)"'
curl -s -o /dev/null -w '%{http_code}\n' https://<domain>/
```

`gh pr checks` and check annotations need a permission the token does not have; the
three commands above do not. A red `verify` with a handshake timeout after a green
`deploy` is the host being starved, not the commit: DEPLOY.md §2b, swap. Production on a
1 GB droplet without swap went unresponsive for four minutes during back-to-back deploys
on the second installation.

## 5. The owner's assistant

[ADR-0013](adr/0013-owner-assistant-account.md) has the account and the ACLs; do them in
its order. Then the parts the ADR leaves to "the agent's configuration":

**Identities.** Each account has its own global git identity and its own `gh` login. Never
set a repository-local `user.name` in the shared tree: it would sign every commit from that
tree, whoever made it, and the audit trail in `git log` is how the two assistants' work is
told apart.

```sh
# development host, as root
sudo -u hermes git config --global user.name Hermes
sudo -u hermes git config --global user.email hermes@<host>
sudo -u hermes gh auth login --with-token < /home/hermes/token.txt && shred -u /home/hermes/token.txt
git config --local --unset-all user.name 2>/dev/null; git config --local --unset-all user.email 2>/dev/null
```

**One home.** The gateway's systemd unit sets `HERMES_HOME`; every `hermes` command run by
hand must use the same value, or `hermes config set` and `hermes skills list` act on a
profile the bot never reads. Read it from the unit first:

```sh
# development host, as root
grep HERMES_HOME /home/hermes/.config/systemd/user/hermes-gateway.service
sudo -u hermes HERMES_HOME=<that value> hermes skills list
```

**Skills, persona, menu.** `skills.external_dirs` in the gateway's `config.yaml` points at
`/srv/<tree>/.hermes/skills`, and the tree is trusted for project skills. `SOUL.md` in
`HERMES_HOME` is the persona; the one the setup wizard leaves there introduces the bot as
"Hermes Agent, built by Nous Research", so replace it before the owner meets it (issue #3
proposes shipping one). Hermes fills the Telegram `/` menu with its own commands, so the four
skills appear only with this block; and `/menu`, which owners type, is not a command until
it is aliased:

```yaml
# development host, the gateway's config.yaml (HERMES_HOME from the unit)
platforms:
  telegram:
    extra:
      command_menu:
        max_commands: 60
        priority_mode: prepend
        priority: [site, todo, recent, ship]
quick_commands:
  menu: {type: alias, target: /help}
```

Before naming a skill, check it is not a built-in: the second installation's `tasks` skill
never fired because `/tasks` is Hermes's own, and became `todo`.

**Telegram.** A bot from BotFather; a group with the owner, the developer and the bot; the
bot promoted to administrator (add it as a member by its `@name` first, then promote it
under the group's Administrators) so it reads every message without touching BotFather's
privacy mode. Access control is membership of that group:
`TELEGRAM_GROUP_ALLOWED_CHATS=<group id>` in the gateway's `.env`; the id (negative, usually
`-100…`) is in the gateway log the first time anyone writes in the group. Leave
`GATEWAY_ALLOW_ALL_USERS` unset (issue #4). If one gateway serves more than one site,
each site is a profile: a `gateway.profile_routes` entry maps the group's `chat_id` to the
profile, and `group_sessions_per_user: false` goes in the gateway's own `config.yaml`,
because the gateway, not the routed profile, decides how sessions are keyed. Issue #11 has the
configuration.

**Restart and test** as the assistant, then in the group:

```sh
# development host, as root
sudo -u hermes HERMES_HOME=<value> hermes gateway restart
sudo -u hermes HERMES_HOME=<value> hermes -z "what can you do?"      # -p <profile> if profiles are in use
```

After any provider re-login, send `/new` in every open chat: a long-lived session keeps the
credential it started with, and a restart does not help because sessions are persisted
(issue #5).

## 6. The first ship

Prove the whole path with a change that cannot break anything: the owner's assistant adds
one line to `app/HANDOFF.md` and runs `/ship`. Expected, in order: a `hermes/<timestamp>`
branch; a pull request whose body says it auto-merges; `check` green in about two minutes;
the merge commit on `main`; `deploy` and `verify` green; the line on the live site's
repository within five minutes. Then, in the tree, `git pull --rebase --autostash`.

If the pull request turns green and stays open, §2 was skipped or `check` was renamed
(`tests/test_ship_pipeline.py` pins the name). If it merged the instant it was armed, same
cause. If `/ship` printed "waiting for someone to merge it", arming failed and the ruleset
is the first thing to check. If the change vanished from the dev site after shipping, the
tree was reset instead of pulled: ADR-0014's consequences, and issue #2 for keeping the
tree current between ships.

## 7. The branding pass

The owner's assistant does copy, the `SITE` block, services, colours and photos; the
`site` skill is the procedure. What the second installation learned about everything else:

- **Artwork arrives as a file in the chat**, often a JPEG or a "vector" that is a masked
  raster. It goes to `app/inbox/` with a `(dev)` issue, never into `app/brand/`. The
  developer traces or redraws it, keeps the editable master outside the served directory
  (`content/brand/`), cuts the served files from the master with a script, and never
  hand-edits a generated file. Issue #9 proposes the scripts.
- **A generator overwrites what the owner chose.** The second site's brand script rewrote
  the watermark the owner had picked from an earlier version; the fix was to make each
  chosen asset an opt-in flag on the script. Decide, per served file, whether it is
  generated or chosen, and make the script refuse to touch the chosen ones.
- **Review folders come out once a choice is made**; the inbox is a handoff, not storage.
  Delete the received file when the `(dev)` issue that consumed it closes, or it sits
  untracked in the shared tree indefinitely (issue #10).
- **Copy written from other people's material** quotes a sentence only when it was read
  verbatim, with a link beside it, and paraphrases everything else with attribution;
  figures, outcomes and legal specifics stay out unless the owner confirms them. The
  owner's assistant will one day be asked in good faith for wording the owner must not
  publish; issue #7 proposes making the site's rules a test.
- **Photos** go through `app/photos/` and the `SITE` slots, with no developer
  ([ADR-0012](adr/0012-photos.md)); a photograph the assistant can see but has no path
  for was compressed by Telegram, and the owner sends it again as a file.

## 8. How the developer's assistant works, day to day

- **Start of a session:** `gh issue list --label dev`, `git status`, and the top of
  `app/HANDOFF.md`. Anything uncommitted under `app/` or `frontend/` goes out with the
  owner's next `/ship`.
- **Stage by name.** The tree is shared; `git add -A` would ship the other assistant's
  half-finished work. `.claude/settings.json` denies it.
- **Every change is a pull request**, on a `claude/<slug>` branch, pushed with
  `git push origin HEAD:refs/heads/claude/<slug>`. Direct pushes to `main` are refused by the
  ruleset for everyone; that is the design.
- **A person merges it.** The developer's assistant does not run `gh pr merge`: an
  unattended session is refused it as a merge without review, `.claude/settings.json`
  denies it, and the owner's assistant's `/ship` is the only thing that arms auto-merge.
  So the message that reports the pull request puts the merge command first, where the
  developer will read it: `gh pr merge <n> --merge`, or the button. After "merged":
  `git pull --rebase --autostash` in the tree, then the three `gh run` commands from §4
  and a `curl` of the live site. Never chain `cmd | tail` with `&&`; the exit status is
  `tail`'s ([ADR-0015](adr/0015-a-person-merges-the-developers-pull-requests.md)).
- **When a command returns 403**, say which setting it is and who can change it, and
  move on. The token is narrow on purpose; the fix is a click by the owner or a step done
  from the laptop, not a wider token.
- **Dependabot majors fail `check` on purpose.** The second site's htmx 2 → 4 and node 22
  → 25 bumps were both red until the code was migrated (htmx 4 renames the swap events and
  makes `hx-boost` inheritance explicit); the gate did its job. Read the changelog, migrate
  on the Dependabot branch, then merge (issue #12).
- **Commit subjects** carry an area prefix (`site:`, `brand:`, `docs:`, `ci:`, `tests:`,
  `hermes:`, `deps:`), because `git log` in a shared tree is read by two assistants.
- **Durable decisions** go in `docs/adr/`, live questions in `docs/open-questions.md`,
  and nothing about test results that a command did not print.

## 9. Exceptions

| Symptom | Cause | Who | Do |
| --- | --- | --- | --- |
| `gh pr checks`: `Resource not accessible by personal access token (statusCheckRollup)` | the token has no check read | developer's assistant | `gh run list --branch <branch>`, `gh run view <id>`; do not widen the token |
| `gh variable list`, `gh secret list`, branch protection: HTTP 403 | no administration | owner | confirm in the web UI; `preflight.sh` prints these as `?` |
| The developer's assistant is refused `gh pr merge --auto` ("merge without review"), or the settings deny it | by design | developer | merge by hand; the assistant puts the command at the top of its message |
| The owner's pull request is green and still open hours later | no ruleset requires `check`, or the job was renamed | owner (web UI) | DEPLOY.md one-time setup; `preflight.sh`; `tests/test_ship_pipeline.py` |
| The owner's pull request merged the instant it was armed | same, with `check` already green | owner | same; the ship script pushes every commit before arming |
| The ruleset editor offers no `check` to require | it has never run here | developer | push the workflow to `main` once, then create the rule |
| `/ship` says "Nothing to publish" after the owner edited | the edit is outside `app/` and `frontend/`, or already shipped | developer | `git status`; move the change or explain |
| `/ship` says "waiting for someone to merge it" | arming failed | developer | the ruleset first, then the assistant's token's pull-request permission |
| The development site is behind `main` after a developer merge | the ship script pulls only when it runs | developer | `git pull --rebase --autostash` after every merge; issue #2 |
| `git push origin main` refused | the ruleset | anyone | open a pull request |
| `verify` red with a TLS or read timeout, `deploy` green | the host was starved, no swap | owner with SSH to production | DEPLOY.md §2b; check the site by hand |
| Caddy keeps retrying a certificate | DNS not pointing here, a proxied record, or no `www` record | owner (DNS) | `WWW_ADDRESS=:8080` until the record exists; DNS-only records |
| `gh auth login --with-token` appears to hang | it reads the token from standard input | whoever logs in | `< file`, then `gh auth status`; shred the file |
| "Where do I run this?" | the instruction did not say | whoever wrote it | every block names host and account; `sudo -u hermes` is run as root on the development host |
| The bot is silent in the group | not an administrator, or the group id is not in `TELEGRAM_GROUP_ALLOWED_CHATS` | developer | id from the gateway log; promote the bot; restart the gateway |
| The bot says it is "Hermes Agent, built by Nous Research" | the stock `SOUL.md` | developer | write the persona; issue #3 |
| The skills are missing from the Telegram `/` menu | the menu is capped and full of built-ins | developer | the `command_menu` block in §5; issue #4 |
| A skill never fires | its name is a Hermes built-in (`/tasks`) | developer | rename it; check the built-ins first |
| `hermes config set` changes nothing the bot does | a different `HERMES_HOME` | developer | the unit's value, every time; issue #5 |
| The gateway returns 401 after a provider re-login | the session pinned the old credential | owner | `/new` in every open chat; issue #5 |
| The assistant can see an image but has no file path | Telegram compressed it | owner | send it again as a file |
| Regenerated brand assets overwrote a chosen one | the generator writes everything | developer | chosen assets are opt-in flags on the script (§7) |
| Untracked files pile up in `app/inbox/` | consumed and never removed | developer | delete them when the issue closes; issue #10 |
| Root's commits are signed as Hermes, or the reverse | a repository-local `user.name` in the shared tree | developer | per-account global identities; `git config --local --unset-all user.name` |
| A Dependabot pull request is red | a major bump changed an API | developer | migrate on its branch, then merge; the gate did its job |
| Someone is about to run `docker compose down -v` | it deletes the certificate volume | anyone | do not; `.claude/settings.json` denies it |
| `gh repo fork` or repository creation: HTTP 403 | the token covers one repository | the developer, from the laptop | prepare a branch and a bundle under `recovery/`, hand over the push; do not widen the token |
