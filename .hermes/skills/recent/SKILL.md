---
name: recent
description: "What changed on the website lately, and whether it has reached production."
version: 1.0.0
author: the developer
metadata:
  hermes:
    tags: [website, status, whitelabel]
    related_skills: [site, todo, ship]
---

# Recent changes

Run, from `/srv/whitelabel`:

```sh
bash .hermes/skills/recent/scripts/recent.sh
```

Relay the output as it is. If the owner asks what a line means: "on dev" is the working
copy at <https://dev.example.com>; "published" means it is on
<https://example.com>; a pull request "waiting" is still being tested and
publishes itself when the tests pass; "failed" means it did not pass and the developer
needs to look — add a `(dev)` task.
