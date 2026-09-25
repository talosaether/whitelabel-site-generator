"""Turn the photos in app/photos/ into metadata-free WebP derivatives in app/media/.

    python3 scripts/build_photos.py           # once: the Docker build
    python3 scripts/build_photos.py --watch   # keep going: the dev host's watcher container

For every JPEG or PNG source `name.jpg` this writes `name.webp` (fits 1600px) and
`name-thumb.webp` (fits 480px). Pixels are copied into a fresh image, so EXIF, GPS and
device details never reach the served file; the orientation tag is applied first so
phone photos come out the right way up. Derivatives newer than their source are left
alone, and derivatives whose source has gone are removed. Needs Pillow; nothing else.
"""
import sys
import time
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / 'app/photos'
OUT = ROOT / 'app/media'
SUFFIXES = {'.jpg', '.jpeg', '.png'}
VARIANTS = {'': (1600, 80), 'thumb': (480, 78)}      # suffix -> (fits within px, quality)


def target(source, variant):
    return OUT / f"{source.stem}{'-' + variant if variant else ''}.webp"


def build(source):
    with Image.open(source) as original:
        image = ImageOps.exif_transpose(original).convert('RGB')
        for variant, (size, quality) in VARIANTS.items():
            resized = image.copy()
            resized.thumbnail((size, size), Image.Resampling.LANCZOS)
            clean = Image.new('RGB', resized.size)
            clean.paste(resized)
            clean.save(target(source, variant), 'WEBP', quality=quality, method=6)


def sync():
    """Build what is new or changed, drop what is orphaned. Returns the names touched."""
    OUT.mkdir(parents=True, exist_ok=True)
    sources = [p for p in sorted(SOURCES.iterdir()) if p.suffix.lower() in SUFFIXES] if SOURCES.is_dir() else []
    touched = []
    for source in sources:
        outputs = [target(source, v) for v in VARIANTS]
        if all(o.exists() and o.stat().st_mtime >= source.stat().st_mtime for o in outputs):
            continue
        try:
            build(source)
            touched.append(source.name)
        except Exception as exc:  # a half-uploaded or corrupt file must not stop the rest
            print(f'skipped {source.name}: {exc}', flush=True)
    stems = {s.stem for s in sources}
    for old in OUT.glob('*.webp'):
        stem = old.stem[:-6] if old.stem.endswith('-thumb') else old.stem
        if stem not in stems:
            old.unlink()
            touched.append(f'-{old.name}')
    return touched


if __name__ == '__main__':
    if '--watch' in sys.argv:
        print(f'watching {SOURCES}', flush=True)
        while True:
            for name in sync():
                print(f'built {name}' if not name.startswith('-') else f'removed {name[1:]}', flush=True)
            time.sleep(2)
    else:
        for name in sync():
            print(name)
        print(f'{len(list(OUT.glob("*.webp")))} derivatives in {OUT}')
