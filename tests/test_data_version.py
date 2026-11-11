"""
Tests for the knowledge base data version (admin/data_version.py).

Each test builds a throwaway git repository with a small data/ folder, makes
the change under test as a commit, and checks how it is classified. The rules:
a new, deleted or renamed technique/weakness/mitigation, or a new objective,
is MINOR; any other change under data/ is PATCH; a change to the version file
alone is not a data change.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'admin'))
import data_version as dv  # noqa: E402

MODELS = 'SCHEMA_VERSION = "5.0"\n'


class Repo:
    def __init__(self, path: Path):
        self.path = path
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Test")
        self.git("config", "commit.gpgsign", "false")
        self.write("solve_it_library/models.py", MODELS)
        self.write_json("data/techniques/DFT-1001.json",
                        {"id": "DFT-1001", "name": "Image a disk", "description": "", "weaknesses": ["DFW-1001"]})
        self.write_json("data/weaknesses/DFW-1001.json",
                        {"id": "DFW-1001", "name": "Missed sectors", "mitigations": []})
        self.write_json("data/mitigations/DFM-1001.json", {"id": "DFM-1001", "name": "Verify the hash"})
        self.objectives([("DFO-1001", ["DFT-1001"]), ("DFO-1002", [])])
        self.commit("initial content")

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.path, check=True,
                              capture_output=True, text=True).stdout

    def write(self, rel, text):
        f = self.path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")

    def write_json(self, rel, obj):
        self.write(rel, json.dumps(obj, indent=4) + "\n")

    def read_json(self, rel):
        return json.loads((self.path / rel).read_text(encoding="utf-8"))

    def objectives(self, pairs):
        self.write_json("data/solve-it.json",
                        [{"id": i, "name": i, "techniques": t} for i, t in pairs])

    def commit(self, msg):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)
        return self.head()

    def head(self):
        return self.git("rev-parse", "HEAD").strip()

    def classify_last(self):
        return dv.classify("HEAD^", "HEAD", root=self.path)


class TestClassify(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.r = Repo(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def edit(self, rel, **fields):
        obj = self.r.read_json(rel)
        obj.update(fields)
        self.r.write_json(rel, obj)

    # --- MINOR ---

    def test_new_technique_is_minor(self):
        self.r.write_json("data/techniques/DFT-1002.json", {"id": "DFT-1002", "name": "New"})
        self.r.commit("add")
        self.assertEqual(self.r.classify_last(), dv.MINOR)

    def test_new_weakness_is_minor(self):
        self.r.write_json("data/weaknesses/DFW-1002.json", {"id": "DFW-1002", "name": "New"})
        self.r.commit("add")
        self.assertEqual(self.r.classify_last(), dv.MINOR)

    def test_new_mitigation_is_minor(self):
        self.r.write_json("data/mitigations/DFM-1002.json", {"id": "DFM-1002", "name": "New"})
        self.r.commit("add")
        self.assertEqual(self.r.classify_last(), dv.MINOR)

    def test_new_objective_is_minor(self):
        self.r.objectives([("DFO-1001", ["DFT-1001"]), ("DFO-1002", []), ("DFO-1003", [])])
        self.r.commit("add objective")
        self.assertEqual(self.r.classify_last(), dv.MINOR)

    def test_deleted_item_is_minor(self):
        (self.r.path / "data/mitigations/DFM-1001.json").unlink()
        self.r.commit("delete")
        self.assertEqual(self.r.classify_last(), dv.MINOR)

    def test_renamed_item_is_minor(self):
        self.r.git("mv", "data/mitigations/DFM-1001.json", "data/mitigations/DFM-1009.json")
        self.edit("data/mitigations/DFM-1009.json", id="DFM-1009")
        self.r.commit("change ID")
        self.assertEqual(self.r.classify_last(), dv.MINOR)

    # --- PATCH ---

    def test_reworded_name_is_patch(self):
        self.edit("data/techniques/DFT-1001.json", name="Image a storage device")
        self.r.commit("reword")
        self.assertEqual(self.r.classify_last(), dv.PATCH)

    def test_filling_an_empty_field_is_patch(self):
        self.edit("data/techniques/DFT-1001.json", description="Copy every sector.")
        self.r.commit("fill")
        self.assertEqual(self.r.classify_last(), dv.PATCH)

    def test_adding_a_link_between_existing_items_is_patch(self):
        self.edit("data/weaknesses/DFW-1001.json", mitigations=["DFM-1001"])
        self.r.commit("link")
        self.assertEqual(self.r.classify_last(), dv.PATCH)

    def test_removing_a_link_is_patch(self):
        self.edit("data/techniques/DFT-1001.json", weaknesses=[])
        self.r.commit("unlink")
        self.assertEqual(self.r.classify_last(), dv.PATCH)

    def test_citation_file_on_its_own_is_patch(self):
        self.r.write("data/references/DFCite-1001.bib", "@misc{x, title={X}}\n")
        self.r.commit("cite")
        self.assertEqual(self.r.classify_last(), dv.PATCH)

    def test_moving_a_technique_between_objectives_is_patch(self):
        self.r.objectives([("DFO-1001", []), ("DFO-1002", ["DFT-1001"])])
        self.r.commit("move")
        self.assertEqual(self.r.classify_last(), dv.PATCH)

    def test_repairing_a_malformed_objectives_file_is_patch(self):
        # A file that did not parse must not make every objective look new.
        self.r.write("data/solve-it.json", '[{"id": "DFO-1001", "techniques": ["DFT-1001"] "name": "x"}]')
        self.r.commit("break the file")
        self.r.objectives([("DFO-1001", ["DFT-1001"]), ("DFO-1002", [])])
        self.r.commit("repair the file")
        self.assertEqual(self.r.classify_last(), dv.PATCH)

    # --- ranges and non-changes ---

    def test_a_range_takes_its_highest_level(self):
        start = self.r.head()
        self.edit("data/techniques/DFT-1001.json", name="Reworded")
        self.r.commit("edit")
        self.r.write_json("data/weaknesses/DFW-1002.json", {"id": "DFW-1002", "name": "New"})
        self.r.commit("add")
        self.edit("data/weaknesses/DFW-1002.json", name="Reworded")
        self.r.commit("edit again")
        self.assertEqual(dv.classify(start, "HEAD", root=self.r.path), dv.MINOR)

    def test_version_file_alone_is_not_a_data_change(self):
        self.r.write_json(dv.VERSION_FILE, {"version": "0.1.0"})
        self.r.commit("version")
        self.assertIsNone(self.r.classify_last())

    def test_change_outside_data_is_not_a_data_change(self):
        self.r.write("README.md", "hello\n")
        self.r.commit("readme")
        self.assertIsNone(self.r.classify_last())


class TestVersionArithmetic(unittest.TestCase):

    def test_patch_increments(self):
        self.assertEqual(dv.next_version("0.97.0", dv.PATCH), "0.97.1")

    def test_minor_increments_and_resets_patch(self):
        self.assertEqual(dv.next_version("0.97.3", dv.MINOR), "0.98.0")

    def test_major_is_kept(self):
        self.assertEqual(dv.next_version("1.4.2", dv.MINOR), "1.5.0")


class TestReplayAndRecord(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.r = Repo(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_replay_follows_the_rules_from_the_first_commit(self):
        obj = self.r.read_json("data/techniques/DFT-1001.json")
        obj["name"] = "Reworded"
        self.r.write_json("data/techniques/DFT-1001.json", obj)
        self.r.commit("patch")
        self.r.write_json("data/weaknesses/DFW-1002.json", {"id": "DFW-1002", "name": "New"})
        self.r.commit("minor")
        self.r.write("README.md", "not data\n")
        self.r.commit("no data change")
        versions = [v for _, v in dv.replay("HEAD", root=self.r.path)]
        self.assertEqual(versions, ["0.1.0", "0.1.1", "0.2.0"])

    def test_record_carries_schema_commit_and_utc_time(self):
        rec = dv.record("0.2.0", "HEAD", root=self.r.path)
        self.assertEqual(rec["schema"], "5.0")
        self.assertEqual(rec["commit"], self.r.head())
        self.assertRegex(rec["committed_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class TestBump(unittest.TestCase):
    """bump() works from the commit the version file records, so it catches up
    any data changes a skipped workflow run missed, and always matches a replay."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.r = Repo(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def edit_name(self, rel, name):
        obj = self.r.read_json(rel)
        obj["name"] = name
        self.r.write_json(rel, obj)

    def test_catches_up_several_changes_and_ignores_its_own_commits(self):
        dv.bump("HEAD", root=self.r.path)
        self.r.commit("version file")                      # bot commit: not a data change
        self.edit_name("data/techniques/DFT-1001.json", "One")
        self.r.commit("patch")
        self.r.write_json("data/mitigations/DFM-1002.json", {"id": "DFM-1002", "name": "New"})
        self.r.commit("minor")                             # a run for this push was skipped
        self.edit_name("data/mitigations/DFM-1002.json", "Two")
        last = self.r.commit("patch")
        dv.bump("HEAD", root=self.r.path)
        rec = self.r.read_json(dv.VERSION_FILE)
        self.assertEqual(rec["version"], "0.2.1")
        self.assertEqual(rec["commit"], last)
        self.assertEqual(rec["version"], dv.replay("HEAD", root=self.r.path)[-1][1])

    def test_no_data_change_leaves_the_file_alone(self):
        dv.bump("HEAD", root=self.r.path)
        self.r.commit("version file")
        before = (self.r.path / dv.VERSION_FILE).read_text()
        self.r.write("README.md", "x\n")
        self.r.commit("not data")
        dv.bump("HEAD", root=self.r.path)
        self.assertEqual((self.r.path / dv.VERSION_FILE).read_text(), before)

    def test_missing_or_unknown_recorded_commit_rebuilds_from_history(self):
        self.edit_name("data/techniques/DFT-1001.json", "One")
        self.r.commit("patch")
        self.r.write_json(dv.VERSION_FILE, {"version": "0.50.0", "commit": "f" * 40})
        dv.bump("HEAD", root=self.r.path)
        self.assertEqual(self.r.read_json(dv.VERSION_FILE)["version"], "0.1.1")


class TestBumpWithMerges(unittest.TestCase):
    """Real data changes arrive as merge commits; bump() must match replay()."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.r = Repo(Path(self._tmp.name))
        dv.bump("HEAD", root=self.r.path)
        self.r.commit("version file")

    def tearDown(self):
        self._tmp.cleanup()

    def edit_name(self, rel, name):
        obj = self.r.read_json(rel)
        obj["name"] = name
        self.r.write_json(rel, obj)

    def merge(self, branch):
        self.r.git("switch", "-q", "main")
        self.r.git("merge", "-q", "--no-ff", "-m", f"Merge {branch}", branch)
        return self.r.head()

    def test_merged_pull_requests_are_one_version_each(self):
        self.r.git("switch", "-q", "-c", "a")
        self.edit_name("data/techniques/DFT-1001.json", "One")
        self.r.commit("edit")
        self.edit_name("data/techniques/DFT-1001.json", "Two")
        self.r.commit("edit again")
        self.merge("a")
        self.r.git("switch", "-q", "-c", "b")
        self.r.write_json("data/mitigations/DFM-1002.json", {"id": "DFM-1002", "name": "New"})
        self.r.commit("add")
        last = self.merge("b")
        dv.bump("HEAD", root=self.r.path)
        rec = self.r.read_json(dv.VERSION_FILE)
        self.assertEqual((rec["version"], rec["commit"]), ("0.2.0", last))

    def test_a_version_file_edited_on_a_branch_is_ignored(self):
        self.r.git("switch", "-q", "-c", "a")
        self.edit_name("data/techniques/DFT-1001.json", "One")
        self.r.commit("edit")
        self.edit_name("data/techniques/DFT-1001.json", "Two")
        self.r.commit("edit again")
        dv.bump("HEAD", root=self.r.path)       # someone bumps locally on the branch
        self.r.commit("locally bumped version file")
        last = self.merge("a")
        dv.bump("HEAD", root=self.r.path)
        rec = self.r.read_json(dv.VERSION_FILE)
        self.assertEqual((rec["version"], rec["commit"]), ("0.1.1", last))
        self.assertEqual(rec["version"], dv.replay("HEAD", root=self.r.path)[-1][1])

    def test_a_schema_change_alone_updates_the_file(self):
        self.r.write("solve_it_library/models.py", 'SCHEMA_VERSION = "5.2"\n')
        self.r.commit("schema change, no data change")
        dv.bump("HEAD", root=self.r.path)
        rec = self.r.read_json(dv.VERSION_FILE)
        self.assertEqual((rec["version"], rec["schema"]), ("0.1.0", "5.2"))


class TestGetVersionInfo(unittest.TestCase):

    def info(self, content):
        from types import SimpleNamespace
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from solve_it_library import KnowledgeBase
        with tempfile.TemporaryDirectory() as d:
            if content is not None:
                Path(d, "solveit_version.json").write_text(content, encoding="utf-8")
            return KnowledgeBase.get_version_info(SimpleNamespace(data_path=d))

    def test_reads_the_record(self):
        self.assertEqual(self.info('{"version": "0.1.0", "schema": "5.1"}')["version"], "0.1.0")

    def test_missing_malformed_or_incomplete_file_gives_none(self):
        self.assertIsNone(self.info(None))
        self.assertIsNone(self.info("{not json"))
        self.assertIsNone(self.info('["a list"]'))
        self.assertIsNone(self.info('{"schema": "5.1"}'))


class TestRealHistory(unittest.TestCase):
    """Fixed points in this repository's own history. History does not change,
    so these only fail if the classification rules change, which renumbers
    every version since: that must be a deliberate decision, not an accident."""

    def setUp(self):
        root = Path(dv.PROJECT_ROOT)
        shallow = subprocess.run(["git", "rev-parse", "--is-shallow-repository"], cwd=root,
                                 capture_output=True, text=True).stdout.strip()
        known = subprocess.run(["git", "cat-file", "-e", "eac86fbf8^{commit}"], cwd=root,
                               capture_output=True).returncode == 0
        if shallow != "false" or not known:
            self.skipTest("needs the full history of SOLVE-IT-DF/solve-it")

    def test_version_at_known_commits(self):
        versions = {c[:9]: v for c, v in dv.replay("eac86fbf8")}
        self.assertEqual(versions["c03373547"], "0.1.0")   # first commit of content
        # A syntax fix in solve-it.json is a patch: same minor as the change before it.
        commits = [c[:9] for c, _ in dv.replay("eac86fbf8")]
        i = commits.index("ee02414e0")
        prev, this = dv.replay("eac86fbf8")[i - 1][1], versions["ee02414e0"]
        self.assertEqual(this, dv.next_version(prev, dv.PATCH))
        self.assertEqual(versions["eac86fbf8"], "0.97.0")  # PR #712, 2026-11-10


if __name__ == '__main__':
    unittest.main()
