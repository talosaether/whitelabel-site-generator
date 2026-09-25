# Open questions

Live items, not history. Each needs a person outside this repository to answer.

## Branding

Every placeholder in the scaffold is listed here so that none ships by accident. The
`SITE` block in `app/main.py` and the templates carry text that describes what should be
there rather than what will be.

- **Name and tagline.** `SITE['name']` is "Your Business" and `SITE['tagline']` reads
  "Tagline goes here".
- **Contact details.** Phone and email are empty, which hides every call, text and mail
  link. The contact page says so in a dashed placeholder box until one is set.
- **Area and hours.** Placeholder sentences.
- **Page headings and descriptions.** `PAGES` in `app/main.py` — each description doubles
  as the page's intro paragraph and its `<meta name="description">`.
- **Services.** Six numbered placeholders; the home page previews the first three.
- **Copy in the templates.** `home.html`, `services.html`, `about.html`, `contact.html`
  each carry a few sentences describing what belongs there.
- **Artwork.** `app/brand/logo.svg` and `icon.svg` are a generic mark. The hero and about
  panels show the logo until `hero_photo` / `about_photo` name a file in `app/photos/`.
- **Palette.** Teal and amber placeholders at the top of `frontend/style.css`.

## Infrastructure

- **The domain.** `example.com` is a placeholder in every place DEPLOY.md §3 lists; the
  instance's real domain replaces it before the first deploy.
- **Production has never been deployed from this repository.** The `DEPLOY_KEY` and
  `DEPLOY_KNOWN_HOSTS` secrets and the `/srv/website` bootstrap on the host are the
  one-time setup in `DEPLOY.md`.
- **The `www` record.** The Caddyfile redirects `www.` to the bare domain, and Caddy will
  request a certificate for it on production's first start. Either add the A record or set
  `WWW_ADDRESS=:8080` in production's `.env` until it exists.
- **No real-device or Safari testing has been done.** Everything verified is Chromium at
  two viewport sizes.
