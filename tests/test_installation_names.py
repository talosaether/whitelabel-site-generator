"""Every name the scaffold is branded with has to change everywhere at once.

Three names identify an instance: the development tree's path (`/srv/<tree>`), the Compose
project (`<project>-local`, `<project>-dev`, `<project>`) and the domain. Each is repeated
in a dozen files: skills, Compose files, Caddyfiles, tests, the working rules. A rename that
misses one fails quietly and late: a skill `cd`s into a directory that is not there, a
production `.env` opts into a project nothing else uses, a canonical URL names a domain the
site does not serve. DEPLOY.md §3 lists the domain's places in prose; this asserts them, and
the other two names with them, so the hundredth installation finds out on the first push.

The canonical spelling of each name is the one the running system reads: the ship script's
`cd` line, compose.yaml's `name:`, and `SITE['domain']` in app/main.py.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "node_modules", "recovery", "__pycache__", ".venv", "static", "media"}
TEXT_SUFFIXES = {".md", ".sh", ".yaml", ".yml", ".py", ".js", ".json", ""}


def read(rel):
    return (ROOT / rel).read_text()


def text_files():
    for path in ROOT.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix in TEXT_SUFFIXES and path.stat().st_size < 400_000:
            yield path


def contains(rel, needle):
    return needle in read(rel)


def has_line(text, pattern):
    return re.search(pattern, text, re.M) is not None


class TreePath(unittest.TestCase):
    """`/srv/<tree>` is where the owner's assistant works; every skill has to agree."""

    def setUp(self):
        match = re.search(r"^cd (/srv/\S+)$", read(".hermes/skills/ship/scripts/ship.sh"), re.M)
        self.assertIsNotNone(match, "ship.sh has no `cd /srv/...` line")
        self.tree = match.group(1)

    def test_every_skill_script_runs_from_the_same_tree(self):
        for script in ("todo", "recent"):
            rel = f".hermes/skills/{script}/scripts/{script}.sh"
            self.assertTrue(has_line(read(rel), rf"^cd {re.escape(self.tree)}$"),
                            f"{rel} does not cd into {self.tree}")

    def test_every_skill_tells_the_assistant_the_same_tree(self):
        for skill in ("site", "todo", "recent", "ship"):
            rel = f".hermes/skills/{skill}/SKILL.md"
            self.assertTrue(contains(rel, self.tree), f"{rel} does not name {self.tree}")

    def test_the_rules_and_the_reconstruction_name_the_same_tree(self):
        adrs = sorted((ROOT / "docs/adr").glob("*owner-assistant-account.md"))
        self.assertTrue(adrs, "no ADR about the owner's assistant's account; its reconstruction names the tree")
        for rel in ["AGENTS.md", "DEPLOY.md"] + [str(a.relative_to(ROOT)) for a in adrs]:
            self.assertTrue(contains(rel, self.tree), f"{rel} does not name {self.tree}")

    def test_no_other_tree_path_survives_a_rename(self):
        allowed = {self.tree, "/srv/website", "/srv/app"}
        stray = {}
        for path in text_files():
            for hit in re.findall(r"/srv/[A-Za-z0-9][A-Za-z0-9_.-]*", path.read_text(errors="replace")):
                if hit not in allowed and not any(hit.startswith(a + "/") for a in allowed):
                    stray.setdefault(hit, set()).add(str(path.relative_to(ROOT)))
        self.assertEqual(stray, {}, f"paths under /srv that are not {sorted(allowed)}: {stray}")


class ComposeProject(unittest.TestCase):
    """`name:` in compose.yaml is `<project>-local`; the two hosts opt into `-dev` and bare."""

    def setUp(self):
        match = re.search(r"^name: (\S+)-local$", read("compose.yaml"), re.M)
        self.assertIsNotNone(match, "compose.yaml must name its project `<project>-local`")
        self.project = match.group(1)

    def test_the_env_example_opts_each_host_into_its_own_project(self):
        env = read(".env.example")
        self.assertTrue(has_line(env, rf"^COMPOSE_PROJECT_NAME={re.escape(self.project)}-dev$"),
                        "the dev block must be uncommented and end in -dev")
        self.assertTrue(has_line(env, rf"^# COMPOSE_PROJECT_NAME={re.escape(self.project)}$"),
                        "the production block must name the bare project, commented out")

    def test_the_working_rules_name_all_three_projects(self):
        rules = read("AGENTS.md")
        for name in (f"`{self.project}-local`", f"`{self.project}-dev`", f"`{self.project}`"):
            self.assertIn(name, rules, f"AGENTS.md does not mention {name}")

    def test_deploy_md_names_the_two_hosts_projects(self):
        deploy = read("DEPLOY.md")
        for name in (f"`{self.project}-dev`", f"`{self.project}`"):
            self.assertIn(name, deploy, f"DEPLOY.md does not mention {name}")

    def test_the_runtime_policy_test_pins_the_same_production_project(self):
        pinned = re.search(r'^\s*PRODUCTION_PROJECT = "([^"]+)"', read("tests/test_production_runtime.py"), re.M)
        self.assertIsNotNone(pinned)
        self.assertEqual(pinned.group(1), self.project)


class Domain(unittest.TestCase):
    """`SITE['domain']` is the canonical URL's host; every default has to be that host."""

    def setUp(self):
        match = re.search(r"^\s*'domain':\s*'([^']+)'", read("app/main.py"), re.M)
        self.assertIsNotNone(match, "no SITE['domain'] in app/main.py")
        self.domain = match.group(1)
        self.dev = f"dev.{self.domain}"
        self.www = f"www.{self.domain}"

    def test_caddy_defaults(self):
        caddy = read("Caddyfile")
        self.assertIn(f"{{$SITE_ADDRESS:{self.domain}}}", caddy)
        self.assertIn(f"{{$WWW_ADDRESS:{self.www}}}", caddy)
        self.assertIn(f"{{$SITE_ADDRESS:{self.dev}}}", read("Caddyfile.dev"))

    def test_compose_defaults(self):
        compose = read("compose.yaml")
        self.assertIn(f"${{SITE_ADDRESS:-{self.domain}}}", compose)
        self.assertIn(f"${{WWW_ADDRESS:-{self.www}}}", compose)

    def test_env_example(self):
        env = read(".env.example")
        for pattern in (rf"^SITE_ADDRESS={re.escape(self.dev)}$",
                        rf"^# SITE_ADDRESS={re.escape(self.domain)}$",
                        rf"^# WWW_ADDRESS={re.escape(self.www)}$"):
            self.assertTrue(has_line(env, pattern), f".env.example lacks a line matching {pattern}")

    def test_the_suites_point_at_production_by_default(self):
        self.assertIn(f"'https://{self.domain}'", read("tests/smoke.py"))
        self.assertIn(f"'https://{self.domain}'", read("tests/browser/playwright.config.js"))

    def test_the_workflow_falls_back_to_the_same_domain(self):
        self.assertIn(self.domain, read(".github/workflows/deploy.yml"))

    def test_the_owner_facing_skills_link_the_right_sites(self):
        recent = read(".hermes/skills/recent/scripts/recent.sh")
        self.assertIn(f"https://{self.dev}", recent)
        self.assertIn(f"https://{self.domain}", recent)
        for skill in ("site", "ship", "recent"):
            self.assertIn(self.dev, read(f".hermes/skills/{skill}/SKILL.md"), f"{skill} skill")

    def test_the_rules_and_the_onboarding_name_the_hosts(self):
        for rel in ("AGENTS.md", "DEPLOY.md", "README.md"):
            self.assertIn(self.dev, read(rel), f"{rel} does not name {self.dev}")


if __name__ == "__main__":
    unittest.main()
