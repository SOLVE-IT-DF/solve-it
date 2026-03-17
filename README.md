# SOLVE-IT - the digital forensics knowledge base

## Quick Links

- SOLVE-IT website - https://solveit-df.org
- Browse the knowledge base - [SOLVE-IT Explorer](https://explore.solveit-df.org)
- Machine-readable version - [SOLVE-IT Data](https://data.solveit-df.org)
- Raw JSON Content - [`/data` folder](https://github.com/chrishargreaves/solve-it/tree/main/data)


## Introduction
The SOLVE-IT knowledge base (Systematic Objective-based Listing of Various Established digital Investigation Techniques) is conceptually inspired by [MITRE ATT&CK](https://attack.mitre.org/matrices/enterprise/) and aims to capture digital forensic techniques that can be used in investigations. It includes details about each technique, examples, potential ways the technique can go wrong (weaknesses), and potential mitigations to either avoid, detect, or minimize the consequences of a weakness if it does occur.


## Contributing
This is a community project so please see [CONTRIBUTING.md](CONTRIBUTING.md) for information on how to contribute to the knowledge base.

## Repository Structure

`data/`
  Techniques, weaknesses and mitigations stored as JSON
  
`solve_it_library/`
  Python utilities for interacting with the knowledge base
  
`reporting_scripts/`
  Scripts to generate markdown and reports
  
`extension_data/`
  Additional optional datasets


## Knowledge base data model
The high-level concepts are:

* **Objectives**: based on ATT&CK tactics, objectives are “the goal that one might wish to achieve in a digital forensic investigation”, e.g. acquire data, or extract information from a file system.

* **Techniques**: “how one might achieve an objective in digital forensics by performing an action”, e.g. for the objective of ‘acquire data’, the technique ‘create disk image’ could be used.

* **Weaknesses**: these represent potential problems resulting from using a technique. They are classified according to the error categories in ASTM E3016-18, the Standard Guide for Establishing Confidence in Digital and Multimedia Evidence Forensic Results by Error Mitigation Analysis.

* **Mitigations**: something that can be done to attempt to prevent a weakness from occurring, or to attempt to minimize its impact.

Each of these concepts are contained in subfolders within the `data` subfolder of the GitHub repository. Each technique, weakness, and mitigation is represented as a JSON file that can be directly viewed.

### Organization of technqiues
The file `solve-it.json` is the default categorization of the techniques, but other categorizations are possible with custom JSON files. These can be directly appled using the [SOLVE-IT Cutom Viewer tool](https://custom-viewer.solveit-df.org).


## Referencing
SOLVE-IT was introduced at [DFRWS EU 2025](https://dfrws.org/presentation/solve-it-a-proposed-digital-forensic-knowledge-base-inspired-by-mitre-attck/). The associated academic paper in [FSI:Digital Investigation](https://www.sciencedirect.com/science/article/pii/S2666281725000034) can be cited as:

```Hargreaves, C., van Beek, H., Casey, E., SOLVE-IT: A proposed digital forensic knowledge base inspired by MITRE ATT&CK, Forensic Science International: Digital Investigation, Volume 52, Supplement, 2025, 301864, ISSN 2666-2817, https://doi.org/10.1016/j.fsidi.2025.301864```
