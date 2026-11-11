#!/usr/bin/env python3
"""Work out and record the version of the knowledge base data.

The data version is 0.MINOR.PATCH and is stored, with the schema version and
the commit it describes, in data/solveit_version.json. It changes every time
something under data/ changes on main:

  MINOR  a technique, weakness or mitigation is added, deleted or renamed
         (its ID changed), or a new objective appears in data/solve-it.json.
         Deleting is expected to give way to deprecation; when deprecation
         exists in the data model it is a MINOR change too.
  PATCH  any other change under data/: rewording, filling or clearing a
         field, adding or removing links, citation files, moving a technique
         between objectives, changes to other objective mappings.

MINOR resets PATCH to 0. The major number stays 0 until 1.0 is declared by
hand. Changes to data/solveit_version.json itself never count.

The schema version is separate: it is set by hand as SCHEMA_VERSION in
solve_it_library/models.py and copied into the version file here.

Usage:
  data_version.py replay [--ref REF]
      Print the version every data change on REF's first-parent line would
      have produced, ending with the version at REF.
  data_version.py init [--ref REF]
      Write data/solveit_version.json from a replay of the whole history.
  data_version.py bump [--ref REF]
      Rewrite data/solveit_version.json from a full replay up to REF, if that
      changes it (including a schema change on its own). Used by
      .github/workflows/bump-data-version.yml. Never edit the file by hand or
      commit a locally bumped copy: the workflow owns it.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = "data/solveit_version.json"
OBJECTIVES_FILE = "data/solve-it.json"
ITEM_DIRS = ("data/techniques/", "data/weaknesses/", "data/mitigations/")
MODELS_FILE = "solve_it_library/models.py"

MINOR = "minor"
PATCH = "patch"


def git(*args: str, root: Path = PROJECT_ROOT) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True,
                          capture_output=True, text=True).stdout


def _show_json(rev: str, path: str, root: Path):
    try:
        return json.loads(git("show", f"{rev}:{path}", root=root))
    except (subprocess.CalledProcessError, ValueError):
        return None


def _objective_ids(objectives) -> set:
    if not isinstance(objectives, list):
        return set()
    return {o.get("id") or o.get("name") for o in objectives if isinstance(o, dict)}


def classify(before: str, after: str, root: Path = PROJECT_ROOT) -> str | None:
    """Return MINOR, PATCH, or None when nothing under data/ changed.

    Compares the two trees directly, so a range of several commits counts
    as one change at the highest level it reaches.
    """
    # -z: paths are NUL-separated and never quoted, so unusual characters in
    # a file name cannot hide it from the checks below.
    fields = git("diff", "--name-status", "--no-renames", "-z", before, after, "--", "data/",
                 root=root).split("\0")
    level = None
    for status, path in zip(fields[0::2], fields[1::2]):
        if path == VERSION_FILE:
            continue
        level = level or PATCH
        if path.startswith(ITEM_DIRS) and path.endswith(".json") and status[0] in "AD":
            return MINOR
        if path == OBJECTIVES_FILE and status[0] != "D":
            new = _show_json(after, path, root)
            old = _show_json(before, path, root) if status[0] != "A" else []
            # A side that does not parse (the file has been committed with a
            # syntax error before) cannot show a new objective: count the
            # change as a patch rather than treating every objective as new.
            if isinstance(new, list) and isinstance(old, list) and _objective_ids(new) - _objective_ids(old):
                return MINOR
    return level


def next_version(version: str, level: str) -> str:
    major, minor, patch = (int(p) for p in version.split("."))
    if level == MINOR:
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def schema_version(rev: str | None = None, root: Path = PROJECT_ROOT) -> str:
    if rev:
        text = git("show", f"{rev}:{MODELS_FILE}", root=root)
    else:
        text = (root / MODELS_FILE).read_text(encoding="utf-8")
    m = re.search(r'^SCHEMA_VERSION\s*=\s*"(\d+\.\d+)"', text, re.MULTILINE)
    if not m:
        raise SystemExit(f"SCHEMA_VERSION not found in {MODELS_FILE}")
    return m.group(1)


def commit_time(rev: str, root: Path = PROJECT_ROOT) -> str:
    ts = int(git("log", "-1", "--format=%ct", rev, root=root).strip())
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def record(version: str, commit: str, root: Path = PROJECT_ROOT) -> dict:
    return {
        "version": version,
        "schema": schema_version(root=root),
        "commit": git("rev-parse", commit, root=root).strip(),
        "committed_at": commit_time(commit, root=root),
    }


def replay(ref: str = "HEAD", root: Path = PROJECT_ROOT) -> list[tuple[str, str]]:
    """Return (commit, version) for each first-parent commit that changed data/.

    The first such commit gives 0.1.0, as it adds the first items.
    """
    commits = git("rev-list", "--first-parent", "--reverse", ref, "--", "data/",
                  root=root).split()
    version = "0.0.0"
    out = []
    for c in commits:
        parents = git("rev-list", "--parents", "-n1", c, root=root).split()[1:]
        before = parents[0] if parents else git("hash-object", "-t", "tree", "/dev/null", root=root).strip()
        level = classify(before, c, root=root)
        if level is None:
            continue
        version = next_version(version, level)
        out.append((c, version))
    return out


def write(rec: dict, root: Path = PROJECT_ROOT) -> None:
    (root / VERSION_FILE).write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")


def bump(ref: str = "HEAD", root: Path = PROJECT_ROOT) -> str:
    """Rewrite the version file from a full replay up to REF, if it changed.

    Always replaying (about 8 seconds for the whole history) means the file
    cannot inherit an error: not from a run GitHub skipped, nor from a version
    file edited on a pull request branch, nor from a schema change with no
    data change, which only updates the 'schema' field.
    """
    history = replay(ref, root=root)
    if not history:
        return "no data changes found"
    new = record(history[-1][1], history[-1][0], root=root)
    try:
        old = json.loads((root / VERSION_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        old = None
    if old == new:
        return f"version file already up to date: {new['version']}, schema {new['schema']}"
    write(new, root=root)
    before = f"{old.get('version')}, schema {old.get('schema')}" if isinstance(old, dict) else "no valid file"
    return f"{before} -> {new['version']}, schema {new['schema']} ({new['commit'][:9]})"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("replay")
    p.add_argument("--ref", default="HEAD")
    p = sub.add_parser("init")
    p.add_argument("--ref", default="HEAD")
    p = sub.add_parser("bump")
    p.add_argument("--ref", default="HEAD")
    args = ap.parse_args(argv)

    if args.cmd == "replay":
        for c, v in replay(args.ref):
            print(f"{v}\t{c[:9]}\t{git('log', '-1', '--format=%cs %s', c).strip()[:80]}")
        return 0

    if args.cmd == "init":
        history = replay(args.ref)
        if not history:
            raise SystemExit("no data changes found")
        commit, version = history[-1]
        write(record(version, commit))
        print(f"wrote {VERSION_FILE}: {version} ({commit[:9]})")
        return 0

    print(bump(args.ref))
    return 0


if __name__ == "__main__":
    sys.exit(main())
