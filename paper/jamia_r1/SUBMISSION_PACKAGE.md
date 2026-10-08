# JAMIA submission package (Revision R1)

Target: **Journal of the American Medical Informatics Association (JAMIA)**,
article type **Research and Applications**. Submission is free on the
subscription route (no submission, page or colour charges); open access would
cost an article fee and is optional. JAMIA allows preprints, so posting to
medRxiv or arXiv makes the paper free to read without paying for open access.

Requirements were checked against the
[JAMIA General Instructions](https://academic.oup.com/jamia/pages/General_Instructions)
on 2026-10-07, and re-checked the same day. The re-check moved the figure
legends to the end, switched citations to brackets after punctuation, put the
reference list in JAMIA style, and fixed the tables where first cited.

## Compliance (`python3 budget.py`, run by `./build.sh`)

| Requirement | JAMIA rule | This build |
|---|---|---|
| Body words (Background → Conclusion) | ≤ 4,000 | **3,135** |
| Structured abstract (Objective, Materials and Methods, Results, Discussion, Conclusion) | ≤ 250 words | **232** |
| Tables | ≤ 4, in the main text where first cited | **4**, fixed in place |
| Figures | ≤ 6, uploaded as separate files; legends at the end of the manuscript; alt text directly under each legend, preceded by "Alt text:" | **5**; legends and alt text on the last pages; files in `figures_for_upload/` |
| Title page | title; all authors' full names, degrees, department, institution, city, country; corresponding author's postal address, email and telephone; ≤ 5 keywords (MeSH); word count | yes |
| Citations | numbered in order of citation, in square brackets immediately after punctuation (`text.[6]`), `[1, 4, 39]`, `[22-25]` | yes |
| Reference list | all authors if ≤ 3, else first 3 + "et al."; italic Medline journal abbreviation; `Journal Year;Vol:pages.`; datasets as `[dataset] Authors, Year, Title, Publisher, Identifier` | yes (19 references, including the Zenodo archive) |
| Spacing | double | yes (line numbers added for reviewers) |
| Required sections | Background and Significance, then sections matching the abstract headings | yes |
| Data availability statement | required | yes |
| CRediT contributions | required at submission | yes |
| AI-use disclosure | cover letter and Methods or Acknowledgments | yes, in both |
| File format | Word, or a PDF compiled from LaTeX | PDF compiled from LaTeX, with source |

## Files to upload

| JAMIA file designation | File |
|---|---|
| Manuscript (PDF compiled from LaTeX) | `main_jamia_r1.pdf` |
| LaTeX source | `source_for_upload/main_jamia_r1.tex`: one self-contained file (sections, numbers, tables and bibliography inlined) that compiles alone with pdflatex to the same text as the PDF |
| Figures (separate files) | `figures_for_upload/Figure1–5.pdf` (vector) or `.png` (600 dpi) |
| Supplementary File | `supplement_jamia_r1.pdf` |
| Supplementary File (reporting checklist) | `tripod_ai_checklist_r1.pdf` |
| Cover letter | `cover_letter.pdf` |

Upload the figures in the order in which they are cited:

1. Label composition
2. H1 across specifications
3. Operating points
4. Risk–coverage
5. Within-site H4

As JAMIA asks, the manuscript PDF does not embed the figures. Their legends,
each followed by its alt text, are on the last pages. If the system also asks
for alt text in a form field, copy it from there.

## Metadata to paste into the submission system

- **Title:** Frozen selective prediction for multimodal chest-radiograph
  models across two hospitals: a preregistered compound-shift evaluation with
  label-dependent cross-site conclusions
- **Keywords (MeSH):** Radiography, Thoracic; Machine Learning; Diagnosis,
  Computer-Assisted; Data Accuracy; Reproducibility of Results
- **Abstract:** copy from page 2 of `main_jamia_r1.pdf`. The five headings are
  already in place.

## What only you can supply

Supplied by the author on 2026-10-07 and filled in:
- degrees, department, address, email, telephone and ORCID iDs;
- ethics: PhysioNet credentialing, with no additional institutional review;
- funding (none) and competing interests (none);
- CRediT roles;
- AI use: ChatGPT, including its Codex agent, and Claude, with no row-level
  data entered;
- the repository URL and Zenodo DOI 10.5281/zenodo.23213133 (v1.0.0);
- no prior submission, no preprint and no related papers;
- Adnan Rahman Sayeem's approval.

The supervisor, Shahadat Hossain, was added as third author on 2026-10-07. His
degree (MSc) and ORCID (0000-0003-4545-2898) were taken from his public ORCID
record, which lists Assistant Professor, CSE, Daffodil International
University; confirm both with him.

The telephone number lives in `private_phone.tex`, which is gitignored so it
never reaches the public repository.

## Authorship (ICMJE criteria, which JAMIA follows)

Every author needs four things:
- a substantive contribution to the design, the analysis or the
  interpretation;
- critical revision of the manuscript;
- approval of the final version;
- accountability for the work.

Supervision alone, or language editing alone, does not qualify. Each
co-author therefore has a real task before submission:

- **Adnan Rahman Sayeem** (Validation; Writing -- review & editing) works
  through `VERIFY.md`:
  - reproduce the tests and every generated number from the public
    repository, which needs no credentialed data;
  - trace ten headline claims to the results files;
  - critically review the interpretation, and return a written note.
- **Shahadat Hossain** (Supervision; Writing -- review & editing):
  - critically reviews the design and interpretation, and returns written
    comments;
  - approves the final version;
  - confirms that he has no competing interests.

  Add Conceptualization or Methodology to his roles only if he actually
  shaped those.

**Completed (confirmed by the corresponding author on 2026-10-09):**
- Adnan Rahman Sayeem returned the `VERIFY.md` check with no mismatches.
- Shahadat Hossain reviewed and approved the manuscript.

No `[AUTHOR INPUT REQUIRED]` markers remain in any file.

## Verification items (resolved 2026-10-09)

- **Aperstein et al.:**
  - Now cited as the *Scientific Reports* version (published online
    24 Aug 2026), verified through Crossref.
  - Crossref has not yet assigned a volume or article number. Add them if they
    appear before you submit.
  - The journal version adds cross-dataset and leave-one-dataset-out
    evaluation. Background and the full-length related work were corrected:
    they had described the work as within-dataset only, which was true only of
    the preprint.
  - The novelty statement is unaffected. That study is image-only, does not
    manipulate clinical context and is not preregistered.
- **MIMIC-CXR release:** confirmed as v2.1.0.
  - The local `SHA256SUMS.txt` lists `cxr-provider-list.csv.gz`, which v2.1.0
    added (release notes, 23 Jul 2024).
  - `mimic-cxr-reports.zip` and the provider list both match that manifest.
- **Preprints still cited:** two, the MIMIC-CXR-JPG and CheXpert Plus
  descriptor papers. Both are the required dataset citations, and no journal
  version exists for either.

## Rebuild

```bash
cd <project root>/paper/jamia_r1
./build.sh          # budget → supplement → manuscript → checklist → cover letter → figure files
```

Every number in the manuscript is generated by `python -m c3e.revision.report`
from `results/c3e_revision/`. To change a number, change the analysis, not the
text.
