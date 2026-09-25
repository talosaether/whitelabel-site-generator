import hashlib
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

ROOT = Path(__file__).parent
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')
# Generated from app/photos by scripts/build_photos.py; absent until the first photo.
app.mount('/media', StaticFiles(directory=ROOT / 'media', check_dir=False), name='media')
# Hand-authored brand artwork — logo and icon — tracked in Git and served as-is.
app.mount('/brand', StaticFiles(directory=ROOT / 'brand'), name='brand')
templates = Jinja2Templates(directory=ROOT / 'templates')


def asset(url: str) -> str:
    """Return an asset URL with a content version, for safe long caching.

    Filenames are stable across builds, so without this a browser can keep serving an
    old stylesheet against fresh HTML. The file is stat'ed on every call rather than
    cached per process: on the development host the stylesheet is rebuilt in place
    while the server keeps running, and a cached version would pin the browser to the
    old file for as long as the process lived. Four stats per page is nothing.
    """
    file = ROOT / url.lstrip('/')
    if not file.is_file():
        return url
    stat = file.stat()
    digest = hashlib.sha256(f'{stat.st_mtime_ns}:{stat.st_size}'.encode()).hexdigest()
    return f'{url}?v={digest[:10]}'


templates.env.globals['asset'] = asset


def photo(name: str, variant: str = '') -> str:
    """The served derivative of a photo in app/photos: 'garden.jpg' -> /media/garden.webp,
    or garden-thumb.webp for variant='thumb'. Versioned like any other asset."""
    stem = Path(name).stem
    return asset(f"/media/{stem}{'-' + variant if variant else ''}.webp")


templates.env.globals['photo'] = photo


@app.middleware('http')
async def cache_headers(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.startswith(('/static/', '/brand/', '/media/')):
        # Versioned URLs can be cached hard; bare ones must revalidate.
        response.headers['Cache-Control'] = ('public, max-age=31536000, immutable'
                                             if request.query_params.get('v') else 'no-cache')
    else:
        response.headers['Cache-Control'] = 'no-cache'
    return response


# ---------------------------------------------------------------------------------------
# Branding. Everything a new instance of this site has to say about itself is here, in
# one block; the templates read these and carry no name, number or address of their own.
# Leave phone and email empty to hide the call, text and mail links everywhere at once.
# ---------------------------------------------------------------------------------------
SITE = {
    'name': 'Your Business',
    # Under the name in the header: three or four words on what this is.
    'tagline': 'Tagline goes here',
    # The canonical origin. Every page's <link rel="canonical"> points at this host, so
    # the development site at dev.* tells search engines the production URL is the one.
    'domain': 'example.com',
    'phone': '',          # E.164, e.g. '+15035550100'. Empty hides call and text links.
    'phone_label': '',    # As printed, e.g. '503-555-0100'.
    'email': '',          # Empty hides the mail link.
    'area': 'The town and the surrounding area',
    'hours': 'Weekdays, nine to five',
    # Photos: a file name from app/photos/ (see the README there), or empty to show the
    # logo panel instead. The _alt text is read out to people who cannot see the picture.
    'hero_photo': '',     # e.g. 'classroom.jpg', shown beside the home page headline
    'hero_alt': '',
    'about_photo': '',    # shown beside the about page copy
    'about_alt': '',
}
# slug: (nav/footer label, page heading, meta description). The description is also the
# page's intro paragraph, so it should read as a sentence rather than a list of keywords.
PAGES = {
    '': ('Home', 'A clear promise, in one line.',
         'Two sentences on who this is for and what they get. This is the meta description too, so it should stand on its own.'),
    'services': ('Services', 'What we offer.',
                 'A one-sentence summary of the services listed on this page, in plain words.'),
    'about': ('About', 'Who is behind this.',
              'A sentence on the people or the organisation, and why they do this work.'),
    'contact': ('Contact', 'Get in touch.',
                'How to reach us, where we are and when we are available.'),
}
# The header carries at most four visible links and hides nothing: the logo is the home
# link, and the footer repeats every page for anyone who wants the full list. Four is
# what a 320px phone row holds; a fifth link breaks the one-row property.
NAV = [('services', 'Services'), ('about', 'About'), ('contact', 'Contact')]
SERVICES = [
    ('First service', 'One or two sentences on what it is and who it is for.'),
    ('Second service', 'One or two sentences on what it is and who it is for.'),
    ('Third service', 'One or two sentences on what it is and who it is for.'),
    ('Fourth service', 'One or two sentences on what it is and who it is for.'),
    ('Fifth service', 'One or two sentences on what it is and who it is for.'),
    ('Sixth service', 'If you are not sure whether we can help, just ask.'),
]


@app.get('/healthz')
def health():
    return {'status': 'ok'}


# GET and HEAD: uptime monitors and link checkers send HEAD, and a 405 there reads as
# an outage.
@app.api_route('/', methods=['GET', 'HEAD'], response_class=HTMLResponse)
@app.api_route('/{slug}', methods=['GET', 'HEAD'], response_class=HTMLResponse)
def page(request: Request, slug: str = ''):
    if slug not in PAGES:
        raise HTTPException(status_code=404)
    label, title, description = PAGES[slug]
    return templates.TemplateResponse(request=request, name='page.html', context={
        'slug': slug, 'label': label, 'title': title, 'description': description,
        'pages': PAGES, 'nav': NAV, 'services': SERVICES, 'site': SITE,
        'canonical': f"https://{SITE['domain']}/{slug}",
    })
