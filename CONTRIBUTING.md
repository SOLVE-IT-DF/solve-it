# Contributing to SOLVE-IT

## Introduction

There are multiple ways you can contribute to SOLVE-IT. This document presents a concise guide to the process. 

A more extensive document "SOLVE-IT for researchers" provides additional guidance and is suitable for anyone that wants to make a contribution. It is available [here](https://github.com/SOLVE-IT-DF/solve-it-education/tree/main/guide-for-researchers). 

A style guide (in progress) is also available [here](STYLE_GUIDE.md).


## Content that can be contributed
There are many areas in which content can be contributed:

* **Techniques** - how one might achieve an objective in digital forensics by performing an action, e.g. for the objective of 'acquire data', the technique 'create disk image' could be used.
* **Weaknesses** - these represent potential problems resulting from using a technique ([see Weakness Categories below](#Weakness-Categories))
* **Mitigations** - something that can be done to attempt to prevent a weakness from occurring, or to minimise its impact. 
* **Examples** - examples of cases where a technique is used, datasets that are relevant to the technique, tools that are able to perform the technique.  
* **References** - references to support the information within techniques, weaknesses and potential mitigations. When a reference is used, we also request a 280 character 'relevancy' string to help users of SOLVE-IT identify if/how a particular reference added is of relevance to their use case. 

Other contributions are also welcome to related projects:

- the [SOLVE-IT website](https://www.solveit-df.org) also invites [articles](https://www.solveit-df.org/articles/) from those making use or contributions to SOLVE-IT. 
- the [SOLVE-IT education repository](https://github.com/SOLVE-IT-DF/solve-it-education) invites additional content for educating others about SOLVE-IT.
- make use of [SOLVE-IT-X](https://github.com/SOLVE-IT-DF/solve-it-x) to build custom versions of SOLVE-IT augmented with your own content. 
- the [Review of AI applicability in digital forensics using SOLVE-IT](https://github.com/SOLVE-IT-DF/solve-it-applications-ai-review) repo, which invites bibtex entries that document the use of AI for assisting with digital forensic techniques.  



## Contribution workflow

The workflow for contributions is: 

* Decide what you need to add ([details](#deciding-what-you-need-to-add))
* Check if it already exists in SOLVE-IT ([details](#check-if-it-already-exists-in-solve-it))
* Raise an issue in GitHub ([details](#raise-an-issue-in-the-github-issue-tracker))
* Wait for review and get assigned IDs for your contribution ([details](#wait-for-review-and-get-assigned-ids))
* Fork the repository, edit or create the relevant JSON files in the /data folder ([details](#edit-and-contribute-code-updates))
* Run validation, commit your changes and submit a pull request ([details](#run-validation-script))
* After review, your new/updated content should be live in the knowledge base ([details](#wait-for-review-then-view-your-content))

## Deciding what you need to add

* Technique: you want to describe a *method* or process to achieve a forensic objective.
* Weakness: you have identified a *potential problem* with using a technique.
* Mitigation: you have identified or developed a *(partial) solution* to a known weakness.

## Check if it already exists in SOLVE-IT
Use the [SOLVE-IT Explorer](https://explore.solveit-df.org/) to search for related content and see if your content is already represented in the knowledge base. If so, you may want to submit updates instead of new content.

You can also make use of the third-party [MCP server for SOLVE-IT](https://github.com/CKE-Proto/solve_it_mcp) to interact with the knowledge base using natural language. 

Alternatively, TSV and other formats for techniques, weaknesses and mitigations are available
on the site that hosts [machine readable versions of the knowledge base](https://data.solveit-df.org), which can be uploaded to other services such as ChatGPT for a quick LLM based review of the content, but is not as effective as the MCP server approach.

## Raise an issue in the GitHub issue tracker
This is the primary way to propose updates to content in the SOLVE-IT knowledge base.

* Visit the SOLVE-IT [issue tracker](https://github.com/SOLVE-IT-DF/solve-it/issues).
* There are templates available for updating existing techniques, weaknesses and mitigations, and also proposing new ones.
* NEW: You can now submit an issue direcly from the [SOLVE-IT Explorer](https://explore.solveit-df.org/), either within a techqniue, weakness, or mitigation (see 'Propose an update to X' button shown below), or to submit new content view the other tabs which have a 'Propose a new X' button. These will link you directly to the correct form in the Issue Tracker.

<img width="600" height="180" alt="Shows updating this content on GitHub button" src="https://github.com/user-attachments/assets/aa4b7dd0-f725-4329-b013-065e138d0277" />

<img width="1512" height="229" alt="Shows the new techqniue button in the 'Techniques' tab" src="https://github.com/user-attachments/assets/e61b86c2-cf1c-4758-a8b5-5fa7d0cdb53f" />


## Wait for review and get assigned IDs
Once your issue has been raised it will be reviewed. To speed up review make sure to have reviewed the contribution guide in full and the (in progress) [style guide](STYLE_GUIDE.md).


## Edit and contribute code updates

* All contributions to the project must be submitted via pull request and linked to an issue.
* Follow the [GitHub Flow](https://docs.github.com/en/get-started/using-github/github-flow) workflow (with [SOLVE-IT validation](#run-validation-script) after step 2):
    1. Create a new branch from `main`.     
    2. Make your changes and commit them with descriptive commit messages.
    3. Submit a pull request to the main repository's `main` branch.
* Provide a clear and detailed description of your changes in the pull request description.
* If you want to share code in progress via pull request, use GitHub's Draft pull request feature.

## Run validation script
Prior to submitting the pull request, or even committing, you should make use of the `/admin/validate_kb.py` script. This can be run with no arguments and will perform multiple tests, build all the different output formats of the knowledge base and give you a report. 

At present, a large number of warnings for incomplete content is normal. This will reduce over time as more content is added to SOLVE-IT.

```
══ Phase 1: Data loading ═════════════════════════════════════
  [OK]    All checks passed.

══ Phase 1b: Deprecated ID format check ══════════════════════
  [OK]    All checks passed.

══ Phase 2: Cross-reference integrity ════════════════════════
  [OK]    All checks passed.

══ Phase 3: ASTM error class flags ═══════════════════════════
  [OK]    All checks passed.

══ Phase 4: CASE/UCO class URLs ══════════════════════════════
  [OK]    All checks passed.

══ Phase 5: Completeness warnings ════════════════════════════
  [WARN]  Technique DFT-1008 has empty/missing description
  [WARN]  Technique DFT-1009 has empty/missing description
  ...
  [PASS]  Completeness stats: 172 techniques, 118 with description, 73 with weaknesses, 129 with CASE classes, 142 citations

══ Phase 6: Generator smoke tests ════════════════════════════
  [OK]    All checks passed.

══ Summary ═══════════════════════════════════════════════════
  Passed: 33   Failed: 0   Warnings: 410

  All checks passed.
```

## Wait for review then view your content
Your pull request will get checked by a SOLVE-IT reviewer and then integrated. You will be able to review your contribution with the [SOLVE-IT Explorer](https://explore.solveit-df.org/). Note that deep links are possible to your content once integrated if you want to share your content further, e.g. https://explore.solveit-df.org/#DFT-1002.  


## Additional notes on references
* Techniques, weaknesses, and mitigations can, and should, contain references to support the information within. 
* The references should be in the appropriate file, e.g. if a reference is supporting defining a technique then it ought to be in the json file for the techniques (DFT-xxxx), if it is highlighting a weakness then it should be in a weakness (DFW-xxxx) json file, and if it is describing a potential mitigation then it should be in the mitigation (DFM-xxxx) json file. 
* For large references, consider supplying the page or chapter number if appropriate. 
* References should not be added just because they are about a topic, but should have meaningful implications in terms of explaining a technique, highlighting a weakness, or providing a mitigation.
* To support this philosophy we will soon be replacing plain text references with a DFCite data structure that requires not just the reference but also a maximum 280 character 'relevancy string' to describe to SOLVE-IT users why a reference is relevant. 


## Weakness Categories
In SOLVE-IT we use _ASTM E3016-18 Standard Guide for Establishing Confidence in Digital and Multimedia Evidence Forensic Results by Error Mitigation Analysis_ **as a guide** for categorising weaknesses.

Weakness classifications are stored in the `categories` list field in each weakness JSON file:

```json
{
  "id": "DFW-1001",
  "name": "Excluding a device that contains relevant information",
  "categories": ["ASTM_INCOMP"],
  "mitigations": [],
  "references": []
}
```

The valid ASTM class codes (all prefixed with `ASTM_`) are:

* `ASTM_INCOMP` — Incompleteness: e.g. failure to recover live artefacts, failure to recover deleted artefacts, other reasons why an artefact might be missed?
* `ASTM_INAC_EX` — Inaccuracy (Existence): e.g. presenting an artefact for something that does not exist
* `ASTM_INAC_ALT` — Inaccuracy (Alteration): e.g. modifying the content of some digital data
* `ASTM_INAC_AS` — Inaccuracy (Association): e.g. presenting live data as deleted and vice versa
* `ASTM_INAC_COR` — Inaccuracy (Corruption): e.g. could the process corrupt data, could the process fail to detect corrupt data?
* `ASTM_MISINT` — Misinterpretation: e.g. could results be presented in a way that encourages misinterpretation?

When proposing or updating a weakness via the GitHub issue forms, enter one class code per line in the "Categories" textarea field.

The full definitions from ASTM are here for reference[^1], but the more concise and very slightly modified[^2] "weakness prompts" taken from the TRWM Helper Worksheets represent the SOLVE-IT categorisations more closely.



[^1]: These ASTM E3016-18 definitions are included here for reference (see [here](https://www.nist.gov/standard/1516) for link to full document. ), but modified versions are used in SOLVE-IT as described above.
    * Incompleteness: All the relevant information has not been acquired or found by the tool. For example, an acquisition might be incomplete or not all relevant artifacts identified from a search.
    * Inaccuracy (Existence): Are all reported artifacts reported as present actually present? For example, a faulty tool might add data that was not present in the original.
    * Inaccuracy (Alteration): Does a forensic tool alter data in a way that changes its meaning, such as updating an existing date-time stamp (for example, associated with a file or e-mail message) to the current date.
    * Inaccuracy (Association): Do all items associated together actually belong together? A faulty tool might incorrectly associate information pertaining to one item with a different, unrelated item. For instance, a tool might parse a web browser history file and incorrectly report that a web search on "how to murder your wife" was executed 75 times when in fact it was only executed once while "history of Rome" (the next item in the history file) was executed 75 times, erroneously associating the count for the second search with the first search.
    * Inaccuracy (Corruption): Does the forensic tool detect and compensate for missing and corrupted data? Missing or corrupt data can arise from many sources, such as bad sectors encountered during acquisition or incomplete deleted file recovery or file carving. For example, a missing piece of data from an incomplete carving of the above web history file could also produce the same incorrect association.
    * Misinterpretation: The results have been incorrectly understood. Misunderstandings of what certain information means can result from a lack of understanding of the underlying data or from ambiguities in the way digital and multimedia evidence forensic tools present information.

[^2]: The slight modifications include: 
    INAC-ALT removes the text "in a way that changes its meaning" as this can cause confusion with tools not converting data correctly during interpretation. 
    INAC-AS needs to be carefully used as the ASTM example is INAC-AS for the 'number of web visits' but is also INAC-EX presenting that visits occurred that didn't. 
    MISINT focuses on results being presented in a way that encourages or does not prevent misinterpretation, rather than "results have been incorrectly understood" as this does not map to the weaknesses in SOLVE-IT well. 


## Common mitigations
* There are some potential mitigations that are quite generic and often applicable:
  * DFM-1027 Dual tool verification
  * DFM-1050 Manual verification of relevant data

* These also are often relevant:
  * DFM-1055 Correlation of data extracted with data from service provider
 
Note: Manual verification of relevant data will not always be appropriate e.g. it is very difficult to manually verify that parsing of all live files on a disk image was done correctly.
Note: Potential mitigations for testing are usually more specific for the exact data extraction that needs to be tested.
