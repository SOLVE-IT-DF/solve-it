# Contributing to SOLVE-IT

THIS DOCUMENT IS UNDER DEVELOPMENT 

## Introduction

There are multiple ways you can contribute to SOLVE-IT. 

## Content that can be contributed
There are many areas in which content can be contributed:

* **Techniques** - how one might achieve an objective in digital forensics by performing an action, e.g. for the objective of 'acquire data', the technique 'create disk image' could be used.
* **Weaknesses** - these represent potential problems resulting from using a technique ([see Weakness Categories below](#Weakness-Categories))
* **Mitigations** - something that can be done to prevent a weakness from occurring, or to minimise its impact. 
* **Examples** - examples of cases where a technique is used, datasets that are relevant to the technique, 
                   tools that are able to perform the technique.  
* **References** - references to support the information within techniques, weaknesses and mitigations. We are working on a [bibtex implementation for references](https://github.com/SOLVE-IT-DF/solve-it/issues/38).

Please also see the [Review of AI applicability in digital forensics using SOLVE-IT](https://github.com/SOLVE-IT-DF/solve-it-applications-ai-review) repo, which invites bibtex entries that
document the use of AI for assisting with digital forensic techniques.  


## Methods to contribute 

We have two main ways that information can be contributed to the knowledge base:

* [Contributing using the issue tracker](#Contributing-using-the-issue-tracker).
* [Contributing directly via the code repo](#Contributing-directly-via-the-code-repo).

All content contributions should start in the issue tracker, since discussion is easier there about concepts than in code review.  



## Contributing using the issue tracker
This is the easiest way to propose updates to content in the SOLVE-IT knowledge base.

* Visit the SOLVE-IT [issue tracker](https://github.com/SOLVE-IT-DF/solve-it/issues).
* Select one of the templates. We offer 'STANDARD' or 'LITE' templates for content contributions:
  * STANDARD asks for all the details needed to populate the content in a structured for.
  * LITE requests the miminal information needed, with a free text 'notes' section for additional information.
* Submit the suggestion as a github issue for review.


## Contributing directly via the code repo

* All contributions to the project must be submitted via pull request. 
* Ensure that your pull request addresses a specific issue or feature request. If none exists, please open a new issue first to discuss the updates.
* Follow the [GitHub Flow](https://guides.github.com/introduction/flow/) workflow:
  1. Create a new branch from `main`. 
  2. Make your changes and commit them with descriptive commit messages.
  3. Submit a pull request to the main repository's `main` branch.
* Provide a clear and detailed description of your changes in the pull request description.
* If you want to share code in progress via pull request, use a prefix "[WORK IN PROGRESS]" in the pull request title. 

### Specifics

* The content on the knowledge base is in `/data`.
* To update a technique, locate the corresponding json file in the `/data/techniques` folder. Update that json with the relevant information.
* New techniques need to be added to `solve-it.json` under the correct objective.
* New techniques can be added by creating a new json file in the same structure. Technique `T1000.json` provides a template.
* You can reference weaknesses and mitigations, either existing ones in the `/data/weaknesses` or `/data/mitigations` folders, or create new.

## Notes on references
* Techniques, weaknesses, and mitigations can, and should, contain references to support the information within. 
* The references should be in the appropriate file, e.g. if a reference is supporting defining a technique then it ought to be in the json file for the techniques (Txxxx), if it is highlighting a weakness then it should be in an weakness (Wxxxx) json file, and if it is describing a mitigation then it should be in the mitigation (Mxxxx) json file. 
* References should not be added just because they are about a topic, but should have meaningful implications in terms of explaining a technique, highlighting a weakness, or providing a mitigation.
* For large references, consider supplying the page or chapter number if appropriate. 



## Weakness Categories
In SOLVE-IT we use _ASTM E3016-18 Standard Guide for Establishing Confidence in Digital and Multimedia Evidence Forensic Results by Error Mitigation Analysis_ **as a guide** for categorising weaknesses. 

The full defintions from ASTM are here for reference[^1], but the more concise and very slightly modified[^2] "weakness prompts" taken from the TRWM Helper Worksheets represent the SOLVE-IT categorisations more closely. 

* Incompleteness: INCOMP: e.g. failure to recover live artefacts, failure to recover deleted artefacts, other reasons why an artefact might be missed?
* Inaccuracy (Existence): INAC-EX: e.g. presenting an artefact for something that does not exist
* Inaccuracy (Alteration): INAC-ALT: e.g. modifying the content of some digital data
* Inaccuracy (Association): INAC-AS: e.g. presenting live data as deleted and vice versa
* Inaccuracy (Corruption): INAC-COR: e.g. could the process corrupt data, could the process fail to detect corrupt data?
* Misinterpreation: MISINT: e.g. could results be presented in a way that encourages misinterpretation?



[^1]: These ASTM E3016-18 defintions are included here for reference (see [here](https://www.nist.gov/standard/1516) for link to full document. ), but modified versions are used in SOLVE-IT as described above.
    * Incompleteness: All the relevant information has not been acquired or found by the tool. For example, an acquisition might be incomplete or not all relevant artifacts identified from a search.
    * Inaccuracy (Existence): Are all reported artifacts reported as present actually present? For example, a faulty tool might add data that was not present in the original.
    * Inaccuracy (Alteration): Does a forensic tool alter data in a way that changes its meaning, such as updating an existing date-time stamp (for example, associated with a file or e-mail message) to the current date.
    * Inaccuracy (Association): Do all items associated together actually belong together? A faulty tool might incorrectly associate information pertaining to one item with a different, unrelated item. For instance, a tool might parse a web browser history file and incorrectly report that a web search on "how to murder your wife" was executed 75 times when in fact it was only executed once while "history of Rome" (the next item in the history file) was executed 75 times, erroneously associating the count for the second search with the first search.
    * Inaccuracy (Corruption): Does the forensic tool detect and compensate for missing and corrupted data? Missing or corrupt data can arise from many sources, such as bad sectors encountered during acquisition or incomplete deleted file recovery or file carving. For example, a missing piece of data from an incomplete carving of the above web history file could also produce the same incorrect association.
    * Misinterpreation: The results have been incorrectly understood. Misunderstandings of what certain information means can result from a lack of understanding of the underlying data or from ambiguities in the way digital and multimedia evidence forensic tools present information.

[^2]: The slight modifications include: 
    INAC-ALT removes the text "in a way that changes its meaning" as this can cause confusion with tools not converting data correctly during interpretation. 
    INAC-AS needs to be carefully used as the ASTM example is INAC-AS for the 'numer of web visits' but is also INAC-EX presenting that visits occurred that didn't. 
    MISINT focuses on results being presented in a way that that encourages or does not prevent misinterpretation, rather than "results have been incorrectly understood" as this does not map to the weaknesses in SOLVE-IT well. 


## Common mitigations
* There are some mitigations that are quite generic and often applicable:
  * M1027 Dual tool verification
  * M1050 Manual verification of relevant data

* These also are often relevant:
  * M1055 Correlation of data extracted with data from service provider
 
Note: Manual verificaiton of relevant data will not always be appropriate e.g. it is very difficult to manually verify that parsing of all live files on a disk image was done correctly.
Note: Mitigations for testing are usually more specific for the exact data extraction that needs to be tested.
