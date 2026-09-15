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
slow and would fail it whenever GitHub was briefly unreachable. Run the script
when a new CASE/UCO release is published, and pass `--uco-ref` / `--case-ref` to pin a
different version. It refuses to write a partial list if any module fails to
fetch, unless you pass `--allow-partial`.

## Tests

- `tests/test_editor_labels.py` — every heading `editor.js` emits exists in the
  matching issue template, and the issue label the workflows are gated on
  matches the template's. This is the one that stops a field silently going
  nowhere.
- `tests/test_editor_body.py` — runs the real body builder through
  `tests/editor_body_harness.mjs` and feeds its output to the real issue
  parsers, so the round trip is checked rather than assumed. Needs Node.
- `tests/test_generate_html.py` — the assets actually reach the generated page.
