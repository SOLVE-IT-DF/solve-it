# Features Changelog

Describes features and tooling updates.

### Autoimplement workflow (2026-03-14)

GitHub Actions workflow to automatically implement TRWM submissions from issue forms into the knowledge base, including validation and detailed PR summaries.

### Customisable HTML explorer views (2026-03-09)

Added support for custom HTML explorer views, allowing reorganisation of technqiues in the knowledge base (PR [#318](https://github.com/SOLVE-IT-DF/solve-it/pull/318)).

### Knowledge base validation (2026-03-05)

Added validation scripts and GitHub workflow to check knowledge base integrity, including CASE class IRI checks and cross-reference validation (PR [#302](https://github.com/SOLVE-IT-DF/solve-it/pull/302)).

### HTML explorer (2026-02-23)

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
