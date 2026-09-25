---
name: todo
description: "The website to-do list: show it, add to it, reword an item, add a note, or mark it done."
version: 3.0.0
author: the developer
metadata:
  hermes:
    tags: [website, todo, issues, whitelabel]
    related_skills: [site, recent, ship]
---

# To-do list

The list is the repository's GitHub issues. An item marked **(dev)** is work for the
developer, who watches the `dev` label; anything else is for the owner or you. The
script is the only thing that touches the list.

| Owner says | Run, from `/srv/whitelabel` |
| --- | --- |
| `/todo` | `bash .hermes/skills/todo/scripts/todo.sh` |
| `/todo add <text>` | `bash .hermes/skills/todo/scripts/todo.sh add "<title>" "<details>"` |
| `/todo edit <n> <text>` | `bash .hermes/skills/todo/scripts/todo.sh edit <n> "<title>" "<details>"` |
| `/todo note <n> <text>` | `bash .hermes/skills/todo/scripts/todo.sh note <n> "<text>"` |
| `/todo done <n>` | `bash .hermes/skills/todo/scripts/todo.sh done <n>` |

Relay the output as it is.

## Writing an item

An item has a **title** and **details**, like a ticket. You write both; the owner talks
in plain sentences and it is your job to turn that into a tidy entry.

- **Title:** one line, under 90 characters, the outcome in plain words. `Contact page:
  add the second phone number`, not the whole request. The script refuses
  a longer one.
- **Details:** what the owner asked for, in their words where it matters, plus anything
  the person doing it will need: which page, what it should say, the path of any file
  they sent (see the `site` skill's inbox rule). Markdown is fine. For a developer item
  this is the whole brief; that issue is how the developer hears about it, there is no
  other channel.
- Start the title with `(dev)` when it needs the developer (anything outside copy, the
  `SITE` block, services, colours and the logo). On `edit`, an item already marked
  `(dev)` stays that way.

`edit` with an empty title (`""`) keeps the title and replaces the details. `note` adds a
comment for things learnt after the item was written: a decision, a second file, a
change of mind. Prefer `note` over rewriting details the developer may have read.

When the owner corrects an item or gives more information, update it without being asked.
