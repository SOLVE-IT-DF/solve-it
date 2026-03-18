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

**Objectives**: based on ATT&CK tactics, objectives are "the goal that one might wish to achieve in a digital forensic investigation", e.g. acquire data, or extract information from a file system.

**Techniques**: "how one might achieve an objective in digital forensics by performing an action", e.g. for the objective of 'acquire data', the technique 'create disk image' could be used.

**Weaknesses**: these represent *potential* problems resulting from using a technique. They are classified according to the error categories in ASTM E3016-18, the Standard Guide for Establishing Confidence in Digital and Multimedia Evidence Forensic Results by Error Mitigation Analysis.

**Mitigations**: something that can be done to *attempt* to prevent a weakness from occurring, or to *attempt* to minimise its impact.


Each of these concepts are contained in subfolders within the [\data](https://github.com/SOLVE-IT-DF/solve-it/tree/main/data) subfolder. Each technique, weakness, and mitigation is represented as a JSON file that can be directly viewed.



## Viewing the knowledge base 

The easiest way to view the knowledge base is with the [SOLVE-IT Explorer](https://explore.solveit-df.org).

### Viewing as JSON

The raw repository JSON files can be viewed in the `data` folder [here](https://github.com/SOLVE-IT-DF/solve-it/tree/main/data), under the subfolders `techniques`, `weaknesses`, `mitigations` and `references`.


## Organisation of the techniques
The file `solve-it.json` is the default categorisation of the techniques, but other categorizations are possible with custom JSON files. The examples repository discusses how this can be done and provides examples for `carrier.json` and `dfrws.json`. See [here](https://github.com/SOLVE-IT-DF/solve-it-examples/tree/main/reorganization_of_techniques) for more information. These can be uploaded to the [SOLVE-IT Custom Viewer](https://custom-viewer.solveit-df.org) (use the 'Use custom categories' button to upload your own organsiational schema).


## Related repositories

- educational material for SOLVE-IT can be found [here](https://github.com/SOLVE-IT-DF/solve-it-education)
   - includes presentations, class exercises, one-page primer, contributing guide for digital forensics researchers.
- example uses of SOLVE-IT can be found [here](https://github.com/SOLVE-IT-DF/solve-it-examples), 
- a repository that uses SOLVE-IT to consider applications of AI to digital forensics can be found [here](https://github.com/SOLVE-IT-DF/solve-it-applications-ai-review)
- an MCP server providing LLM access to SOLVE-IT [here](https://github.com/CKE-Proto/solve_it_mcp) 


## Contributing to the knowledge base

```Hargreaves, C., van Beek, H., Casey, E., SOLVE-IT: A proposed digital forensic knowledge base inspired by MITRE ATT&CK, Forensic Science International: Digital Investigation, Volume 52, Supplement, 2025, 301864, ISSN 2666-2817, https://doi.org/10.1016/j.fsidi.2025.301864```
