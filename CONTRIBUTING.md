# Contributing to SOLVE-IT

## Introduction

There are multiple ways you can contribute to SOLVE-IT. This document provides a quick-start overview — for detailed procedural guidance, see the [Detailed Contributor Guide](CONTRIBUTOR_GUIDE.md). For writing standards, see the [Style Guide](STYLE_GUIDE.md).

## Why contribute?

Contributing to SOLVE-IT gives your work practical visibility within the digital forensics community. The [DFPulse 2024 Practitioner Survey](https://doi.org/10.1016/j.fsidi.2024.301844) revealed that the links between academic work and digital forensics practitioners are very poor — SOLVE-IT bridges that gap.

For *researchers*, linking your work in the specific context of a digital forensic technique makes it easier to find, and distilling it into the fields captured by the entries for techniques, weaknesses, or mitigations makes the application of your work obvious — while providing a means to link to the original publication.

For *practitioners* it is easier to highlight issues in techniques and show how they can be overcome to ensure reliable evidence despite limitations of tools or processes. Through SOLVE-IT you can support colleagues across the world to prevent mistakes being made using your knowledge.  


Whether you are a researcher or a practitioner, the act of distilling work into a SOLVE-IT technique and enumerating weaknesses and mitigations has been reported to improve understanding of the topics and process. Articulating weaknesses forces us all to consider what can go wrong in digital investigations, and proposing mitigations captures solutions that might otherwise remain implicit.


## Content that can be contributed

The SOLVE-IT knowledge base accepts contributions of **techniques**, **weaknesses**, **mitigations**, and **references**. For an explanation of these concepts and how they relate to each other, see [Detailed Contributor Guide — Overview](CONTRIBUTOR_GUIDE.md#overview).

Other contributions are also welcome to related projects:

- the [SOLVE-IT website](https://www.solveit-df.org) also invites [articles](https://www.solveit-df.org/articles/) from those making use or contributions to SOLVE-IT.
- the [SOLVE-IT education repository](https://github.com/SOLVE-IT-DF/solve-it-education) invites additional content for educating others about SOLVE-IT.
- make use of [SOLVE-IT-X](https://github.com/SOLVE-IT-DF/solve-it-x) to build custom versions of SOLVE-IT augmented with your own content.
- the [Review of AI applicability in digital forensics using SOLVE-IT](https://github.com/SOLVE-IT-DF/solve-it-applications-ai-review) - this is a SOLVE-IT-X extension example repo, which invites bibtex entries that document the use of AI for assisting with digital forensic techniques.

## Contribution workflow

All contributions start the same way:

1. **Check if it already exists** — search the [SOLVE-IT Explorer](https://explore.solveit-df.org/) or use the [MCP server](https://github.com/CKE-Proto/solve_it_mcp). If the content already exists, you can propose an update instead of a new item. See the [Detailed Contributor Guide](CONTRIBUTOR_GUIDE.md#check-if-it-already-exists) for more ways to check.
2. **Open a GitHub issue** — use one of the [issue form templates](https://github.com/SOLVE-IT-DF/solve-it/issues/new/choose) to propose your content. You can also submit directly from the Explorer (see below).

From there, there are two paths:

### Path 1: Automated (recommended for most contributions)

3. **Reviewers and automation handle the rest** — your issue is previewed, and a reviewer will check it and may suggest changes. Once approved, your contribution is assigned an ID (if new) and turned into a pull request automatically. Validation runs on the PR. You don't need to edit any files or run any scripts. See the [Detailed Contributor Guide — Pipeline](CONTRIBUTOR_GUIDE.md#the-contribution-pipeline) for details.

### Path 2: Manual edits (for bulk or cross-file changes)

If your contribution requires editing multiple files directly (e.g. bulk updates, structural changes), you can make the changes yourself after your issue has been reviewed:

3. **Fork and edit** — follow the standard [GitHub Flow](https://docs.github.com/en/get-started/using-github/github-flow) workflow.
4. **Run validation** — you must run `python admin/validate_kb.py` before submitting your pull request (see [Validation](#validation)).
5. **Submit a pull request** linked to your issue.

## Submitting from the Explorer

You can submit issues directly from the [SOLVE-IT Explorer](https://explore.solveit-df.org/), either within a technique, weakness, or mitigation (see 'Propose an update to this technique' button shown below), or to submit new content via the tabs which have a 'Propose new technique' button.

<img width="600" height="180" alt="Shows updating this content on GitHub button" src="https://github.com/user-attachments/assets/aa4b7dd0-f725-4329-b013-065e138d0277" />

<img width="1512" height="229" alt="Shows the new technique button in the 'Techniques' tab" src="https://github.com/user-attachments/assets/e61b86c2-cf1c-4758-a8b5-5fa7d0cdb53f" />



## Validation

Prior to submitting a pull request, run the `/admin/validate_kb.py` script with no arguments. This script performs validation of the data structures, builds output formats, and reports any issues. 
At present, a large number of warnings for incomplete content is normal. We can work to reduce these by adding more content.
All other checks should pass.

## After review

Your pull request will be reviewed and merged. You will be able to view your contribution in the [SOLVE-IT Explorer](https://explore.solveit-df.org/) once it synchronies with the main repository. Deep links to techniques, weaknesses and mitigations are available, e.g. [https://explore.solveit-df.org/#DFT-1002](https://explore.solveit-df.org/#DFT-1002) which can be shared.

## Writing style

For guidance on naming, descriptions, weakness categories, and reference formatting, see the [Style Guide](STYLE_GUIDE.md). In particular:

- [Weakness categories (ASTM codes)](STYLE_GUIDE.md#weakness-categories)
- [Reference formatting and relevance summaries](STYLE_GUIDE.md#style-guide-for-references)
- [Common mitigations](CONTRIBUTOR_GUIDE.md#common-mitigations)

## Further resources

- [Detailed Contributor Guide](CONTRIBUTOR_GUIDE.md) — step-by-step instructions for every submission type, the full automated pipeline, and worked examples from published research
- [Style Guide](STYLE_GUIDE.md) — naming conventions, descriptions, ASTM weakness categories, and reference formatting
- [SOLVE-IT Explorer](https://explore.solveit-df.org/) — browse, search, and submit directly from the knowledge base
- [MCP Server](https://github.com/CKE-Proto/solve_it_mcp) — query the knowledge base using natural language via an LLM
- [SOLVE-IT Custom Viewer](https://custom-viewer.solveit-df.org) — view the knowledge base with a custom organization of techniques
