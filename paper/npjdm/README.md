# npj Digital Medicine submission build

The primary target. Formatted as an npj **Article**.

- **This build:** `main_npjdm.tex`
- **Fallback build:** [`../jamia/`](../jamia/) — JAMIA Research and Applications
- **Full-length draft:** [`../main.tex`](../main.tex) — venue-neutral, **never compressed**
- **Venue decision:** [`../../docs/VENUE_SELECTION_PLAN.md`](../../docs/VENUE_SELECTION_PLAN.md)

```bash
cd paper/npjdm
latexmk -pdf main_npjdm.tex   # build
./budget.sh                   # check against every npj limit
```

## Why this is the primary target

Roughly double JAMIA's impact factor, and the venue the original plan named the
closest scope match before ruling it out on cost alone. npj Digital Medicine has
published four papers in this paper's direct lineage:

- *Distribution shift detection for the postmarket surveillance of medical AI
  algorithms: **a retrospective simulation study*** (2024) — the study shape
  Nature Medicine explicitly excludes, published here as routine.
- *Evaluating deep learning sepsis prediction models in ICUs under distribution
  shift: a multi-centre retrospective cohort study* (2026) — compares
  generalization against retraining and fine-tuning across three cohorts.
- *Generalization — a key challenge for responsible AI in patient-facing
  clinical applications* (2024) — selective prediction and deferral when models
  do not generalize.
- *Recalibration of deep learning models for abnormality detection in chest
  radiograph* (2021) — **MIMIC-CXR → CheXpert transfer, repaired by
  recalibration.**

That last one is the argument for the cover letter. This paper's central claim
is that re-calibrating at the receiving site *conceals* a transport failure
rather than repairing it, which complicates a result this journal published.

## What npj requires

From the [official npj submission
guide](https://www.nature.com/documents/npj-submission-guide.pdf), Article type.

| Requirement | Limit |
|---|---|
| Main text | 5,000 words |
| Methods | **counted separately**; typically ≤3,000, "may be longer if necessary" |
| Abstract | ~150 words, **unstructured**, unreferenced |
| Display items | **10 combined** (figures + tables), not 4 + 6 |
| References | usually up to 70 |
| Title | ≤15 words, no punctuation, no abbreviations, no active verbs |
| Headings | *"Avoid 'Introduction' as a heading"*; subheadings mainly in Results |

**The Methods exclusion is the whole story.** JAMIA counts everything against
4,000 words; npj counts 5,000 for the main text and puts Methods outside it.
That turns a 4,720-word cut into a 1,329-word one.

### Structure differs from JAMIA, so the two builds cannot share files

| JAMIA build | npj build |
|---|---|
| Background and Significance | *(unheaded opening — no heading permitted)* |
| Objective | folded into the opening |
| Materials and Methods *(early)* | **Methods — moved to the end**, after Discussion |
| Results | Results |
| Discussion | Discussion *(absorbs Limitations and the Conclusion prose)* |
| Conclusion | *(no such heading in Nature style; Discussion closes on it)* |
| — | **Data Availability** — own section, after Methods, before References |
| — | **Code availability** — inside Methods, under that exact heading |

The related-work subsections became run-in `\paragraph` headings, since npj
confines subheadings mainly to Results. They should dissolve into prose during
compression.

### Title

The question-form title used by the other two builds is not permissible here —
17 words, a question mark, and an active verb, against npj's ≤15 words with no
punctuation and no active verbs. Recast as a noun phrase, 13 words:

> Non-transport of a frozen multimodal selective-prediction policy across
> hospitals under compound context shift

An alternative giving both findings equal billing is noted in `main_npjdm.tex`:
*"Label dependence and non-transport of frozen selective-prediction policies
across hospitals"* (10 words).

## Status

Builds clean at 26 pages. Abstract final at 148 words. Title compliant.

| | Have | Limit | Gap |
|---|---:|---:|---|
| Abstract | 148 | 150 | ✅ |
| Title words | 13 | 15 | ✅ |
| References | 10 | 70 | ✅ |
| Methods | 1,867 | 3,000 | ✅ **1,133 spare** |
| Main text | 6,329 | 5,000 | cut 1,329 |
| Display items | 16 | 10 | remove 6 |
| Placeholders | 7 | 0 | — |

### Outstanding

1. **Cut 1,329 words of main text.** Discussion (2,962) is the obvious source;
   it currently carries the whole of Limitations plus the Conclusion prose.
   Results (1,876) should be protected. The opening (1,491) can lose the
   related-work paragraph headings by dissolving them into prose.
2. **Reduce 16 display items to 10.** The limit is combined here, so converting
   tables to figures does *not* help the way it does at JAMIA — six items have to
   leave. The four H-contrast tables are candidates for one forest plot, which
   is a net saving of three.
3. **Methods has 1,133 words of headroom.** Material cut from the main text can
   move *into* Methods rather than to the supplement, if it is methodological.
   This is the cheapest place to put detail the JAMIA build would have had to
   discard.
4. **Merge the two Limitations subsections**, as in the JAMIA build.
5. **Fill 7 placeholders** — department, corresponding-author institutional
   email, repository URL/DOI (twice), author contributions, competing interests,
   acknowledgements.
6. **Request the APC waiver at submission.** Springer Nature grants
   case-by-case waivers on financial need, separate from the country list that
   excludes Bangladesh. It must be requested *at submission* and cannot be
   considered afterwards.
7. **Reference style** — npj uses Nature style; the build uses `unsrt`
   (numbered in order of appearance, which matches). Check the 10 entries by
   hand before submitting.
