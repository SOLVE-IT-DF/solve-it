# Plan: a version number for the knowledge base data

Status: agreed design, not started (2026-11-11; schema version and JSON key added the same day).
Branch: drafted on `feat/explorer-version`, alongside the Explorer version work, which is separate (see "Related work").

## Problem

Nothing that is built from `data/` (the combined JSON, the TTL and JSON-LD, the Excel workbook, the Explorer) says which state of the knowledge base it was built from. Each consumer checks out `solve-it` `main` on its own, mostly hourly, so two outputs built in the same hour can come from different commits and nobody can tell. The only named versions are the hand-made releases (`v0.2025-07` … `v0.2026-06`).

Calculating a version from git history at build time was tried first and rejected: it needs a full-depth checkout in every consumer (`solve-it-data` and the ontology's knowledge base workflow use shallow ones), and "the last commit that changed `data/`" is a branch commit or a merge depending on what else was merged in between. A version written into `data/` once, when the change reaches `main`, avoids both problems, and any copy of `data/` carries its version with it.

## Decisions

| # | Decision | Agreed |
|---|---|---|
| D1 | What gets a version | Every change to `data/` that reaches `main`, whether by merge or direct push. |
| D2 | Where it is stored | `data/solveit_version.json`. |
| D3 | Format | `0.MINOR.PATCH`, stored as a string. MAJOR stays 0 until 1.0 is declared by hand; what 1.0 means (a completeness threshold) is not yet defined. |
| D4 | MINOR | A new technique, weakness, mitigation or objective, or an item deprecated (or deleted, or its ID changed). PATCH resets to 0. |
| D5 | PATCH | Every other change to `data/`: rewording, filling an empty field, adding or removing links, citation files, moving a technique between objectives, structural changes such as a new field. |
| D6 | Mixed changes | The higher level wins: one version per push. |
| D7 | Starting number | Replayed from the full history, so every number traces back to a merge. The prototype replay gives **0.97.0** at `origin/main` 708feb636; the real classifier sets the final figure. |
| D8 | Size and detail | Not stored. What changed is looked up (see "Looking up what changed"). |
| D9 | Structural changes | They do not affect the data version (PATCH if data files change). They are versioned separately: see D11. |
| D10 | Key in the combined JSON | `solveit_version`, holding the contents of `data/solveit_version.json`. Collides with no reader (survey 2026-11-11). marple2 to be updated to read it. |
| D11 | Schema version | Separate `MAJOR.MINOR` version of the data structure. MAJOR: a change existing readers cannot handle (field removed or renamed, value format changed). MINOR: an addition they can ignore. Set by hand in the PR that changes the schema. |
| D12 | Where the schema version is defined | `SCHEMA_VERSION` constant in `solve_it_library/models.py`, beside the models `admin/validate_kb.py` validates against. The bump bot copies it into the version file. |
| D13 | Schema starting number | Reconstructed from history: **5.0** (see "Schema version"), documented in `CHANGELOG_STRUCTURE.md`. |

Rejected alternatives, for the record:

- Any addition is MINOR (new links, filled fields): 178 minor to 43 patch over the history, so PATCH hardly moves, and the classifier must compare fields, which the prototype got wrong on #274.
- A decimal number (`0.252`): 0.99 has no unambiguous successor.
- A separate build counter beside the version: two numbers for the same thing.
- Size thresholds or per-item counting for large refactors: arbitrary, or dependent on how work is split into PRs.

## The version file

```json
{
  "version": "0.97.0",
  "schema": "5.0",
  "commit": "<full SHA of the commit on main that made the data change>",
  "committed_at": "2026-11-10T14:03:00Z"
}
```

- `commit` is the merge (or direct-push commit) that changed the data, not the bot commit that writes the file: a commit cannot contain its own hash. The bot commit only changes this file.
- `committed_at` is that commit's committer date in UTC, not the time the workflow ran.
- `schema` is copied from `SCHEMA_VERSION` in `solve_it_library/models.py` at each bump.

`KnowledgeBase.list_available_mappings()` (`solve_it_library/solveit_library.py`) treats every top-level `.json` file in `data/` as an objective mapping, so it must skip `solveit_version.json`.

## Classifier

`admin/versioning/classify_data_change.py` (name provisional): given a parent and a commit, return MINOR or PATCH.

- MINOR if, between the two:
  - a file is added under `data/techniques/`, `data/weaknesses/` or `data/mitigations/`;
  - such a file is deleted or renamed (an ID change);
  - an item is newly deprecated (once deprecation exists in the data model; see "Open items");
  - an objective ID appears in `data/solve-it.json` that was not there before.
- PATCH for any other change under `data/`, ignoring `data/solveit_version.json` itself.

A replay mode walks `git rev-list --first-parent` over `data/` and prints the version at each commit; it produces the starting number (D7) and is the main test that the rules behave on real history.

Tests, each built on a throwaway git repository (the pattern in `tests/test_explorer_version.py`):

- new technique, weakness, mitigation: MINOR; new objective: MINOR;
- item deleted, item renamed: MINOR;
- reword, filled field, link added, link removed, citation file added: PATCH;
- technique moved between objectives: PATCH;
- merge containing a new item and edits: MINOR;
- change to `solveit_version.json` alone: no version;
- PATCH resets on MINOR.

Each test must be shown to fail against a deliberately broken classifier before it is trusted.

Prototype (not for reuse as-is): `classify4.py` in the session scratchpad. It reproduced the numbers above but has no tests.

## Bump workflow

`.github/workflows/bump-data-version.yml` (new):

- Trigger: `push` to `main` with `paths: ['data/**', '!data/solveit_version.json']`. Commits pushed with `GITHUB_TOKEN` do not start workflows, so the bot's own commit cannot trigger it.
- Checkout with `fetch-depth: 0`. Classify `github.event.before..github.sha` along the first-parent line (the highest level wins, D6), read the current file, write the new one.
- Commit as `github-actions[bot]` with `[skip ci]`, as `update-changelog.yml` already does.
- `concurrency: { group: bump-data-version, cancel-in-progress: false }`, and before pushing, `git pull --rebase` with a retry, because `update-changelog.yml` also pushes to `main` after data merges. More than one data change reached `main` on 9 days in the last 90.
- If the branch is later protected, the bot will need a bypass. Neither the branch-protection API nor the rulesets API reports anything for `main` today (both return 404).

Bootstrap: the first version file is written by the replay, in the same PR that adds the workflow.

## Consumers

| Output | Where generated | Change |
|---|---|---|
| Combined JSON | `reporting_scripts/generate_combined_json_from_kb.py` | Add top-level `solveit_version` with the file's contents (D10). |
| TTL / JSON-LD | `reporting_scripts/generate_rdf_from_kb.py` | Describe the knowledge base as a dataset with its version. The ontology repo's `validate_kb_conformance.py` rejects terms the ontology does not define; check it accepts standard ones (for example `owl:versionInfo`, `dcterms:modified`) before choosing. |
| Excel | `reporting_scripts/generate_excel_from_kb.py` | An "About" sheet. |
| TSV | `generate_tsv_from_kb.py` | None: no place for it without breaking the files. |
| Explorer and custom viewer | `generate_html_from_kb.py` | Footer reads the file: `Explorer 1.6.0 · Knowledge base 0.97.0 (10 Nov 2026, commit eac86fb)`. Fall back to the git lookup when the file is absent. |
| Workflow builder | separate repo | Reads `solveit_version` for its footer. Its own `_meta` (`fetchedAt`, `lastModified`) is a different key and stays as it is. |
| marple2 (three copies) | separate repos | `api/solveit.py` lines 353 and 406 read a top-level `version` string that the file has never had; change them to read `solveit_version.version`. |

Readers survey (2026-11-11): only the workflow builder and marple2 read the combined JSON, and both pick keys by name, so a new key breaks neither. `_meta` would collide with the builder (its fallback script replaces that key) and `version` with marple2, hence D10. The MCP servers, SOLVE-IT-X, SICL, case-viewer and the TRWM tools read other files.

The consumer repos (`solve-it-data`, `solve-it-ontology`, the viewers) need no workflow changes: they check out `solve-it` and run these generators.

## Schema version

Reconstructed from `CHANGELOG_STRUCTURE.md`, the history of `solve_it_library/models.py`, and the field sets in the data files over time:

| Date | Change | Kind | Version |
|---|---|---|---|
| 2025-01-09 | Initial upload | | 1.0 |
| 2026-02-04 | CASE/UCO output classes changed to full IRIs (#258) | value format: breaking | 2.0 |
| 2026-02-22 | `CASE_input_classes` added to techniques (#274) | new field | 2.1 |
| 2026-03-04 | Objectives gain `id` and `sort_order` (#299) | new fields | 2.2 |
| 2026-03-11 | ID scheme `T1001` to `DFT-1001` (#320) | breaking | 3.0 |
| 2026-03-18 | References become DFCite objects with `relevance_summary_280` (#325) | breaking | 4.0 |
| 2026-03-19 | Six ASTM fields replaced by `categories` (#359) | breaking | 5.0 |

Not counted: misspelt keys that appeared in a few files and were cleaned up (`techqniue`, `INAC-EX_comment`), and `description` appearing in a few weakness and mitigation files; these were fixes. The field scan sampled files per commit, so dates for small changes are approximate.

Documentation, in the same PR:

- `CHANGELOG_STRUCTURE.md`: put the schema version on each entry; add the missing #299 entry; move "New objective: Evaluate evidence" (2026-07-14) to the data changelog, because it is content, not schema. Add a short note at the top explaining the versioning rule, as an HTML comment for agents plus a visible sentence for readers.
- `solve_it_library/models.py`: a comment beside `SCHEMA_VERSION` with the rule and a pointer to the structure changelog.
- CI: a check in `validate-kb.yml` that fails, or warns, when a PR changes `models.py` without changing `SCHEMA_VERSION`. Warn rather than fail, because some `models.py` changes (docstrings, validators that accept the same data) are not schema changes.

## Looking up what changed

The version file records only the commit. Between two versions:

- on GitHub: `https://github.com/SOLVE-IT-DF/solve-it/compare/<commit A>...<commit B>`;
- locally: `git log --first-parent <A>..<B> -- data/`, or `git diff <A> <B> -- data/`.

`changelog/changelog.jsonl` entries record the branch commit where an item was edited, not the merge on `main` (all 24 entries checked on 2026-11-11), so they cannot be matched to a version by commit. They can be matched by date, or the changelog generator could later stamp each entry with the version it arrived in. Not part of this plan.

## Releases

Named releases stay on demand, with the aim of making them more regular. Out of scope here, but next: a workflow that keeps a draft GitHub release up to date (notes from `changelog.jsonl` since the last tag, the statistics table, generated files attached) so publishing is one click; optionally a reminder issue after a set time or number of changes. A release would record the data version it was cut at.

## Open items

1. Deprecation does not exist in the data model: no technique, weakness or mitigation file has a `status` or `deprecated` field. The MINOR rule for it is ready; the field is separate work.
2. RDF terms for the version. The ontology's `validate_kb_conformance.py` only rejects undefined SOLVE-IT terms, so `owl:versionInfo` and `dcterms:` terms pass it; whether `case_validate` (CASE 1.5.0 job) accepts them is untested. Generate a file and run it locally before choosing.
3. What data-version MAJOR / 1.0 means.
4. Whether the schema-change check in CI warns or fails.

## Related work

- Explorer version (same branch, uncommitted): `get_explorer_version` in `generate_html_from_kb.py`, calculated from `<!-- explorer: feature -->` markers in `changelog/CHANGELOG_FEATURES.md`; 1.6.0 today. Code, not data, so it stays calculated.
- `get_source_data_date` / `get_source_data_commit` now use `--first-parent`; they become the fallback once the version file exists.
- Workflow builder footer (CORE `608ef7e`, unpushed) is waiting on the JSON field from this plan.
