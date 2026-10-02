# Digest-pinned so the runner and production run the same bytes. The tag stays for
# readability; the digest is what resolves. Dependabot's docker ecosystem bumps these.
FROM node:26-alpine@sha256:0b36e8c136b94cd4fcf02188228e76c31ad5872eef3fec8cbd2eee500cfd9e80 AS assets
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Photos: originals in app/photos become metadata-free WebPs. Pillow lives only here.
FROM python:3.14-slim@sha256:caaf356f40667c496d405780745b9ac25771c189a51dfcc42430d531ea09f8a2 AS photos
WORKDIR /build
RUN pip install --no-cache-dir Pillow==12.3.0
COPY scripts/build_photos.py ./scripts/build_photos.py
COPY app/photos/ ./app/photos/
RUN python scripts/build_photos.py

FROM python:3.14-slim@sha256:caaf356f40667c496d405780745b9ac25771c189a51dfcc42430d531ea09f8a2
ENV PYTHONUNBUFFERED=1
WORKDIR /srv
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home app
COPY app/ ./app/
COPY --from=assets /build/app/static ./app/static
COPY --from=photos /build/app/media ./app/media
# The originals were only needed by the photos stage; the runtime serves derivatives.
RUN rm -rf /srv/app/photos
# Compile every module once, here. The runtime filesystem is read-only, so anything left
# uncompiled is recompiled from source on each container start — which is most of the time
# a visitor spends waiting during a deploy.
# The site-packages path is asked of the interpreter rather than written out, because a
# literal one goes quietly stale when the base image's minor version moves: compileall
# reports a missing directory and still exits 0, so nothing fails and every module is
# recompiled from source on each container start instead.
RUN python -m compileall -q "$(python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')" /srv/app
# Only now: at runtime there is nowhere to write bytecode anyway, and trying is wasted work.
ENV PYTHONDONTWRITEBYTECODE=1
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
