"""Tests for admin/generate_changelog.py: duplicate handling and source labels."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'admin'))
from generate_changelog import drop_duplicates, render_markdown


def entry(commit="aaaaaaa", id="DFT-1212", action="added", source="trwm", date="2026-10-19"):
    return {"date": date, "action": action, "type": "technique", "id": id,
            "name": "Create a case-specific keyword list", "commit": commit,
            "source": source, "issue": None}


class TestDropDuplicates(unittest.TestCase):

    def test_repeats_of_same_commit_item_and_action_are_removed(self):
        self.assertEqual(len(drop_duplicates([entry(), entry(), entry()])), 1)

    def test_same_item_in_a_different_commit_is_kept(self):
        self.assertEqual(len(drop_duplicates([entry(commit="aaaaaaa"), entry(commit="bbbbbbb")])), 2)

    def test_same_commit_changing_two_items_is_kept(self):
        self.assertEqual(len(drop_duplicates([entry(id="DFT-1211"), entry(id="DFT-1212")])), 2)

    def test_add_and_delete_in_one_commit_are_both_kept(self):
        self.assertEqual(len(drop_duplicates([entry(action="added"), entry(action="deleted")])), 2)

    def test_first_occurrence_and_order_are_kept(self):
        first, other = entry(id="DFT-1211"), entry(id="DFT-1212")
        self.assertEqual(drop_duplicates([first, other, dict(first)]), [first, other])


class TestSourceLabel(unittest.TestCase):

    def render(self, source):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "CHANGELOG_DATA.md"
            render_markdown([entry(source=source)], path)
            return path.read_text()

    def test_trwm_is_labelled(self):
        self.assertIn("Added technique (TRWM):", self.render("trwm"))

    def test_autoimplement_is_not_labelled(self):
        text = self.render("autoimplement")
        self.assertIn("Added technique:", text)
        self.assertNotIn("AUTOIMPLEMENT", text)

    def test_manual_is_not_labelled(self):
        self.assertIn("Added technique:", self.render("manual"))



class TestObjectiveChanges(unittest.TestCase):
    """data/solve-it.json changes: objectives added, removed, renamed; techniques moved."""

    @staticmethod
    def objs(*specs):
        return [{"id": i, "name": n, "description": "", "techniques": list(t)} for i, n, t in specs]

    def changes(self, before, after):
        from generate_changelog import objective_changes
        names = {"DFT-1001": "Image a disk", "DFT-1002": "Hash a file"}
        return objective_changes(before, after, lambda tid: names.get(tid, tid))

    BASE = (("DFO-1001", "Acquire", ["DFT-1001"]), ("DFO-1002", "Preserve", ["DFT-1002"]))

    def test_new_objective_is_recorded_as_added(self):
        out = self.changes(self.objs(*self.BASE), self.objs(*self.BASE, ("DFO-1003", "Evaluate evidence", [])))
        self.assertEqual(out, [{"action": "added", "type": "objective", "id": "DFO-1003", "name": "Evaluate evidence"}])

    def test_removed_objective_is_recorded_as_deleted(self):
        out = self.changes(self.objs(*self.BASE), self.objs(self.BASE[0]))
        self.assertEqual([(c["action"], c["id"]) for c in out], [("deleted", "DFO-1002")])

    def test_renamed_objective_is_recorded_as_updated(self):
        after = self.objs(("DFO-1001", "Acquire data", ["DFT-1001"]), self.BASE[1])
        self.assertEqual([(c["action"], c["id"], c["name"]) for c in self.changes(self.objs(*self.BASE), after)],
                         [("updated", "DFO-1001", "Acquire data")])

    def test_technique_moved_between_objectives(self):
        after = self.objs(("DFO-1001", "Acquire", []), ("DFO-1002", "Preserve", ["DFT-1002", "DFT-1001"]))
        out = self.changes(self.objs(*self.BASE), after)
        self.assertEqual(out, [{"action": "moved", "type": "technique", "id": "DFT-1001",
                                "name": 'Image a disk, from "Acquire" to "Preserve"'}])

    def test_new_technique_placed_under_an_objective_is_not_a_separate_entry(self):
        from generate_changelog import objective_changes
        after = self.objs(("DFO-1001", "Acquire", ["DFT-1001", "DFT-1009"]), self.BASE[1])
        self.assertEqual(objective_changes(self.objs(*self.BASE), after,
                                           changed_techniques=frozenset({"DFT-1009"})), [])

    def test_existing_technique_added_to_a_second_objective_updates_that_objective(self):
        after = self.objs(self.BASE[0], ("DFO-1002", "Preserve", ["DFT-1002", "DFT-1001"]))
        self.assertEqual([(c["action"], c["id"]) for c in self.changes(self.objs(*self.BASE), after)],
                         [("updated", "DFO-1002")])

    def test_objective_gaining_an_id_is_not_a_deletion_and_an_addition(self):
        before = [{"name": "Acquire", "techniques": ["DFT-1001"]}, {"name": "Preserve", "techniques": ["DFT-1002"]}]
        self.assertEqual(self.changes(before, self.objs(*self.BASE)), [])

    def test_existing_technique_removed_from_its_only_objective_updates_it(self):
        after = self.objs(("DFO-1001", "Acquire", []), self.BASE[1])
        self.assertEqual([(c["action"], c["id"]) for c in self.changes(self.objs(*self.BASE), after)],
                         [("updated", "DFO-1001")])

    def test_existing_unplaced_technique_placed_updates_the_objective(self):
        after = self.objs(("DFO-1001", "Acquire", ["DFT-1001", "DFT-1009"]), self.BASE[1])
        from generate_changelog import objective_changes
        out = objective_changes(self.objs(*self.BASE), after)   # DFT-1009 not added by this commit
        self.assertEqual([(c["action"], c["id"]) for c in out], [("updated", "DFO-1001")])

    def test_deleted_technique_leaving_its_objective_is_not_a_separate_entry(self):
        from generate_changelog import objective_changes
        after = self.objs(("DFO-1001", "Acquire", []), self.BASE[1])
        self.assertEqual(objective_changes(self.objs(*self.BASE), after,
                                           changed_techniques=frozenset({"DFT-1001"})), [])

    def test_objective_id_change_is_recorded_as_updated(self):
        after = self.objs(("DFO-1009", "Acquire", ["DFT-1001"]), self.BASE[1])
        self.assertEqual([(c["action"], c["id"]) for c in self.changes(self.objs(*self.BASE), after)],
                         [("updated", "DFO-1009")])

    def test_unparseable_side_gives_no_entries(self):
        self.assertEqual(self.changes(None, self.objs(*self.BASE)), [])

    def test_move_renders_readably(self):
        e = {"date": "2026-11-11", "action": "moved", "type": "technique", "id": "DFT-1001",
             "name": 'Image a disk, from "Acquire" to "Preserve"', "commit": "abc1234", "source": "manual", "issue": None}
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "c.md"
            render_markdown([e], out)
            self.assertIn('Moved technique: Image a disk, from "Acquire" to "Preserve" (DFT-1001)', out.read_text())



class TestObjectiveEntriesEndToEnd(unittest.TestCase):
    """Run the generator's main() on a throwaway repository: a commit Strategy A
    recognises that also moves its technique must give both entries, and a new
    technique's placement must not get one."""

    def test_update_and_move_in_one_commit_are_both_recorded(self):
        import json, subprocess
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)

            def git(*a):
                return subprocess.run(["git", *a], cwd=root, check=True, capture_output=True, text=True).stdout

            def write(rel, obj):
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_text(json.dumps(obj, indent=4) + "\n", encoding="utf-8")

            git("init", "-q", "-b", "main")
            git("config", "user.email", "t@example.invalid"); git("config", "user.name", "T")
            git("config", "commit.gpgsign", "false")
            write("data/techniques/DFT-1001.json", {"id": "DFT-1001", "name": "Image a disk"})
            write("data/solve-it.json", [{"id": "DFO-1001", "name": "Acquire", "techniques": ["DFT-1001"]},
                                         {"id": "DFO-1002", "name": "Preserve", "techniques": []}])
            git("add", "-A"); git("commit", "-q", "-m", "initial")
            write("data/techniques/DFT-1001.json", {"id": "DFT-1001", "name": "Image a storage device"})
            write("data/techniques/DFT-1009.json", {"id": "DFT-1009", "name": "Brand new"})
            write("data/solve-it.json", [{"id": "DFO-1001", "name": "Acquire", "techniques": ["DFT-1009"]},
                                         {"id": "DFO-1002", "name": "Preserve", "techniques": ["DFT-1001"]}])
            git("add", "-A")
            git("commit", "-q", "-m", "Update TRWM submission: Image a storage device (DFT-1001)")
            script = Path(__file__).resolve().parent.parent / "admin" / "generate_changelog.py"
            out = subprocess.run([sys.executable, str(script), "--project-root", str(root), "--dry-run"],
                                 capture_output=True, text=True, check=True).stdout
            entries = [json.loads(l) for l in out.splitlines() if l.startswith("{")]
            last = [e for e in entries if e["commit"] == git("rev-parse", "--short=7", "HEAD").strip()]
            kinds = sorted((e["action"], e["type"], e["id"]) for e in last)
            self.assertIn(("moved", "technique", "DFT-1001"), kinds)
            self.assertTrue(any(k[2] == "DFT-1001" and k[0] != "moved" for k in kinds),
                            "the Strategy A entry for DFT-1001 must survive alongside the move")
            self.assertFalse(any(k[1] == "objective" for k in kinds),
                             "placing the new DFT-1009 is covered by its own entry")
            move = next(e for e in last if e["action"] == "moved")
            self.assertEqual(list(move)[:3], ["date", "action", "type"])

if __name__ == "__main__":
    unittest.main()
