# Continuation prompt

Resume the website in this directory. Read `AGENTS.md`, `README.md`
and recent Git history first, and inspect the code rather than starting over.

This is a white-label scaffold: the architecture, build, tests and two-host deployment are
finished, and the site is waiting for its brand. The development site at
<https://dev.example.com> serves this working tree live; production at
<https://example.com> serves `main`, deployed automatically on push.

- **What to brand, and where:** the table in `README.md`, "Branding it". Everything the
  site says about itself is in the `SITE`, `PAGES`, `NAV` and `SERVICES` blocks of
  `app/main.py`; colours are the custom properties at the top of `frontend/style.css`;
  artwork is `app/brand/`.
- **Why things are as they are:** `docs/adr/`. Add a record rather than silently reversing one.
- **What still needs a human answer:** `docs/open-questions.md`.
- **How to run, edit and test:** `README.md`. **How to deploy:** `DEPLOY.md`.

Run the suites after changes and record what actually passed. Never treat a started build
as a verified deployment. Ask before adding a contact form, analytics, or any third-party
script.
