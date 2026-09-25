# Photos

Put JPEG or PNG originals here, named plainly: `classroom.jpg`, `front-door.png`. The
build (and, on the dev host, a watcher that runs within a couple of seconds of a save)
turns each into `app/media/<name>.webp` and `<name>-thumb.webp`, resized and stripped of
every trace of metadata. Only the derivatives are served, at `/media/`; the originals
never reach the image or the internet.

To show one, name it in the `SITE` block of `app/main.py`: `hero_photo` for the home
page, `about_photo` for the about page, each with an `_alt` description for people who
cannot see it. Leave a slot empty to keep the logo panel.
