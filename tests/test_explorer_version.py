"""
Tests for the Explorer version number and the footer that shows it.

The version is calculated from git history (see get_explorer_version in
reporting_scripts/generate_html_from_kb.py), so each test builds a small
throwaway repository with the history it needs, rather than relying on the
real repository's history, which keeps changing.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'reporting_scripts'))
from generate_html_from_kb import (  # noqa: E402
    EXPLORER_FEATURE_MARKER, get_explorer_version, get_source_data_commit,
    get_source_data_date,
)

CHANGELOG = "changelog/CHANGELOG_FEATURES.md"
EXPLORER_CODE = "reporting_scripts/generate_html_from_kb.py"


class GitRepo:
    """A temporary git repository with helpers for writing and committing."""

    def __init__(self, path: Path):
        self.path = path
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Test")
        self.git("config", "commit.gpgsign", "false")
        self._n = 0

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.path, check=True,
                              capture_output=True, text=True).stdout

    def write(self, rel: str, text: str) -> None:
        f = self.path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")

    def commit(self, msg: str) -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)

    def change_code(self, msg: str = "explorer change") -> None:
        self._n += 1
        self.write(EXPLORER_CODE, f"# version {self._n}\n")
        self.commit(msg)

    def change_other(self, msg: str = "unrelated change") -> None:
        self._n += 1
        self.write("data/techniques/DFT-1001.json", f'{{"n": {self._n}}}\n')
        self.commit(msg)

    def set_features(self, n: int, other: int = 0) -> None:
        """Write a changelog with n marked Explorer entries and `other` unmarked ones."""
        parts = ["# Features Changelog\n"]
        for i in range(n):
            parts.append(f"### Explorer feature {i}\n{EXPLORER_FEATURE_MARKER}\n\nText.\n")
        for i in range(other):
            parts.append(f"### Other feature {i}\n\nText.\n")
        self.write(CHANGELOG, "\n".join(parts))


class TestExplorerVersion(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = GitRepo(Path(self._tmp.name))
        self.repo.change_code("initial code")

    def tearDown(self):
        self._tmp.cleanup()

    def version(self):
        return get_explorer_version(self.repo.path)

    def test_launch_entry_alone_is_1_0_0(self):
        self.repo.set_features(1)
        self.repo.commit("launch entry")
        self.assertEqual(self.version(), "1.0.0")

    def test_each_marked_entry_raises_the_minor_version(self):
        self.repo.set_features(7, other=12)
        self.repo.commit("entries")
        self.assertEqual(self.version(), "1.6.0")

    def test_code_changes_before_the_latest_entry_are_not_counted(self):
        # The usual order in this repository: code first, changelog entry after.
        self.repo.set_features(1)
        self.repo.commit("launch entry")
        self.repo.change_code("feature code")
        self.repo.set_features(2)
        self.repo.commit("feature entry")
        self.assertEqual(self.version(), "1.1.0")

    def test_code_changes_after_the_latest_entry_are_patches(self):
        self.repo.set_features(2)
        self.repo.commit("entries")
        self.repo.change_code("fix one")
        self.repo.change_code("fix two")
        self.assertEqual(self.version(), "1.1.2")

    def test_commits_that_do_not_touch_explorer_code_are_not_patches(self):
        self.repo.set_features(2)
        self.repo.commit("entries")
        self.repo.change_other("data change")
        self.repo.change_other("another data change")
        self.assertEqual(self.version(), "1.1.0")

    def test_feature_merged_from_a_branch_is_not_counted_as_its_own_fix(self):
        # Code and changelog entry on a branch, merged with a merge commit.
        # The merge carries the feature's code, but it is the feature, not a fix.
        self.repo.set_features(1)
        self.repo.commit("launch entry")
        self.repo.git("switch", "-q", "-c", "feat/x")
        self.repo.change_code("feature code")
        self.repo.set_features(2)
        self.repo.commit("feature entry")
        self.repo.change_code("polish on the branch, after the entry")
        self.repo.git("switch", "-q", "main")
        self.repo.change_other("something else on main meanwhile")
        self.repo.git("merge", "-q", "--no-ff", "-m", "Merge feat/x", "feat/x")
        self.assertEqual(self.version(), "1.1.0")
        self.repo.change_code("fix after the merge")
        self.assertEqual(self.version(), "1.1.1")

    def test_a_merged_fix_branch_counts_once_however_many_commits_it_has(self):
        self.repo.set_features(2)
        self.repo.commit("entries")
        self.repo.git("switch", "-q", "-c", "fix/y")
        self.repo.change_code("fix part one")
        self.repo.change_code("fix part two")
        self.repo.change_code("fix part three")
        self.repo.git("switch", "-q", "main")
        self.repo.change_other("something else on main meanwhile")
        self.repo.git("merge", "-q", "--no-ff", "-m", "Merge fix/y", "fix/y")
        self.assertEqual(self.version(), "1.1.1")

    def test_changelog_annotation_does_not_change_the_version(self):
        # admin/generate_changelog.py puts an "Explorer version" line under each
        # marker; the calculation must be unaffected.
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'admin'))
        from generate_changelog import annotate_features_changelog
        self.repo.set_features(3)
        self.repo.commit("entries")
        before = self.version()
        annotate_features_changelog(self.repo.path / CHANGELOG)
        self.repo.commit("annotate")
        self.assertEqual(self.version(), before)

    def test_marker_must_be_directly_under_a_heading(self):
        self.repo.set_features(1)
        text = (self.repo.path / CHANGELOG).read_text()
        text += f"\n### Not counted\n\n{EXPLORER_FEATURE_MARKER}\n"
        self.repo.write(CHANGELOG, text)
        self.repo.commit("entries")
        self.assertEqual(self.version(), "1.0.0")

    def test_no_marked_entries_gives_no_version(self):
        self.repo.set_features(0, other=3)
        self.repo.commit("entries")
        self.assertIsNone(self.version())

    def test_no_git_history_gives_no_version(self):
        with tempfile.TemporaryDirectory() as plain:
            (Path(plain) / "changelog").mkdir()
            (Path(plain) / CHANGELOG).write_text(
                f"### Explorer\n{EXPLORER_FEATURE_MARKER}\n", encoding="utf-8")
            self.assertIsNone(get_explorer_version(Path(plain)))

    def test_shallow_clone_gives_no_version(self):
        # A count from partial history would be a wrong number, not a missing one.
        self.repo.set_features(2)
        self.repo.commit("entries")
        self.repo.change_code("fix")
        with tempfile.TemporaryDirectory() as clone_dir:
            subprocess.run(["git", "clone", "-q", "--depth", "1",
                            f"file://{self.repo.path}", clone_dir],
                           check=True, capture_output=True)
            self.assertIsNone(get_explorer_version(Path(clone_dir)))


class TestSourceDataCommit(unittest.TestCase):

    def test_is_the_last_commit_that_changed_data_not_head(self):
        with tempfile.TemporaryDirectory() as d:
            repo = GitRepo(Path(d))
            repo.change_other("data change")
            data_commit = repo.git("rev-parse", "--short", "HEAD").strip()
            repo.change_code("later code change")
            self.assertEqual(get_source_data_commit(repo.path), data_commit)

    def test_a_merged_data_change_is_identified_by_its_merge(self):
        # The data commit is written on 1 Oct and merged into main on 9 Oct,
        # with no other data change on main in between. The knowledge base
        # changed on 9 Oct, at the merge; plain `git log -- data/` would
        # report the branch commit and 1 Oct instead.
        with tempfile.TemporaryDirectory() as d:
            repo = GitRepo(Path(d))
            repo.change_other("initial data")
            repo.git("switch", "-q", "-c", "content/x")
            os.environ["GIT_COMMITTER_DATE"] = "2026-10-01T12:00:00+00:00"
            try:
                repo.change_other("data edit on the branch")
                repo.git("switch", "-q", "main")
                repo.change_code("unrelated code change on main")
                os.environ["GIT_COMMITTER_DATE"] = "2026-10-09T12:00:00+00:00"
                repo.git("merge", "-q", "--no-ff", "-m", "Merge content/x", "content/x")
            finally:
                del os.environ["GIT_COMMITTER_DATE"]
            merge = repo.git("rev-parse", "--short", "HEAD").strip()
            self.assertEqual(get_source_data_commit(repo.path), merge)
            self.assertEqual(get_source_data_date(repo.path), "2026-10-09")


class TestFooter(unittest.TestCase):
    """The footer shows the Explorer version and the data commit when known,
    and leaves each out, rather than guessing, when it is not."""

    @classmethod
    def setUpClass(cls):
        from generate_html_from_kb import load_from_local, build_indices, generate_html
        repo_root = Path(os.path.dirname(__file__)).parent
        db = load_from_local(str(repo_root))
        idx = build_indices(db)
        cls.with_ids = generate_html(db, idx, source_date="2026-10-30",
                                     source_commit="9fd7804", explorer_version="1.6.0")
        cls.without = generate_html(db, idx, source_date="2026-10-30")

    def test_footer_shows_version_and_commit(self):
        self.assertIn('Explorer <a href="https://www.solveit-df.org/about/changelog/features/#explorer-1.6"', self.with_ids)
        self.assertIn(">1.6.0</a> &middot; Knowledge base: commit", self.with_ids)
        self.assertIn(">9fd7804</a> (30 Oct 2026)", self.with_ids)
        self.assertIn('href="https://github.com/SOLVE-IT-DF/solve-it/commit/9fd7804"', self.with_ids)

    def test_footer_prefers_the_version_file(self):
        from generate_html_from_kb import load_from_local, build_indices, generate_html
        repo_root = Path(os.path.dirname(__file__)).parent
        db = load_from_local(str(repo_root))
        html = generate_html(db, build_indices(db), source_date="2026-10-30", source_commit="9fd7804",
                             explorer_version="1.6.0",
                             version_info={"version": "0.97.0", "schema": "5.0",
                                           "commit": "eac86fbf8b960e5ca1e2eddf501fe2937110be1f",
                                           "committed_at": "2026-11-10T21:35:42Z"})
        base = "https://www.solveit-df.org/about/changelog/"
        self.assertIn(f'Knowledge base <a href="{base}data/#data-0.97.0"', html)
        self.assertIn(f'schema <a href="{base}schema/#schema-5.0"', html)
        self.assertIn(">0.97.0</a>, schema", html)
        self.assertIn(">5.0</a> (10 Nov 2026)", html)
        self.assertIn("commit eac86fbf8", html)      # the commit is still given, in the link title
        self.assertNotIn("9fd7804", html)

    def test_footer_omits_what_is_unknown(self):
        self.assertIn("Knowledge base updated 30 Oct 2026", self.without)
        self.assertNotIn("Explorer 1.", self.without)
        self.assertNotIn("/commit/", self.without)


if __name__ == "__main__":
    unittest.main()
