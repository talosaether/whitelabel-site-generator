"""The dev host follows main by itself, and rebuilds only when the change needs it.

scripts/dev_follow_main.sh runs from a timer on the development host. These tests run
the real script against a scratch origin and clone, with a stubbed `docker` that records
what it was asked to do, so the pull, the stash and the "what changed" decisions are
exercised for real and nothing is built.
"""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts/dev_follow_main.sh"
GIT_ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
}


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                   env={**os.environ, **GIT_ENV})


class DevFollowMain(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.origin = base / "origin.git"
        git(base, "init", "-q", "--bare", "-b", "main", str(self.origin))
        seed = base / "seed"
        git(base, "clone", "-q", str(self.origin), str(seed))
        for name in ("Dockerfile", "requirements.txt", "compose.yaml", "compose.dev.yaml",
                     "Caddyfile", "Caddyfile.dev", "app/templates/home.html",
                     "frontend/package.json", "frontend/package-lock.json"):
            (seed / name).parent.mkdir(parents=True, exist_ok=True)
            (seed / name).write_text("v1\n")
        git(seed, "add", "-A"); git(seed, "commit", "-q", "-m", "seed"); git(seed, "push", "-q", "origin", "main")
        self.seed = seed
        self.dev = base / "dev"
        git(base, "clone", "-q", str(self.origin), str(self.dev))
        self.bin = base / "bin"; self.bin.mkdir()
        self.log = base / "docker.log"
        stub = self.bin / "docker"
        stub.write_text(f'#!/bin/sh\necho "$@" >> "{self.log}"\n')
        stub.chmod(0o755)

    def tearDown(self):
        self.tmp.cleanup()

    def upstream_change(self, *names):
        for name in names:
            (self.seed / name).write_text("v2\n")
        git(self.seed, "add", "-A"); git(self.seed, "commit", "-q", "-m", "change"); git(self.seed, "push", "-q", "origin", "main")

    def run_script(self):
        return subprocess.run(["bash", str(SCRIPT), str(self.dev)], text=True, capture_output=True,
                              env={**os.environ, **GIT_ENV, "PATH": f"{self.bin}:{os.environ['PATH']}"})

    def docker_calls(self):
        return self.log.read_text().splitlines() if self.log.exists() else []

    def test_nothing_new_touches_nothing(self):
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.docker_calls(), [])

    def test_a_template_change_is_just_a_pull(self):
        self.upstream_change("app/templates/home.html")
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((self.dev / "app/templates/home.html").read_text(), "v2\n")
        self.assertEqual(self.docker_calls(), [])

    def test_a_dependency_change_rebuilds_and_restarts_the_watcher(self):
        self.upstream_change("requirements.txt")
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.docker_calls(), ["compose up -d --build", "compose restart assets"])

    def test_a_compose_change_recreates_without_building(self):
        self.upstream_change("compose.dev.yaml")
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.docker_calls(), ["compose up -d"])

    def test_a_caddyfile_change_reloads_the_proxy(self):
        self.upstream_change("Caddyfile.dev")
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.docker_calls(),
                         ["compose exec -T caddy caddy reload --config /etc/caddy/Caddyfile"])

    def test_unshipped_edits_survive_the_pull(self):
        (self.dev / "app/templates/home.html").write_text("owner's draft\n")
        self.upstream_change("requirements.txt")
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((self.dev / "app/templates/home.html").read_text(), "owner's draft\n")
        self.assertEqual((self.dev / "requirements.txt").read_text(), "v2\n")

    def test_refuses_to_act_off_main(self):
        git(self.dev, "switch", "-q", "-c", "hermes/20260101-000000")
        self.upstream_change("requirements.txt")
        r = self.run_script()
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.docker_calls(), [])


if __name__ == "__main__":
    unittest.main()
