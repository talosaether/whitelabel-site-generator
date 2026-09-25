"""Dependency-free HTTP checks against a running stack, through Caddy.

Pass a base URL to test somewhere other than production:

    python3 tests/smoke.py http://localhost
    python3 tests/smoke.py https://dev.example.com

These assert structure — every page renders, carries the right head metadata, the
assets are versioned and cached correctly — and nothing about the copy, so branding the
site does not mean rewriting them. The one exception is the site name in <title>, which
is read from app/main.py rather than hard-coded here.
"""
import json
import re
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent
base = (sys.argv[1] if len(sys.argv) > 1 else 'https://example.com').rstrip('/')
main_py = (ROOT / 'app/main.py').read_text()
SITE_NAME = re.search(r"^SITE = \{\s*\n\s*'name': '([^']+)'", main_py, re.M).group(1)
DOMAIN = re.search(r"^\s*'domain': '([^']+)'", main_py, re.M).group(1)
CANONICAL = f'https://{DOMAIN}'
PAGES = [('', 'Home'), ('services', 'Services'), ('about', 'About'), ('contact', 'Contact')]


def fetch(path, status=200):
    try:
        response = urlopen(base + path, timeout=10)
    except HTTPError as exc:
        response = exc
    with response:
        assert response.status == status, (path, response.status)
        body = response.read().decode()
        # Set by Caddy, so hitting the app container directly fails here on purpose.
        assert response.headers['X-Content-Type-Options'] == 'nosniff', path
        print(f'PASS {status} {path}')
        return body, response.headers


assert json.loads(fetch('/healthz')[0]) == {'status': 'ok'}
for slug, label in PAGES:
    path = '/' + slug
    body, headers = fetch(path)
    assert re.search(r'<h1[^>]*>.+</h1>', body), (path, 'no h1')
    assert f'<title>{label} · {SITE_NAME}</title>' in body, path
    assert f'<link rel="canonical" href="{CANONICAL}/{slug}">' in body, path
    assert '<meta name="description" content="' in body, path
    # Boosted navigation carries these into <head> after each swap.
    assert 'data-description="' in body and f'data-canonical="{CANONICAL}/{slug}"' in body, path
    # Generated assets carry a content version so a stale stylesheet cannot outlive a deploy.
    assert '/static/site.js?v=' in body and '/static/site.css?v=' in body, path
    assert headers['Cache-Control'] == 'no-cache', path
    # Brand mark and site icon ship with every page.
    assert '/brand/logo.svg?v=' in body and '/brand/icon.svg?v=' in body, path
    # The header marks the current page, and only the current page.
    header = body[body.index('<header'):body.index('</header>')]
    assert header.count('aria-current="page"') == 1, path
    # Every page lists every page in the footer.
    footer = body[body.index('<footer'):body.index('</footer>')]
    for other, other_label in PAGES:
        assert f'href="/{other}"' in footer, (path, 'footer lacks', other_label)
    assert 'Skip to content' in body, path

for path, mime in [('/static/site.js', 'javascript'), ('/static/site.css', 'text/css'),
                   ('/brand/logo.svg', 'image/svg+xml'), ('/brand/icon.svg', 'image/svg+xml')]:
    body, headers = fetch(path)
    assert body and mime in headers['Content-Type'], (path, headers['Content-Type'])
    assert headers['Cache-Control'] == 'no-cache', path
    versioned = fetch(path + '?v=test')[1]
    assert versioned['Cache-Control'] == 'public, max-age=31536000, immutable', path
fetch('/not-a-page', 404)
fetch('/static/not-a-file', 404)
fetch('/brand/not-a-file.svg', 404)
fetch('/media/not-a-file.webp', 404)
fetch('/docs', 404)
fetch('/openapi.json', 404)
print('HTTP smoke checks passed.')
