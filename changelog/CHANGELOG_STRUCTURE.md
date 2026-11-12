# Knowledge Base Schema Changelog

Changes to the knowledge base schema.

Each schema change has a version, MAJOR.MINOR. MAJOR goes up for a change that existing readers of the data cannot handle, such as a field removed or renamed or the format of a value changed; MINOR goes up for an addition they can ignore. The current schema version is recorded in `data/solveit_version.json` and in every generated output. Versions before 5.1 were assigned retrospectively, in November 2026.

<!--
Instructions for anyone changing the structure of the data (people and AI agents alike):
change SCHEMA_VERSION in solve_it_library/models.py in the same pull request,
following the rule above, and add an entry here with a "Schema version: X.Y" line
directly under its heading. A change to content only (new items, a new objective)
is not a schema change and does not belong here: the data changelog records it.
-->

### Version file added to the data folder (2026-11-11)

<a id="schema-5.1"></a>Schema version: 5.1

Added `data/solveit_version.json`, which records the knowledge base data version, the schema version and the commit they describe. A workflow updates it on every change to `data/`; it is not edited by hand. It is not an objective mapping, and `list_available_mappings()` no longer lists it. The combined JSON export carries the same record under a new top-level `solveit_version` key, and the RDF export as an ontology header on the data namespace.

### Weakness classes migration (2026-03-19)

<a id="schema-5.0"></a>Schema version: 5.0

Migrated weakness ASTM error classification from 6 individual boolean-style fields (`INCOMP`, `INAC-EX`, etc.) to a single `categories` list field. Each class code is now prefixed with `ASTM_` (e.g. `ASTM_INCOMP`, `ASTM_INAC_EX`). 271 weakness files updated. Issue forms changed from checkboxes to textarea input. Ontology updated to use `hasWeaknessClass` object property with `ASTMErrorCategory` named individuals.

### References format update to DFCites (2026-03-18)

<a id="schema-4.0"></a>Schema version: 4.0

Migrated references to the DFCite format (PR [#325](https://github.com/SOLVE-IT-DF/solve-it/pull/325)). This changes references to a top level object in the data folder. Uses .txt or .bib to index them. Added citation utilities, reference matching, and updated models. Introduces 'relevance_summary_280' field across entire knowledge base as part of DFCite change.  340 files changed.

### ID scheme migration (2026-03-11)

<a id="schema-3.0"></a>Schema version: 3.0

Migrated all knowledge base entries to a new ID naming scheme (PR [#320](https://github.com/SOLVE-IT-DF/solve-it/pull/320)). See article [here](https://www.solveit-df.org/2026/03/09/all-change-ids.html). 1,589 files changed across techniques, weaknesses, mitigations, and references. Follow-up fixes:

- Patched missing contributors due to ID scheme switch
- Hotfix for broken deep links due to naming change
- Restored CASE classes lost in migration
- Fixed ID scanner and assignment scripts to handle pre-migration formats (PR [#337](https://github.com/SOLVE-IT-DF/solve-it/pull/337))

### Objective IDs and sort order added (2026-03-04)

<a id="schema-2.2"></a>Schema version: 2.2

Added an `id` (for example `DFO-1001`) and a `sort_order` to each objective in the objective mappings (PR [#299](https://github.com/SOLVE-IT-DF/solve-it/pull/299)). Both fields are optional in the model, so readers that ignore them are unaffected.

### CASE/UCO input classes added (2026-02-22)

<a id="schema-2.1"></a>Schema version: 2.1

Added CASE/UCO input class fields to techniques across the knowledge base (PR [#274](https://github.com/SOLVE-IT-DF/solve-it/pull/274), PR [#276](https://github.com/SOLVE-IT-DF/solve-it/pull/276)). This complemented the existing CASE/UCO output classes, enabling techniques to describe both their required inputs and produced outputs in terms of the CASE/UCO ontology. 170+ files updated.

### CASE/UCO classes updated to full IRIs (2026-02-04)

<a id="schema-2.0"></a>Schema version: 2.0

Updated all CASE/UCO output class references to full IRIs and generalised the field to support both input and output classes (PR [#258](https://github.com/SOLVE-IT-DF/solve-it/pull/258)). 106 files changed.

### Initial knowledge base upload (2025-01-09)

<a id="schema-1.0"></a>Schema version: 1.0

First commit of SOLVE-IT content — 378 files covering techniques, weaknesses, and mitigations in JSON format.

