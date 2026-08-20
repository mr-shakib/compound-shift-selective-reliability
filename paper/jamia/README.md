# JAMIA submission build

The JAMIA-formatted manuscript, kept separate from the full-length draft.

- **This build:** `main_jamia.tex` → JAMIA *Research and Applications*
- **Full-length draft:** `../main.tex` — venue-neutral, **do not compress it**
- **Venue decision:** [`../../docs/VENUE_SELECTION_PLAN.md`](../../docs/VENUE_SELECTION_PLAN.md)

```bash
cd paper/jamia
latexmk -pdf main_jamia.tex   # build
./budget.sh                   # check against every JAMIA limit
```

## Why two builds

`../main.tex` stays at full length on purpose. Compression to 4,000 words cuts
more than half the body, and the material that comes out has to go into the
supplement rather than be lost. The full-length draft is the supplement's source
text, so it has to survive intact. Compression happens **here**, in
`jamia/sections/`, which holds its own copies.

The two builds share `../figures/` and `../references.bib`, so a regenerated
figure or a new reference is picked up by both without copying.

## What JAMIA requires

Verified against the [JAMIA General
Instructions](https://academic.oup.com/jamia/pages/General_Instructions),
Research and Applications article type.

| Requirement | Limit |
|---|---|
| Body (Background → Conclusion) | 4,000 words |
| Structured abstract | 250 words, five named headings |
| Tables | 4 |
| Figures | 6 |
| References | unlimited |
| Layout | double-spaced, line-numbered |
| Submission format | Word, or LaTeX with a compiled PDF |

> **Not JAMIA Open.** That is a different journal with tighter limits (2,000
> words, 150-word abstract). Guidance found by search often conflates the two.

JAMIA also mandates the section structure, which is why this build is a
restructure and not just a preamble swap:

| `../sections/` (venue-neutral) | `jamia/sections/` (JAMIA) |
|---|---|
| Introduction + Related work | `01_background` — **Background and Significance** |
| *(stated across the introduction)* | `02_objective` — **Objective** *(new)* |
| Methods | `03_materials_methods` — **Materials and Methods** |
| Results | `04_results` — **Results** |
| Discussion + Limitations | `05_discussion` — **Discussion** *(Limitations folded in)* |
| *(draft ends on Future work)* | `06_conclusion` — **Conclusion** *(new)* |

`02_objective.tex` and `06_conclusion.tex` are written for this build; JAMIA
requires a section matching each abstract heading and the venue-neutral draft
has neither.

## Status

The format shell is complete and builds clean. The abstract is final at 250
words. **The body is not yet compressed.**

Run `./budget.sh` for live numbers. At the time of writing:

| | Have | Limit | Gap |
|---|---:|---:|---|
| Body words | 8,720 | 4,000 | cut 4,720 |
| Abstract | 250 | 250 | ✅ |
| Tables | 13 | 4 | move or convert 9 |
| Figures | 3 | 6 | 3 spare |
| Placeholders | 13 | 0 | title page + statements |

### Outstanding

1. **Decide the display set before compressing prose.** The figure budget is
   underused while the table budget is over by more than three times, so
   converting dense tables to figures is the cheapest route to compliance. The
   four H-contrast tables are six numbers each and would read better as one
   forest plot. What survives here determines what compressed Results can say,
   so this decision comes first.
2. **Compress the body by 4,720 words.** Discussion (2,962) and Materials and
   Methods (1,801) are the sources. Results (1,876) carries the confirmatory
   contrasts, the S1 reversal and the label-commensurability finding, and should
   be protected. The seed replicate and threshold sensitivity read naturally as
   supplement with a one-line summary left behind.
3. **Merge the two Limitations subsections.** Folding `06_limitations.tex` into
   the Discussion left it adjacent to the draft's existing "Limitations bearing
   on interpretation". They are deliberately next to each other; merge during
   compression.
4. **Fill the 13 placeholders** — author degrees, department, corresponding
   author postal address and institutional email, ORCID iDs, body word count,
   and the Acknowledgments / CRediT / Funding / Conflicts / Data availability
   statements. The data availability statement is mandatory at JAMIA and is
   drafted; it needs the repository URL or DOI.
5. **Reference style.** JAMIA uses Vancouver with Medline journal
   abbreviations. `vancouver.bst` is not in this TeX Live install, so the build
   uses `unsrt` (numbered in citation order, which matches the ordering rule).
   Install `texlive-publishers` or check the 10 references by hand before
   submitting.
