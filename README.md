# SOLVE-IT (a Systematic Objective-based Listing of Various Established digital Investigation Techniques)

## Quick Links
- [Browse the knowledge base in markdown](https://github.com/SOLVE-IT-DF/solve-it/blob/main/.repo_info/solve-it.md)
- [Download the knowledge base as Excel spreadsheet](https://github.com/SOLVE-IT-DF/solve-it/raw/refs/heads/main/.repo_info/solve-it-latest.xlsx)
- [Propose an addition to the knoweldge base](https://github.com/SOLVE-IT-DF/solve-it/issues/new/choose) - see [CONTRIBUTING.md](CONTRIBUTING.md) for guidance
- [View educational resources](https://github.com/SOLVE-IT-DF/solve-it-education)

## Introduction
The SOLVE-IT knowledge base (Systematic Objective-based Listing of Various Established digital Investigation Techniques) is conceptually inspired by [MITRE ATT&CK](https://attack.mitre.org/matrices/enterprise/) and aims to capture digital forensic techniques that can be used in investigations. It includes details about each technique, examples, potential ways the technique can go wrong (weaknesses), and potential mitigations to either avoid, detect, or minimize the consequences of a weakness if it does occur.

SOLVE-IT was introduced at [DFRWS EU 2025](https://dfrws.org/presentation/solve-it-a-proposed-digital-forensic-knowledge-base-inspired-by-mitre-attck/). The associated academic paper in [FSI:Digital Investigation](https://www.sciencedirect.com/science/article/pii/S2666281725000034) can be cited as:

```Hargreaves, C., van Beek, H., Casey, E., SOLVE-IT: A proposed digital forensic knowledge base inspired by MITRE ATT&CK, Forensic Science International: Digital Investigation, Volume 52, Supplement, 2025, 301864, ISSN 2666-2817, https://doi.org/10.1016/j.fsidi.2025.301864```

This is a community project so please see [CONTRIBUTING.md](CONTRIBUTING.md) for information on how to contribute to the knowledge base.

<img width="1772" height="1080" alt="A high-level view of the SOLVE-IT knowledge base showing the technqiues in table form, organised by objective along the top." src="https://github.com/user-attachments/assets/582678e7-53fd-40de-9f64-b7329a1f3c9e" />


<img width="2554" height="1384" alt="A view of one of the techniques (T1002: Disk Imaging), illustrating the fields recorded for each technique including weaknesses and potential mitigations." src="https://github.com/user-attachments/assets/fbf0f312-9c5d-41c5-81bc-442162854643" />


## Concepts and structure
The high-level concepts are:

**Objectives**: based on ATT&CK tactics, objectives are "the goal that one might wish to achieve in a digital forensic investigation", e.g. acquire data, or extract information from a file system.

**Techniques**: "how one might achieve an objective in digital forensics by performing an action", e.g. for the objective of 'acquire data', the technique 'create disk image' could be used.

**Weaknesses**: these represent *potential* problems resulting from using a technique. They are classified according to the error categories in ASTM E3016-18, the Standard Guide for Establishing Confidence in Digital and Multimedia Evidence Forensic Results by Error Mitigation Analysis.

**Mitigations**: something that can be done to *attempt* to prevent a weakness from occurring, or to *attempt* to minimise its impact.


Each of these concepts are contained in subfolders within the [\data](https://github.com/SOLVE-IT-DF/solve-it/tree/main/data) subfolder. Each technique, weakness, and mitigation is represented as a JSON file that can be directly viewed.



## Viewing the knowledge base 

### Viewing as Markdown

A markdown version of the knowledge base is generated with every commit. You can therefore find the most up-to-date version in the `.repo_info` folder [here](https://github.com/SOLVE-IT-DF/solve-it/blob/main/.repo_info/solve-it.md). 

This markdown version is produced automatically using `reporting_scripts/generate_md_from_kb.py` (requires python >=3.12), and this can be run manually if required. 

### Viewing in Excel

Pre-generated xlsx files can be found in the [releases](https://github.com/SOLVE-IT-DF/solve-it/releases) section, published at regular intervals. 

Alternatively the repository is configured to compile a new version of the Excel spreadsheet with every commit. You can therefore find the most up-to-date version in the `.repo_info` folder [here](https://github.com/SOLVE-IT-DF/solve-it/blob/main/.repo_info/solve-it-latest.xlsx).

If you want to generate your own from the raw data (which is useful if you are adding or editing content), a utility script is provided, `reporting_scripts/generate_excel_from_kb.py`. This python3 script (requires python >=3.12) will generate an Excel spreadsheet (solve-it.xlsx) based on the current version of the JSON data (using the solve-it.json categorisations). This uses the Python xlsxwriter package. 

Another utility script `reporting_scripts/generate_evaluation.py` can be used with a list of technique IDs provided as command line arguments. This provides a repackaged checklist of the supplied techniques, with their weaknesses and potential mitigations. This can be used to review a case, an SOP, a tool workflow, and more. See example in [SOLVE-IT examples repository](https://github.com/SOLVE-IT-DF/solve-it-examples/tree/main/forensic_workflow_example_forensic_imaging).

### Viewing as JSON

The raw repository JSON files can be viewed in the `data` folder [here](https://github.com/SOLVE-IT-DF/solve-it/tree/main/data), under the subfolders `techniques`, `weaknesses` and `mitigations`.

### Notes on color coding

In the Excel and Markdown versions, colors are used to indicate the 'status' of techniques. 
- Red indicates a _placeholder_ (zero weaknesses added)
- Yellow indicates _some content_ (1 or more weaknesses, but missing a technique description, or has 0 mitigations)
- Green indicates _release candidate_ (this cannot be classed as complete, but has 1 or more weaknesses, 1 or more miitgations, and has a description in place)

Note, this is controlled via the `global_solveit_config.py` script in the `extension_data` folder, and this behaviour may be modified by other extensions. 

## Organisation of the techniques
The file `solve-it.json` is the default categorisation of the techniques, but other categorizations are possible with custom JSON files. The examples repository discusses how this can be done and provides examples for `carrier.json` and `dfrws.json`. See [here](https://github.com/SOLVE-IT-DF/solve-it-examples/tree/main/reorganization_of_techniques) for more information. 



## Related repositories

- educational material for SOLVE-IT can be found [here](https://github.com/SOLVE-IT-DF/solve-it-education)
   - includes presentations, class exercises, one-page primer, contributing guide for digital forensics researchers.
- example uses of SOLVE-IT can be found [here](https://github.com/SOLVE-IT-DF/solve-it-examples), 
- a repository that uses SOLVE-IT to consider applications of AI to digital forensics can be found [here](https://github.com/SOLVE-IT-DF/solve-it-applications-ai-review)
- an MCP server providing LLM access to SOLVE-IT [here](https://github.com/CKE-Proto/solve_it_mcp) 


## Contributing to the knowledge base

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for information, which includes an in progress [style guide](https://github.com/SOLVE-IT-DF/solve-it/blob/main/STYLE_GUIDE.md).
