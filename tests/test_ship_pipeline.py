"""The pieces that let the owner's pull request merge itself have to agree on two strings.

The branch ruleset (DEPLOY.md, one-time setup) requires a status check called `check`,
which is the gate job's id in deploy.yml with no `name:` override. And the tree the
assistant ships from is fast-forwardable only if merges are merge commits, so the ship
script must arm with `--merge` and never `--squash` (ADR-0014). Neither is visible from
a green run, so they are asserted here.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "deploy.yml"
SHIP = ROOT / ".hermes" / "skills" / "ship" / "scripts" / "ship.sh"


def job_block(text, job):
    """The lines of one top-level job, up to the next job at the same indentation."""
    match = re.search(rf"^  {job}:\n(.*?)(?=^  [A-Za-z_-]+:\n|\Z)", text, re.S | re.M)
    if match is None:
        raise AssertionError(f"no job {job!r} in deploy.yml")
    return match.group(1)


class GateJobName(unittest.TestCase):
    def test_the_gate_job_is_called_check(self):
        text = WORKFLOW.read_text()
        block = job_block(text, "check")
        self.assertNotRegex(block, r"^    name:", "the ruleset requires a check named `check`; "
                            "a `name:` override would change the status context")

    def test_the_gate_runs_on_pull_requests_and_on_main(self):
        text = WORKFLOW.read_text()
        head = text.split("jobs:", 1)[0]
        self.assertIn("pull_request:", head)
        self.assertRegex(head, r"push:\n\s+branches:\s*\[main\]")


class ShipScript(unittest.TestCase):
    def test_arms_with_a_merge_commit(self):
        text = SHIP.read_text()
        self.assertIn("gh pr merge --auto --merge", text)
        self.assertNotIn("--squash", text)
        self.assertNotIn("--rebase ", text.replace("git pull -q --rebase", ""))

    def test_reports_when_arming_fails(self):
        text = SHIP.read_text()
        self.assertIn("waiting for someone to merge it", text,
                      "a silent arming failure looks like a slow merge to the owner")


if __name__ == "__main__":
    unittest.main()
