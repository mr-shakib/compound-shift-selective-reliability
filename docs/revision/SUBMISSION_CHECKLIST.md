# Submission checklist (Revision R1)

The revised manuscript is **not submission-ready**. Mandatory items below are
missing or need author decisions. Nothing in this list was filled in by
inference.

## Mandatory author input (placeholders in `paper/revision/main_revised.tex`)

- [ ] Ethics statement: the institutional determination (review/exemption)
      for secondary analysis of MIMIC-CXR-JPG and CheXpert Plus, and the data
      use agreements under which each author accessed the data.
- [ ] Funding statement.
- [ ] Competing-interests statement for each author.
- [ ] Author contributions (e.g. CRediT). The repository history does not
      establish individual roles; the second author was added on 2026-08-21.
- [ ] Public repository URL and archived release (e.g. Zenodo DOI); confirm
      that the GitHub remote is public and contains the revision.
- [ ] Corresponding author and contact details; ORCID iDs.
- [ ] Confirm the reviewed PDF ("c3e.pdf") is `paper/main.pdf`; two quoted
      statements were not found in any repository source (issue R-19).

## Scientific blockers to the central claim

- [ ] Expert adjudication (`EXPERT_ADJUDICATION_PROTOCOL.md`), or narrow the
      paper to the endpoint-dependence and within-site findings, as the
      revision currently does.
- [x] M2/M3 replicate: completed 2026-10-07 and folded into the manuscript
      (claims about M3's external context effect narrowed).
- [x] External C2 permutation (queue step 5): completed 2026-10-07 03:04
      and folded into the supplement; no conclusion depends on the donor draw.
- [ ] Decide whether to run one-image-per-study and concordant-study
      sensitivities (SAP), which need image-level inference.

## Housekeeping before submission

- [x] Venue chosen 2026-10-07: JAMIA (free to publish). JAMIA build made
      from the revision in `paper/jamia_r1/` and within all JAMIA limits; see
      `paper/jamia_r1/SUBMISSION_PACKAGE.md` for the upload list and the
      remaining author inputs.
- [ ] Do not submit `paper/jamia/` or `paper/npjdm/`. Both carry superseded
      conclusions, and npj's abstract claims that recalibration "erased" the
      failure, which no analysis supports.
- [ ] Update `AGENTS.md` "Current authorization" to record the R1 work: the
      revision fitted exploratory comparator scores on the calibration tier
      and retrained M2 on the model-train tier, at the author's request in
      this session.
- [ ] Update `paper/supplement/` (TRIPOD+AI checklist) page references to the
      revised manuscript.
- [ ] Journal formatting, word limits and display-item limits.
- [ ] Commit through the safety gate (`docs/PROVENANCE_AND_VERSIONING_POLICY.md`),
      with an explicit allowlist.
