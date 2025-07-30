# SOLVE-IT (a Systematic Objective-based Listing of Various Established digital Investigation Techniques)

## Introduction
The SOLVE-IT knowledge base (Systematic Objective-based Listing of Various Established digital Investigation Techniques) is conceptually inspired by [MITRE ATT&CK](https://attack.mitre.org/matrices/enterprise/) and aims to capture digital forensic techniques that can be used in investigations. It includes details about each technique, examples, potential ways the technique can go wrong (weaknesses), and mitigations to either avoid, detect, or minimize the consequences of a weakness if it does occur.

SOLVE-IT was introduced at [DFRWS EU 2025](https://dfrws.org/presentation/solve-it-a-proposed-digital-forensic-knowledge-base-inspired-by-mitre-attck/). The associated academic paper in [FSI:Digital Investigation](https://www.sciencedirect.com/science/article/pii/S2666281725000034) can be cited as:

```Hargreaves, C., van Beek, H., Casey, E., SOLVE-IT: A proposed digital forensic knowledge base inspired by MITRE ATT&CK, Forensic Science International: Digital Investigation, Volume 52, Supplement, 2025, 301864, ISSN 2666-2817, https://doi.org/10.1016/j.fsidi.2025.301864```

This is a community project so please see [CONTRIBUTING.md](CONTRIBUTING.md) for information on how to contrinute to the knowledge base.

## Related repositories

- educational material for SOLVE-IT can be found [here](https://github.com/SOLVE-IT-DF/solve-it-education) 
- example uses of SOLVE-IT can be found [here](https://github.com/SOLVE-IT-DF/solve-it-examples), 
- a repository that uses SOLVE-IT to consider applications of AI to digital forensics can be found [here](https://github.com/SOLVE-IT-DF/solve-it-applications-ai-review)


## Concepts and structure
The high-level concepts are:

**Objectives**: based on ATT&CK tactics, objectives are "the goal that one might wish to achieve in a digital forensic investigation", e.g. acquire data, or extract information from a file system.

**Techniques**: "how one might achieve an objective in digital forensics by performing an action", e.g. for the objective of 'acquire data', the technique 'create disk image' could be used.

**Potential Weaknesses**: these represent potential problems resulting from using a technique. They are classified according to the error categories in ASTM E3016-18, the Standard Guide for Establishing Confidence in Digital and Multimedia Evidence Forensic Results by Error Mitigation Analysis.

**Mitigations**: something that can be done to prevent a weakness from occurring, or to minimise its impact.


Each of these concepts are contained in subfolders within the [\data](https://github.com/SOLVE-IT-DF/solve-it/tree/main/data) subfolder. Each technqiue, weakness, and mitigation is represented as a json file that can be directly viewed.

## Viewing the knowledge base in a spreadsheet

Pre-generated xlsx files can be found in the [releases](https://github.com/SOLVE-IT-DF/solve-it/releases) section, published at regular intervals. The most up-to-date version can be found [here](https://github.com/SOLVE-IT-DF/solve-it/blob/main/.repo_info/solve-it-latest.xlsx), which is auto-generated on each commit.


If you want to generate your own from the raw data (useful if you are adding or editing content), a utility script is provided, `reporting_scripts/generate_excel_from_kb.py`. This python3 script will generate an Excel spreadsheet (solve-it.xlsx) based on the current version of the json data (using the solve-it.json categorisations). This uses the Python xlsxwriter package. 


A another utility script `reporting_scripts/generate_evaluation.py` can be used with a list of technique IDs provided as command line arguments. This provides a repackaged checklist of the supplied technqiues, with their weaknesses and potential mitigations. This can be used to review a case, an SOP, a tool workflow, and more. See example in [SOLVE-IT examples repository](https://github.com/SOLVE-IT-DF/solve-it-examples/tree/main/forensic_workflow_example_forensic_imaging).

## Organisation of the techniques
The file `solve-it.json` is the default categorisation of the techniques, but other examples are provided in `carrier.json` and `dfrws.json`.


## Contributing to the knowledge base

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for information.
