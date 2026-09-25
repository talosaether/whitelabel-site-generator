"""Production runtime policy: the live services are bounded, and reachable as a Compose
project only from the checkout entitled to them.

Numbers come from the rendered Compose config rather than the file text, so a change
that happens to keep the same words but a different effective value still fails.
"""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIB = 1024 * 1024


def rendered(compose_file, **env):
    result = subprocess.run(
        ["docker", "compose", "-f", compose_file, "config", "--format", "json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        env={"PATH": "/usr/bin:/bin", **env},
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout)


class ProductionRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = rendered("compose.yaml")
        cls.app = cls.config["services"]["app"]
        cls.caddy = cls.config["services"]["caddy"]

    def test_app_memory_is_bounded(self):
        """Unbounded, the kernel picks the OOM victim, and it need not be the app."""
        self.assertEqual(int(self.app["mem_limit"]), 512 * MIB)

    def test_app_processes_and_scratch_space_are_bounded(self):
        self.assertEqual(self.app["pids_limit"], 128)
        self.assertEqual(self.app["tmpfs"], ["/tmp:size=64m,mode=1777"])

    def test_app_keeps_the_whole_cpu(self):
        """Nothing else on the production host should be able to out-schedule the site."""
        self.assertIsNone(self.app.get("cpus"))

    def test_caddy_is_bounded_too(self):
        """Losing the proxy takes the site off the internet, not just one service."""
        self.assertEqual(int(self.caddy["mem_limit"]), 128 * MIB)
        self.assertEqual(self.caddy["pids_limit"], 64)

    def test_logs_rotate_on_both_services(self):
        for name, service in (("app", self.app), ("caddy", self.caddy)):
            with self.subTest(service=name):
                self.assertEqual(
                    service["logging"]["options"],
                    {"max-file": "3", "max-size": "10m"},
                    "json-file never rotates on its own",
                )

    def test_hardening_is_in_place(self):
        self.assertIs(self.app["read_only"], True)
        self.assertEqual(self.app["cap_drop"], ["ALL"])
        self.assertEqual(self.app["security_opt"], ["no-new-privileges:true"])
        self.assertEqual(self.app["restart"], "unless-stopped")
        self.assertEqual(self.caddy["restart"], "unless-stopped")

    def test_production_has_no_development_services(self):
        """The watcher and the bind mount belong to compose.dev.yaml alone."""
        self.assertEqual(sorted(self.config["services"]), ["app", "caddy"])
        self.assertNotIn("volumes", self.app)
        self.assertNotIn("--reload", " ".join(self.app.get("command") or []))


class ComposeProjectIsolationTests(unittest.TestCase):
    """`docker compose` in a stray clone must not reach the live containers.

    Compose names a project after its directory unless told otherwise, so a clone in any
    directory sharing production's name would inherit production's project. The default
    in the file is deliberately not production's name; production opts back in through
    its untracked .env.
    """

    DEPLOY = (ROOT / ".github/workflows/deploy.yml").read_text()
    PRODUCTION_PROJECT = "whitelabel"

    def rendered_from(self, project_dir):
        result = subprocess.run(
            [
                "docker", "compose",
                "-f", str(ROOT / "compose.yaml"),
                "--project-directory", str(project_dir),
                "config", "--format", "json",
            ],
            text=True,
            capture_output=True,
            env={"PATH": "/usr/bin:/bin"},
        )
        if result.returncode != 0:
            raise AssertionError(result.stderr)
        return json.loads(result.stdout)["name"]

    def test_a_clone_does_not_inherit_the_production_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertNotEqual(self.rendered_from(tmp), self.PRODUCTION_PROJECT)

    def test_the_default_does_not_depend_on_the_directory_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            looks_like_production = Path(tmp) / self.PRODUCTION_PROJECT
            looks_like_production.mkdir()
            self.assertNotEqual(
                self.rendered_from(looks_like_production), self.PRODUCTION_PROJECT
            )

    def test_production_opts_back_in_through_its_env_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".env").write_text(
                f"COMPOSE_PROJECT_NAME={self.PRODUCTION_PROJECT}\n"
            )
            self.assertEqual(self.rendered_from(tmp), self.PRODUCTION_PROJECT)

    def test_bootstrap_gives_a_fresh_host_the_production_project(self):
        bootstrap = (ROOT / "scripts/bootstrap.sh").read_text()
        self.assertIn("COMPOSE_PROJECT_NAME=", bootstrap)
        self.assertIn(f"COMPOSE_PROJECT=${{COMPOSE_PROJECT:-{self.PRODUCTION_PROJECT}}}", bootstrap)

    def test_the_deploy_pins_the_project_before_it_runs_compose(self):
        remote = self.DEPLOY[self.DEPLOY.index("<<'REMOTE'"):self.DEPLOY.index("          REMOTE")]
        pin = remote.index(f"COMPOSE_PROJECT_NAME={self.PRODUCTION_PROJECT}")
        executed = min(
            remote.index(statement)
            for statement in (
                "docker compose up -d --no-build || roll_back",
                "wait_healthy ||",
                "docker compose exec -T caddy",
            )
        )
        self.assertLess(pin, executed, "the project must be pinned before any compose call")

    def test_the_deploy_strips_the_development_overlay(self):
        """A COMPOSE_FILE line in production's .env would bind-mount the checkout live."""
        remote = self.DEPLOY[self.DEPLOY.index("<<'REMOTE'"):self.DEPLOY.index("          REMOTE")]
        self.assertIn("sed -i '/^COMPOSE_FILE=/d' .env", remote)


if __name__ == "__main__":
    unittest.main()
