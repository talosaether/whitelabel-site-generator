# 2. At most four visible navigation links, nothing hidden

Status: accepted

## Context

Rendering every page as a responsive grid of pill buttons reads as dated and costs a
phone 280px of vertical space before any content appears. Hiding navigation behind a menu
is worse: NN/G finds it roughly halves discoverability and lengthens task time, and that
four or fewer top-level links should simply be shown. Floating pill bars and bottom tab
bars are for app-like destinations, not a marketing site.

## Decision

The header carries at most four links as plain text with no container. The logo is the
home link, so "Home" is not a separate item. The footer lists every page, NN/G's
recommended backstop. The current page is marked by the text's own underline in the
accent colour — the only place the accent appears in the chrome.

The scaffold ships with three: Services, About, Contact.

## Consequences

- Four links hold one row at every width down to 320px. `tests/browser/site.spec.js`
  asserts the single row including a 320px check, and that the footer lists every page.
- Adding a fifth top-level page breaks the one-row property and forces this decision to
  be revisited — which is the point.
- The header becomes a single line at 860px.
