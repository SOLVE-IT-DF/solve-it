# SOLVE-IT Style Guide


## General
* **Spelling**: US English is used throughout.


## Style Guide for Objectives

* **Top-level organisation**: Objectives are the top-level grouping of techniques within SOLVE-IT.

### **Objective names**

* Use **sentence case** — capitalize only the first word and proper nouns.
  	Example: Find potential digital evidence sources
* Begin with a **present-tense imperative verb** (e.g., "Locate", "Acquire", "Preserve").

### **Descriptions**

* Full sentences ending with a full stop.
* Prefer **one sentence**, maximum **two sentences** (≤ 25 words).
* Use **active voice** and keep grammatical structure consistent across all objectives.
  * e.g. "Collect data from identified evidence sources."  rather than "Data is collected from the identified evidence sources".
  * "Attempt to…" is permitted where there is uncertainty of success.
* Use the Oxford comma for lists

### **Objective name and description "Investigator test"**

* All objectives must pass the "investigator test":
   "As an investigator, I want to \[objective name\]…" must make sense when read aloud.


##  Style Guide for Techniques

### **Technique names**

* Use **sentence case** — capitalize only the first word and proper nouns.
  	Example: Find potential digital evidence sources
* Begin with a **present-tense imperative verb** (e.g., Locate, Connect, Use, "Connect storage medium via hardware write blocker").

### **Technique name and description "Investigator test"**

* All techniques must pass the "investigator test":
   "As an investigator, I want to \[technique name\]…" must make sense when read aloud.

### **Descriptions**

* A brief definition of the technique — 1–2 sentences, typically 15–30 words.
* Focuses on *what* the technique is. Often uses "The process of…" construction.
* Should be self-contained — a reader should understand the technique from the description alone.

### **Details**

* Extended implementation context — 2–4 sentences, typically 40–100+ words.
* Covers practical considerations: equipment/tool variations, relationships to other techniques (by ID), expected outputs, and edge cases.
* Uses a mix of active and instructional voice.

### **Examples**

* Examples (tools, datasets, cases) are a field *within* the technique, not a standalone content type. They illustrate how a technique is applied in practice.


##  Style Guide for Weaknesses

### **Weakness names**

* Use **sentence case** — capitalize only the first word and proper nouns.
* Names should **not** end with a full stop.
* Where possible, name both the problem and its cause.
* There are more naming patterns for weaknesses (all shown with problem and cause where applicable):
    * **Gerund/participle phrases (-ing)**: "Missing the existence of a device by missing synchronisation artefacts"
    * **Noun phrases with explanation**: "Data copied does not include all sectors from LBA0 to LBA max due to the data copying process stopping prematurely"
    * **"Failure to…" phrases**: "Tool fails to display special effects or highlight within a message"
    * **Statements of condition**: "The timestamp used is an inaccurate representation of the actual time" (here the cause is inherent to the data itself — naming a cause is not always applicable)
* A well-named weakness should suggest at least one mitigation directly. For example, "Tool fails to display special effects" immediately suggests testing whether the tool handles them correctly. If you can't think of a mitigation from the weakness name alone, consider whether the cause is specific enough.
* Weakness names should describe what can go wrong, not what to do about it — action-oriented names like "Check the hash" or "Verify the timestamps" are mitigations, not weaknesses.

> **Investigator test:** One of these should make sense read aloud:
    - "As an investigator, I am concerned that \[weakness name\] could occur".
    - "As an investigator, I am concerned that \[weakness name\]".


### **Descriptions**

* 1–2 sentences, active voice preferred.
* Explain what can go wrong and why it matters.
* Avoid naming specific tools.

### Weakness categories

In SOLVE-IT we use _ASTM E3016-18 Standard Guide for Establishing Confidence in Digital and Multimedia Evidence Forensic Results by Error Mitigation Analysis_ **as a guide** for categorizing weaknesses.

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

The full definitions from ASTM are here for reference[^1], but the more concise and very slightly modified[^2] "weakness prompts" taken from the TRWM Helper Worksheets represent the SOLVE-IT categorizations more closely.

[^1]: These ASTM E3016-18 definitions are included here for reference (see [here](https://www.nist.gov/standard/1516) for link to full document), but modified versions are used in SOLVE-IT as described above.
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


##  Style Guide for Mitigations

### **Mitigation names**

* Use **sentence case** — capitalize only the first word and proper nouns.
* Names should **not** end with a full stop.
* Mitigation names should be action-oriented so they pass the investigator test below. Use imperative verb phrases: "Use dual tool verification", "Manually verify relevant data", "Use digital stratigraphy to attempt to attribute data within a specific file system".
* Aim for enough detail to be self-explanatory without reading the linked weakness.

> **Investigator test:** "As an investigator, I can \[mitigation name\] to reduce this risk" should make sense read aloud.

### **Descriptions**

* 1–2 sentences.
* Explain what the mitigation does and how it addresses the weakness.
* Be specific enough that an investigator could act on it.


##  Style Guide for References

### **The DFCite system**

References use unique identifiers (`DFCite-XXXX`) stored as separate files in `/data/references/` (`.txt` for plaintext, `.bib` for BibTeX). Techniques, weaknesses, and mitigations reference them via JSON objects:

```json
{
    "DFCite_id": "DFCite-1018",
    "relevance_summary_280": "Provides the definition used in the description of this technique."
}
```

### **Citation format**

* **BibTeX is the preferred format** — provide a `.bib` entry where possible.
* For the plaintext citation (`.txt` file), use **Harvard referencing style**. Include author(s), year, title, publisher/journal, and URL or DOI where available.
  * Academic papers: "Author, A., Author, B., Year. Title. *Journal*, Volume, pages. DOI/URL"
  * Online resources: "Organization/Author (Year), Title, URL"

### **Relevance summaries**

The `relevance_summary_280` field is a max 280-character explanation of *why* the reference matters to the specific item it is cited in, not just *what* the reference is about. References without summaries appear faded in the Explorer, signaling a contribution opportunity.

* Good: "Provides the definition used in the description of this technique"
* Good: "Demonstrates that Tool X misreports timestamps under condition Y"
* Good: "Chapter 4 describes the validation methodology used in this mitigation"
* Avoid: "A paper about Tool X"
* Use active voice; focus on the reference's specific contribution to the item.
* For large references (books, long papers), include the relevant page, chapter, or section number in the summary to help readers find the relevant content.

### **Inline citations**

You can cite references directly within description, details, and examples text using `[DFCite-xxxx]` syntax (e.g. `[DFCite-1018]`). These are rendered as clickable citation links in the Explorer. Use inline citations when a specific claim or statement in the text is supported by a reference — this is in addition to listing the reference in the item's `references` array with a relevance summary.

### **Placement**

References supporting a technique definition go in the technique file; references highlighting a weakness go in the weakness file; references describing a mitigation go in the mitigation file.

### **Selectivity**

References must have meaningful implications — do not add a reference simply because it mentions the topic. Consider: does this reference explain a technique, highlight a weakness, or provide a mitigation?

### **Primary sources**

Cite the original source where possible rather than a survey or review paper that references it. SOLVE-IT is intended to be of practical use to digital forensics practitioners, so references should point directly to the most useful source. This also ensures the original authors receive proper credit and citation visibility. Only cite a survey or secondary source if it genuinely adds additional insight beyond the original — for example, a novel comparison, synthesis, or reinterpretation of earlier work.

### **Large references**

Supply page or chapter number if appropriate.

### **Deduplication**

Check if a reference already exists before proposing a new one — the automated preview step flags potential duplicates. Technique, weakness, and mitigation forms only accept DFCite IDs (not free-text citations), so references must be created first using the [Propose new reference](https://github.com/SOLVE-IT-DF/solve-it/issues/new?template=1d_propose-new-reference-form.yml) form.

