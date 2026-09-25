# 13. The owner's assistant runs as an unprivileged account

Status: accepted

Builds on [ADR-0010](0010-two-hosts.md), which made the development host's checkout a
tree shared by two assistants.

## Context

The owner's assistant (`hermes`) may write only `app/` and `frontend/`: its skills say
so, and ACLs on the tree enforce it. The account was created with passwordless sudo
(`hermes ALL=(ALL) NOPASSWD:ALL` in `/etc/sudoers.d/hermes`) and membership of the
`sudo` group, which made both the rule and the ACLs decorative: one `sudo` and the
assistant could rewrite its own skills, the deploy configuration, or the tests that gate
production. Nothing it runs needs root. Its gateway is a user-level systemd unit kept
alive by `loginctl enable-linger`; its skills call `git`, `gh`, `curl` and `python3`
as itself; the containers are managed by the developer.

## Decision

The account is an ordinary user with no privilege escalation of any kind, and the ACLs are
the boundary.

- No `sudoers` entry, no membership of `sudo`, `admin` or `docker`. Its password is
  locked; it is reached by the gateway service and by `root` with `sudo -u hermes`.
- The tree at `/srv/whitelabel` is owned by `root`. The assistant has read access to all of it,
  and write access, with a default ACL so new files inherit it, to exactly three places:
  `app/`, `frontend/`, and `.git/` so `/ship` can commit and push.
- `.hermes/` is root-owned and read-only to the assistant. The skills are the whole of
  what it knows about the site, and it cannot change them.
- Its GitHub token is fine-grained, limited to this repository, with contents, pull
  requests and issues; no administration.
- Anything that needs root, the Docker daemon, or a file outside its three directories is
  a `(dev)` issue for the developer. That is the design, not a limitation to work around.

## Reconstruction

On a fresh development host, as root:

```sh
useradd --create-home --shell /bin/bash hermes && passwd -l hermes
loginctl enable-linger hermes
setfacl -m u:hermes:rx /srv/whitelabel
setfacl -R -m u:hermes:rwx -m d:u:hermes:rwx /srv/whitelabel/app /srv/whitelabel/frontend /srv/whitelabel/.git
sudo -u hermes git config --global --add safe.directory /srv/whitelabel
sudo -u hermes git config --global user.name Hermes
sudo -u hermes gh auth login          # the assistant's own fine-grained token
```

Then point the agent's `skills.external_dirs` at `/srv/whitelabel/.hermes/skills`, enable its
messaging platform, and install its gateway as a user unit. Check with
`sudo -l -U hermes`, which must say the user is not allowed to run sudo, and
`id hermes`, which must list only its own group.

## Consequences

- A compromised or confused assistant can damage copy, the palette and the photos, all of
  which are recoverable from Git and never reach production without a green `check`.
  It cannot touch the pipeline, the tests, the deploy secrets, or its own instructions.
- Host maintenance that the assistant used to be able to do for itself now goes through
  the developer. Nothing it does today needed it.
- Widening the boundary means changing the ACL and the skill's rule together; either
  alone is a lie.
