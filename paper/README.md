# C3E paper source

Venue-neutral LaTeX. The target journal is deliberately not chosen yet: it
should follow the finding rather than precede it. Swap the `documentclass` and
preamble in `main.tex` once a venue is fixed; the files under `sections/` should
need no edits.

## Build

```bash
sudo apt install texlive-latex-recommended texlive-latex-extra \
                 texlive-science texlive-fonts-recommended latexmk
make
```

## Drafting rule

Sections marked with `\pending{}` render as a visible red box and must not be
drafted before the confirmatory analysis exists. That covers the abstract,
Results and Discussion. The rule is not bureaucratic: a narrative written
against point estimates tends to survive into the final text after the
intervals disagree with it.

Everything else -- Introduction, Related Work, Methods, Limitations -- is
result-independent and is drafted.

## Citation rule

`references.bib` mirrors `docs/closest_work.csv`. No entry may be added without
verifying the paper against its official page first, per
`docs/closest_work_README.md`. One candidate (CW08) is unverified because
medRxiv refuses automated retrieval; it is absent from the bibliography and
uncited, and must be checked manually before submission.
