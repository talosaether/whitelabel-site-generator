"""Bootstrap provisions a host; the deploy workflow owns the checkout after that.

The guard runs before Docker is installed or anything is pulled, so the real script can
be executed here against a scratch directory. `git` and `docker` are stubbed so nothing
is installed, cloned or started: a stubbed `git` fails, which stops the script at the
point these tests care about.
"""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOOTSTRAP = ROOT / "scripts/bootstrap.sh"


def stub_bin(directory):
    """A PATH where docker is present and git refuses, so the script gets no further."""
    binaries = Path(directory) / "bin"
    binaries.mkdir()
    (binaries / "docker").write_text("#!/bin/sh\nexit 0\n")
    (binaries / "git").write_text("#!/bin/sh\necho 'stub git refuses' >&2\nexit 1\n")
    # Swap looks active, so the script's swapfile step never touches the machine running the tests.
    (binaries / "swapon").write_text("#!/bin/sh\necho '/swapfile file 2G 0B -2'\n")
    for stub in binaries.iterdir():
        stub.chmod(0o755)
    return binaries


def run(tmp, checkout, **env):
    return subprocess.run(
        ["bash", str(BOOTSTRAP)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        env={
            "PATH": f"{stub_bin(tmp)}:{os.defpath}",
            "DIR": str(checkout),
            **env,
        },
    )


class BootstrapGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.checkout = Path(self.tmp.name) / "website"

    def existing(self):
        (self.checkout / ".git").mkdir(parents=True)

    def test_refuses_an_existing_checkout(self):
        self.existing()
        result = run(self.tmp.name, self.checkout)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("the deploy workflow owns it", result.stdout)
        self.assertIn("push to main", result.stdout)

    def test_refusal_costs_the_host_nothing(self):
        self.existing()
        result = run(self.tmp.name, self.checkout)
        for done in ("installing Docker", "updating", "cloning into", "building and starting"):
            self.assertNotIn(done, result.stdout)

    def test_a_fresh_host_reaches_the_clone(self):
        """An empty directory is what this script is for; it must get past the guard."""
        result = run(self.tmp.name, self.checkout)
        self.assertNotIn("the deploy workflow owns it", result.stdout)
        self.assertIn("cloning into", result.stdout)

    def test_override_reaches_the_pull(self):
        """With a bundle to pull from, the override gets as far as git (which the stub refuses)."""
        self.existing()
        bundle = Path(self.tmp.name) / "site.bundle"
        bundle.write_bytes(b"")
        result = run(self.tmp.name, self.checkout, ALLOW_EXISTING_CHECKOUT="yes", REPO=str(bundle))
        self.assertNotIn("the deploy workflow owns it", result.stdout)
        self.assertIn("ALLOW_EXISTING_CHECKOUT=yes", result.stdout)

    def test_override_refuses_a_url(self):
        """The host cannot fetch the private repository, so a URL is refused before git runs."""
        self.existing()
        result = run(self.tmp.name, self.checkout, ALLOW_EXISTING_CHECKOUT="yes")
        self.assertEqual(result.returncode, 1)
        self.assertIn("must be a git bundle", result.stdout)
        self.assertNotIn("updating", result.stdout)

    def test_the_swap_step_is_skipped_when_swap_is_active(self):
        result = run(self.tmp.name, self.checkout)
        self.assertNotIn("swapfile", result.stdout)

    def test_a_deployed_host_is_never_built_on(self):
        script = BOOTSTRAP.read_text()
        self.assertIn("grep -q '^APP_IMAGE=' .env", script)
        self.assertIn("docker compose up -d --no-build", script)

    def test_the_guard_runs_before_the_docker_install(self):
        script = BOOTSTRAP.read_text()
        guard_at = script.index('[ "$ALLOW_EXISTING_CHECKOUT" != yes ]')
        docker_at = script.index("if ! command -v docker")
        self.assertLess(guard_at, docker_at)

    def test_documentation_matches_the_behaviour(self):
        deploy = (ROOT / "DEPLOY.md").read_text()
        self.assertNotIn("re-running pulls and re-ups rather than breaking", deploy)
        self.assertIn("ALLOW_EXISTING_CHECKOUT", deploy)


if __name__ == "__main__":
    unittest.main()
