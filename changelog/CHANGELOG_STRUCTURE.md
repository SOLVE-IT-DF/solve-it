# Knowledge Base Structure Changelog

Changes to the knowledge base schema.

### References format update to DFCites (2026-03-18)

Migrated references to the DFCite format (PR [#325](https://github.com/SOLVE-IT-DF/solve-it/pull/325)). This changes references to a top level object in the data folder. Uses .txt or .bib to index them. Added citation utilities, reference matching, and updated models. Introduces 'relevance_summary_280' field across entire knowledge base as part of DFCite change.  340 files changed.

### ID scheme migration (2026-03-11)

Migrated all knowledge base entries to a new ID naming scheme (PR [#320](https://github.com/SOLVE-IT-DF/solve-it/pull/320)). See article [here](https://www.solveit-df.org/2026/03/09/all-change-ids.html). 1,589 files changed across techniques, weaknesses, mitigations, and references. Follow-up fixes:

- Patched missing contributors due to ID scheme switch
- Hotfix for broken deep links due to naming change
- Restored CASE classes lost in migration
- Fixed ID scanner and assignment scripts to handle pre-migration formats (PR [#337](https://github.com/SOLVE-IT-DF/solve-it/pull/337))

### CASE/UCO input classes added (2026-02-22)

Added CASE/UCO input class fields to techniques across the knowledge base (PR [#274](https://github.com/SOLVE-IT-DF/solve-it/pull/274), PR [#276](https://github.com/SOLVE-IT-DF/solve-it/pull/276)). This complemented the existing CASE/UCO output classes, enabling techniques to describe both their required inputs and produced outputs in terms of the CASE/UCO ontology. 170+ files updated.

### CASE/UCO classes updated to full IRIs (2026-02-04)

Updated all CASE/UCO output class references to full IRIs and generalised the field to support both input and output classes (PR [#258](https://github.com/SOLVE-IT-DF/solve-it/pull/258)). 106 files changed.

### Initial knowledge base upload (2025-01-09)

First commit of SOLVE-IT content — 378 files covering techniques, weaknesses, and mitigations in JSON format.

