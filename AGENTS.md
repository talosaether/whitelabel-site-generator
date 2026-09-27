# Project working rules

- Treat this directory as the project root; run project commands here. Do not scatter
  project files in `/root`, `/opt`, or `/tmp`.
- Start by reading README.md, MISSION.md, `git status`, and recent Git history. Preserve
  existing work.
- Keep source, tests, deployment configuration, and durable decisions in the repository.
  Document necessary host-level changes and reconstruction steps.
- Use ignored `recovery/` for diagnostic logs and raw session evidence. Never commit
  secrets, raw session logs, dependencies, or generated assets.
- Distinguish configuration/syntax checks from build, runtime, and browser verification.
- Keep README.md as onboarding, not a changelog: durable decisions belong in `docs/adr/`,
  live action items in `docs/open-questions.md`. Do not invent test results.
- **Two hosts, two rules.** The development host (`dev.example.com`) serves this
  working tree live: an edit here is on that site as soon as it is saved, with no commit.
  Production (`example.com`) serves `main` only, deployed by
  `.github/workflows/deploy.yml` after the runner has built and tested the commit. So:
  iterate freely in the tree, check the result on the dev host, and treat a push to `main`
  as a production release. Pull requests run the same tests without deploying.
- The production host's checkout is reset on each deploy; never keep work only on that host.
- **The dev tree is shared.** `/srv/whitelabel` is edited by two assistants: Claude
  Code as root, and Hermes as `hermes`, who works with the site owner and may write only
  `app/` and `frontend/`. `app/HANDOFF.md` says who does what and how Hermes ships a change
  (a PR that auto-merges when `check` is green). Stage files by name, never `git add -A`:
  the other assistant may have work in progress in the same tree.
- **Pull requests opened by the developer's assistant are the developer's to merge.** Open
  the PR, put the merge command at the top of the message (`gh pr merge <n> --merge`), and
  after the merge `git pull --rebase --autostash` here and watch the deploy with `gh run`.
  Never arm auto-merge: `.claude/settings.json` denies `gh pr merge`, and the owner's `/ship`
  is the only thing that arms it. `docs/PLAYBOOK.md` is the installation order and the
  exceptions; `scripts/preflight.sh` checks the setup (ADR-0015).
- `compose.yaml` names its project `whitelabel-local` so a stray clone cannot act on a live
  stack. The dev host's `.env` opts into `whitelabel-dev` and the overlay; production's
  opts into `whitelabel`. Do not "fix" the `name:` line, and never add `COMPOSE_FILE` to
  production's `.env`.
