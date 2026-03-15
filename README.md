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



## Referencing
SOLVE-IT was introduced at [DFRWS EU 2025](https://dfrws.org/presentation/solve-it-a-proposed-digital-forensic-knowledge-base-inspired-by-mitre-attck/). The associated academic paper in [FSI:Digital Investigation](https://www.sciencedirect.com/science/article/pii/S2666281725000034) can be cited as:

```Hargreaves, C., van Beek, H., Casey, E., SOLVE-IT: A proposed digital forensic knowledge base inspired by MITRE ATT&CK, Forensic Science International: Digital Investigation, Volume 52, Supplement, 2025, 301864, ISSN 2666-2817, https://doi.org/10.1016/j.fsidi.2025.301864```
