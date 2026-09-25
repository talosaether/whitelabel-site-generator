---
name: ship
description: "Publish the changes on the dev site to the live site."
version: 1.0.0
author: the developer
metadata:
  hermes:
    tags: [website, publish, whitelabel]
    related_skills: [site, recent, todo]
---

# Ship to production

`/ship` means the owner has looked at <https://dev.example.com> and wants it
live. Everything under `app/` and `frontend/` that differs from what is published goes
out together.

Run, from `/srv/whitelabel`, with a short description of what is being published:

```sh
bash .hermes/skills/ship/scripts/ship.sh "new home headline and phone number"
```

The script commits, opens a pull request and arms it to merge itself when the automated
tests pass; merging publishes. Relay the script's output. Then tell the owner: the tests
take about two minutes and publishing about three more, `/recent` shows whether it went
through, and if it says FAILED nothing changed on the live site and the developer needs to
look (`/todo add (dev) …`).

Never run the git commands by hand; the script is the whole procedure.
