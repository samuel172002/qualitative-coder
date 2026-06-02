# Saldaña's Qualitative Coding Framework — Reference

This document describes the theoretical basis for every coding method implemented in this project.

## The Author

Johnny Saldaña is a qualitative researcher and Professor Emeritus at Arizona State University's School of Film, Dance and Theatre. His book *The Coding Manual for Qualitative Researchers* (SAGE Publications, 2009) is the standard reference on qualitative coding. It profiles 29 coding methods organised into First Cycle and Second Cycle approaches. Saldaña advocates **pragmatic eclecticism** — choose the right tool for the right job, since every study is context-specific.

---

## Core Concept

A **code** is a word or short phrase that captures the meaning of a segment of qualitative data (interviews, field notes, documents). Coding is not labelling — it is analysis. The hierarchy:

```
Data → Codes → Categories → Themes/Concepts → Theory
```

- **Code** — a researcher-generated label: `SECURITY`, `STRUGGLING`, `"SURVIVAL"`
- **Category** — a group of related codes (e.g., codes `PUSHING`, `FIGHTING`, `SCRATCHING` → category "Physical Oppression")
- **Theme** — an outcome of coding expressed as a full sentence. `SECURITY` is a code; *"A false sense of security pervades the community"* is a theme.
- **Theory** — an integrated explanatory framework built from categories and themes

Coding is cyclical. First Cycle methods fracture data into coded segments. Second Cycle methods reassemble and elevate those codes into categories, themes, and theory.

---

## First Cycle Coding Methods

### Grammatical Methods

**Attribute Coding** — Logs metadata: participant demographics, date, setting, file format. Not interpretive; used for organising and filtering. Almost every study uses this. *(Not implemented — handled by file metadata.)*

**Magnitude Coding** — Adds intensity or frequency markers to existing codes: HIGH/MEDIUM/LOW, +/−, numerical scales. Always supplements another method. *(Partially implemented via EvaluationCoder polarity.)*

**Simultaneous Coding** — Applies two or more codes to the same data segment when meanings overlap. Used when data is complex and a single code would oversimplify. *(This tool applies multiple coders per segment by design.)*

---

### Elemental Methods

**Structural Coding** *(implemented: `structural`)* — Applies conceptual phrases tied to specific research questions. Acts as both a coding and categorising device. Good for semi-structured interviews across multiple participants.

> *Example:* RQ "How do teachers adapt?" → code `RQ1: ADAPTING TO MANDATES` applied to relevant segments.

**Descriptive Coding** *(implemented: `descriptive`)* — Assigns a noun or noun phrase summarising the *topic* of a passage. Answers "what is this about?" not "what does this mean?" The most basic inventory method.

> *Example:* field notes about fences and guard dogs → `SECURITY`

**In Vivo Coding** *(implemented: `in_vivo`)* — Uses the participant's exact words as codes, always in quotation marks. Prioritise words that are evocative, metaphorical, or capture insider meaning.

> Saldaña: *"In Vivo codes provide a crucial check on whether you have grasped what is significant."*
>
> *Example:* participant says *"that's not professional development — that's survival"* → `"SURVIVAL"`

**Process Coding** *(implemented: `process`)* — Uses gerunds (−ing words) exclusively to capture action. Both observable (`READING`, `LINING UP`) and conceptual (`STRUGGLING`, `NEGOTIATING`).

> Saldaña: processes can be *"strategic, routine, random, novel, automatic, and/or thoughtful."*

**Initial Coding** *(implemented: `initial`)* — Open-ended, unrestricted first pass (formerly "Open Coding" in grounded theory). Codes can be descriptive, in vivo, process-based, or conceptual. Code closely, almost line-by-line. The entry point for grounded theory studies.

---

### Affective Methods

**Emotion Coding** *(implemented: `emotion`)* — Labels emotions: explicit (stated) and inferred (subtextual). Use precise terms — not "happy" but `ELATION`, `CONTENTMENT`, `RELIEF`. If `ANGER` appears, look for the triggering emotion (`SHAME`, `FEAR`, `EMBARRASSMENT`). Note intensity when discernible.

**Values Coding** *(implemented: `values`)* — Codes values (`V:`), attitudes (`A:`), and beliefs (`B:`):

- **Value** — importance attributed to something: `V: PROFESSIONAL AUTONOMY`
- **Attitude** — how one thinks/feels about something: `A: ADMINISTRATION IS OUT OF TOUCH`
- **Belief** — part of a worldview including experience and opinion: `B: TEACHERS KNOW WHAT'S BEST`

**Versus Coding** *(implemented: `versus`)* — Identifies conflicts, tensions, and power dynamics using the format `X VS. Y`. Conflicts can be between people, groups, concepts, or ideologies.

> *Example:* `TEACHERS VS. ADMINISTRATION`, `INNOVATION VS. MANDATE`, `DESIRE VS. DUTY`

**Evaluation Coding** *(implemented: `evaluation`)* — Assigns judgments of merit or worth with polarity: `+` (positive), `−` (negative), `0` (mixed).

> *Example:* `+ PEER LEARNING: EFFECTIVE` or `- IMPLEMENTATION: POORLY PLANNED`

---

### Literary and Language Methods *(not implemented)*

**Dramaturgical Coding** — Treats social life as performance. Codes for: Objectives, Conflicts, Tactics, Attitudes, Emotions, Subtexts. Best for interview data exploring interpersonal dynamics.

**Motif Coding** — Applies symbolic folk-literature elements as codes. Best for narrative and autoethnographic data.

**Narrative Coding** — Applies literary structural elements: point of view, chronology, foreshadowing, turning points, metaphor.

**Verbal Exchange Coding** — Uses conversation types from phatic communion through dialogue. For interaction-focused studies.

---

### Exploratory Methods *(not implemented)*

**Holistic Coding** — Applies a single code to a large chunk of data. Expedient but risks superficiality. Best for getting a broad sense before detailed coding.

**Provisional Coding** — Starts with a researcher-generated list of codes from prior literature. Top-down starting point.

**Hypothesis Coding** — Applies predetermined codes to test a specific hypothesis.

---

## Second Cycle Coding Methods

Second Cycle methods operate on the output of First Cycle coding. They reorganise, synthesise, and elevate codes into categories, themes, and theory.

### Pattern Coding *(implemented)*

*(Miles & Huberman, 1994)* — Groups first-cycle codes into a smaller number of explanatory meta-codes. Pattern codes capture themes, causes/explanations, relationships, or theoretical constructs.

> *"Many pattern codes are captured in the form of metaphors where they can synthesize large blocks of data in a single trope."*

Typically produces 5–15 pattern codes. Caution: *"pattern codes are hunches — some pan out, but many do not."*

### Focused Coding *(implemented)*

*(Charmaz, 2006)* — Searches for the most frequent or significant initial codes to develop "the most salient categories." Requires decisions about which codes make the most analytic sense. Category names should use gerunds when possible to emphasise process. A streamlined alternative to Axial Coding.

### Axial Coding *(implemented)*

*(Strauss & Corbin, 1998)* — Reassembles data fractured during initial coding. The "axis" is a category with extended spokes. Relates categories to subcategories by specifying their:

- **Properties** — characteristics of the category
- **Dimensions** — the range along which properties vary

Uses the paradigm:

```
Conditions (causal, intervening, contextual)
    ↓
Actions / Interactions (routine or strategic responses)
    ↓
Consequences (outcomes)
```

This tells you *"if, when, how, and why"* something happens. Relationship types: causes, enables, constrains, is context for, leads to, strategy for.

### Theoretical Coding *(implemented)*

*(Glaser, 1978)* — Identifies one central/core category that integrates all other categories into a cohesive theory. The core category:

- Appears frequently and has clear explanatory power
- Relates meaningfully to all other categories
- Has implications for general theory

Produces a theoretical statement moving from the particular to the general.

> Saldaña warns: *"mere numeric frequency is not necessarily a reliable indicator of a core category"* — the In Vivo Code `"SURVIVAL"` appeared only four times in 20 months of data yet held summative power for the entire study.

Consider Glaser's **Six C's**: Causes, Contexts, Contingencies, Consequences, Covariances, Conditions.

---

## The Grounded Theory Coding Canon

Six methods form the core of grounded theory methodology:

```
In Vivo → Process → Initial → Focused → Axial → Theoretical
```

These progress from open fracturing of data through reassembly to theory generation.

---

## Analytic Memos

Saldaña insists coding and analytic memo writing are inseparable. A memo is a researcher's written reflection on codes, patterns, and emerging theory. Write memos whenever something strikes you.

> *"Stop whatever you're doing and write a memo immediately."*

Memos are how you "rise above the data." *(This tool generates `analysis_summary.json` as a structured analytic record.)*

---

## Practical Guidelines

- **Quantity benchmarks**: 80–100 codes → 15–20 categories → 5–7 concepts (Lichtman). Creswell suggests starting with 5–6 codes expanding to 25–30, then collapsing to 5–6 themes.
- **Recoding is expected**: *"Rarely will anyone get coding right the first time."*
- **Simultaneous coding** — applying 2+ methods to the same data is legitimate and often recommended.
- **Essential researcher qualities**: organisation, perseverance, tolerance of ambiguity, flexibility, creativity, ethics, and an extensive vocabulary.

---

## References

- Saldaña, J. (2009). *The Coding Manual for Qualitative Researchers*. SAGE Publications.
- Charmaz, K. (2006). *Constructing Grounded Theory*. SAGE Publications.
- Strauss, A., & Corbin, J. (1998). *Basics of Qualitative Research*. SAGE Publications.
- Glaser, B. G. (1978). *Theoretical Sensitivity*. Sociology Press.
- Miles, M. B., & Huberman, A. M. (1994). *Qualitative Data Analysis*. SAGE Publications.
