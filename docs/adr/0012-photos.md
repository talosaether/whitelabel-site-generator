# 12. Photo originals are tracked beside the app; only derivatives are served

Status: accepted

Builds on [ADR-0010](0010-two-hosts.md).

## Context

The scaffold shipped without any way to show a photograph. The predecessor project had a
full catalogue with per-file hashes, captions, categories and a gallery, which was right
for a site that *was* its photographs and wrong for a brochure with two picture slots.
Meanwhile the owner-facing assistant may write only `app/` and `frontend/`, and the whole
point of the dev host is that a change is live seconds after it is saved.

## Decision

- Originals live in `app/photos/` (tracked, JPEG or PNG, plain names). That directory is
  inside the assistant's writable scope, so a photo the owner sends becomes a site change
  the assistant can make alone.
- `scripts/build_photos.py` (Pillow, standard library otherwise) writes `name.webp` (fits
  1600px) and `name-thumb.webp` (fits 480px) into `app/media/`, copying pixels into a
  fresh image so EXIF, GPS and device data never leave the source. It runs once in a
  Dockerfile stage of its own, and continuously in a `photos` watcher container on the
  dev host.
- The runtime image carries the derivatives and deletes `app/photos/`; originals are never
  served and never reach production.
- Two slots, `hero_photo` and `about_photo` in the `SITE` block, each with an `_alt`
  sentence. Empty means the logo panel, so the scaffold looks the same until a photo is
  chosen.

## Consequences

- **No catalogue, no hashes, no gallery.** A second use for photographs is a new
  decision, not an extension of this one.
- **Alt text is a setting, not an afterthought.** The slot is not shown without it being
  at least possible to set; the assistant's skill asks for the sentence.
- **Pillow is pinned in two places** (the Dockerfile stage and the dev watcher), and
  `tests/test_image_pinning.py` insists they agree, as it does for the Python and Node
  base images.
- A corrupt or half-uploaded file is skipped with a message, never a failed build: the
  watcher retries on the next pass and the build ships what it could make.
