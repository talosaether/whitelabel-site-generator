"""The development overlay serves the working tree, live, and nothing else changes.

compose.dev.yaml is what makes dev.example.com an edit-in-place site. These
checks render it over compose.yaml the way the dev host's .env does, and assert the
three things it is for: the app reloads from a bind mount, a watcher rebuilds the
assets into that mount, and the proxy tells search engines to stay away.
"""

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def rendered():
    result = subprocess.run(
        ["docker", "compose", "-f", "compose.yaml", "-f", "compose.dev.yaml",
         "config", "--format", "json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        env={"PATH": "/usr/bin:/bin"},
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout)


class DevOverlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = rendered()
        cls.app = cls.config["services"]["app"]
        cls.assets = cls.config["services"]["assets"]
        cls.caddy = cls.config["services"]["caddy"]

    def mounts(self, service):
        return {v["target"]: v for v in service["volumes"]}

    def test_the_app_reloads_from_the_working_tree(self):
        self.assertIn("--reload", self.app["command"])
        mount = self.mounts(self.app)["/srv/app"]
        self.assertEqual(mount["type"], "bind")
        self.assertEqual(Path(mount["source"]).resolve(), (ROOT / "app").resolve())
        self.assertIs(mount.get("read_only"), True, "the app never writes to the checkout")

    def test_the_hardening_survives_the_overlay(self):
        self.assertIs(self.app["read_only"], True)
        self.assertEqual(self.app["cap_drop"], ["ALL"])

    def test_the_watcher_writes_where_the_app_reads(self):
        self.assertIn("vite build --watch", " ".join(self.assets["command"]))
        mounts = self.mounts(self.assets)
        self.assertEqual(Path(mounts["/build/frontend"]["source"]).resolve(), (ROOT / "frontend").resolve())
        self.assertEqual(Path(mounts["/build/app/static"]["source"]).resolve(), (ROOT / "app/static").resolve())
        self.assertEqual(mounts["/build/frontend/node_modules"]["type"], "volume",
                         "node_modules stays out of the host checkout")
        self.assertEqual(int(self.assets["mem_limit"]), 512 * 1024 * 1024)

    def test_the_photo_watcher_reads_sources_and_writes_derivatives(self):
        photos = self.config["services"]["photos"]
        self.assertIn("--watch", " ".join(photos["command"]))
        mounts = self.mounts(photos)
        self.assertIs(mounts["/build/app/photos"].get("read_only"), True)
        self.assertEqual(Path(mounts["/build/app/media"]["source"]).resolve(), (ROOT / "app/media").resolve())
        self.assertNotIn("/build/app/media", [m for m in mounts if mounts[m].get("read_only")])

    def test_vite_writes_into_the_mounted_static_directory(self):
        self.assertIn("outDir: '../app/static'", (ROOT / "frontend/vite.config.js").read_text())

    def test_the_proxy_serves_the_dev_caddyfile_with_noindex(self):
        mount = self.mounts(self.caddy)["/etc/caddy/Caddyfile"]
        self.assertEqual(Path(mount["source"]).resolve(), (ROOT / "Caddyfile.dev").resolve())
        caddyfile = (ROOT / "Caddyfile.dev").read_text()
        self.assertIn('X-Robots-Tag "noindex, nofollow, noarchive"', caddyfile)
        self.assertIn("reverse_proxy app:8000", caddyfile)
        self.assertNotIn("X-Robots-Tag", (ROOT / "Caddyfile").read_text(),
                         "production must be indexable")

    def test_the_asset_helper_does_not_cache_versions(self):
        """The watcher rewrites site.css under a running server; a cached version would
        pin browsers to the old file for the life of the process."""
        main_py = (ROOT / "app/main.py").read_text()
        self.assertNotIn("_asset_versions", main_py)


if __name__ == "__main__":
    unittest.main()
