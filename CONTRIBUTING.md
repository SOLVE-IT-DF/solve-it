# Contributing to SOLVE-IT

THIS DOCUMENT IS UNDER DEVELOPMENT 

## Introduction

There are multiple ways you can contribute to SOLVE-IT. 

## Content that can be contributed
There are many areas in which content can be contributed:

* **Techniques** - how one might achieve an objective in digital forensics by performing an action, e.g. for the objective of 'acquire data', the technique 'create disk image' could be used.
* **Weaknesses** - these represent potential problems resulting from using a technique.
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
* Select one of the templates. We offer 'FULL' or 'LITE' templates for content contributions:
  * FULL asks for all the details needed to populate the content in a structured for.
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

### Specifics

* The content on the knowledge base is in `/data`.
* To update a technique, locate the corresponding json file in the `/data/techniques` folder. Update that json with the relevant information.
* New techniques need to be added to `solve-it.json` under the correct objective.
* New techniques can be added by creating a new json file in the same structure. Technique `T1000.json` provides a template.
* You can reference weaknesses and mitigations, either existing ones in the `/data/weaknesses` or `/data/mitigations` folders, or create new.

### Notes on references
* Techniques, weaknesses, and mitigations can, and should, contain references to support the information within. 
* The references should be in the appropriate file, e.g. if a reference is supporting defining a technique then it ought to be in the json file for the techniques (Txxxx), if it is highlighting a weakness then it should be in an weakness (Wxxxx) json file, and if it is describing a mitigation then it should be in the mitigation (Mxxxx) json file. 
* References should not be added just because they are about a topic, but should have meaningful implications in terms of explaining a technique, highlighting a weakness, or providing a mitigation.
* For large references, consider supplying the page or chapter number if appropriate. 
