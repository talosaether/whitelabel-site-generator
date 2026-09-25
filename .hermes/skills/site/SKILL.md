---
name: site
description: "Change the website: copy, services, contact details, colours, logo. Live on dev in seconds."
version: 1.0.0
author: the developer
metadata:
  hermes:
    tags: [website, copy, branding, whitelabel]
    related_skills: [todo, recent, ship]
---

# Change the site

## When to use

The owner wants something on the website to read, look or say differently: a headline, a
paragraph, the services list, the phone number or email, opening hours, the colours, the
logo. `/site <what they want>` or any plain request about the site.

## Where things live

Everything is under `/srv/whitelabel`. That directory *is* the development site:
save a file and it is live at <https://dev.example.com> within about two seconds.

| The owner wants to change | Edit |
| --- | --- |
| Business name, tagline, phone, email, area served, hours | The `SITE` block near the top of `app/main.py`. Empty `phone` or `email` hides every call, text or mail link at once. `phone` is E.164 (`+15035550100`), `phone_label` is as printed (`503-555-0100`). |
| A page's heading or its intro sentence (also the search-engine description) | `PAGES` in `app/main.py` |
| The header links | `NAV` in `app/main.py`. Four at most. |
| The services and their one-liners | `SERVICES` in `app/main.py`. The home page shows the first three. |
| Body copy on a page | `app/templates/home.html`, `services.html`, `about.html`, `contact.html` |
| Colours | The custom properties at the top of `frontend/style.css`: `--brand` for buttons, `--accent` for the current-page underline |
| A photograph on the home or about page | Save the original into `app/photos/` (JPEG or PNG, a plain name like `classroom.jpg`), then set `hero_photo` or `about_photo` in the `SITE` block to that file name and write its `_alt` sentence. The watcher makes the web version within seconds; nothing else to do. |
| Logo and browser icon | `app/brand/logo.svg` and `app/brand/icon.svg`. Square SVG. A PNG or JPG logo needs the developer: add a task. |

## Procedure

1. Make sure you have the facts. A phone number, an address, a price, a name: if the
   owner has not given it, ask. Never invent one and never leave a guess in the site.
2. Edit the file in place. In templates change the words, not the markup, unless asked.
   In `app/main.py` touch only the four data blocks (`SITE`, `PAGES`, `NAV`, `SERVICES`).
3. If you edited `app/main.py`, check it still parses and the site still answers:
   ```sh
   python3 -c "import ast; ast.parse(open('app/main.py').read())" && sleep 2 && curl -s -o /dev/null -w '%{http_code}\n' https://dev.example.com/healthz
   ```
   Anything other than `200`: put it back with `git checkout -- app/main.py`, tell the
   owner it did not take, and `/todo add` a note for the developer.
4. Confirm the change is live: fetch the page and look for the new text.
   ```sh
   curl -s https://dev.example.com/about | grep -c 'the new wording'
   ```
5. Tell the owner, in plain words, what changed and which page to look at, with the dev
   link. Do not mention file names unless asked.
6. Do **not** publish. The dev site is for looking. Production changes only when the
   owner runs `/ship`.

## If the owner sends a file

- **A photograph for the site:** copy it from the path shown in the message into
  `app/photos/` with a plain name (`cp <path> app/photos/classroom.jpg`), set
  `hero_photo` or `about_photo` in `SITE` to that name with an `_alt` sentence, wait a
  few seconds, and confirm the page shows it. Originals are never served; the pipeline
  strips their metadata and resizes them.
- **Logo artwork or anything else:** copy it into `app/inbox/` keeping its name and put
  that path in the `(dev)` issue you add. Never place a received file in `app/brand/`.
- **If you can see an image but have no path** (Telegram compressed it), say what you saw
  and ask the owner to send it again **as a file** ("send without compression").

## Rules

- Only `app/` and `frontend/`. Everything else in the tree belongs to the developer and is
  read-only to you; if a request needs it, `/todo add` it marked `(dev)`. That creates
  a GitHub issue the developer watches; it is the only way to reach them.
- Never `git add -A`, never commit, never push from here. `/ship` does the git work.
- Photographs go through `app/photos/` and the `SITE` slots, never straight into a
  template or `app/brand/`.
- Keep the owner's voice. Match the tone already on the page unless asked to change it.
- If a request is bigger than words and colours (a new page, a form, a map), it is a
  developer task: say so and log it.

## Verification

The `curl … | grep -c` in step 4 prints a number above zero, and the owner can see it at
the link you give them.
