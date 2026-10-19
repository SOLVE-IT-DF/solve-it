# Explorer page assets

Files here are read by `../generate_html_from_kb.py` and inlined into the
generated page. They are not served separately: the Explorer is deployed to
GitHub Pages as a single `index.html`, and people also keep local copies of it,
so everything the page needs has to be inside the file.

They live here rather than inside the generator's template string for one
practical reason. That template is a Python f-string, so every `{` and `}` in
it has to be doubled. Editing a few thousand lines of JavaScript under that
rule is not reasonable, and a missed brace fails at build time with an error
that points at the wrong place. Read as files and substituted in, the contents
are never re-scanned for braces, so they are ordinary JavaScript and CSS.

| File | What it is |
|---|---|
| `editor.js` | The "Suggest an edit" form: field specs, the knowledge base and ontology lookups, change detection, and the GitHub issue body it produces. The body opens with an HTML-comment marker that `.github/workflows/issue-preview.yml` turns into the issue labels, because GitHub ignores the `labels=` URL parameter for contributors who cannot add labels by hand. The labels are `content: update <item>`, which the autoimplement and revised-proposal workflows are gated on, and `explorer`, which records the route the issue took and which nothing is gated on. `form input` is deliberately not among them: a blank issue is not a form submission, and no workflow reads that label on an issue from here. |
| `editor.css` | Styling for that form, using the design tokens the page already defines. |
| `ontology_classes.json` | CASE, UCO and SOLVE-IT classes and properties, for the ontology fields. |

A missing file is not fatal — the page still generates, with a warning, just
without the edit form.

## Refreshing the ontology list

`ontology_classes.json` is generated and checked in, not fetched at build time:

```bash
python3 reporting_scripts/build_ontology_classes.py
```

The viewer is rebuilt hourly and the ontologies change a few times a year, so
fetching around thirty Turtle files on every build would make the hourly job
slow and would fail it whenever GitHub was briefly unreachable.

The SOLVE-IT ontology changes often, so its refresh is automatic. A push to
solve-it-ontology's main branch that touches a `solve_it_*.ttl` module sends a
`repository_dispatch` event here (from its `notify-solve-it.yml`), and
`.github/workflows/refresh-ontology-classes.yml` rebuilds the list from the
pushed commit and commits it if anything changed. That needs the
`SOLVE_IT_DISPATCH_TOKEN` secret on solve-it-ontology; if a new class is not
showing up, check that workflow's runs there first.

The SOLVE-IT modules are not listed in the script. It asks the GitHub API for
the files in the ontology repository at the commit being built and reads every
top-level `solve_it_*.ttl`, so a new module is picked up on the push that adds
it. If that listing fails (no network, a bad ref, or the API's rate limit for
anonymous calls, which is 60 an hour), the script writes nothing. It uses
`GITHUB_TOKEN` from the environment when there is one; the workflow sets it.
The UCO and CASE modules are still listed in the script, since they only change
with a release.

CASE/UCO releases are not automatic. When one is published, run the script with
`--uco-ref` / `--case-ref`, or run the refresh workflow by hand after changing
the defaults. `--solveit-ref` builds from a particular ontology branch or commit
rather than `main`. The script refuses to write a partial list if any module
fails to fetch, unless you pass `--allow-partial`.

## Tests

- `tests/test_editor_labels.py` — every heading `editor.js` emits exists in the
  matching issue template, and the issue label the workflows are gated on
  matches the template's. This is the one that stops a field silently going
  nowhere.
- `tests/test_editor_body.py` — runs the real body builder through
  `tests/editor_body_harness.mjs` and feeds its output to the real issue
  parsers, so the round trip is checked rather than assumed. Needs Node.
- `tests/test_generate_html.py` — the assets actually reach the generated page.
