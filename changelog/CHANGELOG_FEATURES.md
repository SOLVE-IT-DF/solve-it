# Features Changelog

Describes features and tooling updates.

<!--
Instructions for anyone adding an entry (people and AI agents alike).

The HTML Explorer's version number is calculated from this file and from git
history by reporting_scripts/generate_html_from_kb.py (get_explorer_version):
  - each entry marked as an Explorer feature raises the minor version
    (1.0.0 was the launch; the next marked entry gives 1.N.0);
  - every other commit that changes the Explorer's code raises the patch number.

When an entry describes a NEW user-visible feature of the Explorer (the HTML
viewer at explore.solveit-df.org, or the custom viewer), copy the marker line
from an existing Explorer entry below (an HTML comment reading
"explorer: feature") and put it directly under the new heading, with no blank
line between them. It cannot be written out here, because HTML comments do
not nest.

Do not mark fixes, internal changes, or features of other tools (the JSON or
RDF exports, issue forms, workflows). Never remove or move an existing marker:
that renumbers every later version. This comment and the markers are HTML
comments, so they do not appear on the website's changelog page.
-->

### Objective changes in the data changelog (2026-11-11)

The data changelog now records changes to objectives: an objective added, removed, renamed, re-described or given a different ID; a technique moved from one objective to another; and an existing technique placed under, or removed from, an objective. A technique added or deleted in the same commit is covered by its own entry. Previously changes to `data/solve-it.json` were not recorded at all. Entries were added for the changes since objectives were given DFO- IDs on 2026-02-27 (PR [#299](https://github.com/SOLVE-IT-DF/solve-it/pull/299)); three of them come from branch commits made just before the IDs existed and are recorded under the IDs those objectives were given, including "Evaluate evidence" (DFO-1024), which moves out of the structure changelog because it changed content, not structure. Earlier changes are not backfilled: before the IDs, objectives were identified only by name, so a renamed objective cannot be told apart from one removed and another added.

### Knowledge base and schema version numbers (2026-11-11)

The knowledge base data now has a version number, 0.MINOR.PATCH, recorded with the schema version and the commit it describes in `data/solveit_version.json`. A workflow updates it on every change to `data/`: adding, deleting or renaming a technique, weakness or mitigation, or adding an objective, raises the minor number; any other change raises the patch number. Numbering was replayed from the whole history, so the first version file is 0.97.0. The schema has its own version, MAJOR.MINOR, set by hand when the structure changes (5.1, see the structure changelog). The combined JSON export carries the record as `solveit_version`, the Turtle and JSON-LD exports as an ontology header, the Excel workbook on its Info sheet, and the Explorer footer shows it, for example "Knowledge base 0.97.0, schema 5.1 (10 Nov 2026)".

### Explorer version and knowledge base commit in the footer (2026-11-11)

The footer of the Explorer and the custom viewer now shows the Explorer's version and the knowledge base commit the page was built from, for example "Explorer 1.6.0 · Knowledge base: commit eac86fbf8 (10 Nov 2026)". The commit links to GitHub. The version is worked out from this changelog and the git history each time the page is built: each new Explorer feature recorded here raises the minor number (1.0 was the launch on 2026-02-23), and any other change to the Explorer's code raises the patch number. The date is now the date a change was merged into main; previously it could be the earlier date it was written on a branch.

### Data changelog no longer repeats entries (2026-11-02)

The data changelog listed some changes many times over, for example one technique addition up to 14 times. Each daily update re-read older commits that had arrived through merged branches and added their entries again. The generator now ignores an entry when the same commit has already recorded the same action on the same item, and the existing repeats have been removed (2,449 entries became 1,103, with every distinct change kept). The "(AUTOIMPLEMENT)" label has also been dropped from entries, since it named the automation that wrote the commit and not anything about the change. The "(TRWM)" label is kept.

### Slide badges from the Explorer (2026-11-02)
<!-- explorer: feature -->

The Explorer's detail panel has a 'badge' button that produces an image (the technique, weakness or mitigation ID and name) for use in slides or other media. The menu offers three shapes (Auto, Standard or Wide) and two formats. SVG is a vector file at the badge's size in points, so it needs no resizing. PNG can be copied to the clipboard at Low quality, which pastes at the right size, or High quality, which has four times the pixels and needs resizing after pasting. A slide width box scales the size to the slide in use, and the resize guidance states the width to set. Dragging the button onto a slide delivers the same file.

### Citations in the combined JSON export (2026-10-28)

The combined JSON export at data.solveit-df.org/solve-it.json now includes a `citations` section alongside techniques, weaknesses, mitigations and objectives. Each DFCite entry carries its raw BibTeX and plaintext, plus a Harvard-style display text, so consumers of the export can show references without parsing BibTeX themselves.

### Editing items from the Explorer (2026-09-15)
<!-- explorer: feature -->

Added an edit form to the detail panel of the HTML Explorer, so a technique, weakness or mitigation can be revised in the page rather than by retyping its current values into a GitHub issue form. The form is prefilled from the item being viewed, offers the CASE, UCO and SOLVE-IT class lists when editing ontology input and output classes, and on submission opens an issue that the existing update pipeline previews as proposed JSON.

### Git history and issue search from the Explorer (2026-07-06)
<!-- explorer: feature -->

Added two buttons to the detail panel of the HTML Explorer. "Show git history" opens the commit history of the JSON file that backs the item being viewed, so the sequence of changes to a technique, weakness or mitigation can be read directly. "Search git issue mentions" opens a GitHub issue search for the item's ID, covering both open and closed issues, so the discussion behind a change can be found from the item itself.

### Drag and drop of techniques out of the Explorer (2026-06-20)
<!-- explorer: feature -->

Techniques in the HTML Explorer can now be dragged out of the page and dropped into another application open alongside it, including one running on a different origin. The drag carries the technique ID, which the receiving application uses to reconstruct the remaining detail from the knowledge base. Techniques can be dragged from the objective grid, from technique tables, and from the detail panel header.

### HTML viewer presentation mode (2026-04-16)
<!-- explorer: feature -->

Added a presentation view to the detail panel (technique only) for slide screenshots: a full-width two-column layout with weaknesses shown alongside their mitigations as a nested tree. Weakness and mitigation panels also gained hero and summary cards, mitigation counts now appear inline on weakness rows.

### Autoimplement workflow (2026-03-14)

GitHub Actions workflow to automatically implement TRWM submissions from issue forms into the knowledge base, including validation and detailed PR summaries.

### Customisable HTML explorer views (2026-03-09)
<!-- explorer: feature -->

Added support for custom HTML explorer views, allowing reorganisation of technqiues in the knowledge base (PR [#318](https://github.com/SOLVE-IT-DF/solve-it/pull/318)).

### Knowledge base validation (2026-03-05)

Added validation scripts and GitHub workflow to check knowledge base integrity, including CASE class IRI checks and cross-reference validation (PR [#302](https://github.com/SOLVE-IT-DF/solve-it/pull/302)).

### HTML explorer (2026-02-23)
<!-- explorer: feature -->

Added generation of a static HTML viewer for browsing the knowledge base, with search, deep linking, and contributor credits.

### Auto ID assignment (2026-02-23)

Automated ID assignment for new techniques, weaknesses, and mitigations via GitHub Actions.

### Issue forms for TRWM submissions (2026-02-21)

GitHub issue form templates for proposing and updating techniques, weaknesses, mitigations, and references, with auto-generated JSON stubs.

### RDF/ontology output (2026-01-08)

Added RDF generation script to export the knowledge base in ontology-compatible format.

### Markdown export (2025-10-10)

Added script to generate a markdown version of the knowledge base.

### SOLVE-IT-X extensions framework (2025-10-13)

Introduced the SOLVE-IT-X extensions framework for customising knowledge base output, including colour coding, technique worksheets, and custom library integration (PR [#228](https://github.com/SOLVE-IT-DF/solve-it/pull/228)).

### solve_it_library (2025-07-16)

Refactored generation scripts into a shared Python library with Pydantic models for techniques, weaknesses, and mitigations.

### GitHub issue templates (2025-05-27)

First issue templates for community contributions to the knowledge base.

### Excel and reporting generation (2025-01-09)

Python scripts for generating Excel (XLSX) summaries of the knowledge base.

### Initial repository (2024-12-19)

Repository created.
