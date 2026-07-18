# Closest-Work Tracking — README

This file explains how to use `closest_work.csv`, the running log of prior work most relevant to the
C3-E research question:

> Does the selective reliability of a multimodal chest-X-ray classifier survive when pre-diagnostic
> clinical context becomes missing and the model is transferred to another hospital?

## Verification rule

**Every paper entered into `closest_work.csv` must be verified against the full paper or the official
publication page** (journal/conference page, arXiv abstract + PDF, or official project page). Do not
rely on secondhand summaries, search-result snippets, citation lists, or model recollection. If a
paper cannot be directly inspected, mark `verification_status` as `unverified` and do not fill in
substantive claims (dataset, modalities, contribution, etc.) beyond what is stated on the page you
actually viewed.

No paper's title, authors, dataset, or findings may be fabricated or guessed. Leave a field blank
rather than inferring it.

## Required questions for every candidate paper

For each paper being logged, answer all of the following before filling in `closest_work.csv`:

1. Does the paper use chest X-rays plus pre-diagnostic clinical history?
2. Does it test an external hospital (true cross-institution evaluation, not just a held-out split of
   the same source)?
3. Does it study natural or synthetic context missingness (i.e., clinical history/indication absent or
   degraded)?
4. Does it evaluate selective prediction or abstention (rejecting low-confidence predictions rather
   than forcing a decision)?
5. Does it test whether uncertainty rankings transfer across institutions?
6. Does it audit target leakage from clinical text (i.e., whether the diagnosis is directly named in
   the history/indication text used as input)?
7. Does it report class-specific or worst-group selective risk (not just aggregate accuracy/AUC)?
8. Does it directly solve our complete proposed intersection (all of the above simultaneously)?

## Blank checklist template

Copy this block for each paper reviewed, fill it in, and keep the answers consistent with the row
added to `closest_work.csv`.

```
### Paper: <title>

- Verified from: <full paper / official publication page URL or DOI actually viewed>
- Verification date: <YYYY-MM-DD>

1. Chest X-ray + pre-diagnostic clinical history?      [ ] Yes  [ ] No  [ ] Unclear
2. External hospital tested?                            [ ] Yes  [ ] No  [ ] Unclear
3. Natural or synthetic context missingness studied?     [ ] Yes  [ ] No  [ ] Unclear
4. Selective prediction / abstention evaluated?          [ ] Yes  [ ] No  [ ] Unclear
5. Uncertainty-ranking transfer across institutions?      [ ] Yes  [ ] No  [ ] Unclear
6. Target leakage from clinical text audited?            [ ] Yes  [ ] No  [ ] Unclear
7. Class-specific / worst-group selective risk reported? [ ] Yes  [ ] No  [ ] Unclear
8. Solves the full proposed intersection directly?       [ ] Yes  [ ] No  [ ] Unclear

Notes:
- <free-text notes, direct quotes with page/section reference, caveats>
```

## Columns in `closest_work.csv`

- `paper_id` — short stable identifier you assign (e.g., `smith2023`)
- `title`, `authors`, `year`, `venue` — bibliographic fields, copied verbatim from the verified source
- `url_or_doi` — the exact link used for verification
- `dataset`, `modalities` — what data/modalities the paper actually uses
- `external_validation`, `missing_modality`, `missingness_mechanism`, `institution_shift`,
  `selective_prediction`, `calibration` — short factual answers tied to questions 1–7 above
- `main_contribution` — one-sentence factual summary, not an opinion
- `direct_threat` — does this paper substantially anticipate our proposed contribution? (yes/no/partial + why)
- `remaining_gap` — what this paper does *not* cover relative to our proposed intersection
- `verification_status` — `verified` (checked against full paper/official page) or `unverified`
- `notes` — anything else relevant, with citations to specific sections/pages

Do not add a row until the checklist above has been completed for that paper.
