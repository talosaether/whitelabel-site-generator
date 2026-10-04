"""The pieces that let the owner's pull request merge itself have to agree.

The ruleset on main requires a status check called `check`, which is the gate job's id in
deploy.yml with no `name:` override. The tree the assistant ships from stays
fast-forwardable only if merges are merge commits, so the ship script must use `--merge`
and never `--squash`. And the script has three endings, each of which the owner hears
about: armed, merged at once because the tests had already passed for that commit, or
waiting for a person. The last two were learned the hard way (the first site's day-long
wait, and the second site's approved pull request that sat green and unarmed), so the
script is run here against a stub `gh` for each.
"""

import os
import re
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "deploy.yml"
SHIP = ROOT / ".hermes" / "skills" / "ship" / "scripts" / "ship.sh"

# A stand-in for gh: logs each call, and answers according to the scenario in $GH_SCENARIO.
STUB_GH = r"""#!/usr/bin/env bash
echo "gh $*" >> "$GH_LOG"
case "$1 $2" in
  "pr create") echo "https://github.com/OWNER/REPO/pull/99" ;;
  "pr merge")
    if [[ " $* " == *" --auto "* ]]; then [ "$GH_SCENARIO" = armed ]; exit $?; fi
    [ "$GH_SCENARIO" = already-green ]; exit $? ;;
  "run list") [ "$GH_SCENARIO" = already-green ] && echo 1 || echo 0 ;;
esac
"""


def job_block(text, job):
    match = re.search(rf"^  {job}:\n(.*?)(?=^  [A-Za-z_-]+:\n|\Z)", text, re.S | re.M)
    if match is None:
        raise AssertionError(f"no job {job!r} in deploy.yml")
    return match.group(1)


class GateJobName(unittest.TestCase):
    def test_the_gate_job_is_called_check(self):
        block = job_block(WORKFLOW.read_text(), "check")
        self.assertNotRegex(block, r"(?m)^    name:", "the ruleset requires a check named `check`; "
                            "a `name:` override would change the status context")

    def test_the_gate_runs_on_pull_requests_and_on_main(self):
        head = WORKFLOW.read_text().split("jobs:", 1)[0]
        self.assertIn("pull_request:", head)
        self.assertRegex(head, r"push:\n\s+branches:\s*\[main\]")


class ShipScriptText(unittest.TestCase):
    def test_merges_are_merge_commits(self):
        text = SHIP.read_text()
        self.assertIn("gh pr merge --auto --merge", text)
        self.assertNotIn("--squash", text)
        self.assertNotIn("--rebase ", text.replace("git pull -q --rebase", ""))

    def test_the_direct_merge_is_only_tried_after_a_green_run(self):
        text = SHIP.read_text()
        self.assertIn('elif passed && gh pr merge --merge "$branch"', text,
                      "merging without arming must be conditional on a successful run for the commit")


class ShipScriptRuns(unittest.TestCase):
    """Run the real script in a throwaway repository with a stub gh on PATH."""

    def ship(self, scenario):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            origin, tree, bindir = tmp / "origin.git", tmp / "tree", tmp / "bin"
            bindir.mkdir()
            gh = bindir / "gh"
            gh.write_text(STUB_GH)
            gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
            env = dict(os.environ, PATH=f"{bindir}:{os.environ['PATH']}", GH_LOG=str(tmp / "gh.log"),
                       GH_SCENARIO=scenario, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
                       GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")

            def git(*args, cwd=tree):
                subprocess.run(["git", *args], cwd=cwd, env=env, check=True, capture_output=True)

            subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
            subprocess.run(["git", "init", "-q", "-b", "main", str(tree)], check=True)
            (tree / "app").mkdir()
            (tree / "frontend").mkdir()
            (tree / "app" / "page.txt").write_text("one\n")
            (tree / "frontend" / "style.css").write_text("a{}\n")
            git("add", "."), git("commit", "-q", "-m", "first")
            git("remote", "add", "origin", str(origin)), git("push", "-q", "origin", "main")
            git("fetch", "-q", "origin")
            (tree / "app" / "page.txt").write_text("two\n")          # the owner's edit
            script = tmp / "ship.sh"
            script.write_text(re.sub(r"(?m)^cd /srv/\S+$", f"cd {tree}", SHIP.read_text()))
            result = subprocess.run(["bash", str(script), "a new headline"], env=env,
                                    capture_output=True, text=True)
            log = (tmp / "gh.log").read_text() if (tmp / "gh.log").exists() else ""
            return result, log

    def test_armed_when_the_tests_have_yet_to_run(self):
        result, log = self.ship("armed")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("merges itself when the tests pass", result.stdout)
        self.assertNotRegex(log, r"gh pr merge --merge", "armed is enough; no direct merge")

    def test_merged_at_once_when_the_commit_was_already_green(self):
        result, log = self.ship("already-green")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("already passed", result.stdout)
        self.assertRegex(log, r"gh pr merge --merge hermes/")

    def test_waiting_is_reported_and_nothing_is_merged_without_a_green_run(self):
        result, log = self.ship("broken")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("waiting for someone to merge it", result.stdout)
        self.assertNotRegex(log, r"gh pr merge --merge hermes/",
                            "no successful run for the commit, so no direct merge")


if __name__ == "__main__":
    unittest.main()
